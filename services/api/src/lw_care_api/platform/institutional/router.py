"""Scoped institution/editorial commands and explicitly approved public text."""

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Request, Response
from sqlalchemy import false, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from starlette.concurrency import run_in_threadpool

from .. import db, storage
from ..control.contracts import Evidence
from ..control.service import has
from ..domain import RuleError, require, scoped
from . import contracts as c
from . import tables as t
from .affiliation import AffiliationService
from .base import Service, predicate, serial
from .knowledge import EDITORS, PUBLISHERS, REVIEWERS, STAFF_ROLES, KnowledgeService, current
from .master import MasterService

REGISTRY = {
    "REGISTRY_STEWARD",
    "FACILITY_ADMIN",
    "STANDARDS_REVIEWER",
    "STANDARDS_DECIDER",
    "ZONE_COORDINATOR",
    "REGIONAL_COORDINATOR",
}
EDITING = EDITORS | PUBLISHERS | REVIEWERS


def clean(row):
    return {
        key: value
        for key, value in row.items()
        if not key.endswith("ciphertext")
        and key not in {"active_key", "object_key", "criteria_snapshot"}
    }


def page(rows):
    return {
        "items": [clean(row) for row in rows[:100]],
        "next_cursor": rows[99]["id"] if len(rows) > 100 else None,
        "as_of": db.now(),
    }


def install(app, cfg, database, box, actor_for):
    router = APIRouter()

    async def available():
        require(
            cfg.institutional_enabled,
            "INSTITUTIONAL_PAUSED",
            "Institutional lifecycle is paused",
            503,
        )
        require(
            (await database.version() or 0) >= 6,
            "INSTITUTIONAL_MIGRATION_REQUIRED",
            "Institutional lifecycle awaits migration 6",
            503,
        )

    async def command(request, payload, service_type, guard, callback, raw_body=None):
        await available()
        body = raw_body if raw_body is not None else payload.model_dump(mode="json")
        if isinstance(payload, c.Response) and body.get("corrective_plan_id") is None:
            # Preserve historical response receipt hashes; a new response still
            # binds the current agreed plan in its protected server-side data.
            body.pop("corrective_plan_id", None)
        if isinstance(payload, c.CorrectivePlan):
            # Preserve receipts for existing individually accountable plans.
            for key in ("owner_team_id", "owner_team_version"):
                if body.get(key) is None:
                    body.pop(key, None)
        actor = None
        try:
            async with database.transaction() as session:
                await serial(session)
                actor = await actor_for(session, request)
                service = service_type(session, cfg, box, actor, request.state.correlation_id)
                await guard(service, body)

                async def apply():
                    result = await callback(service, body)
                    return {
                        "resource": result,
                        "execution_state": "CENTRAL_COMMITTED",
                        "authority_node_id": cfg.authority_node_id,
                    }

                return await service.idempotent(
                    request.url.path, request.headers.get("Idempotency-Key"), body, apply
                )
        except RuleError:
            async with database.transaction() as session:
                await Service(session, cfg, box, actor, request.state.correlation_id).audit(
                    "institutional.command_denied", outcome="DENIED"
                )
            request.state.control_denial_recorded = True
            raise

    async def master_guard(service, body):
        require(
            has(
                service.actor,
                {"PLATFORM_ADMIN"} if body["kind"] == "ZONE_REGION" else {"REGISTRY_STEWARD"},
            )
        )

    async def case_guard(service, body, identifier):
        await service.case(identifier)

    async def content_guard(service, body, identifier, roles):
        await service.article(identifier, roles)

    @router.get("/v1/institutional/context")
    async def context(request: Request):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            return {
                "roles": sorted({g["role"] for g in actor["grants"]}),
                "central_hierarchy": has(actor, {"PLATFORM_ADMIN"}),
                "central_registry": has(actor, {"REGISTRY_STEWARD"}),
                "central_decisions": has(actor, {"STANDARDS_DECIDER"}),
                "as_of": db.now(),
                "publication": "INDEPENDENT_REVIEW_AND_DISTINCT_PUBLISHER",
                "external_distribution": "NOT_ATTEMPTED_PORTAL_ONLY",
                "scanner_configured": bool(cfg.clamav_host),
                "evidence_upload": storage.capability(cfg),
            }

    @router.get("/v1/institutional/catalogue")
    async def catalogue(
        request: Request, kind: str = "facilities", query: str = "", after: str = ""
    ):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            require(any(g["role"] in STAFF_ROLES for g in actor["grants"]))
            if kind == "units":
                rows = list(
                    (
                        await session.execute(
                            select(db.units)
                            .where(
                                db.units.c.id > after,
                                db.units.c.name.ilike("%" + query[:120] + "%"),
                            )
                            .order_by(db.units.c.id)
                            .limit(101)
                        )
                    ).mappings()
                )
                return page(rows)
            if kind == "people":
                # Names/contact identifiers are limited to actual work-scope membership.
                facilities = select(db.facilities.c.id).where(
                    predicate(actor, REGISTRY | EDITING | {"CLINICAL_GOVERNOR"})
                )
                grants = select(db.grants.c.account_id).where(
                    db.grants.c.revoked.is_(False),
                    db.grants.c.valid_from <= db.now(),
                    db.grants.c.valid_until > db.now(),
                    db.grants.c.scope_type == "FACILITY",
                    db.grants.c.scope_id.in_(facilities),
                )
                allowed = (
                    True
                    if has(actor, REGISTRY | EDITING | {"PLATFORM_ADMIN"})
                    else or_(db.accounts.c.id == actor["id"], db.accounts.c.id.in_(grants))
                )
                rows = list(
                    (
                        await session.execute(
                            select(db.accounts.c.id, db.accounts.c.name)
                            .where(
                                allowed,
                                db.accounts.c.active.is_(True),
                                db.accounts.c.id > after,
                                db.accounts.c.name.ilike("%" + query[:120] + "%"),
                            )
                            .order_by(db.accounts.c.id)
                            .limit(101)
                        )
                    ).mappings()
                )
                return page(rows)
            require(
                kind == "facilities", "VALIDATION_FAILED", "Choose facilities, units or people", 422
            )
            rows = list(
                (
                    await session.execute(
                        select(
                            db.facilities.c.id,
                            db.facilities.c.name,
                            db.facilities.c.version,
                            db.facilities.c.zone_id,
                            db.facilities.c.identity_status,
                            db.facilities.c.affiliation_status,
                            db.facilities.c.affiliation_expires_at,
                        )
                        .where(
                            predicate(
                                actor, REGISTRY | EDITING | {"CLINICAL_GOVERNOR", "PLATFORM_ADMIN"}
                            ),
                            db.facilities.c.id > after,
                            db.facilities.c.name.ilike("%" + query[:120] + "%"),
                        )
                        .order_by(db.facilities.c.id)
                        .limit(101)
                    )
                ).mappings()
            )
            return page(rows)

    @router.get("/v1/institutional/changes")
    async def changes(request: Request, after: str = ""):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            allowed = or_(
                t.changes.c.kind == "ZONE_REGION" if has(actor, {"PLATFORM_ADMIN"}) else false(),
                t.changes.c.kind != "ZONE_REGION" if has(actor, {"REGISTRY_STEWARD"}) else false(),
            )
            rows = list(
                (
                    await session.execute(
                        select(t.changes)
                        .where(allowed, t.changes.c.id > after)
                        .order_by(t.changes.c.id)
                        .limit(101)
                    )
                ).mappings()
            )
            return page(rows)

    @router.post("/v1/institutional/changes")
    async def propose(payload: c.MasterChange, request: Request):
        return await command(
            request,
            payload,
            MasterService,
            master_guard,
            lambda service, body: service.propose(body),
        )

    @router.get("/v1/institutional/changes/{identifier}")
    async def master_detail(identifier: UUID, request: Request):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            service = MasterService(session, cfg, box, actor, request.state.correlation_id)
            row = await service.row(t.changes, identifier, lock=False)
            require(
                has(
                    actor,
                    {"PLATFORM_ADMIN"} if row["kind"] == "ZONE_REGION" else {"REGISTRY_STEWARD"},
                )
            )
            await service.audit("registry.proposal_read", str(identifier))
            return {"change": clean(row), "proposal": service.open(row["payload_ciphertext"])}

    @router.post("/v1/institutional/changes/{identifier}/review")
    async def review_master(identifier: UUID, payload: c.Review, request: Request):
        async def guard(service, body):
            row = await service.row(t.changes, identifier)
            require(
                has(
                    service.actor,
                    {"PLATFORM_ADMIN"} if row["kind"] == "ZONE_REGION" else {"REGISTRY_STEWARD"},
                )
            )

        return await command(
            request,
            payload,
            MasterService,
            guard,
            lambda service, body: service.review(str(identifier), body),
        )

    @router.post("/v1/institutional/changes/{identifier}/cancel")
    async def cancel_master(identifier: UUID, payload: c.Versioned, request: Request):
        async def guard(service, body):
            row = await service.row(t.changes, identifier)
            require(
                has(
                    service.actor,
                    {"PLATFORM_ADMIN"} if row["kind"] == "ZONE_REGION" else {"REGISTRY_STEWARD"},
                )
            )

        return await command(
            request,
            payload,
            MasterService,
            guard,
            lambda service, body: service.cancel(str(identifier), body),
        )

    @router.get("/v1/institutional/custody")
    async def custody(request: Request, after: str = ""):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            allowed = or_(
                predicate(
                    actor,
                    {"CLINICAL_GOVERNOR", "REGISTRY_STEWARD", "STANDARDS_DECIDER"},
                    t.custody,
                    "facility_id",
                ),
                t.custody.c.custodian_id == actor["id"],
            )
            rows = list(
                (
                    await session.execute(
                        select(t.custody)
                        .where(allowed, t.custody.c.id > after)
                        .order_by(t.custody.c.id)
                        .limit(101)
                    )
                ).mappings()
            )
            result = page(rows)
            for item, row in zip(result["items"], rows):
                item["continuity_plan"] = Service(
                    session, cfg, box, actor, request.state.correlation_id
                ).open(row["plan_ciphertext"])
            return result

    @router.post("/v1/institutional/custody/{identifier}/accept")
    async def custody_accept(identifier: UUID, payload: c.Versioned, request: Request):
        async def guard(service, body):
            row = await service.row(t.custody, identifier)
            require(row["custodian_id"] == service.actor["id"])
            await service.person(
                service.actor["id"],
                {"CLINICAL_GOVERNOR"},
                await service.facility(row["facility_id"]),
            )

        return await command(
            request,
            payload,
            MasterService,
            guard,
            lambda service, body: service.accept_custody(str(identifier), body),
        )

    @router.get("/v1/institutional/cases")
    async def case_list(request: Request, after: str = ""):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            assigned = (t.cases.c.inspector_id == actor["id"]) & predicate(
                actor, {"INSPECTOR"}, t.cases, "facility_id"
            )
            assigned = or_(
                assigned,
                (t.cases.c.pending_assignments["INSPECTOR"].as_string() == actor["id"])
                & predicate(actor, {"INSPECTOR"}, t.cases, "facility_id"),
            )
            rows = list(
                (
                    await session.execute(
                        select(t.cases)
                        .where(
                            or_(predicate(actor, REGISTRY, t.cases, "facility_id"), assigned),
                            t.cases.c.id > after,
                        )
                        .order_by(t.cases.c.id)
                        .limit(101)
                    )
                ).mappings()
            )
            return page(rows)

    @router.post("/v1/institutional/cases")
    async def open_case(payload: c.CaseOpen, request: Request):
        async def guard(service, body):
            await service.facility(
                body["facility_id"], {"FACILITY_ADMIN", "STANDARDS_REVIEWER", "STANDARDS_DECIDER"}
            )

        return await command(
            request,
            payload,
            AffiliationService,
            guard,
            lambda service, body: service.open_case(body),
        )

    @router.get("/v1/institutional/cases/{identifier}")
    async def case_detail(identifier: UUID, request: Request):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            service = AffiliationService(session, cfg, box, actor, request.state.correlation_id)
            row, facility = await service.case(identifier)
            await service.audit("standards.case_read", str(identifier))
            result = {
                "case": {
                    **clean(row),
                    "criteria_snapshot": row["criteria_snapshot"],
                    "details": service.open(row["details_ciphertext"]),
                },
                "facility": {
                    key: facility[key] for key in ("id", "name", "version", "affiliation_status")
                },
                "next_cursors": {},
            }
            for kind in (
                "findings",
                "notices",
                "decisions",
                "files",
                "responses",
                "prior_files",
                "notice_receipts",
            ):
                group = await case_records(service, row, kind, "")
                result[kind] = group["items"]
                result[kind + "_truncated"] = bool(group["next_cursor"])
                result["next_cursors"][kind] = group["next_cursor"]
            return result

    async def case_records(service, case, kind, after):
        mapping = {
            "findings": t.findings,
            "notices": t.notices,
            "decisions": t.decisions,
            "files": t.case_files,
            "responses": t.responses,
            "prior_files": db.evidence,
            "notice_receipts": t.receipts,
        }
        require(
            kind in mapping, "VALIDATION_FAILED", "Choose an actual dossier record category", 422
        )
        table = mapping[kind]
        if kind == "responses":
            condition = table.c.finding_id.in_(
                select(t.findings.c.id).where(t.findings.c.case_id == case["id"])
            )
        elif kind == "prior_files":
            condition = table.c.application_id.in_(
                select(db.applications.c.id).where(
                    db.applications.c.facility_id == case["facility_id"]
                )
            )
        elif kind == "notice_receipts":
            condition = table.c.resource_id.in_(
                select(t.notices.c.id).where(t.notices.c.case_id == case["id"])
            )
        else:
            condition = table.c.case_id == case["id"]
        rows = list(
            (
                await service.session.execute(
                    select(table).where(condition, table.c.id > after).order_by(table.c.id).limit(4)
                )
            ).mappings()
        )
        result = {
            "items": [
                {
                    **clean(row),
                    **(
                        {"details": service.open(row["details_ciphertext"])}
                        if "details_ciphertext" in row
                        else {}
                    ),
                }
                for row in rows[:3]
            ],
            "next_cursor": rows[2]["id"] if len(rows) > 3 else None,
        }
        if kind == "findings":
            from .teams import verify_plan_team

            for item, row in zip(result["items"], rows[:3]):
                plan = await service.corrective_plan(row)
                if plan:
                    try:
                        await verify_plan_team(service, plan, row, case)
                        plan["team_current"] = True
                    except RuleError:
                        plan["team_current"] = False
                    plan["parties_current"] = (plan["owner_account_id"] == row["owner_id"] == case["respondent_id"]
                        and plan.get("reviewed_by", plan["assigned_reviewer_id"]) == case["reviewer_id"])
                    plan["current_for_response"] = (plan["team_current"] and case["state"] == "INSPECTED"
                        and row["state"] in {"AWAITING_RESPONSE", "RETURNED"} and plan["status"] == "AGREED"
                        and plan["owner_account_id"] == row["owner_id"] == case["respondent_id"]
                        and plan.get("reviewed_by") == case["reviewer_id"])
                    plan["current_for_review"] = (plan["team_current"] and case["state"] == "INSPECTED" and plan["status"] == "PROPOSED"
                        and plan["owner_account_id"] == row["owner_id"] == case["respondent_id"]
                        and plan["assigned_reviewer_id"] == case["reviewer_id"]
                        and plan["proposal_finding_version"] == row["version"])
                item["corrective_plan"] = plan
        return result

    @router.get("/v1/institutional/cases/{identifier}/records")
    async def dossier_records(identifier: UUID, request: Request, kind: str, after: str = ""):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            service = AffiliationService(session, cfg, box, actor, request.state.correlation_id)
            case, _ = await service.case(identifier)
            await service.audit("standards.dossier_records_read", str(identifier))
            return await case_records(service, case, kind, after)

    def case_route(path, model, method, role):
        async def endpoint(identifier: UUID, request: Request, payload: model):
            async def guard(service, body):
                row, facility = await service.case(identifier)
                if role == "DECIDER":
                    require(has(service.actor, {"STANDARDS_DECIDER"}))
                elif role == "INSPECTOR":
                    require(row["inspector_id"] == service.actor["id"])
                elif role == "REVIEWER":
                    require(row["reviewer_id"] == service.actor["id"])
                else:
                    require(scoped(service.actor, {"STANDARDS_REVIEWER"}, facility))

            return await command(
                request,
                payload,
                AffiliationService,
                guard,
                lambda service, body: getattr(service, method)(str(identifier), body),
            )

        router.add_api_route(
            "/v1/institutional/cases/{identifier}/" + path, endpoint, methods=["POST"]
        )

    case_route("assign", c.Assign, "assign", "ASSIGN")
    case_route("inspect", c.Inspection, "inspect", "INSPECTOR")
    case_route("recommend", c.Recommend, "recommend", "REVIEWER")
    case_route("notices", c.Notice, "notice", "DECIDER")
    case_route("decide", c.Decide, "decide", "DECIDER")
    case_route("assignment-offer", c.AssignmentOffer, "offer_assignment", "ASSIGN")

    @router.post("/v1/institutional/cases/{identifier}/assignment-accept")
    async def assignment_accept(identifier: UUID, payload: c.AssignmentAccept, request: Request):
        async def guard(service, body):
            row, _ = await service.case(identifier)
            require(row["pending_assignments"].get(body["assignment_kind"]) == service.actor["id"])

        return await command(
            request,
            payload,
            AffiliationService,
            guard,
            lambda service, body: service.accept_assignment(str(identifier), body),
        )

    def finding_route(path, model, method, owner):
        async def endpoint(identifier: UUID, request: Request, payload: model):
            async def guard(service, body):
                finding = await service.row(t.findings, identifier)
                case, _ = await service.case(finding["case_id"])
                require(
                    (finding["owner_id"] if owner else case["reviewer_id"]) == service.actor["id"]
                )

            return await command(
                request,
                payload,
                AffiliationService,
                guard,
                lambda service, body: getattr(service, method)(str(identifier), body),
            )

        router.add_api_route(
            "/v1/institutional/findings/{identifier}/" + path, endpoint, methods=["POST"]
        )

    finding_route("respond", c.Response, "respond", True)
    finding_route("review", c.FindingReview, "review_finding", False)
    finding_route("corrective-plan", c.CorrectivePlan, "propose_corrective_plan", True)
    finding_route("corrective-plan-review", c.CorrectivePlanReview, "review_corrective_plan", False)

    @router.get("/v1/institutional/findings/{identifier}/corrective-history")
    async def corrective_history(identifier: UUID, request: Request, before_version: int = 0):
        await available()
        require(before_version >= 0, "VALIDATION_FAILED", "Use a valid history version", 422)
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            service = AffiliationService(session, cfg, box, actor, request.state.correlation_id)
            finding = await service.row(t.findings, identifier, lock=False)
            await service.case(finding["case_id"])
            rows = list((await session.execute(select(t.journal).where(
                t.journal.c.resource_id == str(identifier),
                t.journal.c.action.in_(["standards.corrective_plan_proposed", "standards.corrective_plan_reviewed", "standards.response_submitted", "standards.response_reviewed"]),
                t.journal.c.version < before_version if before_version else True,
            ).order_by(t.journal.c.version.desc(), t.journal.c.id.desc()).limit(51))).mappings())
            items = []
            for row in rows[:50]:
                details = service.open(row["payload_ciphertext"])["details"]
                if row["action"] == "standards.response_submitted":
                    response = details["response"]
                    details = {"response_id": response["id"], "author_id": response["author_id"],
                               "response": service.open(response["details_ciphertext"])}
                items.append({"id": row["id"], "action": row["action"], "version": row["version"],
                              "actor_id": row["actor_id"], "recorded_at": row["recorded_at"], "details": details})
            await service.audit("standards.corrective_history_read", str(identifier))
            return {"items": items, "next_before_version": rows[49]["version"] if len(rows) > 50 else None}

    @router.post("/v1/institutional/notices/{identifier}/acknowledge")
    async def notice_ack(identifier: UUID, payload: Evidence, request: Request):
        async def guard(service, body):
            notice = await service.row(t.notices, identifier, lock=False)
            await service.case(notice["case_id"])
            require(notice["recipient_id"] == service.actor["id"])

        return await command(
            request,
            payload,
            AffiliationService,
            guard,
            lambda service, body: service.acknowledge_notice(str(identifier), body),
        )

    @router.post("/v1/institutional/notices/{identifier}/delivery-evidence")
    async def notice_delivery(identifier: UUID, payload: c.NoticeDelivery, request: Request):
        async def guard(service, body):
            notice = await service.row(t.notices, identifier, lock=False)
            _case, facility = await service.case(notice["case_id"])
            require(scoped(service.actor, {"STANDARDS_REVIEWER", "STANDARDS_DECIDER"}, facility))

        async def apply(service, body):
            notice = await service.row(t.notices, identifier, lock=False)
            require(
                notice["created_at"] <= body["observed_at"] <= db.now(),
                "INVALID_EVENT_TIME",
                "Record the actual observed notice service time",
                422,
            )
            row = {
                "id": db.uid(),
                "resource_id": str(identifier),
                "actor_id": service.actor["id"],
                "kind": "NOTICE_DELIVERY_EVIDENCE",
                "recorded_at": db.now(),
                "details_ciphertext": service.seal(body),
            }
            await service.session.execute(t.receipts.insert().values(**row))
            await service.audit("standards.notice_service_evidence_recorded", str(identifier))
            return {
                "id": row["id"],
                "state": "HUMAN_ATTESTED_DELIVERY_EVIDENCE_RECORDED",
                "response_period_waived": False,
                "provider_receipt_inferred": False,
            }

        return await command(request, payload, AffiliationService, guard, apply)

    @router.post("/v1/institutional/cases/{identifier}/files")
    async def upload(
        identifier: UUID,
        request: Request,
        criterion: str,
        filename: str,
        source: str,
        expires_at: datetime,
        expected_version: int,
    ):
        await available()
        require(
            2 <= len(criterion) <= 120
            and 1 <= len(filename) <= 200
            and 3 <= len(source) <= 3000
            and expires_at.tzinfo is not None
            and expires_at > datetime.now(UTC),
            "VALIDATION_FAILED",
            "Supply actual file metadata and future expiry with time zone",
            422,
        )
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            service = AffiliationService(session, cfg, box, actor, request.state.correlation_id)
            row, facility = await service.case(identifier)
            require(
                scoped(actor, {"FACILITY_ADMIN", "REGISTRY_STEWARD"}, facility)
                or row["inspector_id"] == actor["id"]
            )
        chunks = []
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
            require(
                size <= storage.MAX_EVIDENCE_BYTES, "FILE_TOO_LARGE", "Evidence exceeds 10 MiB", 413
            )
            chunks.append(chunk)
        content = b"".join(chunks)
        require(content, "EMPTY_FILE", "The file is empty", 422)
        body = {
            "criterion": criterion,
            "filename": filename,
            "source": source,
            "expires_at": expires_at.astimezone(UTC).isoformat(timespec="microseconds"),
            "expected_version": expected_version,
            "sha256": hashlib.sha256(content).hexdigest(),
        }

        async def guard(service, body):
            row, facility = await service.case(identifier)
            require(
                scoped(service.actor, {"FACILITY_ADMIN", "REGISTRY_STEWARD"}, facility)
                or row["inspector_id"] == service.actor["id"]
            )

        async def apply(service, body):
            row, _ = await service.case(identifier, write=True)
            from ..domain import expected

            expected(row, expected_version)
            require(
                row["state"] in {"OPEN", "ASSIGNED", "INSPECTED"},
                "INVALID_STATE",
                "Evidence is frozen after recommendation/decision",
                409,
            )
            require(
                criterion in {value["code"] for value in row["criteria_snapshot"]["requirements"]},
                "UNKNOWN_CRITERION",
                "Use an adopted criterion code",
                422,
            )
            key = f"evidence/lifecycle/{identifier}/{db.uid()}"
            media = request.headers.get("content-type", "").split(";")[0]
            digest = await run_in_threadpool(storage.store, cfg, key, content, media)
            value = {
                "id": db.uid(),
                "case_id": str(identifier),
                "criterion": criterion,
                "filename": filename,
                "source": source,
                "expires_at": body["expires_at"],
                "sha256": digest,
                "object_key": key,
                "media_type": media,
                "size": size,
                "scan_status": "CLEAN",
                "uploaded_by": service.actor["id"],
                "created_at": db.now(),
            }
            await service.session.execute(t.case_files.insert().values(**value))
            await service.emit("standards.evidence_stored", value, facility_id=row["facility_id"])
            return {key: value for key, value in value.items() if key != "object_key"}

        return await command(request, None, AffiliationService, guard, apply, body)

    @router.get("/v1/institutional/cases/{identifier}/files/{file_id}")
    async def download(identifier: UUID, file_id: UUID, request: Request):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            service = AffiliationService(session, cfg, box, actor, request.state.correlation_id)
            case, _ = await service.case(identifier)
            row = (
                (
                    await session.execute(
                        select(t.case_files).where(
                            t.case_files.c.id == str(file_id),
                            t.case_files.c.case_id == str(identifier),
                        )
                    )
                )
                .mappings()
                .first()
            )
            if not row:
                row = (
                    (
                        await session.execute(
                            select(db.evidence).where(
                                db.evidence.c.id == str(file_id),
                                db.evidence.c.application_id.in_(
                                    select(db.applications.c.id).where(
                                        db.applications.c.facility_id == case["facility_id"]
                                    )
                                ),
                            )
                        )
                    )
                    .mappings()
                    .first()
                )
            require(row, "NOT_FOUND_OR_NOT_PERMITTED", "File unavailable", 404)
            require(
                row["scan_status"] == "CLEAN",
                "EVIDENCE_UNAVAILABLE",
                "Unscanned evidence is unavailable",
                503,
            )
            await service.audit("standards.evidence_read", str(file_id))
        value = await run_in_threadpool(storage.read, cfg, row["object_key"])
        require(
            len(value) == row["size"] and hashlib.sha256(value).hexdigest() == row["sha256"],
            "INTEGRITY_FAILURE",
            "The stored evidence did not verify",
            503,
        )
        return Response(
            value,
            media_type="application/octet-stream",
            headers={"Content-Disposition": "attachment; filename=verified-evidence"},
        )

    @router.get("/v1/institutional/articles")
    async def articles(request: Request, after: str = "", query: str = ""):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            allowed = or_(
                predicate(actor, EDITING, t.articles, "facility_id"),
                t.articles.c.facility_id.is_(None) if has(actor, EDITING) else false(),
            )
            rows = list(
                (
                    await session.execute(
                        select(t.articles, t.revisions.c.title, t.content_states.c.state)
                        .join(t.revisions, t.articles.c.latest_revision_id == t.revisions.c.id)
                        .join(t.content_states, t.content_states.c.revision_id == t.revisions.c.id)
                        .where(
                            allowed,
                            t.articles.c.id > after,
                            t.revisions.c.title.ilike("%" + query[:120] + "%"),
                        )
                        .order_by(t.articles.c.id)
                        .limit(101)
                    )
                ).mappings()
            )
            return page(rows)

    @router.post("/v1/institutional/articles")
    async def create_article(payload: c.Content, request: Request):
        async def guard(service, body):
            if body["facility_id"]:
                await service.facility(body["facility_id"], EDITORS)
            else:
                require(has(service.actor, EDITORS))

        return await command(
            request, payload, KnowledgeService, guard, lambda service, body: service.revise(body)
        )

    @router.get("/v1/institutional/articles/{identifier}")
    async def article_detail(identifier: UUID, request: Request):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            service = KnowledgeService(session, cfg, box, actor, request.state.correlation_id)
            article = await service.article(identifier, EDITING)
            revisions = list(
                (
                    await session.execute(
                        select(t.revisions, t.content_states.c.state)
                        .join(t.content_states, t.content_states.c.revision_id == t.revisions.c.id)
                        .where(t.revisions.c.article_id == str(identifier))
                        .order_by(t.revisions.c.sequence.desc())
                        .limit(4)
                    )
                ).mappings()
            )
            await service.audit("knowledge.editorial_history_read", str(identifier))
            deliveries = await session.scalar(
                select(func.count())
                .select_from(t.deliveries)
                .where(t.deliveries.c.article_id == str(identifier))
            )
            receipt_counts = (
                await session.execute(
                    select(t.content_receipts.c.kind, func.count())
                    .where(
                        t.content_receipts.c.delivery_id.in_(
                            select(t.deliveries.c.id).where(
                                t.deliveries.c.article_id == str(identifier)
                            )
                        )
                    )
                    .group_by(t.content_receipts.c.kind)
                )
            ).all()
            return {
                "article": article,
                "revisions": [
                    {**clean(row), "content": service.open(row["content_ciphertext"])}
                    for row in revisions[:3]
                ],
                "truncated": len(revisions) > 3,
                "next_sequence": revisions[2]["sequence"] if len(revisions) > 3 else None,
                "reviews": [
                    {**clean(review), "evidence": service.open(review["evidence_ciphertext"])}
                    for review in (
                        await session.execute(
                            select(t.content_reviews).where(
                                t.content_reviews.c.revision_id.in_(
                                    [row["id"] for row in revisions[:3]]
                                )
                            )
                        )
                    ).mappings()
                ],
                "measurements": {
                    "portal_deliveries": deliveries,
                    "receipt_events": dict(receipt_counts),
                    "understanding_and_health_outcomes_inferred": False,
                },
            }

    @router.get("/v1/institutional/articles/{identifier}/revisions")
    async def revision_page(identifier: UUID, request: Request, before_sequence: int = 2147483647):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            service = KnowledgeService(session, cfg, box, actor, request.state.correlation_id)
            await service.article(identifier, EDITING)
            rows = list(
                (
                    await session.execute(
                        select(t.revisions, t.content_states.c.state)
                        .join(t.content_states, t.content_states.c.revision_id == t.revisions.c.id)
                        .where(
                            t.revisions.c.article_id == str(identifier),
                            t.revisions.c.sequence < before_sequence,
                        )
                        .order_by(t.revisions.c.sequence.desc())
                        .limit(4)
                    )
                ).mappings()
            )
            await service.audit("knowledge.earlier_revisions_read", str(identifier))
            return {
                "items": [
                    {**clean(row), "content": service.open(row["content_ciphertext"])}
                    for row in rows[:3]
                ],
                "next_sequence": rows[2]["sequence"] if len(rows) > 3 else None,
            }

    def content_route(path, model, method, roles):
        async def endpoint(identifier: UUID, request: Request, payload: model):
            async def guard(service, body):
                await service.article(identifier, roles)

            return await command(
                request,
                payload,
                KnowledgeService,
                guard,
                lambda service, body: getattr(service, method)(str(identifier), body),
            )

        router.add_api_route(
            "/v1/institutional/articles/{identifier}/" + path, endpoint, methods=["POST"]
        )

    @router.post("/v1/institutional/articles/{identifier}/revise")
    async def revise_article(identifier: UUID, payload: c.Revision, request: Request):
        async def guard(service, body):
            await service.article(identifier, EDITORS)

        return await command(
            request,
            payload,
            KnowledgeService,
            guard,
            lambda service, body: service.revise(body, str(identifier)),
        )

    content_route("submit", c.Versioned, "submit", EDITORS)
    content_route("review", c.ContentReview, "review_content", REVIEWERS)
    content_route("publish", c.Versioned, "publish", PUBLISHERS)
    content_route("withdraw", c.Versioned, "withdraw", PUBLISHERS)
    content_route("distribute", c.Distribute, "distribute", PUBLISHERS)

    @router.get("/v1/institutional/inbox")
    async def inbox(request: Request, after: str = ""):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            allowed = or_(
                t.articles.c.facility_id.is_(None),
                predicate(actor, STAFF_ROLES, t.articles, "facility_id"),
            )
            rows = list(
                (
                    await session.execute(
                        select(t.deliveries, t.revisions.c.title)
                        .join(t.articles, t.articles.c.id == t.deliveries.c.article_id)
                        .join(t.revisions, t.revisions.c.id == t.deliveries.c.revision_id)
                        .where(
                            allowed,
                            t.deliveries.c.recipient_id == actor["id"],
                            t.deliveries.c.id > after,
                        )
                        .order_by(t.deliveries.c.id)
                        .limit(101)
                    )
                ).mappings()
            )
            return page(rows)

    @router.get("/v1/institutional/inbox/{identifier}")
    async def inbox_content(identifier: UUID, request: Request, jurisdiction: str = ""):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            service = KnowledgeService(session, cfg, box, actor, request.state.correlation_id)
            delivery = await service.row(t.deliveries, identifier)
            require(delivery["recipient_id"] == actor["id"])
            article = await service.article(delivery["article_id"])
            await service.reader(article)
            revision, state = await service.revision(article, article["published_revision_id"])
            require(
                current(revision, state),
                "CONTENT_NOT_CURRENT",
                "This content is withdrawn, superseded, expired or due for review",
                410,
            )
            await service.audit("knowledge.recipient_content_read", revision["id"])
            require(
                not jurisdiction or jurisdiction in revision["jurisdictions"],
                "APPLICABILITY_MISMATCH",
                "This version does not cover the selected jurisdiction",
                404,
            )
            if revision["kind"] == "CLINICAL_GUIDANCE" and not jurisdiction:
                return {
                    "delivery": clean(delivery),
                    "revision": clean(revision),
                    "state": "APPLICABILITY_SELECTION_REQUIRED",
                    "body_served": False,
                    "receipt_inferred": False,
                }
            return {
                "delivery": clean(delivery),
                "revision": {
                    **clean(revision),
                    "content": service.open(revision["content_ciphertext"]),
                },
                "receipt_inferred": False,
                "jurisdiction": jurisdiction,
                "body_served": True,
            }

    @router.post("/v1/institutional/inbox/{identifier}/receipt")
    async def content_receipt(identifier: UUID, payload: c.ContentReceipt, request: Request):
        async def guard(service, body):
            row = await service.row(t.deliveries, identifier)
            require(row["recipient_id"] == service.actor["id"])
            await service.reader(await service.article(row["article_id"]))

        return await command(
            request,
            payload,
            KnowledgeService,
            guard,
            lambda service, body: service.content_receipt(str(identifier), body),
        )

    def public_query():
        return (
            select(t.revisions, t.articles.c.facility_id)
            .join(t.articles, t.articles.c.published_revision_id == t.revisions.c.id)
            .where(t.articles.c.id == t.revisions.c.article_id)
            .join(t.content_states, t.content_states.c.revision_id == t.revisions.c.id)
            .where(
                t.content_states.c.state == "PUBLISHED",
                t.revisions.c.audience == "PUBLIC",
                t.revisions.c.valid_from <= db.now(),
                t.revisions.c.valid_until > db.now(),
                t.revisions.c.review_due_at > db.now(),
            )
        )

    @router.get("/v1/knowledge")
    async def library(language: str = "", jurisdiction: str = "", query: str = "", after: str = ""):
        await available()
        async with database.transaction() as session:
            statement = public_query().where(
                t.revisions.c.article_id > after, t.revisions.c.title.ilike("%" + query[:120] + "%")
            )
            if language:
                statement = statement.where(t.revisions.c.language == language[:40])
            if jurisdiction:
                if database.postgres:
                    statement = statement.where(
                        t.revisions.c.jurisdictions.cast(JSONB).contains([jurisdiction[:80]])
                    )
                else:
                    values = func.json_each(t.revisions.c.jurisdictions).table_valued("value")
                    statement = statement.where(
                        select(1)
                        .select_from(values)
                        .where(values.c.value == jurisdiction[:80])
                        .exists()
                    )
            rows = list(
                (
                    await session.execute(statement.order_by(t.revisions.c.article_id).limit(101))
                ).mappings()
            )
            return {
                "items": [
                    {
                        key: row[key]
                        for key in (
                            "article_id",
                            "id",
                            "title",
                            "sequence",
                            "kind",
                            "language",
                            "jurisdictions",
                            "valid_from",
                            "valid_until",
                            "review_due_at",
                            "facility_id",
                        )
                    }
                    for row in rows[:100]
                ],
                "next_cursor": rows[99]["article_id"] if len(rows) > 100 else None,
                "as_of": db.now(),
            }

    @router.get("/v1/knowledge/{identifier}")
    async def public_article(identifier: UUID, jurisdiction: str = ""):
        await available()
        async with database.transaction() as session:
            row = (
                (await session.execute(public_query().where(t.articles.c.id == str(identifier))))
                .mappings()
                .first()
            )
            if not row:
                published = await session.scalar(
                    select(t.articles.c.published_revision_id).where(
                        t.articles.c.id == str(identifier)
                    )
                )
                public = (
                    await session.scalar(
                        select(t.revisions.c.id).where(
                            t.revisions.c.id == published, t.revisions.c.audience == "PUBLIC"
                        )
                    )
                    if published
                    else None
                )
                require(
                    not public,
                    "CONTENT_NOT_CURRENT",
                    "This publication is withdrawn, superseded, expired or due for review",
                    410,
                )
                require(
                    False, "NOT_FOUND_OR_NOT_PERMITTED", "Current public content unavailable", 404
                )
            require(
                not jurisdiction or jurisdiction in row["jurisdictions"],
                "APPLICABILITY_MISMATCH",
                "Choose a jurisdiction explicitly covered by this version",
                404,
            )
            result = {
                key: row[key]
                for key in (
                    "article_id",
                    "id",
                    "title",
                    "sequence",
                    "kind",
                    "language",
                    "jurisdictions",
                    "valid_from",
                    "valid_until",
                    "review_due_at",
                )
            }
            if row["kind"] == "CLINICAL_GUIDANCE" and not jurisdiction:
                return {**result, "state": "APPLICABILITY_SELECTION_REQUIRED", "body_served": False}
            body = KnowledgeService(session, cfg, box, None, "public-content").open(
                row["content_ciphertext"]
            )
            return {
                **result,
                "state": "CURRENT_APPROVED_PUBLICATION",
                "body_served": True,
                "content": {
                    key: body[key]
                    for key in (
                        "body",
                        "correction_summary",
                        "purpose",
                        "support_text",
                        "support_url",
                        "licence_reference",
                        "sources",
                    )
                },
                "care_acceptance_inferred": False,
            }

    @router.get("/v1/institutional/history/{kind}/{identifier}")
    async def history(kind: str, identifier: UUID, request: Request, after: str = ""):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            service = Service(session, cfg, box, actor, request.state.correlation_id)
            if kind == "articles":
                await service.article(identifier, EDITING)
                condition = t.journal.c.resource_id == str(identifier)
            else:
                require(kind == "cases", "VALIDATION_FAILED", "Choose cases or articles", 422)
                await service.case(identifier)
                condition = or_(
                    t.journal.c.resource_id == str(identifier),
                    t.journal.c.resource_id.in_(
                        select(t.findings.c.id).where(t.findings.c.case_id == str(identifier))
                    ),
                    t.journal.c.resource_id.in_(
                        select(t.decisions.c.id).where(t.decisions.c.case_id == str(identifier))
                    ),
                    t.journal.c.resource_id.in_(
                        select(t.notices.c.id).where(t.notices.c.case_id == str(identifier))
                    ),
                )
            rows = list(
                (
                    await session.execute(
                        select(t.journal)
                        .where(condition, t.journal.c.id > after)
                        .order_by(t.journal.c.id)
                        .limit(2)
                    )
                ).mappings()
            )
            await service.audit("institutional.history_read", str(identifier))
            return {
                "items": [
                    {
                        **clean(row),
                        "details": service.open(row["payload_ciphertext"]).get("details"),
                    }
                    for row in rows[:1]
                ],
                "next_cursor": rows[0]["id"] if len(rows) > 1 else None,
            }

    from .captures import install_capture_routes
    from .teams import install_team_routes

    install_team_routes(router, cfg, database, box, actor_for, available, command, c)
    install_capture_routes(router, cfg, database, box, actor_for, available, command)
    app.include_router(router)
