"""Phase 5 service capacity, accepted teamwork and actual inpatient transitions."""

from datetime import datetime

from sqlalchemy import func, select, update

from .. import db
from ..domain import require, valid_interval
from . import flow_index as f
from . import store as s
from . import tables as t
from .continuity import EMRService

OPEN_ENCOUNTERS = {"ARRIVED", "TRIAGED", "ACKNOWLEDGED", "IN_PROGRESS"}
OPEN_TASKS = {"ASSIGNED", "ACCEPTED", "IN_PROGRESS", "BLOCKED"}


class AdvancedService(EMRService):
    async def phase5(self):
        version = await self.session.scalar(select(func.max(db.schema_versions.c.version)))
        require(
            (version or 0) >= 7,
            "CLINICAL_WORKFLOW_MIGRATION_REQUIRED",
            "This workflow awaits migration 7",
            503,
        )
        require(
            await f.ready(self.session),
            "CLINICAL_WORK_INDEX_RECONCILIATION_REQUIRED",
            "Rebuild the clinical work index from current source records before this workflow can proceed",
            503,
        )

    async def advanced_ready(self):
        return (await self.session.scalar(select(func.max(db.schema_versions.c.version))) or 0) >= 7

    async def governor(self):
        from .router import governor

        require(governor(self.actor, self.facility_id))
        return await s.site_for(self.session, self.cfg, self.facility_id, write=True)

    async def flow(self, kind, body, *, capability="CARE", closed=False, status="RECORDED"):
        await self.phase5()
        _, _, encounter = await self.context(
            body, capability, allow_closed=closed or bool(body.get("amends_id"))
        )
        if body.get("amends_id"):
            old = await self.linked(
                body["amends_id"], kind, body["patient_id"], body["encounter_id"]
            )
            require(
                old["status"] == "RECORDED" and body.get("amendment_reason"),
                "AMENDMENT_REASON_REQUIRED",
                "Reference the original actual record and explain its correction",
                409,
            )
        if body.get("programme_id"):
            programme = await self.linked(body["programme_id"], "programme", body["patient_id"])
            require(
                self.content(programme)["programme_type"] in {"MATERNAL", "NEWBORN", "CHILD"},
                "PROGRAMME_SCOPE_MISMATCH",
                "Use the actual applicable maternal or child episode",
                409,
            )
            if programme["confidentiality"] == "RESTRICTED":
                await s.privilege_for(
                    self.session,
                    self.actor["id"],
                    self.facility_id,
                    "SENSITIVE",
                    encounter["service"],
                )
        unique = (
            body.get("signed_note_id")
            if kind == "birth"
            else body.get("administration_id")
            if kind == "immunisation"
            else None
        )
        return await self.create(
            kind,
            {**body, "attested_by": self.actor["id"]},
            patient_id=body["patient_id"],
            encounter_id=body["encounter_id"],
            service=encounter["service"],
            status=status,
            action="clinical." + kind + "_recorded",
            contract="LWH-EXT-CLINICAL-030",
            unique_value=unique if not body.get("amends_id") else None,
        )

    async def config_for(self, service):
        rows = (
            (
                await self.session.execute(
                    select(t.records)
                    .join(f.index, f.index.c.record_id == t.records.c.id)
                    .where(
                        f.index.c.facility_id == self.facility_id,
                        f.index.c.kind == "service_capacity",
                        f.index.c.service == service,
                        f.index.c.status == "CONFIGURED",
                        f.index.c.starts_at <= db.now(),
                        f.index.c.ends_at > db.now(),
                    )
                )
            )
            .mappings()
            .all()
        )
        require(
            len(rows) <= 1,
            "CAPACITY_CONFIGURATION_CONFLICT",
            "Resolve overlapping service capacity windows",
            409,
        )
        return self.content(rows[0]) if rows else None

    async def assignment(self, account_id, service, capability="CARE", exclude=None):
        await s.privilege_for(self.session, account_id, self.facility_id, capability, service)
        if not await self.advanced_ready():
            return "NOT_CONFIGURED"
        require(
            await f.ready(self.session),
            "CLINICAL_WORK_INDEX_RECONCILIATION_REQUIRED",
            "Reconcile the current workload before accepting new care",
            503,
        )
        config = await self.config_for(service)
        if not config:
            return "NOT_CONFIGURED"
        if capability == "CARE":
            live = select(f.index.c.record_id).where(
                f.index.c.facility_id == self.facility_id,
                f.index.c.kind == "encounter",
                f.index.c.service == service,
                f.index.c.status.in_(OPEN_ENCOUNTERS),
            )
            if exclude:
                live = live.where(f.index.c.record_id != exclude)
            total = await self.session.scalar(select(func.count()).select_from(live.subquery()))
            require(
                total < config["max_open_encounters"],
                "SERVICE_CAPACITY_EXHAUSTED",
                "The service has no confirmed capacity for another assignment",
                409,
            )
        if config["require_roster"]:
            shifts = list(
                (
                    await self.session.execute(
                        select(t.records)
                        .join(f.index, f.index.c.record_id == t.records.c.id)
                        .where(
                            f.index.c.facility_id == self.facility_id,
                            f.index.c.kind == "duty_shift",
                            f.index.c.service == service,
                            f.index.c.accountable_id == account_id,
                            f.index.c.status == "ACCEPTED",
                            f.index.c.starts_at <= db.now(),
                            f.index.c.ends_at > db.now(),
                        )
                    )
                ).mappings()
            )
            matching = [
                self.content(row) for row in shifts if self.content(row)["capability"] == capability
            ]
            require(
                len(matching) == 1,
                "ACCEPTED_SHIFT_REQUIRED",
                "A single current personally accepted service shift is required",
                409,
            )
            if capability == "CARE":
                mine = await self.session.scalar(
                    select(func.count())
                    .select_from(f.index)
                    .where(
                        f.index.c.facility_id == self.facility_id,
                        f.index.c.kind == "encounter",
                        f.index.c.service == service,
                        f.index.c.accountable_id == account_id,
                        f.index.c.status.in_(OPEN_ENCOUNTERS),
                        f.index.c.record_id != (exclude or ""),
                    )
                )
                require(
                    mine < matching[0]["capacity"],
                    "STAFF_CAPACITY_EXHAUSTED",
                    "The clinician's accepted workload is full",
                    409,
                )
        return "CURRENT_CONFIGURATION_CHECKED"

    async def capacity(self, body):
        await self.phase5()
        site = await self.governor()
        valid_interval(
            datetime.fromisoformat(body["starts_at"]), datetime.fromisoformat(body["ends_at"])
        )
        require(
            body["service"] in site["services"],
            "SERVICE_NOT_ACTIVATED",
            "Activate this service before configuring capacity",
            409,
        )
        overlap = await self.session.scalar(
            select(f.index.c.record_id)
            .where(
                f.index.c.facility_id == self.facility_id,
                f.index.c.kind == "service_capacity",
                f.index.c.service == body["service"],
                f.index.c.status == "CONFIGURED",
                f.index.c.starts_at < body["ends_at"],
                f.index.c.ends_at > body["starts_at"],
            )
            .limit(1)
        )
        require(
            not overlap,
            "CAPACITY_WINDOW_OVERLAP",
            "A configured capacity window already covers part of this period",
            409,
        )
        return await self.create(
            "service_capacity",
            body,
            site=site,
            service=body["service"],
            status="CONFIGURED",
            contract="LWH-EXT-CLINICAL-031",
        )

    async def shift(self, body):
        await self.phase5()
        site = await self.governor()
        valid_interval(
            datetime.fromisoformat(body["starts_at"]), datetime.fromisoformat(body["ends_at"])
        )
        require(
            body["ends_at"] > db.now(), "INVALID_EVENT_TIME", "Offer a current or future shift", 422
        )
        await s.privilege_for(
            self.session, body["account_id"], self.facility_id, body["capability"], body["service"]
        )
        prior = list(
            (
                await self.session.execute(
                    select(t.records)
                    .join(f.index, f.index.c.record_id == t.records.c.id)
                    .where(
                        f.index.c.facility_id == self.facility_id,
                        f.index.c.kind == "duty_shift",
                        f.index.c.accountable_id == body["account_id"],
                        f.index.c.service == body["service"],
                        f.index.c.status.in_(["OFFERED", "ACCEPTED"]),
                        f.index.c.starts_at < body["ends_at"],
                        f.index.c.ends_at > body["starts_at"],
                    )
                )
            ).mappings()
        )
        require(
            not any(self.content(row)["capability"] == body["capability"] for row in prior),
            "SHIFT_WINDOW_OVERLAP",
            "Resolve the existing offered or accepted shift first",
            409,
        )
        return await self.create(
            "duty_shift",
            body,
            site=site,
            service=body["service"],
            status="OFFERED",
            contract="LWH-EXT-CLINICAL-031",
        )

    async def capacity_revision(self, identifier, body):
        await self.phase5()
        await self.governor()
        row = await self.row(identifier, "service_capacity")
        require(
            body["service"] == row["service"],
            "SERVICE_CONTEXT_MISMATCH",
            "Revise this service's actual capacity without changing its identity",
            409,
        )
        body["starts_at"] = max(body["starts_at"], db.now())
        valid_interval(
            datetime.fromisoformat(body["starts_at"]), datetime.fromisoformat(body["ends_at"])
        )
        overlap = await self.session.scalar(
            select(f.index.c.record_id)
            .where(
                f.index.c.facility_id == self.facility_id,
                f.index.c.kind == "service_capacity",
                f.index.c.service == row["service"],
                f.index.c.record_id != identifier,
                f.index.c.status == "CONFIGURED",
                f.index.c.starts_at < body["ends_at"],
                f.index.c.ends_at > body["starts_at"],
            )
            .limit(1)
        )
        require(
            not overlap,
            "CAPACITY_WINDOW_OVERLAP",
            "Resolve the other approved capacity window first",
            409,
        )
        return await self.change(
            row,
            {**body, "revised_by": self.actor["id"], "unresolved_ownership_retained": True},
            "CONFIGURED",
            body["expected_version"],
            "clinical.capacity_revised",
            "LWH-EXT-CLINICAL-031",
        )

    async def shift_action(self, identifier, body):
        await self.phase5()
        row = await self.row(identifier, "duty_shift")
        data = self.content(row)
        if body["action"] == "WITHDRAW":
            await self.governor()
            require(
                row["status"] in {"OFFERED", "ACCEPTED"},
                "INVALID_STATE",
                "Only an offered or accepted shift can be withdrawn",
                409,
            )
            s.event_time(body["occurred_at"])
            return await self.change(
                row,
                {**data, "withdrawal": body, "unresolved_ownership_retained": True},
                "WITHDRAWN",
                body["expected_version"],
                "clinical.shift_withdrawn",
                "LWH-EXT-CLINICAL-031",
            )
        require(
            data["account_id"] == self.actor["id"],
            "ACCESS_DENIED",
            "The named professional must personally accept or end the shift",
            403,
        )
        await s.privilege_for(
            self.session, self.actor["id"], self.facility_id, data["capability"], row["service"]
        )
        require(
            body["action"] in {"ACCEPT", "DECLINE", "END"},
            "INVALID_ACTION",
            "Choose accept, decline or end",
            422,
        )
        require(
            row["status"] == ("ACCEPTED" if body["action"] == "END" else "OFFERED"),
            "INVALID_STATE",
            "Review the current shift state",
            409,
        )
        require(
            data["ends_at"] > db.now(),
            "SHIFT_EXPIRED",
            "Expired coverage cannot be accepted as current",
            409,
        )
        s.event_time(body["occurred_at"])
        data.update(last_action=body, unresolved_ownership_retained=True)
        return await self.change(
            row,
            data,
            {"ACCEPT": "ACCEPTED", "DECLINE": "DECLINED", "END": "ENDED"}[body["action"]],
            body["expected_version"],
            "clinical.shift_changed",
            "LWH-EXT-CLINICAL-031",
        )

    async def encounter(self, body):
        try:
            await s.privilege_for(
                self.session, self.actor["id"], self.facility_id, "CARE", body["service"]
            )
        except Exception as exc:
            from ..domain import RuleError

            if not isinstance(exc, RuleError) or exc.code != "CLINICAL_PRIVILEGE_REQUIRED":
                raise
        else:
            body["capacity_assessment"] = await self.assignment(self.actor["id"], body["service"])
        return await super().encounter(body)

    async def encounter_action(self, identifier, body, action):
        if action == "claim":
            row = await self.row(identifier, "encounter")
            await self.assignment(self.actor["id"], row["service"], exclude=identifier)
        return await super().encounter_action(identifier, body, action)

    async def team_handover(self, body):
        await self.phase5()
        _, _, encounter = await self.context(body, body["capability"], allow_closed=True)
        data = self.content(encounter)
        require(
            encounter["version"] == body["expected_encounter_version"],
            "VERSION_CONFLICT",
            "Review the current encounter before offering handover",
            412,
        )
        require(
            body["recipient_id"] != self.actor["id"],
            "INVALID_SUCCESSOR",
            "Name a different professional",
            409,
        )
        if body["capability"] == "CARE":
            require(
                data["owner_id"] == self.actor["id"],
                "ACCESS_DENIED",
                "Only the current accountable clinician can offer ownership",
                403,
            )
        else:
            stays = (
                (
                    await self.session.execute(
                        select(t.records).where(
                            t.records.c.encounter_id == encounter["id"],
                            t.records.c.kind == "stay",
                            t.records.c.status.in_(["ADMITTED", "TRANSFER_PENDING", "ON_LEAVE"]),
                        )
                    )
                )
                .mappings()
                .all()
            )
            require(
                any(
                    self.content(stay)["responsible_nurse_id"] == self.actor["id"]
                    and self.content(stay).get("nursing_responsibility_state") == "ACCEPTED"
                    for stay in stays
                ),
                "ACCESS_DENIED",
                "The accountable bedside nurse must offer nursing handover",
                403,
            )
        await s.privilege_for(
            self.session,
            body["recipient_id"],
            self.facility_id,
            body["capability"],
            encounter["service"],
        )
        require(
            body["due_at"] > db.now(),
            "INVALID_DEADLINE",
            "Record the actual future response deadline",
            422,
        )
        active = await self.session.scalar(
            select(f.index.c.record_id)
            .where(
                f.index.c.facility_id == self.facility_id,
                f.index.c.kind == "team_handover",
                f.index.c.encounter_id == encounter["id"],
                f.index.c.accountable_id == self.actor["id"],
                f.index.c.status == "OFFERED",
            )
            .limit(1)
        )
        require(not active, "HANDOVER_ALREADY_PENDING", "Resolve the existing offer first", 409)
        tasks = (
            (
                await self.session.execute(
                    select(t.records).where(
                        t.records.c.encounter_id == encounter["id"],
                        t.records.c.kind == "task",
                        t.records.c.status.in_(OPEN_TASKS),
                    )
                )
            )
            .mappings()
            .all()
        )
        snapshots = {
            row["id"]: row["version"]
            for row in tasks
            if self.content(row)["owner_id"] == self.actor["id"]
            and self.content(row).get("owner_capability", "CARE") == body["capability"]
        }
        return await self.create(
            "team_handover",
            {**body, "owner_id": self.actor["id"], "task_versions": snapshots},
            patient_id=body["patient_id"],
            encounter_id=encounter["id"],
            service=encounter["service"],
            status="OFFERED",
            contract="LWH-EXT-CLINICAL-032",
        )

    async def handover_action(self, identifier, body):
        await self.phase5()
        row = await self.linked(identifier, "team_handover", body["patient_id"])
        data = self.content(row)
        require(row["status"] == "OFFERED", "INVALID_STATE", "This offer is no longer pending", 409)
        require(
            body["action"] in {"ACCEPT", "DECLINE", "CANCEL"},
            "INVALID_ACTION",
            "Choose accept, decline or cancel",
            422,
        )
        target = data["owner_id"] if body["action"] == "CANCEL" else data["recipient_id"]
        require(self.actor["id"] == target)
        await s.privilege_for(
            self.session, self.actor["id"], self.facility_id, data["capability"], row["service"]
        )
        s.event_time(body["occurred_at"])
        if body["action"] == "ACCEPT":
            require(
                data["due_at"] > db.now(),
                "HANDOVER_RESPONSE_OVERDUE",
                "The offer expired; the sender must review and reoffer current work",
                409,
            )
            encounter = await self.row(row["encounter_id"], "encounter")
            current = self.content(encounter)
            tasks = (
                (
                    await self.session.execute(
                        select(t.records).where(
                            t.records.c.encounter_id == encounter["id"],
                            t.records.c.kind == "task",
                            t.records.c.status.in_(OPEN_TASKS),
                        )
                    )
                )
                .mappings()
                .all()
            )
            owned = {
                task["id"]: task["version"]
                for task in tasks
                if self.content(task)["owner_id"] == data["owner_id"]
                and self.content(task).get("owner_capability", "CARE") == data["capability"]
            }
            require(
                owned == data["task_versions"],
                "HANDOVER_WORK_CHANGED",
                "Open work changed; the sender must review and reoffer the complete current workload",
                409,
            )
            await self.assignment(
                self.actor["id"], row["service"], data["capability"], exclude=encounter["id"]
            )
            if data["capability"] == "CARE":
                require(
                    current["owner_id"] == data["owner_id"],
                    "HANDOVER_OWNER_CHANGED",
                    "Current encounter ownership changed",
                    409,
                )
                current["owner_id"] = self.actor["id"]
            if self.actor["id"] not in current["team_ids"]:
                current["team_ids"].append(self.actor["id"])
            await s.add_member(
                self.session, self.cfg, self.actor["id"], encounter, data["capability"]
            )
            await self.change(
                encounter,
                current,
                encounter["status"],
                encounter["version"],
                "clinical.team_handover_accepted",
                "LWH-EXT-CLINICAL-032",
            )
            for task in tasks:
                if task["id"] in owned:
                    content = self.content(task)
                    content.update(owner_id=self.actor["id"], handover_to=None)
                    content.setdefault("history", []).append(
                        {
                            "action": "TEAM_HANDOVER_ACCEPTED",
                            "actor_id": self.actor["id"],
                            "handover_id": identifier,
                            "occurred_at": body["occurred_at"],
                        }
                    )
                    await self.change(
                        task,
                        content,
                        "ACCEPTED",
                        task["version"],
                        "care.task_handover_accepted",
                        "LWH-EXT-CLINICAL-032",
                    )
            stays = (
                (
                    await self.session.execute(
                        select(t.records).where(
                            t.records.c.encounter_id == encounter["id"],
                            t.records.c.kind == "stay",
                            t.records.c.status.in_(["ADMITTED", "TRANSFER_PENDING", "ON_LEAVE"]),
                        )
                    )
                )
                .mappings()
                .all()
            )
            key = (
                "responsible_clinician_id"
                if data["capability"] == "CARE"
                else "responsible_nurse_id"
            )
            for stay in stays:
                content = self.content(stay)
                if content[key] == data["owner_id"]:
                    content[key] = self.actor["id"]
                    await self.change(
                        stay,
                        content,
                        stay["status"],
                        stay["version"],
                        "inpatient.shift_handover_accepted",
                        "LWH-EXT-CLINICAL-032",
                    )
            if data["capability"] == "CARE":
                orders = (
                    (
                        await self.session.execute(
                            select(t.records).where(
                                t.records.c.encounter_id == encounter["id"],
                                t.records.c.kind == "order",
                            )
                        )
                    )
                    .mappings()
                    .all()
                )
                for order in orders:
                    content = self.content(order)
                    if content.get("result_owner_id") == data["owner_id"]:
                        content["result_owner_id"] = self.actor["id"]
                        content.setdefault("ownership_history", []).append(
                            {
                                "handover_id": identifier,
                                "previous_owner_id": data["owner_id"],
                                "accepted_by": self.actor["id"],
                                "occurred_at": body["occurred_at"],
                            }
                        )
                        await self.change(
                            order,
                            content,
                            order["status"],
                            order["version"],
                            "diagnostic.result_responsibility_handed_over",
                            "LWH-EXT-CLINICAL-032",
                        )
        data["resolution"] = {**body, "actor_id": self.actor["id"]}
        return await self.change(
            row,
            data,
            {"ACCEPT": "ACCEPTED", "DECLINE": "DECLINED", "CANCEL": "CANCELLED"}[body["action"]],
            body["expected_version"],
            "clinical.team_handover_changed",
            "LWH-EXT-CLINICAL-032",
        )

    async def admission_order(self, body):
        await self.signed_note(body["signed_note_id"], body["patient_id"], body["encounter_id"])
        return await self.flow(
            "admission_order", {**body, "owner_id": self.actor["id"]}, status="ORDERED"
        )

    async def bed_hold(self, body):
        await self.phase5()
        _, _, encounter = await self.context(body, "NURSING")
        order = await self.linked(
            body["admission_order_id"], "admission_order", body["patient_id"], body["encounter_id"]
        )
        require(
            order["version"] == body["expected_order_version"] and order["status"] == "ORDERED",
            "ADMISSION_ORDER_NOT_CURRENT",
            "Select the current unfulfilled admission order",
            409,
        )
        require(
            body["expires_at"] > db.now(),
            "INVALID_DEADLINE",
            "Record an actual future hold expiry",
            422,
        )
        bed = (
            (
                await self.session.execute(
                    select(t.beds)
                    .where(t.beds.c.id == body["bed_id"], t.beds.c.facility_id == self.facility_id)
                    .with_for_update()
                )
            )
            .mappings()
            .first()
        )
        require(
            bed and bed["active"] and not bed["stay_id"],
            "BED_UNAVAILABLE",
            "The bed is not available",
            409,
        )
        require(
            bed["version"] == body["expected_bed_version"],
            "VERSION_CONFLICT",
            "The bed changed",
            412,
        )
        await self.available_bed(body["bed_id"], None)
        return await self.create(
            "bed_hold",
            {**body, "owner_id": self.actor["id"]},
            patient_id=body["patient_id"],
            encounter_id=encounter["id"],
            service=encounter["service"],
            status="HELD",
            contract="LWH-EXT-CLINICAL-033",
        )

    async def available_bed(self, identifier, patient_id):
        if not await self.advanced_ready():
            return []
        rows = list(
            (
                await self.session.execute(
                    select(t.records)
                    .join(f.index, f.index.c.record_id == t.records.c.id)
                    .where(
                        f.index.c.facility_id == self.facility_id,
                        f.index.c.kind == "bed_hold",
                        f.index.c.source_id == identifier,
                        f.index.c.status == "HELD",
                        f.index.c.ends_at > db.now(),
                    )
                )
            ).mappings()
        )
        require(
            not any(row["patient_id"] != patient_id for row in rows),
            "BED_RESERVED",
            "The bed is held for another admission",
            409,
        )
        return rows

    async def admission(self, body):
        holds = await self.available_bed(body["bed_id"], body["patient_id"])
        order = None
        if await self.advanced_ready():
            encounter = await self.row(body["encounter_id"], "encounter")
            config = await self.config_for(encounter["service"])
            require(
                not config
                or not config["require_admission_order"]
                or body.get("admission_order_id"),
                "ADMISSION_ORDER_REQUIRED",
                "The adopted service configuration requires a separate admission order",
                409,
            )
            if body.get("admission_order_id"):
                order = await self.linked(
                    body["admission_order_id"],
                    "admission_order",
                    body["patient_id"],
                    body["encounter_id"],
                )
                require(
                    order["status"] == "ORDERED",
                    "ADMISSION_ORDER_NOT_CURRENT",
                    "This admission order was already fulfilled or cancelled",
                    409,
                )
            for hold in holds:
                require(
                    order and self.content(hold)["admission_order_id"] == order["id"],
                    "BED_RESERVATION_MISMATCH",
                    "Use the admission order that owns this bed hold",
                    409,
                )
        if await self.advanced_ready():
            body["nursing_responsibility_state"] = "AWAITING_ACCEPTANCE"
        result = await super().admission(body)
        for hold in holds:
            await self.change(
                hold,
                {**self.content(hold), "stay_id": result["id"]},
                "CONSUMED",
                hold["version"],
                "inpatient.bed_hold_consumed",
                "LWH-EXT-CLINICAL-033",
            )
        if order:
            await self.change(
                order,
                {**self.content(order), "stay_id": result["id"]},
                "ADMITTED",
                order["version"],
                "inpatient.admission_order_fulfilled",
                "LWH-EXT-CLINICAL-033",
            )
        return result

    async def stay_action(self, identifier, body):
        if body["action"] == "ACCEPT_TRANSFER":
            row = await self.row(identifier, "stay")
            offer = self.content(row).get("transfer_offer") or {}
            require(offer.get("receiving_clinician_id") == self.actor["id"])
            await self.assignment(
                offer["receiving_nurse_id"], row["service"], "NURSING", exclude=row["encounter_id"]
            )
            await self.available_bed(
                self.content(row)["transfer_offer"]["receiving_bed_id"], row["patient_id"]
            )
        return await super().stay_action(identifier, body)

    async def ward_event(self, identifier, body):
        await self.phase5()
        row = await self.linked(identifier, "stay", body["patient_id"])
        data, action = self.content(row), body["action"]
        capability = "NURSING" if action in {"RELEASE_BED", "ACCEPT_NURSING"} else "CARE"
        await self.guard(
            capability,
            patient_id=row["patient_id"],
            encounter_id=row["encounter_id"],
            write=True,
            relationship=action != "ACCEPT_NURSING",
        )
        s.event_time(body["occurred_at"])
        status = row["status"]
        if action == "ACCEPT_NURSING":
            require(
                status == "ADMITTED"
                and data["responsible_nurse_id"] == self.actor["id"]
                and data.get("nursing_responsibility_state") != "ACCEPTED",
                "NURSING_RECEIPT_REQUIRED",
                "Only the named qualified bedside nurse can personally accept current ward care",
                409,
            )
            await self.assignment(
                self.actor["id"], row["service"], "NURSING", exclude=row["encounter_id"]
            )
            encounter = await self.row(row["encounter_id"], "encounter")
            context = self.content(encounter)
            if self.actor["id"] not in context["team_ids"]:
                context["team_ids"].append(self.actor["id"])
            await s.add_member(self.session, self.cfg, self.actor["id"], encounter, "NURSING")
            await self.change(
                encounter,
                context,
                encounter["status"],
                encounter["version"],
                "inpatient.nursing_receipt_accepted",
                "LWH-EXT-CLINICAL-034",
            )
            data["nursing_responsibility_state"] = "ACCEPTED"
            data["nursing_accepted_at"] = body["occurred_at"]
        elif action == "RELEASE_BED":
            require(
                status in {"SELF_DISCHARGED", "DECEASED", "DISCHARGED"},
                "BED_RELEASE_NOT_AUTHORISED",
                "Record the actual final clinical disposition before separately releasing the bed",
                409,
            )
            bed = (
                (
                    await self.session.execute(
                        select(t.beds).where(t.beds.c.stay_id == identifier).with_for_update()
                    )
                )
                .mappings()
                .first()
            )
            require(
                bed and bed["version"] == body["expected_bed_version"],
                "VERSION_CONFLICT",
                "Select the occupied bed's current version",
                412,
            )
            await self.session.execute(
                update(t.beds)
                .where(t.beds.c.id == bed["id"], t.beds.c.version == bed["version"])
                .values(stay_id=None, version=bed["version"] + 1)
            )
            data["bed_released_at"] = body["occurred_at"]
        elif action == "DECLINE_TRANSFER":
            require(
                status == "TRANSFER_PENDING"
                and self.actor["id"] == data.get("transfer_offer", {}).get("receiving_clinician_id")
            )
            data["declined_transfer"] = data["transfer_offer"]
            data["transfer_offer"] = None
            status = "ADMITTED"
        else:
            require(
                data["responsible_clinician_id"] == self.actor["id"],
                "ACCESS_DENIED",
                "The accountable clinician must record this disposition",
                403,
            )
            allowed_states = (
                {"ON_LEAVE"}
                if action == "RETURN"
                else {"ADMITTED", "ON_LEAVE"}
                if action in {"SELF_DISCHARGE", "DEATH"}
                else {"ADMITTED"}
            )
            require(
                status in allowed_states,
                "INVALID_STATE",
                "Review the current ward disposition",
                409,
            )
            if body.get("follow_up_owner_id"):
                await s.privilege_for(
                    self.session,
                    body["follow_up_owner_id"],
                    self.facility_id,
                    "CARE",
                    row["service"],
                )
            if action != "RETURN":
                require(
                    body.get("signed_summary_id"),
                    "SIGNED_SUMMARY_REQUIRED",
                    "Sign the actual clinical summary first",
                    409,
                )
                await self.signed_note(
                    body["signed_summary_id"], row["patient_id"], row["encounter_id"]
                )
                await self.validate_obligations(row["encounter_id"])
            if action == "LEAVE":
                require(
                    body.get("expected_return_at")
                    and body["expected_return_at"] > body["occurred_at"],
                    "RETURN_PLAN_REQUIRED",
                    "Record the agreed expected return and accountable review plan",
                    422,
                )
                encounter = await self.row(row["encounter_id"], "encounter")
                await self.task(
                    encounter,
                    "Review expected inpatient return",
                    body["instructions"],
                    body["follow_up_owner_id"],
                    body["expected_return_at"],
                    identifier,
                )
            status = {
                "LEAVE": "ON_LEAVE",
                "RETURN": "ADMITTED",
                "SELF_DISCHARGE": "SELF_DISCHARGED",
                "DEATH": "DECEASED",
            }[action]
        data.setdefault("history", []).append(
            {
                **body,
                "actor_id": self.actor["id"],
                "recorded_at": db.now(),
                "statutory_registration_inferred": False,
                "financial_settlement_inferred": False,
            }
        )
        return await self.change(
            row,
            data,
            status,
            body["expected_version"],
            "inpatient.special_disposition_recorded",
            "LWH-EXT-CLINICAL-034",
        )

    async def nursing(self, body):
        return await self.flow("nursing_assessment", body, capability="NURSING")

    async def fluid(self, body):
        return await self.flow("fluid_entry", body, capability="NURSING")

    async def instructions(self, body):
        await self.signed_note(body["signed_summary_id"], body["patient_id"], body["encounter_id"])
        result = await self.flow("care_instructions", body, closed=True)
        encounter = await self.row(body["encounter_id"], "encounter")
        await self.task(
            encounter,
            "Review continuing care and instructions",
            body["pending_work_explained"],
            body["review_owner_id"],
            body["review_due_at"],
            result["id"],
        )
        return result
