"""Renewal, corrective work, notices and independent central review."""

from sqlalchemy import select

from .. import db
from ..control.service import has
from ..domain import expected, record_change, require, scoped
from . import tables as t
from .base import Service
from .corrective import CorrectivePlans
from .master import MasterService


async def latest_decision(session, facility_id):
    old = (
        (
            await session.execute(
                select(db.decisions)
                .join(db.applications, db.applications.c.id == db.decisions.c.application_id)
                .where(db.applications.c.facility_id == facility_id)
                .order_by(db.decisions.c.created_at.desc())
                .limit(1)
            )
        )
        .mappings()
        .first()
    )
    new = (
        (
            await session.execute(
                select(t.decisions)
                .where(t.decisions.c.facility_id == facility_id)
                .order_by(t.decisions.c.created_at.desc())
                .limit(1)
            )
        )
        .mappings()
        .first()
    )
    return new if new and (not old or new["created_at"] >= old["created_at"]) else old


class AffiliationService(CorrectivePlans, Service):
    async def offer_assignment(self, identifier, body):
        case, facility = await self.case(identifier, write=True)
        require(scoped(self.actor, {"STANDARDS_REVIEWER"}, facility))
        expected(case, body["expected_version"])
        require(
            case["state"] not in {"DECIDED", "REMITTED"},
            "INVALID_STATE",
            "A completed case retains its original assignments",
            409,
        )
        kind = body["assignment_kind"]
        role = {
            "RESPONDENT": "FACILITY_ADMIN",
            "INSPECTOR": "INSPECTOR",
            "REVIEWER": "STANDARDS_REVIEWER",
        }[kind]
        field = kind.lower() + "_id"
        require(
            body["successor_id"] != case[field],
            "NO_CHANGE",
            "The named person is already assigned",
            409,
        )
        await self.person(body["successor_id"], {role}, facility)
        if kind != "RESPONDENT":
            excluded = {
                case["created_by"],
                case["respondent_id"],
                case["reviewer_id"] if kind == "INSPECTOR" else case["inspector_id"],
                facility["created_by"],
            }
            require(
                body["successor_id"] not in excluded,
                "INDEPENDENT_REVIEW_REQUIRED",
                "The new assessor must remain independent",
                409,
            )
            if case["kind"] == "APPEAL":
                require(
                    body["successor_id"] not in await self.participants(case),
                    "APPEAL_INDEPENDENCE_REQUIRED",
                    "The appeal successor cannot belong to the challenged team",
                    409,
                )
        pending = {**case["pending_assignments"], kind: body["successor_id"]}
        case = await self.change(t.cases, case, {"pending_assignments": pending})
        await self.emit("standards.assignment_offered", case, body)
        return {**self.case_view(case), "ownership_transferred": False}

    async def accept_assignment(self, identifier, body):
        case, facility = await self.case(identifier, write=True)
        expected(case, body["expected_version"])
        kind = body["assignment_kind"]
        require(
            case["pending_assignments"].get(kind) == self.actor["id"]
            and case["state"] not in {"DECIDED", "REMITTED"},
            "NO_PERSONAL_OFFER",
            "No current personal assignment offer is available",
            409,
        )
        await self.person(
            self.actor["id"],
            {
                {
                    "RESPONDENT": "FACILITY_ADMIN",
                    "INSPECTOR": "INSPECTOR",
                    "REVIEWER": "STANDARDS_REVIEWER",
                }[kind]
            },
            facility,
        )
        if kind != "RESPONDENT":
            require(
                self.actor["id"]
                not in {
                    case["created_by"],
                    case["respondent_id"],
                    case["reviewer_id"] if kind == "INSPECTOR" else case["inspector_id"],
                    facility["created_by"],
                },
                "INDEPENDENT_REVIEW_REQUIRED",
                "Current assignments conflict with this offer",
                409,
            )
        pending = {key: value for key, value in case["pending_assignments"].items() if key != kind}
        values = {kind.lower() + "_id": self.actor["id"], "pending_assignments": pending}
        if kind == "REVIEWER" and case["state"] == "RECOMMENDED":
            values.update(state="INSPECTED", recommendation=None)
        case = await self.change(t.cases, case, values)
        if kind == "RESPONDENT":
            from sqlalchemy import update

            await self.session.execute(
                update(t.findings)
                .where(t.findings.c.case_id == case["id"], t.findings.c.state != "RESOLVED")
                .values(owner_id=self.actor["id"], version=t.findings.c.version + 1)
            )
        await self.emit("standards.assignment_accepted", case, body)
        return {
            **self.case_view(case),
            "ownership_transferred": True,
            "prior_authorship_preserved": True,
        }

    async def participants(self, case):
        people = {
            case["created_by"],
            case["respondent_id"],
            case["inspector_id"],
            case["reviewer_id"],
        }
        people.update(
            (
                await self.session.execute(
                    select(t.journal.c.actor_id).where(t.journal.c.resource_id == case["id"])
                )
            ).scalars()
        )
        identifier = case["base_decision_id"]
        visited = set()
        while identifier and identifier not in visited:
            visited.add(identifier)
            old = (
                (
                    await self.session.execute(
                        select(db.decisions).where(db.decisions.c.id == identifier)
                    )
                )
                .mappings()
                .first()
            )
            if old:
                application = await self.row(db.applications, old["application_id"], lock=False)
                people.update(
                    {
                        old["decider_id"],
                        application["created_by"],
                        application["inspector_id"],
                        application["reviewer_id"],
                    }
                )
                break
            decision = (
                (
                    await self.session.execute(
                        select(t.decisions).where(t.decisions.c.id == identifier)
                    )
                )
                .mappings()
                .first()
            )
            if not decision:
                break
            prior = await self.row(t.cases, decision["case_id"], lock=False)
            people.update(
                {
                    decision["decider_id"],
                    prior["created_by"],
                    prior["inspector_id"],
                    prior["reviewer_id"],
                    prior["respondent_id"],
                }
            )
            identifier = prior["base_decision_id"]
        return people

    async def open_case(self, body):
        facility = await self.facility(
            body["facility_id"],
            {"FACILITY_ADMIN", "STANDARDS_REVIEWER", "STANDARDS_DECIDER"},
            lock=True,
        )
        require(
            body["due_at"] > db.now(),
            "VALIDATION_FAILED",
            "Use an actual future case/calendar deadline",
            422,
        )
        await self.person(body["respondent_id"], {"FACILITY_ADMIN"}, facility)
        criteria = await self.row(db.criteria, body["criteria_id"], lock=False)
        require(
            criteria["jurisdiction"] == facility["jurisdiction"]
            and criteria["site_type"] == facility["site_type"]
            and criteria["valid_from"] <= db.now() < criteria["valid_until"],
            "CRITERIA_NOT_APPLICABLE",
            "Choose current adopted criteria for the actual site type and jurisdiction",
            409,
        )
        head = await latest_decision(self.session, facility["id"])
        if body["kind"] in {"RENEWAL", "APPEAL", "REINSTATEMENT"}:
            require(
                head, "DECISION_PROVENANCE_REQUIRED", "An actual prior decision is required", 409
            )
        if body["base_decision_id"]:
            require(
                head and body["base_decision_id"] == head["id"],
                "STALE_DECISION",
                "The selected decision is no longer current",
                409,
            )
        if body["kind"] == "RENEWAL":
            require(
                facility["affiliation_status"] in {"ACTIVE", "CONDITIONAL", "EXPIRED"},
                "INVALID_STATE",
                "Renewal cannot bypass a suspension/removal review",
                409,
            )
        if body["kind"] == "REINSTATEMENT":
            require(
                facility["affiliation_status"] in {"SUSPENDED", "REMOVED", "EXPIRED"},
                "INVALID_STATE",
                "A reinstatement review requires a restricted or expired affiliation",
                409,
            )
        active = await self.session.scalar(
            select(t.cases.c.id)
            .where(
                t.cases.c.facility_id == facility["id"],
                t.cases.c.kind == body["kind"],
                t.cases.c.state.not_in(["DECIDED", "REMITTED"]),
            )
            .limit(1)
        )
        require(
            not active, "CASE_ALREADY_OPEN", "Continue the existing open case of this type", 409
        )
        row = {
            "id": db.uid(),
            "facility_id": facility["id"],
            "kind": body["kind"],
            "state": "OPEN",
            "version": 1,
            "criteria_id": criteria["id"],
            "criteria_snapshot": criteria,
            "base_decision_id": head["id"] if head else None,
            "created_by": self.actor["id"],
            "respondent_id": body["respondent_id"],
            "inspector_id": None,
            "reviewer_id": None,
            "recommendation": None,
            "due_at": body["due_at"],
            "created_at": db.now(),
            "details_ciphertext": self.seal(body),
        }
        await self.session.execute(t.cases.insert().values(**row))
        await self.emit("standards.case_opened", row)
        return self.case_view(row)

    def case_view(self, row):
        return {key: value for key, value in row.items() if key != "details_ciphertext"}

    async def assign(self, identifier, body):
        row, facility = await self.case(identifier, write=True)
        require(scoped(self.actor, {"STANDARDS_REVIEWER"}, facility))
        expected(row, body["expected_version"])
        require(
            row["state"] in {"OPEN", "ASSIGNED"},
            "INVALID_STATE",
            "Reassignment after observations requires a new reviewed case",
            409,
        )
        excluded = {row["created_by"], row["respondent_id"], facility["created_by"]}
        require(
            body["inspector_id"] != body["reviewer_id"]
            and not ({body["inspector_id"], body["reviewer_id"]} & excluded),
            "INDEPENDENT_REVIEW_REQUIRED",
            "Applicant, inspector and reviewer must be distinct",
            409,
        )
        if row["kind"] == "APPEAL":
            require(
                not ({body["inspector_id"], body["reviewer_id"]} & await self.participants(row)),
                "APPEAL_INDEPENDENCE_REQUIRED",
                "Appeal assessors must be independent of the challenged decisions",
                409,
            )
        await self.person(body["inspector_id"], {"INSPECTOR"}, facility)
        await self.person(body["reviewer_id"], {"STANDARDS_REVIEWER"}, facility)
        row = await self.change(
            t.cases,
            row,
            {
                "state": "ASSIGNED",
                "inspector_id": body["inspector_id"],
                "reviewer_id": body["reviewer_id"],
            },
        )
        await self.emit("standards.case_assigned", row, body)
        return self.case_view(row)

    async def inspect(self, identifier, body):
        row, facility = await self.case(identifier, write=True)
        require(row["inspector_id"] == self.actor["id"])
        await self.person(self.actor["id"], {"INSPECTOR"}, facility)
        expected(row, body["expected_version"])
        require(
            row["state"] == "ASSIGNED" and body["observed_at"] <= db.now(),
            "INVALID_STATE",
            "Record actual observations for the assigned case",
            409,
        )
        definitions = {value["code"]: value for value in row["criteria_snapshot"]["requirements"]}
        codes = [value["criterion"] for value in body["findings"]]
        require(
            len(codes) == len(set(codes))
            and set(codes) <= set(definitions)
            and {code for code, value in definitions.items() if value["required"]} <= set(codes),
            "INCOMPLETE_FINDINGS",
            "Observe every required criterion once using its actual code",
            409,
        )
        for finding in body["findings"]:
            require(
                finding["due_at"] > db.now(),
                "VALIDATION_FAILED",
                "Record the actual response deadline",
                422,
            )
            if finding["outcome"] == "MET":
                require(
                    finding["evidence_ids"],
                    "EVIDENCE_REQUIRED",
                    "A met finding needs actual current scanned evidence",
                    409,
                )
            await self.valid_files(row, finding["evidence_ids"], finding["criterion"])
            value = {
                "id": db.uid(),
                "case_id": row["id"],
                "criterion": finding["criterion"],
                "outcome": finding["outcome"],
                "state": "RESOLVED" if finding["outcome"] == "MET" else "AWAITING_RESPONSE",
                "owner_id": row["respondent_id"],
                "due_at": finding["due_at"],
                "version": 1,
                "inspector_id": self.actor["id"],
                "details_ciphertext": self.seal(finding),
            }
            await self.session.execute(t.findings.insert().values(**value))
            await self.emit("standards.finding_recorded", value, finding, facility["id"])
        row = await self.change(t.cases, row, {"state": "INSPECTED"})
        await self.emit("standards.case_inspected", row, body)
        return self.case_view(row)

    async def respond(self, identifier, body):
        finding = await self.row(t.findings, identifier)
        case, facility = await self.case(finding["case_id"], write=True)
        require(finding["owner_id"] == self.actor["id"] and case["state"] == "INSPECTED")
        await self.person(self.actor["id"], {"FACILITY_ADMIN"}, facility)
        expected(finding, body["expected_version"])
        require(
            finding["state"] in {"AWAITING_RESPONSE", "RETURNED"},
            "INVALID_STATE",
            "This finding is not awaiting a response",
            409,
        )
        plan = await self.agreed_plan(finding, case)
        require(body.get("corrective_plan_id") in {None, plan["plan_id"]},
                "STALE_CORRECTIVE_PLAN", "Respond to the exact current agreed plan", 409)
        require(len(body["evidence_ids"]) == len(set(body["evidence_ids"])),
                "VALIDATION_FAILED", "Reference each actual evidence item once", 422)
        await self.valid_files(case, body["evidence_ids"], finding["criterion"])
        response = {
            "id": db.uid(),
            "finding_id": finding["id"],
            "author_id": self.actor["id"],
            "created_at": db.now(),
            "details_ciphertext": self.seal({**body, "corrective_plan_id": plan["plan_id"],
                                             "plan_agreement_version": plan["agreement_finding_version"]}),
        }
        await self.session.execute(t.responses.insert().values(**response))
        finding = await self.change(t.findings, finding, {"state": "RESPONSE_SUBMITTED"})
        await self.emit(
            "standards.response_submitted", finding, {"response": response}, facility["id"]
        )
        return {
            "id": finding["id"],
            "version": finding["version"],
            "state": finding["state"],
            "response_id": response["id"],
            "resolved": False,
        }

    async def review_finding(self, identifier, body):
        finding = await self.row(t.findings, identifier)
        case, facility = await self.case(finding["case_id"], write=True)
        require(case["reviewer_id"] == self.actor["id"] and case["state"] == "INSPECTED")
        await self.person(self.actor["id"], {"STANDARDS_REVIEWER"}, facility)
        expected(finding, body["expected_version"])
        response = await self.row(t.responses, body["response_id"], lock=False)
        require(
            response["finding_id"] == finding["id"]
            and response["author_id"] != self.actor["id"]
            and finding["state"] == "RESPONSE_SUBMITTED",
            "INVALID_REVIEW",
            "Review the actual submitted response independently",
            409,
        )
        submitted = await self.finding_fact(finding, "standards.response_submitted", finding["version"])
        require(submitted and submitted["details"]["response"]["id"] == response["id"],
                "STALE_RESPONSE", "Review the response bound to this exact finding version", 409)
        if body["decision"] == "RESOLVE":
            await self.response_plan(finding, case, response)
            await self.valid_files(
                case,
                self.open(response["details_ciphertext"])["evidence_ids"],
                finding["criterion"],
            )
        finding = await self.change(
            t.findings,
            finding,
            {"state": "RESOLVED" if body["decision"] == "RESOLVE" else "RETURNED"},
        )
        await self.emit("standards.response_reviewed", finding, body, facility["id"])
        return {key: value for key, value in finding.items() if key != "details_ciphertext"}

    async def recommend(self, identifier, body):
        row, facility = await self.case(identifier, write=True)
        require(row["reviewer_id"] == self.actor["id"])
        await self.person(self.actor["id"], {"STANDARDS_REVIEWER"}, facility)
        expected(row, body["expected_version"])
        require(
            row["state"] == "INSPECTED",
            "INVALID_STATE",
            "Complete actual assigned inspection and response review first",
            409,
        )
        await self.acceptance_findings(row, body["action"])
        row = await self.change(
            t.cases, row, {"state": "RECOMMENDED", "recommendation": body["action"]}
        )
        await self.emit("standards.recommended", row, body)
        return self.case_view(row)

    async def acceptance_findings(self, case, action):
        rows = list(
            (
                await self.session.execute(
                    select(t.findings).where(t.findings.c.case_id == case["id"])
                )
            ).mappings()
        )
        require(rows, "INCOMPLETE_FINDINGS", "Actual findings are required", 409)
        if action in {"APPROVE", "RENEW", "REINSTATE"}:
            require(
                all(row["state"] == "RESOLVED" for row in rows),
                "UNRESOLVED_FINDINGS",
                "Resolve findings through independent evidence review before an unrestricted recognition",
                409,
            )
        if action in {"APPROVE", "RENEW", "REINSTATE", "CONDITIONAL"}:
            for finding in rows:
                if finding["outcome"] == "MET":
                    await self.valid_files(
                        case,
                        self.open(finding["details_ciphertext"])["evidence_ids"],
                        finding["criterion"],
                    )
                else:
                    await self.agreed_plan(finding, case, current_parties=finding["state"] != "RESOLVED")
                    if finding["state"] != "RESOLVED":
                        continue
                    resolved = await self.finding_fact(finding, "standards.response_reviewed", finding["version"])
                    require(resolved and resolved["details"]["decision"] == "RESOLVE",
                            "RESOLUTION_HISTORY_REQUIRED", "The actual independent resolution must be retained", 409)
                    response = await self.row(t.responses, resolved["details"]["response_id"], lock=False)
                    await self.response_plan(finding, case, response, current_parties=False)
                    await self.valid_files(
                        case,
                        self.open(response["details_ciphertext"])["evidence_ids"],
                        finding["criterion"],
                    )

    async def notice(self, identifier, body):
        row, _facility = await self.case(identifier, write=True)
        require(has(self.actor, {"STANDARDS_DECIDER"}))
        expected(row, body["expected_version"])
        require(
            body["response_due"] > db.now() and row["state"] not in {"DECIDED", "REMITTED"},
            "INVALID_STATE",
            "Issue an actual prospective response window while the case is open",
            409,
        )
        value = {
            "id": db.uid(),
            "case_id": row["id"],
            "recipient_id": row["respondent_id"],
            "issuer_id": self.actor["id"],
            "response_due": body["response_due"],
            "created_at": db.now(),
            "details_ciphertext": self.seal(body),
        }
        await self.session.execute(t.notices.insert().values(**value))
        await self.emit("standards.notice_issued", value, facility_id=row["facility_id"])
        return {
            "id": value["id"],
            "case_id": row["id"],
            "delivery_state": "AVAILABLE_IN_AUTHENTICATED_PORTAL",
            "external_delivery_claimed": False,
        }

    async def acknowledge_notice(self, identifier, body):
        notice = await self.row(t.notices, identifier, lock=False)
        await self.case(notice["case_id"])
        require(notice["recipient_id"] == self.actor["id"])
        value = {
            "id": db.uid(),
            "resource_id": notice["id"],
            "actor_id": self.actor["id"],
            "kind": "NOTICE_ACKNOWLEDGED",
            "recorded_at": db.now(),
            "details_ciphertext": self.seal(body),
        }
        await self.session.execute(t.receipts.insert().values(**value))
        return {
            "id": value["id"],
            "notice_id": notice["id"],
            "state": "ACKNOWLEDGED",
            "case_closed": False,
        }

    async def decide(self, identifier, body):
        case, facility = await self.case(identifier, write=True)
        require(has(self.actor, {"STANDARDS_DECIDER"}))
        expected(case, body["expected_version"])
        require(
            self.actor["id"]
            not in {
                case["created_by"],
                case["respondent_id"],
                case["inspector_id"],
                case["reviewer_id"],
                facility["created_by"],
            },
            "INDEPENDENT_DECIDER_REQUIRED",
            "The central decider must be independent of applicant, inspection and review",
            409,
        )
        if case["kind"] == "APPEAL":
            require(
                self.actor["id"] not in await self.participants(case),
                "APPEAL_INDEPENDENCE_REQUIRED",
                "A challenged decision needs an independent review authority",
                409,
            )
        head = await latest_decision(self.session, facility["id"])
        require(
            (head["id"] if head else None) == case["base_decision_id"],
            "STALE_DECISION",
            "Another decision changed the case basis; open the appropriate current review",
            409,
        )
        action = body["action"]
        urgent = body["urgent_protective_action"]
        if urgent:
            require(
                action in {"SUSPEND", "REMOVE"}
                and len(body["protective_authority_reference"]) >= 5,
                "PROTECTIVE_AUTHORITY_REQUIRED",
                "An urgent protective decision needs its actual adopted authority",
                409,
            )
        else:
            require(
                case["state"] == "RECOMMENDED" and case["recommendation"] == action,
                "RECOMMENDATION_REQUIRED",
                "Use the exact independent recommendation",
                409,
            )
            await self.person(case["reviewer_id"], {"STANDARDS_REVIEWER"}, facility)
            await self.acceptance_findings(case, action)
        criteria = await self.row(db.criteria, case["criteria_id"], lock=False)
        require(
            criteria["valid_from"] <= db.now() < criteria["valid_until"],
            "CRITERIA_NOT_APPLICABLE",
            "The adopted criteria are no longer current",
            409,
        )
        require(
            action not in {"RENEW", "REINSTATE"}
            or (action == "RENEW" and case["kind"] == "RENEWAL")
            or (action == "REINSTATE" and case["kind"] == "REINSTATEMENT"),
            "INVALID_DECISION",
            "Use the appropriate renewal/reinstatement case",
            409,
        )
        require(
            action not in {"UPHOLD", "REMIT"} or case["kind"] == "APPEAL",
            "INVALID_DECISION",
            "Only an appeal can be upheld or remitted",
            409,
        )
        if action in {"APPROVE", "CONDITIONAL", "RENEW", "REINSTATE"}:
            await self.person(case["respondent_id"], {"FACILITY_ADMIN"}, facility)
            require(
                facility["identity_status"] == "VERIFIED"
                and body["expires_at"]
                and body["expires_at"] > db.now(),
                "INVALID_DECISION",
                "Verified identity and an actual future recognition expiry are required",
                409,
            )
            require(
                facility["affiliation_status"] not in {"SUSPENDED", "REMOVED"}
                or action == "REINSTATE",
                "REINSTATEMENT_REQUIRED",
                "An ordinary renewal or approval cannot bypass an adverse restriction",
                409,
            )
            if action == "CONDITIONAL":
                require(
                    body["conditions"], "CONDITIONS_REQUIRED", "Record the actual conditions", 409
                )
            if action in {"APPROVE", "CONDITIONAL"}:
                require(
                    head
                    and case["kind"] in {"NONCOMPLIANCE", "RENEWAL"}
                    and (
                        case["kind"] == "RENEWAL"
                        or body["expires_at"] <= facility["affiliation_expires_at"]
                    ),
                    "RENEWAL_REQUIRED",
                    "Corrective closure cannot create recognition or extend it without a renewal case",
                    409,
                )
        if action in {"SUSPEND", "REMOVE", "REJECT"}:
            notice = (
                (
                    await self.session.execute(
                        select(t.notices)
                        .where(t.notices.c.case_id == case["id"])
                        .order_by(t.notices.c.created_at.desc())
                        .limit(1)
                    )
                )
                .mappings()
                .first()
            )
            require(
                notice,
                "NOTICE_REQUIRED",
                "Record the notice and response/review route before an adverse decision",
                409,
            )
            require(
                urgent or notice["response_due"] <= db.now(),
                "RESPONSE_WINDOW_OPEN",
                "Acknowledgement does not waive the actual response window",
                409,
            )
            served = await self.session.scalar(
                select(t.receipts.c.id)
                .where(
                    t.receipts.c.resource_id == notice["id"],
                    t.receipts.c.kind.in_(["NOTICE_ACKNOWLEDGED", "NOTICE_DELIVERY_EVIDENCE"]),
                )
                .limit(1)
            )
            require(
                urgent or served,
                "NOTICE_SERVICE_REQUIRED",
                "Record actual acknowledgement or delivery evidence; portal availability alone does not establish service",
                409,
            )
        if action in {"SUSPEND", "REMOVE"}:
            require(
                body["custody_owner_id"] and len(body["continuity_plan"]) >= 5,
                "CONTINUITY_REQUIRED",
                "Record a nominated clinical custodian and continuity plan",
                409,
            )
            await self.person(body["custody_owner_id"], {"CLINICAL_GOVERNOR"}, facility)
        value = {
            "id": db.uid(),
            "case_id": case["id"],
            "facility_id": facility["id"],
            "decider_id": self.actor["id"],
            "action": action,
            "effective_at": db.now(),
            "expires_at": body["expires_at"],
            "created_at": db.now(),
            "details_ciphertext": self.seal(body),
        }
        await self.session.execute(t.decisions.insert().values(**value))
        if action not in {"UPHOLD", "REMIT"}:
            facility.pop("region_id", None)
            status = {
                "APPROVE": "ACTIVE",
                "CONDITIONAL": "CONDITIONAL",
                "RENEW": "ACTIVE",
                "REINSTATE": "ACTIVE",
                "SUSPEND": "SUSPENDED",
                "REMOVE": "REMOVED",
                "REJECT": "REJECTED",
            }[action]
            facility = await self.change(
                db.facilities,
                facility,
                {
                    "affiliation_status": status,
                    "affiliation_scope": body["scope"],
                    "conditions": body["conditions"],
                    "affiliation_expires_at": body["expires_at"]
                    if status in {"ACTIVE", "CONDITIONAL"}
                    else facility["affiliation_expires_at"],
                    "publication_status": "WITHDRAWN",
                    "updated_at": db.now(),
                },
            )
            await record_change(
                self.session,
                self.actor,
                "Facility",
                facility,
                "affiliation.lifecycle_decided",
                self.correlation,
            )
        if action in {"SUSPEND", "REMOVE"}:
            await MasterService(
                self.session, self.cfg, self.box, self.actor, self.correlation
            ).create_custody(
                facility["id"], value["id"], body["custody_owner_id"], body["continuity_plan"]
            )
        case = await self.change(
            t.cases, case, {"state": "REMITTED" if action == "REMIT" else "DECIDED"}
        )
        await self.emit("standards.central_decision", value, body, facility["id"])
        return {
            "id": value["id"],
            "case_id": case["id"],
            "case_version": case["version"],
            "action": action,
            "affiliation_status": facility["affiliation_status"],
            "publication_reapproval_required": True,
            "clinical_history_deleted": False,
            "custody_acceptance_required": action in {"SUSPEND", "REMOVE"},
        }
