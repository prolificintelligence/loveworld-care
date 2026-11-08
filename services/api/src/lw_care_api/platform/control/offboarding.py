"""Immediate identity restriction with separately accepted, versioned clinical handover."""

import json

from sqlalchemy import select, update

from .. import db
from ..clinical import store as clinical_store
from ..clinical import tables as clinical
from ..domain import require
from . import tables as t
from .service import ControlService, has, load

OPEN_KINDS = {"task", "encounter", "stay", "programme", "order", "procedure", "referral"}
TERMINAL = {"COMPLETED", "CLOSED", "DISCHARGED", "CANCELLED", "REJECTED", "DECLINED", "ENDED"}
FIELDS = {
    "owner_id": "CARE",
    "responsible_id": "CARE",
    "responsible_clinician_id": "CARE",
    "responsible_nurse_id": "NURSING",
    "result_owner_id": "CARE",
}


class OffboardingService(ControlService):
    async def offboard(self, body):
        require(has(self.actor, {"PLATFORM_ADMIN"}))
        require(
            body["account_id"] not in {self.actor["id"], body["coordinator_id"]},
            "INDEPENDENT_REVIEW_REQUIRED",
            "The operator and handover coordinator must remain distinct from the departing account",
            422,
        )
        await self.factor(body)
        account = await load(self.session, db.accounts, body["account_id"], lock=True)
        require(account["active"], "INVALID_STATE", "This account is already restricted", 409)
        coordinator = await load(self.session, db.accounts, body["coordinator_id"])
        grants = [
            dict(r)
            for r in (
                await self.session.execute(
                    select(db.grants).where(
                        db.grants.c.account_id == coordinator["id"],
                        db.grants.c.revoked.is_(False),
                        db.grants.c.valid_from <= db.now(),
                        db.grants.c.valid_until > db.now(),
                    )
                )
            ).mappings()
        ]
        require(
            coordinator["active"] and has({"grants": grants}, {"CLINICAL_GOVERNOR"}),
            "COORDINATOR_NOT_ELIGIBLE",
            "Nominate a current global clinical governance coordinator for outstanding work",
            422,
        )
        row = {
            "id": db.uid(),
            "account_id": account["id"],
            "coordinator_id": coordinator["id"],
            "created_by": self.actor["id"],
            "reason_ciphertext": self.box.encrypt(body["evidence"]),
            "created_at": db.now(),
        }
        await self.session.execute(t.offboardings.insert().values(**row))
        count = 0
        for source in (
            await self.session.execute(
                select(clinical.records).where(
                    clinical.records.c.kind.in_(OPEN_KINDS),
                    clinical.records.c.status.not_in(TERMINAL),
                )
            )
        ).mappings():
            data = json.loads(self.box.decrypt(source["content_ciphertext"]))["content"]
            for field in FIELDS:
                if data.get(field) != account["id"]:
                    continue
                await self.session.execute(
                    t.handover_items.insert().values(
                        id=db.uid(),
                        offboarding_id=row["id"],
                        facility_id=source["facility_id"],
                        source_id=source["id"],
                        source_version=source["version"],
                        source_kind=source["kind"],
                        owner_field=field,
                        successor_id=None,
                        state="AWAITING_SUCCESSOR",
                        version=1,
                        accepted_at=None,
                        created_at=db.now(),
                    )
                )
                count += 1
        await self.session.execute(
            update(db.accounts).where(db.accounts.c.id == account["id"]).values(active=False)
        )
        security = await self.security(account["id"])
        await self.session.execute(
            update(t.account_security)
            .where(t.account_security.c.account_id == account["id"])
            .values(
                credential_epoch=security["credential_epoch"] + 1,
                recovery_set_id=None,
                updated_at=db.now(),
            )
        )
        await self.session.execute(
            update(db.sessions)
            .where(db.sessions.c.account_id == account["id"])
            .values(revoked=True)
        )
        await self.session.execute(
            update(db.grants).where(db.grants.c.account_id == account["id"]).values(revoked=True)
        )
        await self.session.execute(
            update(clinical.privileges)
            .where(clinical.privileges.c.account_id == account["id"])
            .values(revoked=True)
        )
        await self.session.execute(
            update(t.recoveries)
            .where(
                t.recoveries.c.account_id == account["id"],
                t.recoveries.c.state.not_in(["COMPLETED", "REJECTED"]),
            )
            .values(state="CANCELLED", pending_password_hash=None, pending_totp_ciphertext=None)
        )
        await self.audit(
            "identity.account_restricted",
            row["id"],
            details={
                "account_id": account["id"],
                "open_clinical_handover_items": count,
                "historical_authorship_preserved": True,
            },
        )
        return {
            "id": row["id"],
            "account_restricted": True,
            "open_clinical_handover_items": count,
            "coordinator_id": coordinator["id"],
            "offboarding_complete": False,
            "remaining_review": "Review other institutional, financial and protected case responsibilities separately; restriction does not erase their owners.",
        }

    async def item(self, identifier):
        row = await load(self.session, t.handover_items, identifier, lock=True)
        case = await load(self.session, t.offboardings, row["offboarding_id"])
        allowed = self.actor["id"] in {case["coordinator_id"], row["successor_id"]} or has(
            self.actor, {"PLATFORM_ADMIN"}
        )
        require(allowed, "NOT_FOUND_OR_NOT_PERMITTED", "Handover item unavailable", 404)
        return row, case

    async def offer(self, identifier, body):
        row, case = await self.item(identifier)
        require(
            self.actor["id"] == case["coordinator_id"]
            and has(self.actor, {"CLINICAL_GOVERNOR"}, row["facility_id"])
        )
        require(
            row["state"] != "ACCEPTED" and row["version"] == body["expected_version"],
            "VERSION_CONFLICT",
            "Reload the current handover item",
            412,
        )
        source = await load(self.session, clinical.records, row["source_id"], lock=True)
        from ..clinical.service import ClinicalService

        await ClinicalService(
            self.session, self.cfg, self.box, self.actor, row["facility_id"], self.correlation
        ).usable(source)
        data = json.loads(self.box.decrypt(source["content_ciphertext"]))["content"]
        require(
            data.get(row["owner_field"]) == case["account_id"] and source["status"] not in TERMINAL,
            "SOURCE_CHANGED",
            "The source responsibility has changed; review the actual clinical workflow",
            409,
        )
        require(
            body["successor_id"] != case["account_id"],
            "INVALID_SUCCESSOR",
            "Choose a different current professional",
            422,
        )
        await clinical_store.privilege_for(
            self.session,
            body["successor_id"],
            row["facility_id"],
            FIELDS[row["owner_field"]],
            source["service"],
        )
        await self.session.execute(
            update(t.handover_items)
            .where(
                t.handover_items.c.id == identifier,
                t.handover_items.c.version == body["expected_version"],
            )
            .values(
                successor_id=body["successor_id"],
                state="OFFERED",
                version=row["version"] + 1,
                source_version=source["version"],
            )
        )
        await self.audit(
            "identity.clinical_handover_offered",
            identifier,
            details={"successor_id": body["successor_id"]},
        )
        return {
            "id": identifier,
            "version": row["version"] + 1,
            "state": "OFFERED",
            "ownership_transferred": False,
        }

    async def accept(self, identifier, body):
        row, case = await self.item(identifier)
        require(
            row["successor_id"] == self.actor["id"] and row["state"] == "OFFERED",
            "NOT_FOUND_OR_NOT_PERMITTED",
            "Personal handover offer unavailable",
            404,
        )
        require(
            row["version"] == body["expected_version"],
            "VERSION_CONFLICT",
            "Reload the handover before accepting",
            412,
        )
        await clinical_store.site_for(self.session, self.cfg, row["facility_id"], write=True)
        source = await clinical_store.fetch(
            self.session, row["facility_id"], row["source_id"], lock=True
        )
        from ..clinical.service import ClinicalService

        await ClinicalService(
            self.session, self.cfg, self.box, self.actor, row["facility_id"], self.correlation
        ).usable(source)
        require(
            source["patient_id"] == body["patient_id"]
            and source["version"] == row["source_version"],
            "SOURCE_CHANGED",
            "Confirm the exact patient and current source version before accepting",
            412,
        )
        await clinical_store.guard(
            self.session,
            self.cfg,
            self.actor,
            row["facility_id"],
            FIELDS[row["owner_field"]],
            patient_id=source["patient_id"],
            service=source["service"],
            write=True,
            relationship=False,
        )
        data = json.loads(self.box.decrypt(source["content_ciphertext"]))["content"]
        require(
            data.get(row["owner_field"]) == case["account_id"],
            "SOURCE_CHANGED",
            "The source owner changed",
            409,
        )
        data[row["owner_field"]] = self.actor["id"]
        if source["kind"] == "encounter":
            data["team_ids"] = list(
                dict.fromkeys(
                    [
                        identifier
                        for identifier in data.get("team_ids", [])
                        if identifier != case["account_id"]
                    ]
                    + [self.actor["id"]]
                )
            )
        data.setdefault("supervised_handover_history", []).append(
            {
                "offboarding_id": case["id"],
                "item_id": identifier,
                "accepted_by": self.actor["id"],
                "previous_owner": case["account_id"],
                "evidence": body["evidence"],
                "accepted_at": db.now(),
            }
        )
        if source["encounter_id"]:
            encounter = await clinical_store.fetch(
                self.session, row["facility_id"], source["encounter_id"], "encounter"
            )
            await clinical_store.add_member(
                self.session,
                self.cfg,
                self.actor["id"],
                encounter,
                capability=FIELDS[row["owner_field"]],
            )
        elif source["kind"] == "encounter":
            await clinical_store.add_member(
                self.session,
                self.cfg,
                self.actor["id"],
                source,
                capability=FIELDS[row["owner_field"]],
            )
        status = "ACCEPTED" if source["kind"] == "task" else source["status"]
        await clinical_store.change(
            self.session,
            self.cfg,
            self.box,
            self.actor,
            source,
            data,
            status,
            source["version"],
            self.correlation,
            "care.supervised_handover_accepted",
            "LWH-EXT-CONTROL-001",
        )
        await self.session.execute(
            update(t.handover_items)
            .where(t.handover_items.c.id == identifier)
            .values(state="ACCEPTED", version=row["version"] + 1, accepted_at=db.now())
        )
        await self.audit("identity.clinical_handover_accepted", identifier)
        return {
            "id": identifier,
            "version": row["version"] + 1,
            "state": "ACCEPTED",
            "ownership_transferred": True,
            "source_id": source["id"],
        }

    async def preview(self, identifier):
        row, _case = await self.item(identifier)
        require(
            row["successor_id"] == self.actor["id"] and row["state"] == "OFFERED",
            "NOT_FOUND_OR_NOT_PERMITTED",
            "Personal handover offer unavailable",
            404,
        )
        source = await clinical_store.fetch(self.session, row["facility_id"], row["source_id"])
        await clinical_store.privilege_for(
            self.session,
            self.actor["id"],
            row["facility_id"],
            FIELDS[row["owner_field"]],
            source["service"],
        )
        require(
            source["version"] == row["source_version"],
            "SOURCE_CHANGED",
            "The source changed; request a refreshed offer",
            412,
        )
        patient = await clinical_store.fetch(
            self.session, row["facility_id"], source["patient_id"], "patient"
        )
        content = clinical_store.opened(self.box, patient)["data"]
        await clinical_store.audit(
            self.session,
            self.actor,
            row["facility_id"],
            patient["id"],
            "care.handover_identity_read",
            self.correlation,
            purpose="PROPOSED_CARE_HANDOVER",
        )
        return {
            "handover_id": identifier,
            "patient": {
                "id": patient["id"],
                **{
                    key: content.get(key)
                    for key in ("display_name", "local_identifier", "birth_date", "sex")
                },
            },
            "source_kind": source["kind"],
            "source_version": source["version"],
            "responsibility": row["owner_field"],
            "instruction": "Confirm this patient through the facility's independent identity process before accepting. No chart-browsing authority is granted by preview.",
        }
