"""Human-reviewed disclosure and personally accepted, owned patient requests."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from .. import db
from ..clinical import store as cs
from ..clinical import tables as ct
from ..clinical.router import governor
from ..domain import require
from . import tables as t
from .service import PersonalService, load, version

SOURCE_STATES = {
    "PLAN": {"care_instructions": {"RECORDED"}, "note": {"SIGNED"}},
    "MEDICINE": {"medication": {"VERIFIED"}},
    "APPOINTMENT": {"appointment": {"CONFIRMED", "ARRIVED", "COMPLETED", "CANCELLED", "NO_SHOW"}},
    "RESULT": {"result": {"FINAL"}},
    "TIMELINE": {
        "note": {"SIGNED"},
        "observation": {"RECORDED"},
        "care_instructions": {"RECORDED"},
    },
}


class CareService(PersonalService):
    async def source_blocks(self, facility, patient):
        # Retained pre-portal amendments are authoritative too. Stream only this
        # subject's correction-capable records; never expose their private text.
        blocked = set()
        result = await self.session.stream(
            select(ct.records).where(
                ct.records.c.facility_id == facility,
                ct.records.c.patient_id == patient,
                ct.records.c.status.in_(["SIGNED", "FINAL", "RECORDED", "ENTERED_IN_ERROR"]),
            )
        )
        async for row in result.mappings():
            data = cs.opened(self.box, row)["data"]
            target = data.get("amends_id") or data.get("corrects_id")
            if row["kind"] == "record_error":
                target = data.get("target_id")
            if target:
                blocked.add(target)
        return blocked

    async def service_current(self, row):
        require(
            row["active"]
            and row["valid_until"] > db.now()
            and row["primary_accepted"]
            and row["fallback_accepted"],
            "RECEIVING_SERVICE_UNAVAILABLE",
            "This service is not currently accepting requests",
            409,
        )
        await cs.site_for(self.session, self.cfg, row["facility_id"])
        for account in (row["primary_id"], row["fallback_id"]):
            await cs.privilege_for(self.session, account, row["facility_id"], "CARE")

    async def create_service(self, body):
        facility = body["facility_id"]
        require(governor(self.actor, facility))
        await cs.site_for(self.session, self.cfg, facility, write=True)
        require(
            body["primary_id"] != body["fallback_id"] and body["valid_until"] > db.now(),
            "VALIDATION_FAILED",
            "Name distinct primary/fallback staff and a future expiry",
            422,
        )
        for account in (body["primary_id"], body["fallback_id"]):
            await cs.privilege_for(self.session, account, facility, "CARE")
        identifier = db.uid()
        row = {
            "id": identifier,
            "facility_id": facility,
            "name": body["name"],
            "primary_id": body["primary_id"],
            "fallback_id": body["fallback_id"],
            "primary_accepted": False,
            "fallback_accepted": False,
            "response_minutes": body["response_minutes"],
            "valid_until": body["valid_until"],
            "active": True,
            "version": 1,
            "created_by": self.actor["id"],
            "created_at": db.now(),
            "payload_ciphertext": self.seal(identifier, body),
        }
        await self.session.execute(t.services.insert().values(**row))
        await self.event(t.services, row, "personal.service_proposed", body)
        return {k: v for k, v in row.items() if not k.endswith("ciphertext")}

    async def service_action(self, identifier, body):
        row = await load(self.session, t.services, identifier)
        await cs.site_for(self.session, self.cfg, row["facility_id"], write=True)
        if body["action"] == "PAUSE":
            require(
                governor(self.actor, row["facility_id"])
                or self.actor["id"] in {row["primary_id"], row["fallback_id"]}
            )
            values = {"active": False}
        else:
            require(
                row["active"]
                and row["valid_until"] > db.now()
                and self.actor["id"] in {row["primary_id"], row["fallback_id"]}
            )
            await cs.privilege_for(self.session, self.actor["id"], row["facility_id"], "CARE")
            values = {
                "primary_accepted"
                if row["primary_id"] == self.actor["id"]
                else "fallback_accepted": True
            }
        current = await self.change(
            t.services, row, values, body["expected_version"], "personal.service_changed", body
        )
        return {k: v for k, v in current.items() if not k.endswith("ciphertext")}

    async def release(self, identifier, body):
        link = await load(self.session, t.links, identifier)
        await self.staff(link["facility_id"], "CARE", patient=link["patient_id"], write=True)
        await self.current_link(link, "READ")
        source = await cs.fetch(self.session, link["facility_id"], body["source_id"])
        require(
            source["patient_id"] == link["patient_id"] and source["confidentiality"] == "STANDARD",
            "DISCLOSURE_NOT_PERMITTED",
            "This source is outside this subject's permitted disclosure",
            403,
        )
        version(source, body["expected_source_version"])
        require(
            source["id"] not in await self.source_blocks(link["facility_id"], link["patient_id"]),
            "SOURCE_SUPERSEDED",
            "Release the reviewed correction instead of the superseded source",
            409,
        )
        require(
            source["status"] in SOURCE_STATES[body["kind"]].get(source["kind"], set()),
            "SOURCE_NOT_READY_FOR_PATIENT",
            "The source is not signed, verified or ready for this release",
            409,
        )
        if source["kind"] == "result":
            require(
                cs.opened(self.box, source)["data"].get("reviewed_at"),
                "CLINICAL_REVIEW_REQUIRED",
                "Record clinical review before patient release",
                409,
            )
        identifier = db.uid()
        row = {
            "id": identifier,
            "link_id": link["id"],
            "source_id": source["id"],
            "source_version": source["version"],
            "kind": body["kind"],
            "created_by": self.actor["id"],
            "created_at": db.now(),
            "due_at": body.get("due_at"),
            "payload_ciphertext": self.seal(identifier, body),
        }
        await self.session.execute(t.releases.insert().values(**row))
        await self.event(t.releases, row, "personal.care_released", body)
        return {"id": identifier, "state": "RELEASED", "link_id": link["id"]}

    async def withdraw(self, identifier, body):
        row = await load(self.session, t.releases, identifier)
        link = await load(self.session, t.links, row["link_id"])
        await self.staff(link["facility_id"], "CARE", patient=link["patient_id"], write=True)
        await self.session.execute(
            t.withdrawals.insert().values(
                id=db.uid(),
                release_id=row["id"],
                actor_id=self.actor["id"],
                created_at=db.now(),
                payload_ciphertext=self.box.encrypt(cs.canonical(body)),
            )
        )
        await self.audit("personal.care_withdrawn", link["id"])
        return {"id": row["id"], "state": "WITHDRAWN"}

    async def message(self, row, content, sender):
        identifier = db.uid()
        await self.session.execute(
            t.messages.insert().values(
                id=identifier,
                request_id=row["id"],
                actor_id=self.actor["id"],
                sender_type=sender,
                created_at=db.now(),
                payload_ciphertext=self.seal(identifier, {"text": content}),
            )
        )

    async def create_request(self, identifier, body):
        link = await self.own_link(identifier, "REQUEST")
        from ..institutional.master import accepting_new_care

        await accepting_new_care(self.session, link["facility_id"])
        service = await load(self.session, t.services, body["service_id"])
        require(
            service["facility_id"] == link["facility_id"],
            "NOT_FOUND_OR_NOT_PERMITTED",
            "Receiving service unavailable",
            404,
        )
        await self.service_current(service)
        identifier, stamp = db.uid(), db.now()
        row = {
            "id": identifier,
            "link_id": link["id"],
            "service_id": service["id"],
            "facility_id": link["facility_id"],
            "patient_id": link["patient_id"],
            "created_by": self.actor["id"],
            "kind": body["kind"],
            "state": "SUBMITTED",
            "version": 1,
            "owner_id": service["primary_id"],
            "fallback_id": service["fallback_id"],
            "handover_to": None,
            "due_at": (
                datetime.now(UTC) + timedelta(minutes=service["response_minutes"])
            ).isoformat(timespec="microseconds"),
            "created_at": stamp,
            "updated_at": stamp,
            "accepted_at": None,
            "closed_at": None,
        }
        await self.session.execute(t.requests.insert().values(**row))
        await self.message(row, body["text"], "PATIENT_REPORTED")
        await self.event(t.requests, row, "personal.request_received", {"kind": body["kind"]})
        return await self.request_view(row)

    async def request_view(self, row):
        result = {
            k: row[k]
            for k in (
                "id",
                "link_id",
                "kind",
                "state",
                "version",
                "created_at",
                "updated_at",
                "due_at",
                "accepted_at",
                "closed_at",
            )
        }
        for field in ("owner_id", "fallback_id"):
            result[field.replace("_id", "_name")] = await self.session.scalar(
                select(db.accounts.c.name).where(db.accounts.c.id == row[field])
            )
        result["overdue"] = row["state"] != "CLOSED" and row["due_at"] < db.now()
        result["next_step"] = (
            "Await the named team's acceptance; no clinician review is confirmed"
            if row["state"] == "SUBMITTED"
            else "A team member has accepted responsibility; review the human messages"
            if row["state"] != "CLOSED"
            else "Request closed; the recorded messages explain the outcome"
        )
        result["handover_pending"] = bool(row["handover_to"])
        return result

    async def owned_request(self, identifier):
        row = await load(self.session, t.requests, identifier)
        require(
            self.actor["id"] in {row["owner_id"], row["fallback_id"], row["handover_to"]},
            "NOT_FOUND_OR_NOT_PERMITTED",
            "This request is not assigned to you",
            404,
        )
        await cs.guard(
            self.session, self.cfg, self.actor, row["facility_id"], "CARE", relationship=False
        )
        return row

    async def request_action(self, identifier, body):
        row = await self.owned_request(identifier)
        await cs.site_for(self.session, self.cfg, row["facility_id"], write=True)
        require(row["state"] != "CLOSED", "INVALID_TRANSITION", "This request is closed", 409)
        action = body["action"]
        values = {}
        if action == "ACCEPT":
            require(
                row["state"] == "SUBMITTED"
                and self.actor["id"] in {row["owner_id"], row["fallback_id"]}
            )
            values = {"state": "ACCEPTED", "owner_id": self.actor["id"], "accepted_at": db.now()}
            if self.actor["id"] == row["fallback_id"]:
                values["fallback_id"] = row["owner_id"]
        elif action == "ACCEPT_HANDOVER":
            require(row["handover_to"] == self.actor["id"])
            values = {"owner_id": self.actor["id"], "handover_to": None}
        else:
            require(
                row["accepted_at"] and row["owner_id"] == self.actor["id"],
                "PERSONAL_ACCEPTANCE_REQUIRED",
                "The personally accepting owner must perform this action",
                403,
            )
            if action == "OFFER_HANDOVER":
                require(
                    body.get("successor_id") and body["successor_id"] != self.actor["id"],
                    "VALIDATION_FAILED",
                    "Name a distinct receiving professional",
                    422,
                )
                await cs.privilege_for(
                    self.session, body["successor_id"], row["facility_id"], "CARE"
                )
                values = {"handover_to": body["successor_id"]}
            else:
                require(
                    body.get("text"),
                    "RESPONSE_REQUIRED",
                    "Record the actual patient-readable response",
                    422,
                )
                values = {"state": "RESPONDED" if action == "RESPOND" else "CLOSED"}
                if action == "CLOSE":
                    require(
                        not row["handover_to"],
                        "HANDOVER_PENDING",
                        "Resolve the offered handover before closure",
                        409,
                    )
                    values["closed_at"] = db.now()
                await self.message(row, body["text"], "HUMAN_CARE_TEAM")
        current = await self.change(
            t.requests,
            row,
            values,
            body["expected_version"],
            "personal.request_" + action.lower(),
            body,
        )
        return await self.request_view(current)

    async def reply(self, identifier, body):
        row = await load(self.session, t.requests, identifier)
        await self.own_link(row["link_id"], "REQUEST")
        require(row["created_by"] == self.actor["id"] and row["state"] != "CLOSED")
        await self.message(row, body["text"], "PATIENT_REPORTED")
        current = await self.change(
            t.requests,
            row,
            {},
            body["expected_version"],
            "personal.patient_reply",
            {"reason": body["reason"]},
        )
        return await self.request_view(current)


async def invalidate_amended_source(session, box, actor, row, content):
    """A signed amendment/corrected result withdraws obsolete patient summaries atomically."""
    old = (
        content.get("amends_id")
        or content.get("corrects_id")
        or (content.get("target_id") if row["kind"] == "record_error" else None)
    )
    if not old or row["status"] not in {"SIGNED", "FINAL", "RECORDED", "ENTERED_IN_ERROR"}:
        return
    releases = list(
        (
            await session.execute(
                select(t.releases.c.id)
                .outerjoin(t.withdrawals, t.withdrawals.c.release_id == t.releases.c.id)
                .where(t.releases.c.source_id == old, t.withdrawals.c.id.is_(None))
            )
        ).scalars()
    )
    for identifier in releases:
        await session.execute(
            t.withdrawals.insert().values(
                id=db.uid(),
                release_id=identifier,
                actor_id=actor["id"],
                created_at=db.now(),
                payload_ciphertext=box.encrypt(
                    cs.canonical({"reason": "SOURCE_AMENDED", "replacement_source": row["id"]})
                ),
            )
        )
