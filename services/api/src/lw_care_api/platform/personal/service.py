"""Verified actor/subject authority, encrypted history and explicit bounded grants."""

import hashlib
import json

from sqlalchemy import func, select, update

from .. import db
from ..clinical import store as cs
from ..clinical import tables as ct
from ..domain import require
from . import tables as t


async def load(session, table, identifier, *, lock=False):
    query = select(table).where(table.c.id == str(identifier))
    row = (await session.execute(query.with_for_update() if lock else query)).mappings().first()
    require(row, "NOT_FOUND_OR_NOT_PERMITTED", "Personal care resource unavailable", 404)
    return dict(row)


def version(row, expected):
    require(
        row["version"] == expected,
        "VERSION_CONFLICT",
        "Refresh and review the current version",
        412,
    )


class PersonalService:
    def __init__(self, session, cfg, box, actor, correlation):
        self.session, self.cfg, self.box, self.actor, self.correlation = (
            session,
            cfg,
            box,
            actor,
            correlation,
        )

    def seal(self, identifier, value):
        return cs.seal(self.box, identifier, value)

    def data(self, row):
        payload = json.loads(self.box.decrypt(row["payload_ciphertext"]))
        require(
            payload["id"] == row["id"], "INTEGRITY_FAILURE", "Personal record integrity failed", 503
        )
        return payload["content"]

    async def audit(self, action, link=None, outcome="SUCCESS"):
        await self.session.execute(
            t.audit.insert().values(
                id=db.uid(),
                link_id=link,
                actor_id=self.actor["id"] if self.actor else None,
                action=action,
                outcome=outcome,
                created_at=db.now(),
                correlation_id=self.correlation,
            )
        )

    async def event(self, table, row, action, evidence):
        payload = cs.canonical(
            {
                "resource": {k: v for k, v in row.items() if not k.endswith("ciphertext")},
                "evidence": evidence,
            }
        )
        await self.session.execute(
            t.events.insert().values(
                id=db.uid(),
                resource_type=table.name,
                resource_id=row["id"],
                version=row.get("version", 1),
                actor_id=self.actor["id"],
                action=action,
                created_at=db.now(),
                payload_ciphertext=self.box.encrypt(payload),
                payload_hash=hashlib.sha256(payload.encode()).hexdigest(),
            )
        )
        await self.audit(action, row["id"] if table is t.links else row.get("link_id"))

    async def change(self, table, row, values, expected, action, evidence):
        version(row, expected)
        values = values | {"version": expected + 1}
        if "updated_at" in table.c:
            values["updated_at"] = db.now()
        changed = await self.session.execute(
            update(table)
            .where(table.c.id == row["id"], table.c.version == expected)
            .values(**values)
        )
        require(changed.rowcount == 1, "VERSION_CONFLICT", "Refresh this changed record", 412)
        current = row | values
        await self.event(table, current, action, evidence)
        return current

    async def staff(self, facility, capability="RECORDS", *, patient=None, write=False):
        return await cs.guard(
            self.session,
            self.cfg,
            self.actor,
            facility,
            capability,
            patient_id=patient,
            write=write,
            relationship=capability != "RECORDS",
        )

    async def current_link(self, row, permission=None):
        require(
            row["state"] == "APPROVED"
            and row["valid_until"] > db.now()
            and row["review_at"] > db.now(),
            "PERSONAL_ACCESS_REVIEW_REQUIRED",
            "This access is expired, withdrawn or awaiting review",
            403,
        )
        if permission:
            require(
                permission in row["permissions"],
                "PERSONAL_ACTION_NOT_PERMITTED",
                "This action is outside the verified permission",
                403,
            )
        await cs.site_for(self.session, self.cfg, row["facility_id"])
        patient = (
            (
                await self.session.execute(
                    select(ct.records)
                    .where(
                        ct.records.c.id == row["patient_id"],
                        ct.records.c.facility_id == row["facility_id"],
                        ct.records.c.kind == "patient",
                    )
                    .with_for_update(read=True)
                )
            )
            .mappings()
            .first()
        )
        require(
            patient
            and patient["status"] == "CONFIRMED"
            and patient["version"] == row["patient_version"],
            "PERSONAL_IDENTITY_REVIEW_REQUIRED",
            "The patient identity needs renewed verification",
            403,
        )
        return dict(patient)

    async def own_link(self, identifier, permission=None):
        query = select(t.links).where(
            t.links.c.id == str(identifier), t.links.c.account_id == self.actor["id"]
        )
        row = (await self.session.execute(query.with_for_update(read=True))).mappings().first()
        require(row, "NOT_FOUND_OR_NOT_PERMITTED", "Personal care context unavailable", 404)
        await self.current_link(row, permission)
        return dict(row)

    async def link_view(self, row, *, staff=False):
        result = {
            k: row[k]
            for k in (
                "id",
                "facility_id",
                "relationship",
                "state",
                "version",
                "permissions",
                "valid_until",
                "review_at",
                "created_at",
            )
        }
        result["facility_name"] = await self.session.scalar(
            select(db.facilities.c.name).where(db.facilities.c.id == row["facility_id"])
        )
        result["subject_label"] = self.data(row).get("subject_label", "Awaiting identity review")
        result["usable"] = False
        if row["state"] == "APPROVED":
            from ..domain import RuleError

            try:
                await self.current_link(row)
                result["usable"] = True
            except RuleError:
                result["subject_label"] = "Access requires review"
        if staff:
            result.update(
                account_id=row["account_id"],
                patient_id=row["patient_id"],
                patient_version=row["patient_version"],
                evidence=self.data(row),
            )
            account = await load(self.session, db.accounts, row["account_id"])
            result["account"] = {k: account[k] for k in ("id", "name", "email", "active")}
        return result

    async def create_link(self, body, *, recipient=None, patient=None):
        facility = await load(self.session, db.facilities, body["facility_id"])
        await cs.site_for(self.session, self.cfg, facility["id"])
        recipient = recipient or self.actor["id"]
        account = await load(self.session, db.accounts, recipient)
        require(
            account["active"],
            "ACCOUNT_VERIFICATION_REQUIRED",
            "The recipient must activate their account first",
            409,
        )
        count = await self.session.scalar(
            select(func.count())
            .select_from(t.links)
            .where(
                t.links.c.account_id == recipient,
                t.links.c.state == "PENDING",
                t.links.c.facility_id == facility["id"],
            )
        )
        require(
            count < 10,
            "PENDING_REVIEW_LIMIT",
            "Ask the facility to resolve the existing access requests",
            409,
        )
        identifier, stamp = db.uid(), db.now()
        row = {
            "id": identifier,
            "account_id": recipient,
            "submitted_by": self.actor["id"],
            "facility_id": facility["id"],
            "patient_id": patient,
            "patient_version": None,
            "relationship": body["relationship"],
            "state": "PENDING",
            "version": 1,
            "permissions": [],
            "valid_until": None,
            "review_at": None,
            "reviewer_id": None,
            "active_key": None,
            "self_key": None,
            "created_at": stamp,
            "updated_at": stamp,
            "payload_ciphertext": self.seal(identifier, body),
        }
        await self.session.execute(t.links.insert().values(**row))
        await self.event(t.links, row, "personal.access_requested", body)
        return {"id": identifier, "state": "PENDING", "version": 1}

    async def review_link(self, identifier, body):
        row = await load(self.session, t.links, identifier)
        await self.staff(row["facility_id"], write=True)
        require(
            self.actor["id"] not in {row["account_id"], row["submitted_by"]},
            "INDEPENDENT_REVIEW_REQUIRED",
            "Another verified records professional must review this request",
            403,
        )
        require(
            row["state"] in {"PENDING", "APPROVED"},
            "INVALID_TRANSITION",
            "Submit a new request after withdrawal or denial",
            409,
        )
        values = {
            "state": "DENIED",
            "permissions": [],
            "active_key": None,
            "self_key": None,
            "reviewer_id": self.actor["id"],
        }
        content = self.data(row) | {"review": body}
        if body["decision"] == "APPROVE":
            require(
                body.get("patient_id")
                and body.get("valid_until")
                and body.get("review_at")
                and db.now() < body["review_at"] <= body["valid_until"]
                and body["permissions"],
                "VERIFICATION_INCOMPLETE",
                "Record the verified patient, permissions, expiry and next review",
                422,
            )
            require(
                row["patient_id"] in (None, body["patient_id"]),
                "IDENTITY_CHANGE_REQUIRES_NEW_REQUEST",
                "Withdraw the incorrect link and verify a new request; identities cannot be silently reassigned",
                409,
            )
            patient = await cs.fetch(
                self.session, row["facility_id"], body["patient_id"], "patient"
            )
            require(
                patient["status"] == "CONFIRMED",
                "CONFIRMED_IDENTITY_REQUIRED",
                "Resolve the provisional patient identity first",
                409,
            )
            version(patient, body["expected_patient_version"])
            require(
                "SHARE" not in body["permissions"] or row["relationship"] == "SELF",
                "DELEGATION_NOT_PERMITTED",
                "Representative access does not include onward delegation",
                422,
            )
            values.update(
                state="APPROVED",
                patient_id=patient["id"],
                patient_version=patient["version"],
                permissions=sorted(set(body["permissions"])),
                valid_until=body["valid_until"],
                review_at=body["review_at"],
                active_key=f"{row['account_id']}:{patient['id']}",
                self_key=patient["id"] if row["relationship"] == "SELF" else None,
            )
            content["subject_label"] = cs.opened(self.box, patient)["data"]["display_name"]
        values["payload_ciphertext"] = self.seal(row["id"], content)
        current = await self.change(
            t.links, row, values, body["expected_version"], "personal.access_reviewed", body
        )
        return {"id": current["id"], "state": current["state"], "version": current["version"]}

    async def revoke_link(self, identifier, body, staff=False):
        row = await load(self.session, t.links, identifier)
        if staff:
            await self.staff(row["facility_id"], write=True)
        elif row["account_id"] != self.actor["id"]:
            own = (
                (
                    await self.session.execute(
                        select(t.links).where(
                            t.links.c.account_id == self.actor["id"],
                            t.links.c.patient_id == row["patient_id"],
                            t.links.c.relationship == "SELF",
                            t.links.c.state == "APPROVED",
                        )
                    )
                )
                .mappings()
                .first()
            )
            require(
                own and row["relationship"] == "REPRESENTATIVE",
                "NOT_FOUND_OR_NOT_PERMITTED",
                "Permission unavailable",
                404,
            )
            await self.current_link(own, "SHARE")
        require(
            row["state"] in {"PENDING", "APPROVED"},
            "INVALID_TRANSITION",
            "This permission is already closed",
            409,
        )
        current = await self.change(
            t.links,
            row,
            {"state": "REVOKED", "permissions": [], "active_key": None, "self_key": None},
            body["expected_version"],
            "personal.access_revoked",
            body,
        )
        return {"id": current["id"], "state": "REVOKED", "version": current["version"]}

    async def share(self, identifier, body):
        link = await self.own_link(identifier, "SHARE")
        require(link["relationship"] == "SELF" and body["recipient_account_id"] != self.actor["id"])
        return await self.create_link(
            {
                "facility_id": link["facility_id"],
                "relationship": "REPRESENTATIVE",
                "patient_reference": "Verified self-authorised representative request",
                "relationship_basis": body["relationship_basis"],
            },
            recipient=body["recipient_account_id"],
            patient=link["patient_id"],
        )
