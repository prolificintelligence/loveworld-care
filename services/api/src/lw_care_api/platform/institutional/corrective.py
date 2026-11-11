"""Finding-bound, individually owned plans in the existing protected encrypted journal.

LWH-EXT-CORRECTIVE-001 is not canonical team ownership or policy adoption.
Original observations and response evidence are never overwritten.
"""

from sqlalchemy import select

from .. import db
from ..domain import expected, require
from . import tables as t
from .teams import bound_team, verify_plan_team

CONTRACT = "LWH-EXT-CORRECTIVE-001"
PROPOSED = "standards.corrective_plan_proposed"
REVIEWED = "standards.corrective_plan_reviewed"


class CorrectivePlans:
    async def finding_fact(self, finding, action, version=None):
        query = select(t.journal).where(
            t.journal.c.resource_id == finding["id"], t.journal.c.action == action
        )
        if version is not None:
            query = query.where(t.journal.c.version == version)
        row = (
            (
                await self.session.execute(
                    query.order_by(t.journal.c.version.desc(), t.journal.c.id.desc()).limit(1)
                )
            )
            .mappings()
            .first()
        )
        return self.open(row["payload_ciphertext"]) if row else None

    async def corrective_plan(self, finding):
        row = (
            (
                await self.session.execute(
                    select(t.journal)
                    .where(
                        t.journal.c.resource_id == finding["id"],
                        t.journal.c.action.in_([PROPOSED, REVIEWED]),
                    )
                    .order_by(t.journal.c.version.desc(), t.journal.c.id.desc())
                    .limit(1)
                )
            )
            .mappings()
            .first()
        )
        if not row:
            return None
        value = self.open(row["payload_ciphertext"])["details"]
        require(
            value.get("contract") == CONTRACT,
            "PLAN_HISTORY_UNAVAILABLE",
            "The actual corrective-plan contract is unavailable",
            409,
        )
        return {**value, "recorded_version": row["version"], "recorded_at": row["recorded_at"]}

    async def agreed_plan(self, finding, case, *, current_parties=True):
        plan = await self.corrective_plan(finding)
        require(
            plan and plan["status"] == "AGREED",
            "CORRECTIVE_PLAN_REQUIRED",
            "Propose and independently agree the actual corrective action and deadline first",
            409,
        )
        require(
            plan["finding_id"] == finding["id"]
            and plan["case_id"] == case["id"]
            and plan["owner_account_id"] == finding["owner_id"]
            and plan["due_at"] == finding["due_at"]
            and plan["reviewed_by"] != plan["owner_account_id"]
            and case["reviewer_id"] != plan["owner_account_id"],
            "STALE_CORRECTIVE_PLAN",
            "The actual finding, owner, review and deadline must still match this plan",
            409,
        )
        require(
            plan["proposal_finding_version"]
            < plan["agreement_finding_version"]
            == plan["recorded_version"]
            <= finding["version"],
            "PLAN_HISTORY_UNAVAILABLE",
            "The actual agreement must follow its proposal in protected history",
            409,
        )
        if current_parties:
            require(
                plan["owner_account_id"] == case["respondent_id"]
                and plan["reviewed_by"] == case["reviewer_id"],
                "STALE_CORRECTIVE_PLAN",
                "Assignment changed; agree a fresh plan and submit the actual current owner's response",
                409,
            )
        await verify_plan_team(self, plan, finding, case, current=current_parties)
        return plan

    async def propose_corrective_plan(self, identifier, body):
        finding = await self.row(t.findings, identifier)
        case, facility = await self.case(finding["case_id"], write=True)
        require(self.actor["id"] == finding["owner_id"] == case["respondent_id"])
        await self.person(self.actor["id"], {"FACILITY_ADMIN"}, facility)
        expected(finding, body["expected_version"])
        require(
            case["state"] == "INSPECTED" and finding["outcome"] != "MET",
            "INVALID_STATE",
            "Corrective plans apply to an observed unresolved control while its case is in review",
            409,
        )
        require(
            body["due_at"] > db.now(),
            "VALIDATION_FAILED",
            "Record the actual prospective deadline and its authority",
            422,
        )
        require(
            case["reviewer_id"] and case["reviewer_id"] != self.actor["id"],
            "INDEPENDENT_REVIEW_REQUIRED",
            "An independent assigned reviewer must agree the plan",
            409,
        )
        team = await bound_team(self, finding, case, body)
        finding = await self.change(t.findings, finding, {"state": "AWAITING_RESPONSE"})
        plan = {
            "contract": CONTRACT,
            "plan_id": db.uid(),
            "finding_id": finding["id"],
            "case_id": case["id"],
            "status": "PROPOSED",
            "required_action": body["required_action"],
            "owner_account_id": self.actor["id"],
            "proposed_by": self.actor["id"],
            "assigned_reviewer_id": case["reviewer_id"],
            "due_at": body["due_at"],
            "deadline_authority_reference": body["deadline_authority_reference"],
            "proposal_finding_version": finding["version"],
            "evidence": body["evidence"],
        }
        if team:
            plan["owner_team"] = team
        await self.emit(PROPOSED, finding, plan, facility["id"])
        return {
            "id": finding["id"],
            "version": finding["version"],
            "state": finding["state"],
            "corrective_plan": plan,
        }

    async def review_corrective_plan(self, identifier, body):
        finding = await self.row(t.findings, identifier)
        case, facility = await self.case(finding["case_id"], write=True)
        require(self.actor["id"] == case["reviewer_id"])
        await self.person(self.actor["id"], {"STANDARDS_REVIEWER"}, facility)
        expected(finding, body["expected_version"])
        plan = await self.corrective_plan(finding)
        require(
            case["state"] == "INSPECTED"
            and plan
            and plan["status"] == "PROPOSED"
            and plan["finding_id"] == finding["id"]
            and plan["case_id"] == case["id"]
            and plan["plan_id"] == body["plan_id"]
            and plan["owner_account_id"] == finding["owner_id"] == case["respondent_id"]
            and plan["assigned_reviewer_id"] == self.actor["id"] != plan["proposed_by"]
            and plan["proposal_finding_version"] == finding["version"],
            "STALE_CORRECTIVE_PLAN",
            "Review the exact current owner's proposal independently",
            409,
        )
        if body["decision"] == "AGREE":
            await verify_plan_team(self, plan, finding, case)
            await self.person(finding["owner_id"], {"FACILITY_ADMIN"}, facility)
            require(
                plan["due_at"] > db.now(),
                "VALIDATION_FAILED",
                "An elapsed deadline cannot be adopted as a prospective plan",
                422,
            )
        finding = await self.change(
            t.findings, finding, {"due_at": plan["due_at"]} if body["decision"] == "AGREE" else {}
        )
        plan = {
            **plan,
            "status": "AGREED" if body["decision"] == "AGREE" else "RETURNED",
            "reviewed_by": self.actor["id"],
            "agreement_finding_version": finding["version"],
            "review_reason": body["evidence"],
        }
        plan.pop("recorded_version", None)
        plan.pop("recorded_at", None)
        await self.emit(REVIEWED, finding, plan, facility["id"])
        return {
            "id": finding["id"],
            "version": finding["version"],
            "state": finding["state"],
            "corrective_plan": plan,
        }

    async def response_plan(self, finding, case, response, *, current_parties=True):
        plan = await self.agreed_plan(finding, case, current_parties=current_parties)
        data = self.open(response["details_ciphertext"])
        require(
            data.get("corrective_plan_id") == plan["plan_id"]
            and response["finding_id"] == finding["id"]
            and data.get("plan_agreement_version") == plan["agreement_finding_version"]
            and response["author_id"] == plan["owner_account_id"],
            "STALE_CORRECTIVE_RESPONSE",
            "Review the actual response to this exact agreed plan",
            409,
        )
        return data
