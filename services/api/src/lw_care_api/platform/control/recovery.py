"""Email plus independent proof recovery; accounts and professional grants stay distinct."""

import secrets

import pyotp
from sqlalchemy import select, update
from starlette.concurrency import run_in_threadpool

from .. import db
from ..domain import require
from ..security import accept_totp, digest, hash_password, issue_session, verify_password
from . import tables as t
from .service import ControlService, has, later


class RecoveryService(ControlService):
    async def codes(self, body):
        await self.factor(body)
        security = await self.security(self.actor["id"])
        set_id = db.uid()
        values = [secrets.token_hex(20) for _ in range(10)]
        for code in values:
            await self.session.execute(
                t.backup_codes.insert().values(
                    id=db.uid(),
                    account_id=self.actor["id"],
                    set_id=set_id,
                    code_hash=digest(self.actor["id"] + ":" + code),
                    used_at=None,
                    created_at=db.now(),
                )
            )
        await self.session.execute(
            update(t.account_security)
            .where(t.account_security.c.account_id == security["account_id"])
            .values(recovery_set_id=set_id, updated_at=db.now())
        )
        await self.audit("identity.recovery_codes_rotated", self.actor["id"])
        return {
            "id": set_id,
            "codes": values,
            "created_at": db.now(),
            "instruction": "Keep these one-use codes securely. Previous sets are no longer valid.",
        }

    async def consume_code(self, account_id, code, security):
        result = await self.session.execute(
            update(t.backup_codes)
            .where(
                t.backup_codes.c.account_id == account_id,
                t.backup_codes.c.set_id == security["recovery_set_id"],
                t.backup_codes.c.code_hash == digest(account_id + ":" + code),
                t.backup_codes.c.used_at.is_(None),
            )
            .values(used_at=db.now())
        )
        return result.rowcount == 1

    async def request_recovery(self, body):
        require(
            self.cfg.resend_api_key and self.cfg.email_from,
            "AUTHORITY_UNAVAILABLE",
            "Account email delivery is unavailable",
            503,
        )
        account = (
            (
                await self.session.execute(
                    select(db.accounts).where(
                        db.accounts.c.email == body["email"].lower(), db.accounts.c.active.is_(True)
                    )
                )
            )
            .mappings()
            .first()
        )
        if account:
            existing = await self.session.scalar(
                select(t.recoveries.c.id).where(
                    t.recoveries.c.account_id == account["id"],
                    t.recoveries.c.expires_at > db.now(),
                    t.recoveries.c.state.not_in(["COMPLETED", "REJECTED", "CANCELLED"]),
                )
            )
            if not existing:
                security = await self.security(account["id"])
                raw = secrets.token_urlsafe(48)
                identifier = db.uid()
                await self.session.execute(
                    t.recoveries.insert().values(
                        id=identifier,
                        account_id=account["id"],
                        token_hash=digest(raw),
                        credential_epoch=security["credential_epoch"],
                        state="EMAIL_PENDING",
                        proof_method=None,
                        email_proved_at=None,
                        expires_at=later(60),
                        pending_password_hash=None,
                        pending_totp_ciphertext=None,
                        created_at=db.now(),
                        completed_at=None,
                    )
                )
                from .jobs import enqueue

                self.delivery_job_id = await enqueue(
                    self.session,
                    self.box,
                    "RECOVERY_EMAIL",
                    "recovery:" + identifier,
                    {"recovery_id": identifier, "account_id": account["id"], "token": raw},
                    owner_id=account["id"],
                )
                await self.audit("identity.recovery_requested", identifier)
            else:
                self.delivery_job_id = await self.session.scalar(
                    select(t.jobs.c.id).where(t.jobs.c.effect_key == "recovery:" + existing)
                )
        return {
            "status": "REQUEST_RECEIVED",
            "instruction": "Recovery instructions are queued for the registered email of an eligible account. Check your authenticator or saved recovery codes.",
        }

    async def challenge(self, token):
        row = (
            (
                await self.session.execute(
                    select(t.recoveries)
                    .where(t.recoveries.c.token_hash == digest(token))
                    .with_for_update()
                )
            )
            .mappings()
            .first()
        )
        require(
            row
            and row["expires_at"] > db.now()
            and row["state"] not in {"COMPLETED", "REJECTED", "CANCELLED"},
            "AUTH_REQUIRED",
            "Recovery is invalid, used or expired",
            401,
        )
        security = await self.security(row["account_id"])
        account = (
            (
                await self.session.execute(
                    select(db.accounts)
                    .where(db.accounts.c.id == row["account_id"], db.accounts.c.active.is_(True))
                    .with_for_update()
                )
            )
            .mappings()
            .first()
        )
        require(
            account and security["credential_epoch"] == row["credential_epoch"],
            "AUTH_REQUIRED",
            "Account recovery authority has changed",
            401,
        )
        return dict(row), dict(account), security

    async def prove(self, body):
        row, account, security = await self.challenge(body["token"])
        if row["state"] != "EMAIL_PENDING":
            return {"status": row["state"], "expires_at": row["expires_at"]}
        method = body["method"]
        proved = method == "INDEPENDENT_REVIEW"
        if method == "AUTHENTICATOR":
            proved = await accept_totp(self.session, account, body["proof"], self.box)
        if method == "BACKUP_CODE":
            proved = await self.consume_code(account["id"], body["proof"], security)
        require(proved, "AUTH_REQUIRED", "The recovery proof could not be verified", 401)
        state = "REVIEW_REQUIRED" if method == "INDEPENDENT_REVIEW" else "AUTHORIZED"
        await self.session.execute(
            update(t.recoveries)
            .where(t.recoveries.c.id == row["id"])
            .values(state=state, proof_method=method, email_proved_at=db.now())
        )
        await self.audit(
            "identity.email_and_recovery_proof_recorded",
            row["id"],
            details={"method": method, "state": state},
        )
        return {
            "status": state,
            "expires_at": row["expires_at"],
            "review_requirement": "Two independent currently authorised identity reviewers"
            if state == "REVIEW_REQUIRED"
            else None,
        }

    async def review(self, identifier, body):
        require(has(self.actor, {"IDENTITY_REVIEWER"}))
        await self.factor(body)
        row = (
            (
                await self.session.execute(
                    select(t.recoveries).where(t.recoveries.c.id == identifier).with_for_update()
                )
            )
            .mappings()
            .first()
        )
        require(
            row and row["state"] == "REVIEW_REQUIRED" and row["expires_at"] > db.now(),
            "NOT_FOUND_OR_NOT_PERMITTED",
            "Current recovery review unavailable",
            404,
        )
        require(
            row["account_id"] != self.actor["id"],
            "INDEPENDENT_REVIEW_REQUIRED",
            "You cannot approve your own recovery",
            403,
        )
        await self.session.execute(
            t.recovery_reviews.insert().values(
                id=db.uid(),
                recovery_id=identifier,
                reviewer_id=self.actor["id"],
                decision=body["decision"],
                evidence_ciphertext=self.box.encrypt(body["evidence"]),
                created_at=db.now(),
            )
        )
        decisions = list(
            (
                await self.session.execute(
                    select(t.recovery_reviews.c.decision).where(
                        t.recovery_reviews.c.recovery_id == identifier
                    )
                )
            ).scalars()
        )
        state = (
            "REJECTED"
            if "REJECT" in decisions
            else "AUTHORIZED"
            if len(decisions) >= 2
            else "REVIEW_REQUIRED"
        )
        await self.session.execute(
            update(t.recoveries).where(t.recoveries.c.id == identifier).values(state=state)
        )
        await self.audit(
            "identity.recovery_reviewed",
            identifier,
            details={"decision": body["decision"], "state": state},
        )
        return {"id": identifier, "state": state, "independent_reviews": len(decisions)}

    async def setup(self, body):
        row, account, _ = await self.challenge(body["token"])
        require(
            row["state"] in {"AUTHORIZED", "ENROLLING"},
            "RECOVERY_REVIEW_REQUIRED",
            "Complete the required recovery proof and independent reviews first",
            409,
        )
        if row["state"] == "ENROLLING":
            require(
                await run_in_threadpool(
                    verify_password, body["password"], row["pending_password_hash"]
                ),
                "RECOVERY_ALREADY_PREPARED",
                "Use the same prepared password or request recovery again after expiry",
                409,
            )
            secret = self.box.decrypt(row["pending_totp_ciphertext"])
        else:
            secret = pyotp.random_base32()
            password_hash = await run_in_threadpool(hash_password, body["password"])
            await self.session.execute(
                update(t.recoveries)
                .where(t.recoveries.c.id == row["id"])
                .values(
                    state="ENROLLING",
                    pending_password_hash=password_hash,
                    pending_totp_ciphertext=self.box.encrypt(secret),
                )
            )
        await self.audit("identity.recovery_enrolment_prepared", row["id"])
        return {
            "status": "ENROLLING",
            "setup_key": secret,
            "authenticator_uri": pyotp.TOTP(secret).provisioning_uri(
                name=account["email"], issuer_name="LW Health Intelligence Platform"
            ),
            "expires_at": row["expires_at"],
        }

    async def finish(self, body):
        row, account, security = await self.challenge(body["token"])
        require(
            row["state"] == "ENROLLING",
            "INVALID_STATE",
            "Prepare the replacement authenticator first",
            409,
        )
        pending = {
            **account,
            "totp_ciphertext": row["pending_totp_ciphertext"],
            "totp_last_step": -1,
        }
        # Validate the new factor without consuming an unrelated old counter.
        code = pyotp.TOTP(self.box.decrypt(pending["totp_ciphertext"]))
        from datetime import UTC, datetime

        step = code.timecode(datetime.now(UTC))
        import hmac

        require(
            hmac.compare_digest(code.at(step * 30), body["otp"]),
            "AUTH_REQUIRED",
            "Replacement authenticator code could not be verified",
            401,
        )
        await self.session.execute(
            update(db.accounts)
            .where(db.accounts.c.id == account["id"])
            .values(
                password_hash=row["pending_password_hash"],
                totp_ciphertext=row["pending_totp_ciphertext"],
                totp_last_step=step,
            )
        )
        await self.session.execute(
            update(db.sessions)
            .where(db.sessions.c.account_id == account["id"])
            .values(revoked=True)
        )
        await self.session.execute(
            update(t.account_security)
            .where(
                t.account_security.c.account_id == account["id"],
                t.account_security.c.credential_epoch == security["credential_epoch"],
            )
            .values(
                credential_epoch=security["credential_epoch"] + 1,
                recovery_set_id=None,
                updated_at=db.now(),
            )
        )
        await self.session.execute(
            update(t.recoveries)
            .where(
                t.recoveries.c.account_id == account["id"],
                t.recoveries.c.id != row["id"],
                t.recoveries.c.state.not_in(["COMPLETED", "REJECTED"]),
            )
            .values(state="CANCELLED", pending_password_hash=None, pending_totp_ciphertext=None)
        )
        await self.session.execute(
            update(t.recoveries)
            .where(t.recoveries.c.id == row["id"])
            .values(
                state="COMPLETED",
                pending_password_hash=None,
                pending_totp_ciphertext=None,
                completed_at=db.now(),
            )
        )
        await self.audit(
            "identity.recovery_completed",
            row["id"],
            details={
                "account_id": account["id"],
                "grants_changed": False,
                "prior_sessions_revoked": True,
            },
        )
        return await issue_session(self.session, account["id"], self.cfg.session_minutes)
