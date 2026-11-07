"""Protected safety review, accepted responsibilities and independent outcome review."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from .. import db
from ..domain import RuleError, require
from . import store as s
from . import tables as t
from .analytics import AnalyticsService
from .service import GLOBAL, current


class DirectorateService(AnalyticsService):
    async def category(self, body):
        self.governor()
        require(
            body["valid_from"] < body["valid_until"],
            "VALIDATION_FAILED",
            "Category validity must be ordered",
            422,
        )
        await s.eligible_person(
            self.session, body["escalation_owner_id"], s.CASE_REVIEWERS | s.GOVERNORS, GLOBAL
        )
        row = {
            "id": db.uid(),
            "name": body["name"],
            "category_version": body["category_version"],
            "payload": body,
            "created_by": self.actor["id"],
            "created_at": db.now(),
        }
        await self.session.execute(t.event_categories.insert().values(**row))
        await self.log("EVENT_CATEGORY", row, "quality.event_category_adopted", GLOBAL)
        return row

    async def duty(self, body):
        self.governor()
        scope = await s.scope_for(self.session, body["scope_type"], body.get("scope_id"))
        require(
            body["valid_from"] < body["valid_until"] and body["valid_until"] > db.now(),
            "VALIDATION_FAILED",
            "Duty coverage requires an ordered, unexpired interval",
            422,
        )
        await s.eligible_person(self.session, body["account_id"], s.CASE_REVIEWERS, scope)
        row = {
            "id": db.uid(),
            **scope,
            **{key: body[key] for key in ("account_id", "valid_from", "valid_until", "evidence")},
            "created_by": self.actor["id"],
            "accepted_at": None,
        }
        await self.session.execute(t.duty_windows.insert().values(**row))
        await self.log(
            "DUTY_WINDOW", {**row, "version": 1}, "quality.duty_offer_recorded", scope, content=body
        )
        await s.audit(
            self.session,
            self.actor,
            "quality.duty_coverage_offered",
            scope,
            row["id"],
            self.correlation,
        )
        return row

    async def accept_duty(self, identifier, body):
        row = await s.load(self.session, t.duty_windows, identifier, lock=True)
        s.require_role(self.actor, s.CASE_REVIEWERS, row)
        require(
            row["account_id"] == self.actor["id"]
            and not row["accepted_at"]
            and row["valid_until"] > db.now(),
            "ACCESS_DENIED",
            "Only the named reviewer can accept their current duty window",
            403,
        )
        await self.session.execute(
            update(t.duty_windows)
            .where(t.duty_windows.c.id == identifier)
            .values(accepted_at=db.now())
        )
        await self.log(
            "DUTY_WINDOW",
            {**row, "version": 2, "accepted_at": db.now()},
            "quality.duty_acceptance_recorded",
            row,
            content=body,
        )
        await s.audit(
            self.session,
            self.actor,
            "quality.duty_coverage_accepted",
            row,
            identifier,
            self.correlation,
        )
        return {**row, "accepted_at": db.now()}

    async def covered(self, account_id, scope):
        windows = (
            await self.session.execute(
                select(t.duty_windows).where(
                    t.duty_windows.c.account_id == account_id,
                    t.duty_windows.c.accepted_at.is_not(None),
                    t.duty_windows.c.valid_from <= db.now(),
                    t.duty_windows.c.valid_until > db.now(),
                )
            )
        ).mappings()
        for window in windows:
            proxy = {
                "grants": [
                    {
                        "role": "SAFETY_REVIEWER",
                        "scope_type": window["scope_type"],
                        "scope_id": window["scope_id"],
                    }
                ]
            }
            if s.permits(proxy, s.CASE_REVIEWERS, scope):
                try:
                    await s.eligible_person(self.session, account_id, s.CASE_REVIEWERS, scope)
                except RuleError as exc:
                    if exc.code != "OWNER_NOT_ELIGIBLE":
                        raise
                    continue
                return True
        return False

    async def case_for(self, identifier, *, metadata=False):
        row = await s.load(self.session, t.cases, identifier, lock=True)
        reporter = row["created_by"] == self.actor["id"] and s.permits(
            self.actor, s.CASE_REPORTERS, row
        )
        reviewer = s.permits(self.actor, s.CASE_REVIEWERS, row)
        require(
            reporter
            or (
                reviewer
                and (metadata or self.actor["id"] in {row["reviewer_id"], row["handover_to"]})
            ),
            "NOT_FOUND_OR_NOT_PERMITTED",
            "Safety case unavailable for your assigned review purpose",
            404,
        )
        return row

    def case_view(self, row):
        result = s.opened(self.box, row)
        if row["reviewer_id"] != self.actor["id"]:
            result["data"] = {
                "capture": result["data"]["capture"],
                "review_details": "RESTRICTED_TO_ASSIGNED_REVIEWER",
            }
        result["ownership_exception"] = (
            "UNASSIGNED"
            if not row["reviewer_id"]
            else (
                "ACKNOWLEDGEMENT_OVERDUE"
                if not row["acknowledged_at"] and row["acknowledge_by"] < db.now()
                else None
            )
        )
        result["external_dispatch"] = "NOT_INFERRED_FROM_THIS_REPORT"
        return result

    async def safety_case(self, body):
        scope = await self.scope(body, s.CASE_REPORTERS)
        require(
            body["scope_type"] != "GLOBAL" and body["occurred_at"] <= db.now(),
            "VALIDATION_FAILED",
            "Report an actual occurrence at an identified reporting unit",
            422,
        )
        category = await s.load(self.session, t.event_categories, body["category_id"])
        require(
            current(category["payload"]),
            "CATEGORY_NOT_CURRENT",
            "Use an applicable current event category",
            409,
        )
        windows = (
            await self.session.execute(
                select(t.duty_windows)
                .where(
                    t.duty_windows.c.accepted_at.is_not(None),
                    t.duty_windows.c.valid_from <= db.now(),
                    t.duty_windows.c.valid_until > db.now(),
                )
                .order_by(t.duty_windows.c.valid_until.desc())
            )
        ).mappings()
        reviewer_id = None
        for window in windows:
            if window["account_id"] != self.actor["id"] and await self.covered(
                window["account_id"], scope
            ):
                reviewer_id = window["account_id"]
                break
        row = {
            "id": db.uid(),
            **scope,
            "category_id": body["category_id"],
            "version": 1,
            "state": "SIGNAL",
            "urgent": body["urgent"],
            "reviewer_id": reviewer_id,
            "handover_to": None,
            "created_by": self.actor["id"],
            "occurred_at": body["occurred_at"],
            "created_at": db.now(),
            "acknowledge_by": (
                datetime.now(UTC)
                + timedelta(minutes=category["payload"]["acknowledgement_minutes"])
            ).isoformat(timespec="microseconds"),
            "acknowledged_at": None,
            "duplicate_of": None,
            "payload_ciphertext": self.box.encrypt(
                s.canonical({"capture": body, "review_history": [], "external_receipts": []})
            ),
        }
        await self.session.execute(t.cases.insert().values(**row))
        await self.log("SAFETY_CASE", row, "quality.event_reported", scope, "LWH-EVT-010")
        if body["urgent"] and not reviewer_id:
            await self.exception(
                row,
                "SAFETY_CASE",
                "URGENT_UNASSIGNED",
                category["payload"]["escalation_owner_id"],
                row["created_at"],
            )
        return self.case_view(row)

    async def case_action(self, identifier, body):
        row = await self.case_for(identifier, metadata=body["action"] == "ASSIGN")
        s.require_role(self.actor, s.CASE_REVIEWERS, row)
        require(
            body["occurred_at"] <= db.now(),
            "VALIDATION_FAILED",
            "Record the actual review event time",
            422,
        )
        data, action, state = self.data(row), body["action"], row["state"]
        changes = {}
        if action == "ACCEPT_HANDOVER":
            require(
                row["handover_to"] == self.actor["id"] and state != "CLOSED",
                "ACCESS_DENIED",
                "Only the named successor can accept an open review",
            )
            require(
                await self.covered(self.actor["id"], row),
                "REVIEWER_NOT_COVERED",
                "The successor must have accepted current duty coverage",
                409,
            )
            changes.update(reviewer_id=self.actor["id"], handover_to=None)
        elif action == "OFFER_HANDOVER":
            require(
                row["reviewer_id"] == self.actor["id"] and state != "CLOSED",
                "ACCESS_DENIED",
                "Only the current reviewer can offer open responsibility",
            )
            successor = body.get("reviewer_id")
            require(
                successor and successor not in {self.actor["id"], row["created_by"]},
                "INVALID_SUCCESSOR",
                "Name an independent successor",
                422,
            )
            await s.eligible_person(self.session, successor, s.CASE_REVIEWERS, row)
            changes["handover_to"] = successor
        elif action == "ASSIGN":
            require(
                row["reviewer_id"] in (None, self.actor["id"])
                and body.get("reviewer_id") == self.actor["id"]
                and self.actor["id"] != row["created_by"],
                "ACCESS_DENIED",
                "A covered reviewer must personally accept an unassigned case",
            )
            require(
                await self.covered(self.actor["id"], row),
                "REVIEWER_NOT_COVERED",
                "Accept actual duty coverage before taking this case",
                409,
            )
            changes["reviewer_id"] = self.actor["id"]
        else:
            require(
                row["reviewer_id"] == self.actor["id"],
                "ACCESS_DENIED",
                "Only the assigned reviewer can change the case",
            )
            allowed, target = {
                "ACKNOWLEDGE": ({"SIGNAL"}, "ACKNOWLEDGED"),
                "START_REVIEW": ({"ACKNOWLEDGED"}, "UNDER_REVIEW"),
                "VERIFY": ({"UNDER_REVIEW"}, "VERIFIED"),
                "UNSUBSTANTIATED": ({"UNDER_REVIEW"}, "UNSUBSTANTIATED"),
                "DUPLICATE": ({"UNDER_REVIEW"}, "DUPLICATE"),
                "CLOSE": ({"VERIFIED", "UNSUBSTANTIATED", "DUPLICATE"}, "CLOSED"),
                "REOPEN": ({"CLOSED"}, "UNDER_REVIEW"),
                "RECORD_EXTERNAL_RECEIPT": (
                    {
                        "SIGNAL",
                        "ACKNOWLEDGED",
                        "UNDER_REVIEW",
                        "VERIFIED",
                        "UNSUBSTANTIATED",
                        "DUPLICATE",
                    },
                    state,
                ),
            }[action]
            require(
                state in allowed,
                "INVALID_STATE",
                "This safety review action is not valid for the current state",
                409,
            )
            state = target
            if action == "ACKNOWLEDGE":
                changes["acknowledged_at"] = db.now()
            if action in {"VERIFY", "UNSUBSTANTIATED", "DUPLICATE"}:
                require(
                    row["created_by"] != self.actor["id"],
                    "INDEPENDENT_REVIEW_REQUIRED",
                    "A signal originator cannot verify their own classification",
                    403,
                )
            if action == "DUPLICATE":
                require(
                    body.get("related_case_id") and body["related_case_id"] != identifier,
                    "RELATED_CASE_REQUIRED",
                    "Select the reviewed primary occurrence",
                    422,
                )
                primary = await self.case_for(body["related_case_id"])
                require(
                    primary["state"] == "VERIFIED"
                    and primary["category_id"] == row["category_id"]
                    and primary["duplicate_of"] is None,
                    "PRIMARY_EVENT_NOT_VERIFIED",
                    "Link to an independently verified primary occurrence in the same category",
                    409,
                )
                changes["duplicate_of"] = primary["id"]
            if action == "CLOSE":
                category = await s.load(self.session, t.event_categories, row["category_id"])
                require(
                    not category["payload"]["external_receipt_required"]
                    or data["external_receipts"],
                    "EXTERNAL_RECEIPT_REQUIRED",
                    "The adopted category requires recorded external receipt evidence before closure",
                    409,
                )
                unresolved = await self.session.scalar(
                    select(t.actions.c.id)
                    .where(
                        t.actions.c.source_type == "SAFETY_CASE",
                        t.actions.c.source_id == identifier,
                        t.actions.c.state != "REVIEWED_COMPLETE",
                    )
                    .limit(1)
                )
                require(
                    not unresolved,
                    "OPEN_CORRECTIVE_ACTION",
                    "Accepted corrective work remains unresolved",
                    409,
                )
            if action == "RECORD_EXTERNAL_RECEIPT":
                require(
                    body.get("external_agency") and body.get("external_receipt"),
                    "EXTERNAL_EVIDENCE_REQUIRED",
                    "Record the actual external recipient and receipt evidence",
                    422,
                )
                data["external_receipts"].append(
                    {
                        "agency": body["external_agency"],
                        "evidence": body["external_receipt"],
                        "occurred_at": body["occurred_at"],
                        "recorded_by": self.actor["id"],
                        "verification": "MANUAL_ATTESTATION_NOT_PROVIDER_INTEGRATION",
                    }
                )
        data["review_history"].append(
            {**body, "actor_id": self.actor["id"], "recorded_at": db.now()}
        )
        row = await s.amend(
            self.session,
            t.cases,
            row,
            {**changes, "state": state, "payload_ciphertext": self.box.encrypt(s.canonical(data))},
            body["expected_version"],
        )
        await self.log("SAFETY_CASE", row, "quality.event_reviewed", row)
        return self.case_view(row)

    async def action_for(self, identifier):
        row = await s.load(self.session, t.actions, identifier, lock=True)
        roles = (
            s.CASE_REVIEWERS if row["protected"] else s.PROGRAMMES | s.ACTION_OWNERS | s.REVIEWERS
        )
        s.require_role(self.actor, roles, row)
        participants = {
            row["created_by"],
            row["owner_id"],
            row["fallback_id"],
            row["reviewer_id"],
            row["handover_to"],
        }
        require(
            self.actor["id"] in participants,
            "NOT_FOUND_OR_NOT_PERMITTED",
            "Action unavailable outside its accountable team",
            404,
        )
        return row

    async def action(self, body):
        scope = await self.scope(body, s.PROGRAMMES | s.CASE_REVIEWERS)
        source_context = {"type": body["source_type"], "captured_at": db.now()}
        protected = body["source_type"] == "SAFETY_CASE"
        if protected:
            source = await self.case_for(body.get("source_id"))
            source_context.update(id=source["id"], version=source["version"], state=source["state"])
            require(
                source["reviewer_id"] == self.actor["id"],
                "ACCESS_DENIED",
                "The assigned case reviewer must originate protected corrective work",
            )
        else:
            s.require_role(self.actor, s.PROGRAMMES, scope)
            if body["source_type"] == "RETURN":
                source_return, source = await self.return_for(
                    body.get("source_id"), s.PROGRAMMES | s.SOURCE_READERS
                )
                source_context.update(
                    id=source_return["id"],
                    version=source_return["version"],
                    state=source_return["state"],
                    source_hash=source_return["source_hash"],
                )
            elif body["source_type"] == "SNAPSHOT":
                snapshot = await s.load(self.session, t.snapshots, body.get("source_id"))
                source_context.update(id=snapshot["id"], source_hash=snapshot["source_hash"])
                source = await self.cohort_for(snapshot["cohort_id"], s.PROGRAMMES)
                require(
                    await self.session.scalar(
                        select(t.snapshot_reviews.c.id).where(
                            t.snapshot_reviews.c.snapshot_id == snapshot["id"],
                            t.snapshot_reviews.c.decision == "RELEASE",
                        )
                    ),
                    "SNAPSHOT_NOT_RELEASED",
                    "Link the action to reviewed leadership evidence",
                    409,
                )
            else:
                source = scope
                require(
                    body.get("source_id") is None,
                    "VALIDATION_FAILED",
                    "A justified request uses its recorded justification, not an unrelated source identifier",
                    422,
                )
        require(
            s.permits(
                {
                    "grants": [
                        {
                            "role": "PROGRAMME_OWNER",
                            "scope_type": scope["scope_type"],
                            "scope_id": scope["scope_id"],
                        }
                    ]
                },
                s.PROGRAMMES,
                source,
            ),
            "SOURCE_SCOPE_MISMATCH",
            "The action scope must cover the referenced evidence",
            422,
        )
        require(
            body["reviewer_id"] not in {body["owner_id"], self.actor["id"]},
            "INDEPENDENT_REVIEW_REQUIRED",
            "Name a separate completion reviewer",
            422,
        )
        require(
            body["owner_id"] != body["fallback_id"] and body["review_at"] >= body["due_at"],
            "VALIDATION_FAILED",
            "Name a distinct fallback owner and an ordered review date",
            422,
        )
        role_set = s.CASE_REVIEWERS if protected else s.ACTION_OWNERS
        for account_id in (body["owner_id"], body["fallback_id"], body["reviewer_id"]):
            await s.eligible_person(self.session, account_id, role_set, scope)
        data = {
            **body,
            "source_context": source_context,
            "progress": [],
            "outcome_review": None,
            "accepted_at": None,
        }
        row = {
            "id": db.uid(),
            **scope,
            "version": 1,
            "state": "ASSIGNED",
            "source_type": body["source_type"],
            "source_id": body.get("source_id"),
            "owner_id": body["owner_id"],
            "fallback_id": body["fallback_id"],
            "reviewer_id": body["reviewer_id"],
            "created_by": self.actor["id"],
            "due_at": body["due_at"],
            "review_at": body["review_at"],
            "protected": protected,
            "handover_to": None,
            "payload_ciphertext": self.box.encrypt(s.canonical(data)),
            "created_at": db.now(),
            "updated_at": db.now(),
        }
        await self.session.execute(t.actions.insert().values(**row))
        await self.log("ACTION", row, "programme.action_assigned", row, "LWH-EVT-012")
        return s.opened(self.box, row)

    async def action_update(self, identifier, body):
        row = await self.action_for(identifier)
        data, action, state = self.data(row), body["action"], row["state"]
        changes = {}
        if action in {"ACCEPT_COMPLETION", "REJECT_COMPLETION", "OUTCOME_REVIEW"}:
            require(
                self.actor["id"] == row["reviewer_id"]
                and self.actor["id"] not in {row["owner_id"], row["created_by"]},
                "INDEPENDENT_REVIEW_REQUIRED",
                "Only the independent assigned reviewer can decide completion/outcome",
                403,
            )
            if action == "OUTCOME_REVIEW":
                require(
                    state == "REVIEWED_COMPLETE"
                    and body.get("outcome")
                    and body.get("limitations"),
                    "OUTCOME_EVIDENCE_REQUIRED",
                    "Reviewed completion, observed outcome and limitations are required",
                    422,
                )
                data["outcome_review"] = {
                    **body,
                    "reviewer_id": self.actor["id"],
                    "recorded_at": db.now(),
                }
            else:
                require(
                    state == "EVIDENCE_SUBMITTED",
                    "INVALID_STATE",
                    "Review the submitted completion evidence",
                    409,
                )
                state = "REVIEWED_COMPLETE" if action == "ACCEPT_COMPLETION" else "IN_PROGRESS"
        elif action == "ACCEPT_HANDOVER":
            require(
                row["handover_to"] == self.actor["id"] and state != "REVIEWED_COMPLETE",
                "ACCESS_DENIED",
                "Only the named eligible successor can accept open responsibility",
            )
            changes.update(owner_id=self.actor["id"], handover_to=None)
            data["accepted_at"] = db.now()
            state = "ACCEPTED"
        elif action == "RESOURCE_APPROVAL":
            require(
                self.actor["id"] == row["reviewer_id"] and state != "REVIEWED_COMPLETE",
                "ACCESS_DENIED",
                "The independent resource reviewer must record approval",
            )
            data["resource_state"], data["budget_authority"] = "APPROVED", body["evidence"]
        else:
            require(
                self.actor["id"] == row["owner_id"],
                "ACCESS_DENIED",
                "The current action owner must record progress",
            )
            if action == "OFFER_HANDOVER":
                require(
                    state != "REVIEWED_COMPLETE"
                    and body.get("successor_id")
                    not in (None, self.actor["id"], row["reviewer_id"]),
                    "INVALID_SUCCESSOR",
                    "Name an eligible successor distinct from the owner and reviewer",
                    422,
                )
                await s.eligible_person(
                    self.session,
                    body["successor_id"],
                    s.CASE_REVIEWERS if row["protected"] else s.ACTION_OWNERS,
                    row,
                )
                changes["handover_to"] = body["successor_id"]
            else:
                allowed, target = {
                    "ACCEPT": ({"ASSIGNED"}, "ACCEPTED"),
                    "START": ({"ACCEPTED", "BLOCKED"}, "IN_PROGRESS"),
                    "BLOCK": ({"ASSIGNED", "ACCEPTED", "IN_PROGRESS"}, "BLOCKED"),
                    "PROGRESS": ({"IN_PROGRESS"}, "IN_PROGRESS"),
                    "SUBMIT_EVIDENCE": ({"IN_PROGRESS", "BLOCKED"}, "EVIDENCE_SUBMITTED"),
                    "REOPEN": ({"REVIEWED_COMPLETE"}, "ACCEPTED"),
                }[action]
                require(
                    state in allowed,
                    "INVALID_STATE",
                    "This action transition is unavailable in the current state",
                    409,
                )
                if action in {"START", "SUBMIT_EVIDENCE"}:
                    require(
                        data["resource_state"] != "AWAITING_APPROVAL",
                        "RESOURCE_AUTHORITY_REQUIRED",
                        "Required resources are awaiting actual approval",
                        409,
                    )
                if action == "ACCEPT":
                    data["accepted_at"] = db.now()
                state = target
        data["progress"].append({**body, "actor_id": self.actor["id"], "recorded_at": db.now()})
        row = await s.amend(
            self.session,
            t.actions,
            row,
            {
                **changes,
                "state": state,
                "payload_ciphertext": self.box.encrypt(s.canonical(data)),
                "updated_at": db.now(),
            },
            body["expected_version"],
        )
        await self.log(
            "ACTION",
            row,
            "programme.action_reviewed"
            if action in {"ACCEPT_COMPLETION", "REJECT_COMPLETION", "OUTCOME_REVIEW"}
            else "programme.action_changed",
            row,
            "LWH-EVT-013"
            if action in {"ACCEPT_COMPLETION", "REJECT_COMPLETION", "OUTCOME_REVIEW"}
            else None,
        )
        return s.opened(self.box, row)

    async def exception(self, row, kind, exception_type, owner_id, due_at):
        existing = await self.session.scalar(
            select(t.escalations.c.id).where(
                t.escalations.c.resource_type == kind,
                t.escalations.c.resource_id == row["id"],
                t.escalations.c.exception_type == exception_type,
                t.escalations.c.due_at == due_at,
            )
        )
        if existing:
            return existing
        identifier = db.uid()
        await self.session.execute(
            t.escalations.insert().values(
                id=identifier,
                **s.scope_values(row),
                resource_type=kind,
                resource_id=row["id"],
                exception_type=exception_type,
                owner_id=owner_id,
                due_at=due_at,
                created_at=db.now(),
            )
        )
        return identifier

    async def reconcile(self):
        count = 0
        for row in (
            await self.session.execute(
                select(t.actions).where(
                    t.actions.c.state != "REVIEWED_COMPLETE", t.actions.c.due_at < db.now()
                )
            )
        ).mappings():
            await self.exception(row, "ACTION", "ACTION_OVERDUE", row["fallback_id"], row["due_at"])
            count += 1
        for row in (
            await self.session.execute(
                select(t.cases).where(
                    t.cases.c.state != "CLOSED",
                    t.cases.c.acknowledged_at.is_(None),
                    t.cases.c.acknowledge_by < db.now(),
                )
            )
        ).mappings():
            category = await s.load(self.session, t.event_categories, row["category_id"])
            await self.exception(
                row,
                "SAFETY_CASE",
                "ACKNOWLEDGEMENT_OVERDUE",
                category["payload"]["escalation_owner_id"],
                row["acknowledge_by"],
            )
            count += 1
        return {
            "examined_overdue_obligations": count,
            "external_notifications": "NOT_INFERRED",
            "as_of": db.now(),
        }

    async def acknowledge_exception(self, identifier, body):
        row = await s.load(self.session, t.escalations, identifier)
        s.require_role(self.actor, s.ALL_ROLES, row)
        require(
            row["owner_id"] == self.actor["id"],
            "ACCESS_DENIED",
            "Only the named fallback can acknowledge this escalation",
        )
        require(
            not await self.session.scalar(
                select(t.escalation_receipts.c.id).where(
                    t.escalation_receipts.c.escalation_id == identifier
                )
            ),
            "ALREADY_ACKNOWLEDGED",
            "This escalation already has an acknowledgement",
            409,
        )
        receipt = {
            "id": db.uid(),
            "escalation_id": identifier,
            "actor_id": self.actor["id"],
            "evidence_ciphertext": self.box.encrypt(body["evidence"]),
            "created_at": db.now(),
        }
        await self.session.execute(t.escalation_receipts.insert().values(**receipt))
        await s.audit(
            self.session,
            self.actor,
            "programme.escalation_acknowledged",
            row,
            identifier,
            self.correlation,
        )
        return {
            "id": receipt["id"],
            "escalation_id": identifier,
            "acknowledged_at": receipt["created_at"],
            "responsibility_transferred": False,
        }
