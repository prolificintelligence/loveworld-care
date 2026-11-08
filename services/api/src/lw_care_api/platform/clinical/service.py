"""Clinical transactions with version, patient, privilege and state guards."""

from decimal import Decimal

from sqlalchemy import select, update

from .. import db
from ..domain import RuleError, require
from . import store as s
from . import tables as t


class ClinicalService:
    def __init__(self, session, cfg, box, actor, facility_id, correlation):
        self.session, self.cfg, self.box = session, cfg, box
        self.actor, self.facility_id, self.correlation = actor, facility_id, correlation

    async def guard(self, capability, **kwargs):
        return await s.guard(
            self.session, self.cfg, self.actor, self.facility_id, capability, **kwargs
        )

    async def row(self, identifier, kind=None, lock=True):
        return await s.fetch(self.session, self.facility_id, identifier, kind, lock=lock)

    def content(self, row):
        return s.opened(self.box, row)["data"]

    async def create(self, kind, content, *, site=None, **kwargs):
        if kind in {
            "patient",
            "encounter",
            "stay",
            "appointment",
            "programme",
            "admission_order",
            "bed_hold",
        }:
            from ..institutional.master import accepting_new_care

            await accepting_new_care(self.session, self.facility_id)
        site = site or await s.site_for(self.session, self.cfg, self.facility_id, write=True)
        return await s.create(
            self.session,
            self.cfg,
            self.box,
            self.actor,
            site,
            kind,
            content,
            self.correlation,
            **kwargs,
        )

    async def change(self, row, content, status, version, action, contract):
        return await s.change(
            self.session,
            self.cfg,
            self.box,
            self.actor,
            row,
            content,
            status,
            version,
            self.correlation,
            action,
            contract,
        )

    async def context(self, body, capability="CARE", *, allow_closed=False, relationship=True):
        s.event_time(body["occurred_at"])
        site, privilege, encounter = await self.guard(
            capability,
            patient_id=body["patient_id"],
            encounter_id=body["encounter_id"],
            write=True,
            relationship=relationship,
        )
        require(
            allow_closed or encounter["status"] not in {"COMPLETED", "CANCELLED", "TRANSFERRED"},
            "ENCOUNTER_CLOSED",
            "Use a follow-up encounter or a permitted addendum",
            409,
        )
        return site, privilege, encounter

    async def linked(self, identifier, kind, patient_id, encounter_id=None):
        row = await self.row(identifier, kind)
        require(
            row["patient_id"] == patient_id
            and (not encounter_id or row["encounter_id"] == encounter_id),
            "PATIENT_CONTEXT_MISMATCH",
            "The referenced clinical record belongs to a different context",
            409,
        )
        if kind in {"order", "medication", "specimen", "procedure", "sharing_grant"}:
            await self.usable(row)
        return row

    async def signed_note(self, identifier, patient_id, encounter_id=None):
        row = await self.linked(identifier, "note", patient_id, encounter_id)
        require(
            row["status"] == "SIGNED",
            "SIGNED_RECORD_REQUIRED",
            "A signed clinical record is required",
            409,
        )
        await self.usable(row)
        return row

    async def usable(self, row):
        errors = (
            await self.session.execute(
                select(t.records).where(
                    t.records.c.facility_id == self.facility_id,
                    t.records.c.kind == "record_error",
                    t.records.c.patient_id == row["patient_id"],
                )
            )
        ).mappings()
        require(
            not any(self.content(e)["target_id"] == row["id"] for e in errors),
            "RECORD_ENTERED_IN_ERROR",
            "This source is marked entered in error; review its history",
            409,
        )

    async def task(
        self, encounter, title, instructions, owner_id, due_at, source_id=None, capability="CARE"
    ):
        await s.privilege_for(
            self.session, owner_id, self.facility_id, capability, encounter["service"]
        )
        await s.member_for(self.session, owner_id, self.facility_id, encounter["patient_id"])
        return await self.create(
            "task",
            {
                "title": title,
                "instructions": instructions,
                "owner_id": owner_id,
                "owner_capability": capability,
                "due_at": due_at,
                "source_id": source_id,
                "handover_to": None,
                "history": [],
            },
            patient_id=encounter["patient_id"],
            encounter_id=encounter["id"],
            service=encounter["service"],
            status="ASSIGNED",
            contract="LWH-EXT-CLINICAL-008",
            action="care.task_assigned",
        )

    async def patient(self, body):
        site, _, _ = await self.guard("REGISTER", write=True, relationship=False)
        identifier = db.uid()
        body["local_identifier"] = (
            body.get("local_identifier") or f"{self.cfg.authority_node_id[:8]}-{identifier}"
        )
        body["identifier_issuer"] = self.facility_id
        return await self.create(
            "patient",
            body,
            site=site,
            identifier=identifier,
            status="PROVISIONAL" if body["provisional"] else "CONFIRMED",
            unique_value=body["local_identifier"].casefold(),
            tokens=s.search_tokens(self.cfg, f"{body['display_name']} {body['local_identifier']}"),
        )

    async def correct_patient(self, identifier, body):
        await self.guard("REGISTER", patient_id=identifier, write=True, relationship=False)
        row = await self.row(identifier, "patient")
        before = self.content(row)
        require(
            body.get("local_identifier") in (None, before["local_identifier"]),
            "IDENTIFIER_IMMUTABLE",
            "A local identifier cannot be reassigned to another identity",
            409,
        )
        body["local_identifier"] = before["local_identifier"]
        body["identifier_issuer"] = self.facility_id
        result = await self.change(
            row,
            body,
            "PROVISIONAL" if body["provisional"] else "CONFIRMED",
            body["expected_version"],
            "records.demographics_corrected",
            "LWH-EXT-CLINICAL-002",
        )
        await self.session.execute(
            update(t.records)
            .where(t.records.c.id == identifier)
            .values(
                search_tokens=s.search_tokens(
                    self.cfg, f"{body['display_name']} {body['local_identifier']}"
                )
            )
        )
        return result

    async def encounter(self, body):
        s.event_time(body["occurred_at"])
        owns = True
        try:
            site, _, _ = await self.guard(
                "CARE",
                patient_id=body["patient_id"],
                service=body["service"],
                write=True,
                relationship=False,
            )
        except RuleError as exc:
            if exc.code != "CLINICAL_PRIVILEGE_REQUIRED":
                raise
            site, _, _ = await self.guard(
                "REGISTER",
                patient_id=body["patient_id"],
                service=body["service"],
                write=True,
                relationship=False,
            )
            owns = False
        body["owner_id"], body["team_ids"] = (
            (self.actor["id"], [self.actor["id"]]) if owns else (None, [])
        )
        result = await self.create(
            "encounter",
            body,
            site=site,
            patient_id=body["patient_id"],
            service=body["service"],
            status="ARRIVED",
            contract="LWH-EVT-015",
            action="clinical.encounter_changed",
        )
        if owns:
            await s.add_member(self.session, self.cfg, self.actor["id"], result)
        return result

    async def encounter_action(self, identifier, body, action):
        row = await self.row(identifier, "encounter")
        capability = "CARE"
        try:
            await self.guard(
                capability,
                patient_id=body["patient_id"],
                encounter_id=identifier,
                write=True,
                relationship=action not in {"join", "claim", "triage"},
            )
        except RuleError as exc:
            if action not in {"join", "triage"} or exc.code != "CLINICAL_PRIVILEGE_REQUIRED":
                raise
            capability = "NURSING"
            await self.guard(
                capability,
                patient_id=body["patient_id"],
                encounter_id=identifier,
                write=True,
                relationship=action not in {"join", "triage"},
            )
        data = self.content(row)
        require(
            row["status"] not in {"COMPLETED", "CANCELLED", "TRANSFERRED"},
            "INVALID_STATE",
            "This encounter is closed",
            409,
        )
        status = row["status"]
        if action == "claim":
            require(
                data["owner_id"] is None,
                "ENCOUNTER_ALREADY_OWNED",
                "Another clinician already accepted this encounter",
                409,
            )
            data["owner_id"] = self.actor["id"]
            data["team_ids"].append(self.actor["id"])
            status = "ACKNOWLEDGED"
            await s.add_member(self.session, self.cfg, self.actor["id"], row)
        elif action == "join":
            require(
                self.actor["id"] not in data["team_ids"],
                "INVALID_STATE",
                "You already accepted this care assignment",
                409,
            )
            # A named task/handover/admission must propose the assignment first.
            proposed = data.get("proposed_team_ids", [])
            require(
                self.actor["id"] in proposed,
                "ACCESS_DENIED",
                "A treating team invitation is required",
            )
            data["team_ids"].append(self.actor["id"])
            await s.add_member(self.session, self.cfg, self.actor["id"], row, capability)
        elif action == "start":
            require(
                status in {"ARRIVED", "TRIAGED", "ACKNOWLEDGED"},
                "INVALID_STATE",
                "Assessment has already started",
                409,
            )
            status = "IN_PROGRESS"
        elif action == "triage":
            require(
                data["owner_id"] is None or self.actor["id"] in data["team_ids"],
                "TREATING_RELATIONSHIP_REQUIRED",
                "Accept a team assignment before triaging an owned encounter",
                403,
            )
            s.event_time(body["occurred_at"])
            require(
                status in {"ARRIVED", "TRIAGED"},
                "INVALID_STATE",
                "Triage amendment requires a clinical note after assessment starts",
                409,
            )
            data["triage"] = {**body, "assessor_id": self.actor["id"]}
            status = "TRIAGED"
        elif action == "complete":
            require(
                self.actor["id"] == data["owner_id"],
                "ACCESS_DENIED",
                "Only the accountable encounter owner can complete it",
            )
            await self.signed_note(body["signed_summary_id"], body["patient_id"], identifier)
            s.event_time(body["occurred_at"])
            if body["disposition"] == "ADMITTED":
                stays = (
                    await self.session.execute(
                        select(t.records.c.id).where(
                            t.records.c.encounter_id == identifier,
                            t.records.c.kind == "stay",
                            t.records.c.status.in_(["ADMITTED", "TRANSFER_PENDING", "ON_LEAVE"]),
                        )
                    )
                ).first()
                require(
                    stays,
                    "ADMISSION_REQUIRED",
                    "Record the actual admission before this disposition",
                    409,
                )
            if body["disposition"] in {"REFERRED", "TRANSFERRED"}:
                referrals = (
                    await self.session.execute(
                        select(t.records).where(
                            t.records.c.encounter_id == identifier,
                            t.records.c.kind == "referral",
                            t.records.c.status.in_(["ACCEPTED", "TRANSFERRED", "CLOSED"]),
                        )
                    )
                ).first()
                require(
                    referrals,
                    "HANDOVER_REQUIRED",
                    "Record receiving acceptance before completing this transfer",
                    409,
                )
            await self.validate_obligations(identifier)
            data["disposition"] = {**body, "signed_by": self.actor["id"]}
            status = "COMPLETED"
        return await self.change(
            row, data, status, body["expected_version"], "clinical.encounter_changed", "LWH-EVT-015"
        )

    async def validate_obligations(self, encounter_id):
        pending = (
            await self.session.execute(
                select(t.records).where(
                    t.records.c.encounter_id == encounter_id,
                    t.records.c.kind == "task",
                    t.records.c.status.not_in(["COMPLETED", "CANCELLED"]),
                )
            )
        ).mappings()
        for task in pending:
            data = self.content(task)
            try:
                await s.privilege_for(
                    self.session,
                    data["owner_id"],
                    self.facility_id,
                    data.get("owner_capability", "CARE"),
                    task["service"],
                )
            except RuleError:
                require(
                    False,
                    "PENDING_OBLIGATION_OWNER_REQUIRED",
                    "An unresolved task needs a currently eligible owner",
                    409,
                )

    async def note(self, body, identifier=None):
        capability = "NURSING" if body["note_type"] == "NURSING" else "CARE"
        _, _, encounter = await self.context(
            body, capability, allow_closed=bool(body.get("amends_id"))
        )
        if body["confidentiality"] == "RESTRICTED" or body["note_type"] == "MENTAL_HEALTH":
            await self.guard(
                "SENSITIVE", patient_id=body["patient_id"], encounter_id=body["encounter_id"]
            )
            body["confidentiality"] = "RESTRICTED"
        if body.get("amends_id"):
            original = await self.linked(
                body["amends_id"], "note", body["patient_id"], body["encounter_id"]
            )
            require(
                original["status"] == "SIGNED",
                "SIGNED_RECORD_REQUIRED",
                "An addendum must reference retained signed evidence",
                409,
            )
            if original["confidentiality"] == "RESTRICTED":
                require(
                    body["confidentiality"] == "RESTRICTED",
                    "ACCESS_DENIED",
                    "Corrections retain source confidentiality",
                )
        if identifier:
            row = await self.linked(identifier, "note", body["patient_id"], body["encounter_id"])
            require(
                row["status"] == "DRAFT" and row["created_by"] == self.actor["id"],
                "SIGNED_CONTENT_IMMUTABLE",
                "Only your unsigned draft can be edited; use an addendum for signed content",
                409,
            )
            return await self.change(
                row,
                body,
                "DRAFT",
                body["expected_version"],
                "clinical.document_drafted",
                "LWH-EXT-CLINICAL-003",
            )
        return await self.create(
            "note",
            body,
            patient_id=body["patient_id"],
            encounter_id=body["encounter_id"],
            service=encounter["service"],
            status="DRAFT",
            confidentiality=body["confidentiality"],
        )

    async def edit_note(self, identifier, body):
        return await self.note(body, identifier)

    async def sign_note(self, identifier, body):
        row = await self.linked(identifier, "note", body["patient_id"])
        data = self.content(row)
        capability = "NURSING" if data["note_type"] == "NURSING" else "CARE"
        await self.guard(
            capability, patient_id=row["patient_id"], encounter_id=row["encounter_id"], write=True
        )
        if row["confidentiality"] == "RESTRICTED":
            await self.guard(
                "SENSITIVE", patient_id=row["patient_id"], encounter_id=row["encounter_id"]
            )
        require(
            row["status"] == "DRAFT" and row["created_by"] == self.actor["id"],
            "ACCESS_DENIED",
            "Only the author can intentionally sign their current draft",
        )
        data["attestation"] = {
            "intent_confirmed": True,
            "signed_at": db.now(),
            "signer_id": self.actor["id"],
            "reason": body["reason"],
        }
        return await self.change(
            row,
            data,
            "SIGNED",
            body["expected_version"],
            "clinical.document_amended" if data.get("amends_id") else "clinical.document_signed",
            "LWH-EVT-017" if data.get("amends_id") else "LWH-EVT-016",
        )

    async def fact(self, kind, body):
        capability = "NURSING" if kind == "observation" else "CARE"
        try:
            _, _, encounter = await self.context(body, capability)
        except RuleError as exc:
            if kind != "observation" or exc.code != "CLINICAL_PRIVILEGE_REQUIRED":
                raise
            _, _, encounter = await self.context(body, "CARE")
        return await self.create(
            kind,
            body,
            patient_id=body["patient_id"],
            encounter_id=body["encounter_id"],
            service=encounter["service"],
            status=body.get("clinical_status", "RECORDED"),
        )

    async def consent(self, body):
        _, _, encounter = await self.context(body)
        require(
            body["valid_until"] > db.now(),
            "VALIDATION_FAILED",
            "Consent validity must be explicit and current",
            422,
        )
        if body.get("supersedes_id"):
            await self.linked(body["supersedes_id"], "consent", body["patient_id"])
        return await self.create(
            "consent",
            body,
            patient_id=body["patient_id"],
            encounter_id=body["encounter_id"],
            service=encounter["service"],
            status=body["decision"],
        )

    async def valid_consent(self, identifier, patient_id):
        row = await self.linked(identifier, "consent", patient_id)
        await self.usable(row)
        data = self.content(row)
        require(
            row["status"] in {"CONSENTED", "OTHER_LAWFUL_AUTHORITY"}
            and data["valid_until"] > db.now(),
            "CONSENT_REQUIRED",
            "Current consent or recorded lawful authority is required",
            409,
        )
        successors = (
            await self.session.execute(
                select(t.records).where(
                    t.records.c.patient_id == patient_id,
                    t.records.c.facility_id == self.facility_id,
                    t.records.c.kind == "consent",
                )
            )
        ).mappings()
        require(
            not any(self.content(c).get("supersedes_id") == identifier for c in successors),
            "CONSENT_SUPERSEDED",
            "Consent has changed; review the latest decision",
            409,
        )
        return row

    async def create_task(self, body):
        _, _, encounter = await self.context(
            body, body.get("owner_capability", "CARE"), allow_closed=True
        )
        if body.get("source_id"):
            await self.linked(body["source_id"], None, body["patient_id"])
        return await self.task(
            encounter,
            body["title"],
            body["instructions"],
            body["owner_id"],
            body["due_at"],
            body.get("source_id"),
            body.get("owner_capability", "CARE"),
        )

    async def task_action(self, identifier, body):
        row = await self.linked(identifier, "task", body["patient_id"])
        await self.guard(
            self.content(row).get("owner_capability", "CARE"),
            patient_id=row["patient_id"],
            encounter_id=row["encounter_id"],
            write=True,
        )
        data, action, status = self.content(row), body["action"], row["status"]
        if action == "ACCEPT_HANDOVER":
            require(
                data.get("handover_to") == self.actor["id"],
                "ACCESS_DENIED",
                "Only the named successor can accept",
            )
            data["owner_id"], data["handover_to"] = self.actor["id"], None
            status = "ACCEPTED"
        else:
            require(
                data["owner_id"] == self.actor["id"],
                "ACCESS_DENIED",
                "Only the accountable task owner can act",
            )
            transitions = {
                "ACCEPT": ({"ASSIGNED"}, "ACCEPTED"),
                "START": ({"ACCEPTED"}, "IN_PROGRESS"),
                "COMPLETE": ({"ACCEPTED", "IN_PROGRESS", "BLOCKED"}, "COMPLETED"),
                "BLOCK": ({"ASSIGNED", "ACCEPTED", "IN_PROGRESS"}, "BLOCKED"),
                "REOPEN": ({"COMPLETED"}, "ASSIGNED"),
            }
            if action == "OFFER_HANDOVER":
                require(
                    status != "COMPLETED" and body.get("successor_id") != self.actor["id"],
                    "INVALID_STATE",
                    "Select an eligible successor for open work",
                    409,
                )
                await s.privilege_for(
                    self.session,
                    body.get("successor_id"),
                    self.facility_id,
                    data.get("owner_capability", "CARE"),
                    row["service"],
                )
                await s.member_for(
                    self.session, body["successor_id"], self.facility_id, row["patient_id"]
                )
                data["handover_to"] = body["successor_id"]
            else:
                allowed, next_status = transitions[action]
                if action == "COMPLETE" and data.get("source_id"):
                    source = await self.row(data["source_id"])
                    if source["kind"] == "result":
                        report = self.content(source)
                        require(
                            report.get("reviewed_at") and report.get("communicated_at"),
                            "RESULT_FOLLOWUP_INCOMPLETE",
                            "Record clinical review and actual communication before closing result follow-up",
                            409,
                        )
                    elif source["kind"] == "order":
                        require(
                            source["status"] in {"FULFILLED", "CANCELLED", "REJECTED"},
                            "RESULT_PENDING",
                            "The diagnostic order still has an unresolved result obligation",
                            409,
                        )
                require(
                    status in allowed,
                    "INVALID_STATE",
                    "The task changed; review its current state",
                    409,
                )
                status = next_status
        data["history"].append({**body, "actor_id": self.actor["id"], "recorded_at": db.now()})
        return await self.change(
            row, data, status, body["expected_version"], "care.task_changed", "LWH-EXT-CLINICAL-008"
        )

    async def order(self, body):
        _, _, encounter = await self.context(body)
        await s.privilege_for(
            self.session, body["result_owner_id"], self.facility_id, "CARE", encounter["service"]
        )
        await s.member_for(
            self.session, body["result_owner_id"], self.facility_id, body["patient_id"]
        )
        return await self.create(
            "order",
            {**body, "history": []},
            patient_id=body["patient_id"],
            encounter_id=body["encounter_id"],
            service=encounter["service"],
            status="DRAFT",
        )

    async def order_action(self, identifier, body):
        row = await self.linked(identifier, "order", body["patient_id"])
        action, data = body["action"], self.content(row)
        await self.guard(
            "CARE" if action in {"SIGN", "CANCEL"} else "DIAGNOSTICS",
            patient_id=row["patient_id"],
            encounter_id=row["encounter_id"],
            write=True,
        )
        transitions = {
            "SIGN": ({"DRAFT"}, "RELEASED"),
            "ACCEPT": ({"RELEASED", "ON_HOLD"}, "ACCEPTED"),
            "START": ({"ACCEPTED"}, "IN_PROGRESS"),
            "HOLD": ({"RELEASED", "ACCEPTED", "IN_PROGRESS"}, "ON_HOLD"),
            "CANCEL": ({"DRAFT", "RELEASED", "ACCEPTED", "ON_HOLD"}, "CANCELLED"),
            "REJECT": ({"RELEASED", "ACCEPTED"}, "REJECTED"),
        }
        allowed, status = transitions[action]
        require(
            row["status"] in allowed,
            "INVALID_STATE",
            "The order cannot take this action in its current state",
            409,
        )
        if action == "SIGN":
            require(
                row["created_by"] == self.actor["id"],
                "ACCESS_DENIED",
                "Only the requesting author can sign the order",
            )
            data["signed_at"], data["signer_id"] = db.now(), self.actor["id"]
            await self.task(
                await self.row(row["encounter_id"], "encounter"),
                "Diagnostic result follow-up",
                data["clinical_question"],
                data["result_owner_id"],
                db.now(),
                identifier,
            )
        data["history"].append({**body, "actor_id": self.actor["id"], "recorded_at": db.now()})
        return await self.change(
            row,
            data,
            status,
            body["expected_version"],
            "clinical.order_released" if action == "SIGN" else "clinical.order_changed",
            "LWH-EVT-018" if action == "SIGN" else "LWH-EXT-CLINICAL-011",
        )

    async def specimen(self, body):
        _, _, encounter = await self.context(body, "DIAGNOSTICS", allow_closed=True)
        order = await self.linked(
            body["order_id"], "order", body["patient_id"], body["encounter_id"]
        )
        require(
            order["status"] in {"ACCEPTED", "IN_PROGRESS"}
            and self.content(order)["order_type"] == "LABORATORY",
            "INVALID_STATE",
            "An accepted laboratory order is required",
            409,
        )
        return await self.create(
            "specimen",
            {**body, "history": []},
            patient_id=body["patient_id"],
            encounter_id=body["encounter_id"],
            service=encounter["service"],
            status="LABELLED",
            unique_value=body["accession"],
            contract="LWH-EVT-019",
            action="diagnostic.specimen_changed",
        )

    async def specimen_action(self, identifier, body):
        row = await self.linked(identifier, "specimen", body["patient_id"])
        await self.guard(
            "DIAGNOSTICS",
            patient_id=row["patient_id"],
            encounter_id=row["encounter_id"],
            write=True,
        )
        s.event_time(body["occurred_at"])
        data = self.content(row)
        order = await self.linked(data["order_id"], "order", row["patient_id"])
        require(
            order["status"] in {"ACCEPTED", "IN_PROGRESS"},
            "ORDER_NOT_CURRENT",
            "Review the current order before processing",
            409,
        )
        allowed, status = {
            "COLLECT": ({"LABELLED"}, "COLLECTED"),
            "RECEIVE": ({"COLLECTED"}, "RECEIVED"),
            "REJECT": ({"LABELLED", "COLLECTED", "RECEIVED"}, "REJECTED"),
            "ANALYSE": ({"RECEIVED"}, "ANALYSED"),
        }[body["action"]]
        require(
            row["status"] in allowed, "INVALID_STATE", "The specimen cannot take this action", 409
        )
        data["history"].append({**body, "actor_id": self.actor["id"]})
        return await self.change(
            row,
            data,
            status,
            body["expected_version"],
            "diagnostic.specimen_changed",
            "LWH-EVT-019",
        )

    async def result(self, body):
        _, _, encounter = await self.context(body, "DIAGNOSTICS", allow_closed=True)
        order = await self.linked(
            body["order_id"], "order", body["patient_id"], body["encounter_id"]
        )
        require(
            order["status"] in {"ACCEPTED", "IN_PROGRESS", "FULFILLED"},
            "ORDER_NOT_CURRENT",
            "An accepted diagnostic order is required",
            409,
        )
        order_data = self.content(order)
        if order_data["order_type"] == "LABORATORY":
            require(
                body.get("specimen_id"),
                "SPECIMEN_REQUIRED",
                "Link the actual analysed specimen",
                422,
            )
            specimen = await self.linked(
                body["specimen_id"], "specimen", body["patient_id"], body["encounter_id"]
            )
            require(
                specimen["status"] == "ANALYSED"
                and self.content(specimen)["order_id"] == order["id"],
                "SPECIMEN_MISMATCH",
                "The result needs the correct analysed specimen",
                409,
            )
        if order_data["order_type"] == "IMAGING":
            require(
                body.get("study_identifier"),
                "STUDY_REQUIRED",
                "Record the actual study/accession identifier",
                422,
            )
        if body.get("corrects_id"):
            previous = await self.linked(
                body["corrects_id"], "result", body["patient_id"], body["encounter_id"]
            )
            require(
                previous["status"] == "FINAL" and self.content(previous)["order_id"] == order["id"],
                "INVALID_STATE",
                "Corrections must reference a released report for the same order",
                409,
            )
        else:
            existing = await self.session.scalar(
                select(t.records.c.id).where(
                    t.records.c.kind == "result",
                    t.records.c.identifier_hash == s.keyed_hash(self.cfg, "result", order["id"]),
                    t.records.c.facility_id == self.facility_id,
                )
            )
            require(
                not existing,
                "RESULT_CORRECTION_REQUIRED",
                "A report already exists; use a reasoned correction",
                409,
            )
        return await self.create(
            "result",
            {**body, "history": []},
            patient_id=body["patient_id"],
            encounter_id=body["encounter_id"],
            service=encounter["service"],
            status="PRELIMINARY",
            unique_value=order["id"] if not body.get("corrects_id") else None,
        )

    async def result_action(self, identifier, body):
        row = await self.linked(identifier, "result", body["patient_id"])
        action, data = body["action"], self.content(row)
        await self.guard(
            "DIAGNOSTICS" if action == "RELEASE" else "CARE",
            patient_id=row["patient_id"],
            encounter_id=row["encounter_id"],
            write=True,
        )
        status = row["status"]
        order = await self.linked(data["order_id"], "order", row["patient_id"])
        order_data = self.content(order)
        if action == "RELEASE":
            require(
                status == "PRELIMINARY"
                and order["status"] in {"ACCEPTED", "IN_PROGRESS", "FULFILLED"},
                "INVALID_STATE",
                "Only a preliminary report on a current order can be released",
                409,
            )
            status = "FINAL"
            data["verifier_id"], data["released_at"] = self.actor["id"], db.now()
            await self.task(
                await self.row(row["encounter_id"], "encounter"),
                "Critical result review" if data["critical"] else "Released result review",
                "Review the released report, record clinical response and patient communication.",
                order_data["result_owner_id"],
                db.now(),
                identifier,
            )
            if order["status"] != "FULFILLED":
                await self.change(
                    order,
                    order_data,
                    "FULFILLED",
                    order["version"],
                    "clinical.order_changed",
                    "LWH-EXT-CLINICAL-011",
                )
        else:
            require(
                status == "FINAL" and order_data["result_owner_id"] == self.actor["id"],
                "ACCESS_DENIED",
                "The responsible result clinician must record this action",
            )
            if action == "REVIEW":
                require(
                    data.get("acknowledged_at"),
                    "ACKNOWLEDGEMENT_REQUIRED",
                    "Acknowledge the report before clinical review",
                    409,
                )
            if action == "COMMUNICATE":
                require(
                    data.get("reviewed_at"),
                    "CLINICAL_REVIEW_REQUIRED",
                    "Record clinical review before patient communication",
                    409,
                )
            field = {
                "ACKNOWLEDGE": "acknowledged_at",
                "REVIEW": "reviewed_at",
                "COMMUNICATE": "communicated_at",
            }[action]
            require(
                not data.get(field), "INVALID_STATE", "This report action is already recorded", 409
            )
            data[field] = db.now()
        data["history"].append({**body, "actor_id": self.actor["id"], "recorded_at": db.now()})
        return await self.change(
            row,
            data,
            status,
            body["expected_version"],
            (
                "diagnostic.result_amended"
                if data.get("corrects_id")
                else "diagnostic.result_released"
            )
            if action == "RELEASE"
            else "diagnostic.result_followup_recorded",
            ("LWH-EVT-021" if data.get("corrects_id") else "LWH-EVT-020")
            if action == "RELEASE"
            else "LWH-EXT-CLINICAL-007",
        )

    async def product(self, body):
        await self.guard("PHARMACY", write=True, relationship=False)
        require(
            body["valid_until"] > db.now(),
            "VALIDATION_FAILED",
            "The adopted formulary entry must be current",
            422,
        )
        return await self.create(
            "product",
            body,
            service="PHARMACY",
            status="ACTIVE",
            unique_value=body["code"]["system"]
            + ":"
            + body["code"]["code"]
            + ":"
            + body["code"]["version"],
        )

    async def medication(self, body):
        _, _, encounter = await self.context(body, "PRESCRIBE")
        product = await self.row(body["product_id"], "product")
        product_data = self.content(product)
        require(
            product["status"] == "ACTIVE" and product_data["valid_until"] > db.now(),
            "FORMULARY_EXPIRED",
            "A current adopted product is required",
            409,
        )
        require(
            body["route"] in product_data["permitted_routes"],
            "ROUTE_NOT_ADOPTED",
            "The route is outside the adopted product entry",
            422,
        )
        body["product_snapshot"] = product_data
        body["automated_checking"] = "UNAVAILABLE_MANUAL_REVIEW_RECORDED"
        body["history"] = []
        return await self.create(
            "medication",
            body,
            patient_id=body["patient_id"],
            encounter_id=body["encounter_id"],
            service=encounter["service"],
            status="DRAFT",
            contract="LWH-EVT-022",
            action="medicines.order_changed",
        )

    async def medication_action(self, identifier, body):
        row = await self.linked(identifier, "medication", body["patient_id"])
        action, data = body["action"], self.content(row)
        await self.guard(
            "PHARMACY" if action == "VERIFY" else "PRESCRIBE",
            patient_id=row["patient_id"],
            encounter_id=row["encounter_id"],
            write=True,
        )
        if action in {"SIGN", "VERIFY", "RESUME"}:
            product = await self.row(data["product_id"], "product")
            require(
                product["status"] == "ACTIVE" and self.content(product)["valid_until"] > db.now(),
                "FORMULARY_EXPIRED",
                "Review the current adopted product before signing or verifying",
                409,
            )
        allowed, status = {
            "SIGN": ({"DRAFT"}, "SIGNED"),
            "VERIFY": ({"SIGNED"}, "VERIFIED"),
            "HOLD": ({"SIGNED", "VERIFIED"}, "ON_HOLD"),
            "RESUME": ({"ON_HOLD"}, "SIGNED"),
            "STOP": ({"SIGNED", "VERIFIED", "ON_HOLD"}, "STOPPED"),
        }[action]
        require(
            row["status"] in allowed, "INVALID_STATE", "Review the current medication order", 409
        )
        if action == "SIGN":
            require(
                row["created_by"] == self.actor["id"],
                "ACCESS_DENIED",
                "The actual prescriber must sign",
            )
            data["signed_at"], data["prescriber_id"] = db.now(), self.actor["id"]
        data["history"].append({**body, "actor_id": self.actor["id"], "recorded_at": db.now()})
        return await self.change(
            row, data, status, body["expected_version"], "medicines.order_changed", "LWH-EVT-022"
        )

    async def lot(self, body):
        await self.guard("PHARMACY", write=True, relationship=False)
        await self.row(body["product_id"], "product")
        require(
            body["expires_at"] > db.now(),
            "VALIDATION_FAILED",
            "Expired stock cannot be received as available",
            422,
        )
        identifier = db.uid()
        values = {
            "id": identifier,
            "facility_id": self.facility_id,
            "product_id": body["product_id"],
            "batch": body["batch"],
            "expires_at": body["expires_at"],
            "quantity": Decimal(body["quantity"]),
            "unit": body["unit"],
            "status": "AVAILABLE",
            "version": 1,
        }
        await self.session.execute(t.lots.insert().values(**values))
        await self.session.execute(
            t.movements.insert().values(
                id=db.uid(),
                lot_id=identifier,
                source_id=identifier,
                quantity=Decimal(body["quantity"]),
                reason=body["evidence"],
                actor_id=self.actor["id"],
                recorded_at=db.now(),
            )
        )
        await s.audit(
            self.session,
            self.actor,
            self.facility_id,
            None,
            "stock.received",
            self.correlation,
            purpose="MEDICATION_SERVICE",
        )
        return {**values, "quantity": str(values["quantity"])}

    async def lot_action(self, identifier, body):
        await self.guard("PHARMACY", write=True, relationship=False)
        lot = (
            (
                await self.session.execute(
                    select(t.lots)
                    .where(t.lots.c.id == identifier, t.lots.c.facility_id == self.facility_id)
                    .with_for_update()
                )
            )
            .mappings()
            .first()
        )
        require(lot, "NOT_FOUND_OR_NOT_PERMITTED", "Stock lot unavailable", 404)
        require(
            lot["version"] == body["expected_version"],
            "VERSION_CONFLICT",
            "The stock lot changed",
            412,
        )
        status = {"QUARANTINE": "QUARANTINED", "RECALL": "RECALLED", "RELEASE": "AVAILABLE"}[
            body["action"]
        ]
        if status == "AVAILABLE":
            require(
                lot["expires_at"] > db.now() and lot["status"] != "RECALLED",
                "INVALID_STATE",
                "Expired or recalled stock cannot be released",
                409,
            )
        values = {"status": status, "version": lot["version"] + 1}
        await self.session.execute(update(t.lots).where(t.lots.c.id == identifier).values(**values))
        await s.audit(
            self.session,
            self.actor,
            self.facility_id,
            None,
            "stock." + status.lower(),
            self.correlation,
            purpose="MEDICATION_SERVICE",
        )
        await self.session.execute(
            t.movements.insert().values(
                id=db.uid(),
                lot_id=identifier,
                source_id=db.uid(),
                quantity=0,
                reason=body["reason"],
                actor_id=self.actor["id"],
                recorded_at=db.now(),
            )
        )
        return {**dict(lot), **values, "quantity": str(lot["quantity"])}

    async def dispense(self, body):
        _, _, encounter = await self.context(body, "PHARMACY", allow_closed=True)
        medication = await self.linked(
            body["medication_id"], "medication", body["patient_id"], body["encounter_id"]
        )
        data = self.content(medication)
        require(
            medication["status"] == "VERIFIED"
            and medication["version"] == body["expected_order_version"],
            "ORDER_NOT_CURRENT",
            "The current pharmacy-verified order is required",
            409,
        )
        require(
            data["stops_at"] > body["occurred_at"],
            "ORDER_EXPIRED",
            "The medication order has stopped",
            409,
        )
        lot = (
            (
                await self.session.execute(
                    select(t.lots)
                    .where(t.lots.c.id == body["lot_id"], t.lots.c.facility_id == self.facility_id)
                    .with_for_update()
                )
            )
            .mappings()
            .first()
        )
        require(
            lot and lot["product_id"] == data["product_id"],
            "PRODUCT_MISMATCH",
            "The lot must match the exact ordered product",
            409,
        )
        require(
            lot["status"] == "AVAILABLE" and lot["expires_at"] > db.now(),
            "STOCK_UNAVAILABLE",
            "The lot is expired, recalled or quarantined",
            409,
        )
        require(
            lot["version"] == body["expected_lot_version"],
            "VERSION_CONFLICT",
            "The stock lot changed",
            412,
        )
        quantity = Decimal(body["quantity"])
        require(
            lot["quantity"] >= quantity,
            "INSUFFICIENT_STOCK",
            "The lot has insufficient available quantity",
            409,
        )
        identifier = db.uid()
        result = await self.create(
            "dispense",
            {
                **body,
                "batch": lot["batch"],
                "unit": lot["unit"],
                "product_snapshot": data["product_snapshot"],
            },
            identifier=identifier,
            patient_id=body["patient_id"],
            encounter_id=body["encounter_id"],
            service=encounter["service"],
            status="DISPENSED",
            contract="LWH-EVT-023",
            action="medicines.dispensed",
        )
        changed = await self.session.execute(
            update(t.lots)
            .where(
                t.lots.c.id == lot["id"],
                t.lots.c.version == lot["version"],
                t.lots.c.quantity >= quantity,
            )
            .values(quantity=lot["quantity"] - quantity, version=lot["version"] + 1)
        )
        require(changed.rowcount == 1, "STOCK_CONFLICT", "The available stock changed", 409)
        await self.session.execute(
            t.movements.insert().values(
                id=db.uid(),
                lot_id=lot["id"],
                source_id=identifier,
                quantity=-quantity,
                reason=body["verification"],
                actor_id=self.actor["id"],
                recorded_at=db.now(),
            )
        )
        return result

    async def administration(self, body):
        _, _, encounter = await self.context(body, "NURSING")
        medication = await self.linked(
            body["medication_id"], "medication", body["patient_id"], body["encounter_id"]
        )
        data = self.content(medication)
        require(
            medication["status"] == "VERIFIED"
            and medication["version"] == body["expected_order_version"],
            "ORDER_NOT_CURRENT",
            "Administration requires the current verified order",
            409,
        )
        if body["outcome"] == "GIVEN":
            require(
                data["starts_at"] <= body["occurred_at"] < data["stops_at"],
                "ORDER_EXPIRED",
                "The actual event is outside the order period",
                409,
            )
            require(
                Decimal(body["dose"]) == Decimal(data["dose"])
                and body["dose_unit"] == data["dose_unit"]
                and body["route"] == data["route"],
                "DOSE_ORDER_MISMATCH",
                "Record the current prescribed dose, unit and route; amendments require a new reviewed order",
                409,
            )
        # Unique actual task identity spans clients and operation keys. A replay cannot create a second MAR effect.
        unique = f"{medication['id']}:{body['occurrence_key']}"
        slot = f"{medication['id']}:{body['scheduled_at']}"
        require(
            body["occurrence_key"] == s.keyed_hash(self.cfg, "administration_slot", slot),
            "INVALID_OCCURRENCE_KEY",
            "Use the server-issued medication occurrence key",
            422,
        )
        return await self.create(
            "administration",
            body,
            patient_id=body["patient_id"],
            encounter_id=body["encounter_id"],
            service=encounter["service"],
            status=body["outcome"],
            unique_value=unique,
            contract="LWH-EVT-024",
            action="medicines.administered_or_omitted",
        )

    async def bed(self, body):
        await self.guard("REGISTER", write=True, relationship=False)
        values = {
            "id": db.uid(),
            "facility_id": self.facility_id,
            "ward": body["ward"],
            "label": body["label"],
            "active": True,
            "stay_id": None,
            "version": 1,
        }
        await self.session.execute(t.beds.insert().values(**values))
        await s.audit(
            self.session,
            self.actor,
            self.facility_id,
            None,
            "inpatient.bed_configured",
            self.correlation,
            purpose="REGISTRATION",
        )
        return values

    async def admission(self, body):
        _, _, encounter = await self.context(body)
        require(
            body["responsible_clinician_id"] == self.actor["id"],
            "ACCESS_DENIED",
            "The admitting clinician must accept responsibility",
        )
        await self.signed_note(
            body["signed_admission_note_id"], body["patient_id"], body["encounter_id"]
        )
        await s.privilege_for(
            self.session,
            body["responsible_nurse_id"],
            self.facility_id,
            "NURSING",
            encounter["service"],
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
            "The local bed is not available",
            409,
        )
        require(
            bed["version"] == body["expected_bed_version"],
            "VERSION_CONFLICT",
            "The bed changed",
            412,
        )
        active = await self.session.scalar(
            select(t.records.c.id).where(
                t.records.c.kind == "stay",
                t.records.c.patient_id == body["patient_id"],
                t.records.c.facility_id == self.facility_id,
                t.records.c.status.in_(["ADMITTED", "TRANSFER_PENDING", "ON_LEAVE"]),
            )
        )
        require(
            not active, "ACTIVE_STAY_EXISTS", "This patient already has an active local stay", 409
        )
        result = await self.create(
            "stay",
            {**body, "history": []},
            patient_id=body["patient_id"],
            encounter_id=body["encounter_id"],
            service=encounter["service"],
            status="ADMITTED",
            contract="LWH-EVT-026",
            action="inpatient.stay_changed",
        )
        changed = await self.session.execute(
            update(t.beds)
            .where(
                t.beds.c.id == bed["id"],
                t.beds.c.version == bed["version"],
                t.beds.c.stay_id.is_(None),
            )
            .values(stay_id=result["id"], version=bed["version"] + 1)
        )
        require(
            changed.rowcount == 1, "BED_UNAVAILABLE", "Another admission occupied this bed", 409
        )
        if (self.session.info.get("platform_schema_version") or 0) < 7:
            await s.add_member(
                self.session, self.cfg, body["responsible_nurse_id"], encounter, "NURSING"
            )
        return result

    async def stay_action(self, identifier, body):
        row = await self.linked(identifier, "stay", body["patient_id"])
        await self.guard(
            "CARE",
            patient_id=row["patient_id"],
            encounter_id=row["encounter_id"],
            write=True,
            relationship=body["action"] != "ACCEPT_TRANSFER",
        )
        s.event_time(body["occurred_at"])
        data, action, status = self.content(row), body["action"], row["status"]
        require(
            status in {"ADMITTED", "TRANSFER_PENDING"}, "INVALID_STATE", "This stay is closed", 409
        )
        if action == "OFFER_TRANSFER":
            require(
                status == "ADMITTED" and data["responsible_clinician_id"] == self.actor["id"],
                "ACCESS_DENIED",
                "The accountable clinician must offer transfer",
            )
            require(
                all(
                    body.get(k)
                    for k in ("receiving_bed_id", "receiving_clinician_id", "receiving_nurse_id")
                ),
                "VALIDATION_FAILED",
                "Name the receiving bed, clinician and nurse",
                422,
            )
            require(
                body["receiving_bed_id"] != data["bed_id"],
                "INVALID_STATE",
                "Select a different receiving bed",
                409,
            )
            await s.privilege_for(
                self.session,
                body["receiving_clinician_id"],
                self.facility_id,
                "CARE",
                row["service"],
            )
            await s.privilege_for(
                self.session,
                body["receiving_nurse_id"],
                self.facility_id,
                "NURSING",
                row["service"],
            )
            data["transfer_offer"] = body
            # The offered successor sees only the scoped handover until accepting.
            status = "TRANSFER_PENDING"
        elif action == "ACCEPT_TRANSFER":
            offer = data.get("transfer_offer", {})
            require(
                status == "TRANSFER_PENDING"
                and offer.get("receiving_clinician_id") == self.actor["id"],
                "ACCESS_DENIED",
                "Only the named receiving clinician can accept",
            )
            target = (
                (
                    await self.session.execute(
                        select(t.beds)
                        .where(
                            t.beds.c.id == offer["receiving_bed_id"],
                            t.beds.c.facility_id == self.facility_id,
                        )
                        .with_for_update()
                    )
                )
                .mappings()
                .first()
            )
            require(
                target and target["active"] and not target["stay_id"],
                "BED_UNAVAILABLE",
                "The receiving bed is unavailable",
                409,
            )
            await self.session.execute(
                update(t.beds)
                .where(t.beds.c.stay_id == identifier)
                .values(stay_id=None, version=t.beds.c.version + 1)
            )
            assigned = await self.session.execute(
                update(t.beds)
                .where(t.beds.c.id == target["id"], t.beds.c.stay_id.is_(None))
                .values(stay_id=identifier, version=target["version"] + 1)
            )
            require(assigned.rowcount == 1, "BED_UNAVAILABLE", "The receiving bed changed", 409)
            data.update(
                bed_id=target["id"],
                responsible_clinician_id=self.actor["id"],
                responsible_nurse_id=offer["receiving_nurse_id"],
            )
            encounter = await self.row(row["encounter_id"], "encounter")
            await s.add_member(self.session, self.cfg, self.actor["id"], encounter)
            if (self.session.info.get("platform_schema_version") or 0) < 7:
                await s.add_member(
                    self.session, self.cfg, offer["receiving_nurse_id"], encounter, "NURSING"
                )
            else:
                data["nursing_responsibility_state"] = "AWAITING_ACCEPTANCE"
            data["transfer_offer"] = None
            status = "ADMITTED"
        elif action == "DISCHARGE":
            require(
                data["responsible_clinician_id"] == self.actor["id"],
                "ACCESS_DENIED",
                "The accountable clinician must discharge",
            )
            require(
                body.get("signed_summary_id")
                and body.get("instructions")
                and body.get("medication_reconciliation"),
                "DISCHARGE_PACKAGE_REQUIRED",
                "A signed summary, instructions and medicine reconciliation are required",
                422,
            )
            await self.signed_note(
                body["signed_summary_id"], row["patient_id"], row["encounter_id"]
            )
            await self.validate_obligations(row["encounter_id"])
            await self.session.execute(
                update(t.beds)
                .where(t.beds.c.stay_id == identifier)
                .values(stay_id=None, version=t.beds.c.version + 1)
            )
            status = "DISCHARGED"
        data["history"].append({**body, "actor_id": self.actor["id"]})
        return await self.change(
            row, data, status, body["expected_version"], "inpatient.stay_changed", "LWH-EVT-026"
        )

    async def programme(self, body):
        _, _, encounter = await self.context(body)
        if body["programme_type"] == "MENTAL_HEALTH":
            await self.guard(
                "SENSITIVE", patient_id=body["patient_id"], encounter_id=body["encounter_id"]
            )
        await s.privilege_for(
            self.session, body["responsible_id"], self.facility_id, "CARE", encounter["service"]
        )
        if body.get("linked_patient_id"):
            require(
                body.get("relationship_evidence")
                and body["linked_patient_id"] != body["patient_id"],
                "RELATIONSHIP_EVIDENCE_REQUIRED",
                "Each linked patient needs a separate identity and relationship evidence",
                422,
            )
            await self.guard("CARE", patient_id=body["linked_patient_id"])
        result = await self.create(
            "programme",
            {**body, "reviews": []},
            patient_id=body["patient_id"],
            encounter_id=body["encounter_id"],
            service=encounter["service"],
            status="ACTIVE",
            confidentiality="RESTRICTED"
            if body["programme_type"] == "MENTAL_HEALTH"
            else "STANDARD",
        )
        await self.task(
            encounter,
            "Programme review",
            body["goals"],
            body["responsible_id"],
            body["review_at"],
            result["id"],
        )
        return result

    async def programme_review(self, identifier, body):
        row = await self.linked(identifier, "programme", body["patient_id"])
        await self.guard(
            "CARE", patient_id=row["patient_id"], encounter_id=row["encounter_id"], write=True
        )
        if row["confidentiality"] == "RESTRICTED":
            await self.guard(
                "SENSITIVE", patient_id=row["patient_id"], encounter_id=row["encounter_id"]
            )
        s.event_time(body["occurred_at"])
        data = self.content(row)
        require(
            data["responsible_id"] == self.actor["id"],
            "ACCESS_DENIED",
            "The programme owner must record the review",
        )
        data["reviews"].append({**body, "actor_id": self.actor["id"]})
        data["review_at"] = body["next_review_at"]
        result = await self.change(
            row,
            data,
            "ACTIVE",
            body["expected_version"],
            "clinical.programme_reviewed",
            "LWH-EXT-CLINICAL-004",
        )
        await self.task(
            await self.row(row["encounter_id"], "encounter"),
            "Programme review",
            body["plan"],
            data["responsible_id"],
            body["next_review_at"],
            identifier,
        )
        return result

    async def procedure(self, body):
        _, _, encounter = await self.context(body, "PROCEDURE")
        await self.valid_consent(body["consent_id"], body["patient_id"])
        require(
            self.actor["id"] in body["team_ids"],
            "ACCESS_DENIED",
            "The operator must belong to the planned team",
        )
        for actor_id in body["team_ids"]:
            await s.privilege_for(
                self.session, actor_id, self.facility_id, "PROCEDURE", encounter["service"]
            )
        await s.privilege_for(
            self.session, body["result_owner_id"], self.facility_id, "CARE", encounter["service"]
        )
        return await self.create(
            "procedure",
            {**body, "history": [], "operator_id": self.actor["id"]},
            patient_id=body["patient_id"],
            encounter_id=body["encounter_id"],
            service=encounter["service"],
            status="PLANNED",
        )

    async def procedure_action(self, identifier, body):
        row = await self.linked(identifier, "procedure", body["patient_id"])
        await self.guard(
            "PROCEDURE", patient_id=row["patient_id"], encounter_id=row["encounter_id"], write=True
        )
        s.event_time(body["occurred_at"])
        action, data, status = body["action"], self.content(row), row["status"]
        require(
            self.actor["id"] in data["team_ids"]
            or (action == "ACCEPT_HANDOVER" and data.get("handover_to") == self.actor["id"]),
            "ACCESS_DENIED",
            "Only the procedure team or named successor can act",
        )
        for actor_id in body["participants"]:
            await s.privilege_for(
                self.session, actor_id, self.facility_id, "PROCEDURE", row["service"]
            )
        require(
            self.actor["id"] in body["participants"],
            "ACCESS_DENIED",
            "The attesting actor must be an actual participant",
        )
        transitions = {
            "SIGN_IN": ({"PLANNED"}, "SIGNED_IN"),
            "TIME_OUT": ({"SIGNED_IN"}, "TIME_OUT_COMPLETE"),
            "PERFORM": ({"TIME_OUT_COMPLETE"}, "PERFORMED"),
            "SIGN_OUT": ({"PERFORMED"}, "RECOVERY"),
            "OFFER_HANDOVER": ({"RECOVERY"}, "HANDOVER_PENDING"),
            "ACCEPT_HANDOVER": ({"HANDOVER_PENDING"}, "HANDED_OVER"),
            "CANCEL": ({"PLANNED", "SIGNED_IN"}, "CANCELLED"),
        }
        allowed, next_status = transitions[action]
        require(
            status in allowed, "INVALID_STATE", "The procedure phase cannot take this action", 409
        )
        if action in {"SIGN_IN", "TIME_OUT", "PERFORM"}:
            await self.valid_consent(data["consent_id"], row["patient_id"])
        if action == "PERFORM":
            require(
                body.get("actual_procedure")
                and body.get("complications")
                and body.get("specimens")
                and body.get("implants_devices"),
                "PERFORMED_RECORD_REQUIRED",
                "Record the actual procedure, specimens, devices and complications with explicit absence where applicable",
                422,
            )
            data["performed"] = body
        elif action == "OFFER_HANDOVER":
            require(
                body.get("successor_id") and body["successor_id"] != self.actor["id"],
                "SUCCESSOR_REQUIRED",
                "Name an independent eligible receiver",
                422,
            )
            await s.privilege_for(
                self.session, body["successor_id"], self.facility_id, "PROCEDURE", row["service"]
            )
            data["handover_to"] = body["successor_id"]
        elif action == "ACCEPT_HANDOVER":
            require(
                data.get("handover_to") == self.actor["id"],
                "ACCESS_DENIED",
                "The named successor must accept",
            )
            data["responsible_id"] = self.actor["id"]
        data["history"].append({**body, "actor_id": self.actor["id"]})
        return await self.change(
            row,
            data,
            next_status,
            body["expected_version"],
            "clinical.procedure_recorded"
            if action == "PERFORM"
            else "clinical.procedure_phase_recorded",
            "LWH-EVT-027" if action == "PERFORM" else "LWH-EXT-CLINICAL-009",
        )

    async def transfusion(self, body):
        _, _, encounter = await self.context(body, "PROCEDURE")
        procedure = await self.linked(
            body["procedure_id"], "procedure", body["patient_id"], body["encounter_id"]
        )
        require(
            procedure["status"] in {"TIME_OUT_COMPLETE", "PERFORMED", "RECOVERY"},
            "INVALID_STATE",
            "The authorised procedure must reach the appropriate clinical phase",
            409,
        )
        await self.valid_consent(self.content(procedure)["consent_id"], body["patient_id"])
        require(
            body["witness_id"] != self.actor["id"],
            "INDEPENDENT_WITNESS_REQUIRED",
            "A different authorised witness is required",
            422,
        )
        await s.privilege_for(
            self.session, body["witness_id"], self.facility_id, "PROCEDURE", encounter["service"]
        )
        return await self.create(
            "transfusion",
            {**body, "history": [], "witness_accepted": False},
            patient_id=body["patient_id"],
            encounter_id=body["encounter_id"],
            service=encounter["service"],
            status="AWAITING_WITNESS",
            unique_value=body["component_identifier"],
        )

    async def transfusion_action(self, identifier, body):
        row = await self.linked(identifier, "transfusion", body["patient_id"])
        await self.guard(
            "PROCEDURE", patient_id=row["patient_id"], encounter_id=row["encounter_id"], write=True
        )
        s.event_time(body["occurred_at"])
        data, action, status = self.content(row), body["action"], row["status"]
        if action == "START":
            require(
                status == "AWAITING_WITNESS"
                and self.actor["id"] == data["witness_id"]
                and body["witness_id"] == row["created_by"],
                "INDEPENDENT_WITNESS_REQUIRED",
                "The named independent witness must confirm the actual start",
            )
            data["witness_accepted"] = True
            status = "IN_PROGRESS"
        else:
            require(
                status in {"IN_PROGRESS", "REACTION_REVIEW"}
                and self.actor["id"] in {row["created_by"], data["witness_id"]},
                "INVALID_STATE",
                "Only the current transfusion team can record actual monitoring or closure",
                409,
            )
            status = {
                "MONITOR": status,
                "STOP": "STOPPED",
                "COMPLETE": "COMPLETED",
                "REACTION": "REACTION_REVIEW",
            }[action]
            if action == "REACTION":
                procedure = await self.row(data["procedure_id"], "procedure")
                await self.task(
                    await self.row(row["encounter_id"], "encounter"),
                    "Transfusion reaction review",
                    body["observation"],
                    self.content(procedure)["result_owner_id"],
                    db.now(),
                    identifier,
                )
        data["history"].append({**body, "actor_id": self.actor["id"]})
        return await self.change(
            row,
            data,
            status,
            body["expected_version"],
            "clinical.transfusion_recorded",
            "LWH-EXT-CLINICAL-010",
        )

    async def referral(self, body):
        _, _, encounter = await self.context(body)
        await self.signed_note(body["summary_note_id"], body["patient_id"], body["encounter_id"])
        _, share = await self.valid_share(
            body["sharing_grant_id"], body["patient_id"], body["destination"], "REFERRAL"
        )
        require(
            body["summary_note_id"] in share["record_ids"],
            "SHARING_NOT_AUTHORISED",
            "The signed referral summary must be included in the sharing scope",
            403,
        )
        require(
            body["owner_id"] == self.actor["id"],
            "ACCESS_DENIED",
            "The referring clinician must retain initial responsibility",
        )
        return await self.create(
            "referral",
            {**body, "history": []},
            patient_id=body["patient_id"],
            encounter_id=body["encounter_id"],
            service=encounter["service"],
            status="DRAFT",
            contract="LWH-EVT-028",
            action="referral.state_changed",
        )

    async def referral_action(self, identifier, body):
        row = await self.linked(identifier, "referral", body["patient_id"])
        await self.guard(
            "CARE", patient_id=row["patient_id"], encounter_id=row["encounter_id"], write=True
        )
        s.event_time(body["occurred_at"])
        data, action = self.content(row), body["action"]
        require(
            data["owner_id"] == self.actor["id"],
            "ACCESS_DENIED",
            "The originating accountable clinician must act",
        )
        allowed, status = {
            "REQUEST": ({"DRAFT"}, "REQUESTED"),
            "RECORD_ACCEPTANCE": ({"REQUESTED"}, "ACCEPTED"),
            "TRANSFER": ({"ACCEPTED"}, "TRANSFERRED"),
            "CLOSE": ({"TRANSFERRED"}, "CLOSED"),
            "CANCEL": ({"DRAFT", "REQUESTED", "ACCEPTED"}, "CANCELLED"),
        }[action]
        require(
            row["status"] in allowed, "INVALID_STATE", "The referral cannot take this action", 409
        )
        if action == "REQUEST":
            await self.valid_share(
                data["sharing_grant_id"], row["patient_id"], data["destination"], "REFERRAL"
            )
        if action == "RECORD_ACCEPTANCE":
            require(
                body.get("receiver_name") and body.get("acceptance_evidence"),
                "ACCEPTANCE_EVIDENCE_REQUIRED",
                "Record the actual named receiver and acceptance evidence",
                422,
            )
        if action == "TRANSFER":
            require(
                body.get("actual_handover"), "HANDOVER_REQUIRED", "Record the actual handover", 422
            )
        data["history"].append({**body, "actor_id": self.actor["id"]})
        return await self.change(
            row, data, status, body["expected_version"], "referral.state_changed", "LWH-EVT-028"
        )

    async def record_error(self, identifier, body):
        row = await self.row(identifier)
        require(
            row["patient_id"] == body["patient_id"]
            and row["kind"]
            not in {"patient", "encounter", "record_error", "invoice", "cash_receipt", "tariff"},
            "PATIENT_CONTEXT_MISMATCH",
            "Select a clinical source record in this chart",
            409,
        )
        require(
            row["version"] == body["expected_version"],
            "VERSION_CONFLICT",
            "Review the latest source version",
            412,
        )
        await self.guard("RECORDS", patient_id=row["patient_id"], write=True)
        if row["confidentiality"] == "RESTRICTED":
            await self.guard("SENSITIVE", patient_id=row["patient_id"], service=row["service"])
        return await self.create(
            "record_error",
            {**body, "target_id": identifier, "target_version": row["version"]},
            patient_id=row["patient_id"],
            encounter_id=row["encounter_id"],
            service=row["service"],
            status="ENTERED_IN_ERROR",
            contract="LWH-EVT-017",
            action="clinical.document_amended",
            unique_value=identifier,
            confidentiality=row["confidentiality"],
        )
