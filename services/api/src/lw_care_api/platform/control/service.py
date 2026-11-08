"""Current authority, immutable decisions and encrypted command receipts."""

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text
from starlette.concurrency import run_in_threadpool

from .. import db
from ..domain import require
from ..security import accept_totp, verify_password
from . import tables as t


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def later(minutes):
    return (datetime.now(UTC) + timedelta(minutes=minutes)).isoformat(timespec="microseconds")


def has(actor, roles, facility_id=None):
    return bool(actor) and any(
        g["role"] in roles
        and (
            g["scope_type"] == "GLOBAL"
            or (facility_id and g["scope_type"] == "FACILITY" and g["scope_id"] == str(facility_id))
        )
        for g in actor["grants"]
    )


async def load(session, table, identifier, *, lock=False):
    query = select(table).where(table.c.id == str(identifier))
    row = (await session.execute(query.with_for_update() if lock else query)).mappings().first()
    require(row, "NOT_FOUND_OR_NOT_PERMITTED", "Control record unavailable", 404)
    return dict(row)


async def serial(session, database):
    if database.postgres:
        await session.execute(text("SELECT pg_advisory_xact_lock(782025012)"))


class ControlService:
    def __init__(self, session, cfg, box, actor, correlation):
        self.session, self.cfg, self.box, self.actor, self.correlation = (
            session,
            cfg,
            box,
            actor,
            correlation,
        )

    async def audit(self, action, resource=None, *, outcome="SUCCESS", details=None):
        await self.session.execute(
            t.audit.insert().values(
                id=db.uid(),
                actor_id=self.actor["id"] if self.actor else None,
                action=action,
                resource_id=resource,
                outcome=outcome,
                details=details,
                correlation_id=self.correlation,
                created_at=db.now(),
            )
        )

    async def factor(self, body):
        require(self.actor, "AUTH_REQUIRED", "Sign in to continue", 401)
        account = (
            (
                await self.session.execute(
                    select(db.accounts)
                    .where(db.accounts.c.id == self.actor["id"])
                    .with_for_update()
                )
            )
            .mappings()
            .one()
        )
        correct = await run_in_threadpool(
            verify_password, body["password"], account["password_hash"]
        )
        require(
            correct and await accept_totp(self.session, dict(account), body["otp"], self.box),
            "AUTH_REQUIRED",
            "Confirm your current password and a fresh authenticator code",
            401,
        )

    async def security(self, account_id):
        row = (
            (
                await self.session.execute(
                    select(t.account_security)
                    .where(t.account_security.c.account_id == account_id)
                    .with_for_update()
                )
            )
            .mappings()
            .first()
        )
        if row:
            return dict(row)
        row = {
            "account_id": account_id,
            "credential_epoch": 0,
            "recovery_set_id": None,
            "updated_at": db.now(),
        }
        await self.session.execute(t.account_security.insert().values(**row))
        return row

    async def idempotent(self, operation, key, body, callback):
        require(
            key and 8 <= len(key) <= 160,
            "VALIDATION_FAILED",
            "A durable Idempotency-Key is required",
            422,
        )
        signature = hmac.new(
            bytes.fromhex(self.cfg.data_key_hex), canonical(body).encode(), hashlib.sha256
        ).hexdigest()
        row = (
            (
                await self.session.execute(
                    select(t.receipts).where(
                        t.receipts.c.actor_id == self.actor["id"],
                        t.receipts.c.operation == operation,
                        t.receipts.c.key == key,
                    )
                )
            )
            .mappings()
            .first()
        )
        if row:
            require(
                row["request_hash"] == signature,
                "IDEMPOTENCY_KEY_REUSE",
                "This operation key was used for different input",
                409,
            )
            require(
                row["expires_at"] > db.now(),
                "RECEIPT_EXPIRED",
                "Reload the current record before submitting a new operation",
                409,
            )
            return json.loads(self.box.decrypt(row["response_ciphertext"]))
        result = await callback()
        await self.session.execute(
            t.receipts.insert().values(
                id=db.uid(),
                actor_id=self.actor["id"],
                operation=operation,
                key=key,
                request_hash=signature,
                response_ciphertext=self.box.encrypt(canonical(result)),
                expires_at=later(5 if operation.endswith("recovery-codes") else 1440),
            )
        )
        return result

    async def package_state(self, row):
        reviews = [
            dict(r)
            for r in (
                await self.session.execute(
                    select(t.package_reviews).where(t.package_reviews.c.package_id == row["id"])
                )
            ).mappings()
        ]
        required = {"TECHNICAL", "CLINICAL", "PRIVACY"}
        if row["payload"].get("financial_policy_reference"):
            required.add("FINANCE")
        withdrawn = await self.session.scalar(
            select(t.revocations.c.id).where(t.revocations.c.package_id == row["id"])
        )
        approved = {r["review_kind"] for r in reviews if r["decision"] == "APPROVE"}
        state = (
            "REVOKED"
            if withdrawn
            else "REJECTED"
            if any(r["decision"] == "REJECT" for r in reviews)
            else "ADOPTED"
            if required <= approved
            else "AWAITING_REVIEW"
        )
        if (
            state == "ADOPTED"
            and not row["payload"]["valid_from"] <= db.now() < row["payload"]["valid_until"]
        ):
            state = "NOT_CURRENT"
        return {
            "state": state,
            "required_reviews": sorted(required),
            "completed_reviews": [
                {k: r[k] for k in ("id", "review_kind", "reviewer_id", "decision", "created_at")}
                for r in reviews
            ],
        }

    async def policy_package(self, body):
        require(
            has(
                self.actor,
                {"PLATFORM_ADMIN", "CLINICAL_GOVERNOR", "PRIVACY_OFFICER", "FINANCE_GOVERNOR"},
                body.get("facility_id"),
            )
        )
        if body.get("facility_id"):
            facility = await load(self.session, db.facilities, body["facility_id"])
            require(
                facility["jurisdiction"] == body["jurisdiction"],
                "JURISDICTION_MISMATCH",
                "Use the actual facility jurisdiction",
                422,
            )
        else:
            require(
                has(
                    self.actor,
                    {"PLATFORM_ADMIN", "CLINICAL_GOVERNOR", "PRIVACY_OFFICER", "FINANCE_GOVERNOR"},
                )
            )
        row = {
            "id": db.uid(),
            "name": body["name"],
            "package_version": body["package_version"],
            "jurisdiction": body["jurisdiction"],
            "facility_id": body.get("facility_id"),
            "payload": body,
            "payload_hash": digest(body),
            "created_by": self.actor["id"],
            "created_at": db.now(),
        }
        await self.session.execute(t.packages.insert().values(**row))
        await self.audit("activation.package_proposed", row["id"])
        return row | await self.package_state(row)

    async def package_review(self, identifier, body):
        row = await load(self.session, t.packages, identifier)
        role = {
            "TECHNICAL": "PLATFORM_ADMIN",
            "CLINICAL": "CLINICAL_GOVERNOR",
            "PRIVACY": "PRIVACY_OFFICER",
            "FINANCE": "FINANCE_GOVERNOR",
        }[body["review_kind"]]
        require(has(self.actor, {role}, row["facility_id"]))
        require(
            row["created_by"] != self.actor["id"],
            "INDEPENDENT_REVIEW_REQUIRED",
            "The proposer cannot approve their own activation package",
            403,
        )
        state = await self.package_state(row)
        require(
            state["state"] == "AWAITING_REVIEW",
            "INVALID_STATE",
            "This package is not awaiting review",
            409,
        )
        require(
            body["review_kind"] in state["required_reviews"],
            "UNEXPECTED_REVIEW",
            "This review is not required for this package",
            422,
        )
        await self.session.execute(
            t.package_reviews.insert().values(
                id=db.uid(),
                package_id=identifier,
                review_kind=body["review_kind"],
                reviewer_id=self.actor["id"],
                decision=body["decision"],
                evidence_ciphertext=self.box.encrypt(body["evidence"]),
                created_at=db.now(),
            )
        )
        await self.audit(
            "activation.package_reviewed",
            identifier,
            details={"kind": body["review_kind"], "decision": body["decision"]},
        )
        return {"id": identifier, **await self.package_state(row)}

    async def revoke_package(self, identifier, body):
        row = await load(self.session, t.packages, identifier)
        require(
            has(
                self.actor,
                {"PLATFORM_ADMIN", "CLINICAL_GOVERNOR", "PRIVACY_OFFICER", "FINANCE_GOVERNOR"},
                row["facility_id"],
            )
        )
        await self.session.execute(
            t.revocations.insert().values(
                id=db.uid(),
                package_id=identifier,
                actor_id=self.actor["id"],
                reason=body["evidence"],
                created_at=db.now(),
            )
        )
        await self.audit("activation.package_revoked", identifier)
        return {"id": identifier, **await self.package_state(row)}


async def validate_activation(session, cfg, box, actor, facility, body):
    require(
        body.get("activation_package_id"),
        "ACTIVATION_DOSSIER_REQUIRED",
        "A current independently reviewed country/service activation package is required",
        409,
    )
    service = ControlService(session, cfg, box, actor, "activation")
    row = await load(session, t.packages, body["activation_package_id"])
    require(
        (await service.package_state(row))["state"] == "ADOPTED",
        "ACTIVATION_PACKAGE_UNAVAILABLE",
        "Activation reviews, validity or withdrawal prevent this activation",
        403,
    )
    require(
        row["jurisdiction"] == facility["jurisdiction"]
        and row["facility_id"] in {None, facility["id"]},
        "ACTIVATION_SCOPE_MISMATCH",
        "Package scope does not match the facility",
        403,
    )
    require(
        set(body["services"]) <= set(row["payload"]["services"]),
        "ACTIVATION_SCOPE_MISMATCH",
        "Requested services exceed the reviewed package",
        403,
    )
    require(
        row["payload"]["valid_from"]
        <= body["valid_from"]
        < body["valid_until"]
        <= row["payload"]["valid_until"],
        "ACTIVATION_VALIDITY_MISMATCH",
        "Facility validity must remain within its reviewed package",
        422,
    )
    return row
