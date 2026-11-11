"""Immutable form snapshots; capture never becomes plan agreement or resolution."""

from uuid import UUID

from fastapi import Request
from sqlalchemy import and_, or_, select

from .. import db
from ..domain import RuleError, expected, require
from . import capture_contracts as c
from . import tables as t
from .base import Service
from .corrective import CorrectivePlans
from .teams import team_record

CONTRACT = "LWH-EXT-CORRECTIVE-CAPTURE-001"
ACTION = "standards.corrective_form_captured"


class CaptureService(CorrectivePlans, Service):
    def authority(self):
        try:
            return str(UUID(self.cfg.authority_node_id))
        except ValueError:
            require(
                False,
                "CAPTURE_AUTHORITY_UNAVAILABLE",
                "Canonical capture requires an actual UUID authority identity",
                503,
            )

    async def context(self, identifier, body=None, *, write=False):
        finding = await self.row(t.findings, identifier, lock=write)
        case, facility = await self.case(finding["case_id"], write=write)
        if body is not None:
            respondent = self.actor["id"] == finding["owner_id"] == case["respondent_id"]
            reviewer = self.actor["id"] == case["reviewer_id"]
            require(respondent or reviewer)
            await self.person(
                self.actor["id"],
                {"FACILITY_ADMIN"} if respondent else {"STANDARDS_REVIEWER"},
                facility,
            )
            form = body["form"]
            require(
                form["actor_id"] == self.actor["id"]
                and form["facility_or_unit_id"] == facility["id"],
                "CAPTURE_SCOPE_MISMATCH",
                "Record the form under your actual identity and finding facility",
                409,
            )
            require(
                form["authority_node_id"] == self.authority(),
                "AUTHORITY_NODE_MISMATCH",
                "Refresh the current authority before recording the form",
                409,
            )
        return finding, case, facility

    async def projection(self, finding, case):
        known = {"finding_id": finding["id"]}
        binding = {
            "finding_id": finding["id"],
            "finding_version": finding["version"],
            "case_id": case["id"],
            "case_version": case["version"],
        }
        try:
            plan = await self.agreed_plan(
                finding, case, current_parties=finding["state"] != "RESOLVED"
            )
        except RuleError:
            return known, binding
        known.update(required_action=plan["required_action"], due_at=plan["due_at"])
        binding.update(
            plan_id=plan["plan_id"], plan_agreement_version=plan["agreement_finding_version"]
        )
        if plan.get("owner_team"):
            known["owner_team_id"] = plan["owner_team"]["id"]
            binding["owner_team_version"] = plan["owner_team"]["version"]
        fact = await self.finding_fact(finding, "standards.response_submitted")
        if not fact:
            return known, binding
        response = fact["details"]["response"]
        try:
            data = await self.response_plan(
                finding, case, response, current_parties=finding["state"] != "RESOLVED"
            )
        except RuleError:
            return known, binding
        known.update(response=data["completion_evidence"], evidence_refs=data["evidence_ids"])
        binding.update(response_id=response["id"], response_author_id=response["author_id"])
        row = (
            (
                await self.session.execute(
                    select(t.journal)
                    .where(
                        t.journal.c.resource_id == finding["id"],
                        t.journal.c.action == "standards.response_reviewed",
                        t.journal.c.version == finding["version"],
                    )
                    .limit(1)
                )
            )
            .mappings()
            .first()
        )
        if row:
            review = self.open(row["payload_ciphertext"])["details"]
            if review["response_id"] == response["id"]:
                known["review_result"] = review["decision"] + ": " + review["evidence"]
                binding.update(review_version=row["version"], review_actor_id=row["actor_id"])
        return known, binding

    async def record(self, identifier, body):
        finding, case, facility = await self.context(identifier, body, write=True)
        expected(finding, body["expected_version"])
        expected(case, body["expected_case_version"])
        require(
            case["state"] == "INSPECTED",
            "INVALID_STATE",
            "Record corrective forms while the case is under review",
            409,
        )
        form = body["form"]
        require(
            not form.get("recorded_at") or form["recorded_at"] <= db.now(),
            "VALIDATION_FAILED",
            "A recorded form time cannot be in the future",
            422,
        )
        answers = form["answers"]
        if isinstance(answers.get("finding_id"), str):
            require(
                answers["finding_id"] == finding["id"],
                "CAPTURE_SCOPE_MISMATCH",
                "The answer must identify this actual source finding",
                409,
            )
        if isinstance(answers.get("owner_team_id"), str):
            team = await team_record(self, answers["owner_team_id"])
            require(
                team["facility_id"] == facility["id"],
                "CAPTURE_SCOPE_MISMATCH",
                "Team reference belongs to another facility",
                409,
            )
        if isinstance(answers.get("evidence_refs"), list):
            identifiers = answers["evidence_refs"]
            require(
                len(set(identifiers)) == len(identifiers),
                "VALIDATION_FAILED",
                "Do not duplicate evidence references",
                422,
            )
            # Even drafts cannot use references to another case or criterion.
            await self.valid_files(case, identifiers, finding["criterion"])
        known, binding = await self.projection(finding, case)
        if form["stage"] == "submitted":
            for key, answer in answers.items():
                if isinstance(answer, dict) or key == "finding_id" or answer == []:
                    continue
                if key == "review_result":
                    require(
                        self.actor["id"] == case["reviewer_id"],
                        "INDEPENDENT_REVIEW_REQUIRED",
                        "Only the assigned independent reviewer can record the actual review result",
                        409,
                    )
                require(
                    key in known
                    and (
                        set(answer) == set(known[key])
                        if key == "evidence_refs"
                        else answer == known[key]
                    ),
                    "CAPTURE_SOURCE_MISMATCH",
                    "Use the actual current recorded source value, or record an explicit absence reason",
                    409,
                )
        identifier, at = db.uid(), db.now()
        result = {
            "id": identifier,
            "contract": CONTRACT,
            "capture_status": "SUBMITTED_SOURCE_CHECKED"
            if form["stage"] == "submitted"
            else "DRAFT_UNVERIFIED",
            "effect": "FORM_CAPTURE_ONLY_NO_WORKFLOW_TRANSITION",
            "recorded_at": at,
            "recorded_by": self.actor["id"],
            "source_binding": binding,
            "form": form,
            "reason": body["evidence"],
        }
        await self.session.execute(
            t.journal.insert().values(
                id=identifier,
                resource_id=finding["id"],
                facility_id=facility["id"],
                action=ACTION,
                actor_id=self.actor["id"],
                version=finding["version"],
                recorded_at=at,
                correlation_id=self.correlation,
                payload_ciphertext=self.seal(result),
            )
        )
        await self.audit(ACTION, identifier)
        return result

    async def history(self, identifier, before):
        finding, case, facility = await self.context(identifier)
        query = select(t.journal).where(
            t.journal.c.resource_id == finding["id"], t.journal.c.action == ACTION
        )
        if before:
            cursor = (
                (await self.session.execute(query.where(t.journal.c.id == str(before))))
                .mappings()
                .first()
            )
            require(cursor, "NOT_FOUND_OR_NOT_PERMITTED", "Capture cursor unavailable", 404)
            query = query.where(
                or_(
                    t.journal.c.recorded_at < cursor["recorded_at"],
                    and_(
                        t.journal.c.recorded_at == cursor["recorded_at"],
                        t.journal.c.id < cursor["id"],
                    ),
                )
            )
        rows = (
            (
                await self.session.execute(
                    query.order_by(t.journal.c.recorded_at.desc(), t.journal.c.id.desc()).limit(51)
                )
            )
            .mappings()
            .all()
        )
        known, binding = await self.projection(finding, case)
        await self.audit("standards.corrective_captures_read", finding["id"])
        return {
            "items": [self.open(row["payload_ciphertext"]) for row in rows[:50]],
            "next_before_id": rows[49]["id"] if len(rows) > 50 else None,
            "context": {
                **binding,
                "actor_id": self.actor["id"],
                "authority_node_id": self.authority(),
                "facility_or_unit_id": facility["id"],
                "case_state": case["state"],
            },
            "recorded_source_values": known,
        }


def install_capture_routes(router, cfg, database, box, actor_for, available, command):
    @router.post("/v1/institutional/findings/{identifier}/corrective-captures")
    async def capture(identifier: UUID, payload: c.CorrectiveCapture, request: Request):
        body = payload.model_dump(mode="json")
        body["form"] = payload.form.model_dump(mode="json", exclude_unset=True)
        return await command(
            request,
            payload,
            CaptureService,
            lambda service, data: service.context(identifier, data),
            lambda service, data: service.record(identifier, data),
            raw_body=body,
        )

    @router.get("/v1/institutional/findings/{identifier}/corrective-captures")
    async def captures(identifier: UUID, request: Request, before_id: UUID | None = None):
        await available()
        async with database.transaction() as session:
            service = CaptureService(
                session, cfg, box, await actor_for(session, request), request.state.correlation_id
            )
            return await service.history(identifier, before_id)
