"""Directorate reporting HTTP boundary; no clinical or confidential-case drill-through."""

from uuid import UUID

from fastapi import APIRouter, Request, Response
from sqlalchemy import and_, false, func, or_, select, text

from .. import db
from ..domain import RuleError, require
from . import contracts as c
from . import store as s
from . import tables as t
from .operations import DirectorateService
from .service import catalogue

PREFIX = "/v1/reporting"


def install(app, cfg, database, box, actor_for):
    router = APIRouter(prefix=PREFIX)

    async def service_for(session, request):
        require(
            cfg.reporting_enabled,
            "REPORTING_PAUSED",
            "Reporting is paused by the service operator",
            503,
        )
        require(
            (await database.version() or 0) >= 3,
            "REPORTING_MIGRATION_REQUIRED",
            "Reporting installation is awaiting its database migration",
            503,
        )
        request.state.reporting_ready = True
        actor = await actor_for(session, request)
        return DirectorateService(session, cfg, box, actor, request.state.correlation_id)

    async def command(request, payload, callback, authorize):
        body = payload.model_dump(mode="json")
        actor = None
        try:
            async with database.transaction() as session:
                service = await service_for(session, request)
                if database.postgres:
                    await session.execute(text("SELECT pg_advisory_xact_lock(782025011)"))
                    service.actor = await actor_for(session, request)
                actor = service.actor
                await authorize(service, body)

                async def apply():
                    return s.envelope(cfg, await callback(service, body))

                return await s.idempotent(
                    session,
                    database,
                    box,
                    actor,
                    request.url.path,
                    request.headers.get("Idempotency-Key"),
                    body,
                    apply,
                )
        except RuleError:
            if getattr(request.state, "reporting_ready", False):
                request.state.reporting_denial_recorded = True
                async with database.transaction() as session:
                    await s.audit(
                        session,
                        actor,
                        "reporting.command_denied",
                        None,
                        None,
                        request.state.correlation_id,
                        outcome="DENIED",
                    )
            raise

    async def governor(service, body):
        service.governor()

    async def scoped_source(service, body):
        await service.scope(body, s.ANALYSTS)

    async def active_member(service):
        require(
            any(g["role"] in s.ALL_ROLES for g in service.actor["grants"]),
            "REPORTING_ASSIGNMENT_REQUIRED",
            "A reporting, review or oversight assignment is required",
            403,
        )

    async def scopes(session, actor, query=""):
        unit_clauses, facility_clauses = [], []
        zone = db.units.alias("reporting_zone")
        all_units = False
        for grant in actor["grants"]:
            if grant["role"] not in s.ALL_ROLES:
                continue
            if grant["scope_type"] == "GLOBAL":
                all_units = True
            elif grant["scope_type"] == "REGION":
                unit_clauses.extend(
                    [db.units.c.id == grant["scope_id"], db.units.c.parent_id == grant["scope_id"]]
                )
                facility_clauses.append(zone.c.parent_id == grant["scope_id"])
            elif grant["scope_type"] == "ZONE":
                unit_clauses.append(db.units.c.id == grant["scope_id"])
                facility_clauses.append(db.facilities.c.zone_id == grant["scope_id"])
            elif grant["scope_type"] == "FACILITY":
                facility_clauses.append(db.facilities.c.id == grant["scope_id"])
        unit_query = select(db.units).where(
            True if all_units else or_(*unit_clauses) if unit_clauses else false()
        )
        facility_query = select(
            db.facilities.c.id,
            db.facilities.c.name,
            db.facilities.c.zone_id,
            zone.c.parent_id.label("region_id"),
        ).join(zone, zone.c.id == db.facilities.c.zone_id)
        facility_query = facility_query.where(
            True if all_units else or_(*facility_clauses) if facility_clauses else false()
        )
        if query:
            unit_query = unit_query.where(db.units.c.name.ilike("%" + query[:160] + "%"))
            facility_query = facility_query.where(
                db.facilities.c.name.ilike("%" + query[:160] + "%")
            )
        units = list(
            (await session.execute(unit_query.order_by(db.units.c.name).limit(201))).mappings()
        )
        facilities = list(
            (
                await session.execute(facility_query.order_by(db.facilities.c.name).limit(201))
            ).mappings()
        )
        result = (
            [{"scope_type": "GLOBAL", "scope_id": "GLOBAL", "label": "Directorate / global scope"}]
            if all_units
            else []
        )
        result.extend(
            {
                "scope_type": row["kind"],
                "scope_id": row["id"],
                "label": row["name"],
                "region_id": row["id"] if row["kind"] == "REGION" else row["parent_id"],
                "zone_id": row["id"] if row["kind"] == "ZONE" else None,
            }
            for row in units[:200]
        )
        result.extend(
            {
                "scope_type": "FACILITY",
                "scope_id": row["id"],
                "label": row["name"],
                "facility_id": row["id"],
                "zone_id": row["zone_id"],
                "region_id": row["region_id"],
            }
            for row in facilities[:200]
        )
        return {
            "items": result,
            "truncated": len(units) > 200 or len(facilities) > 200,
            "recovery": "Search the exact unit name to narrow results",
        }

    @router.get("/context")
    async def context(request: Request, query: str = ""):
        async with database.transaction() as session:
            service = await service_for(session, request)
            actor = service.actor
            roles = sorted({g["role"] for g in actor["grants"] if g["role"] in s.ALL_ROLES})
            return {
                "roles": roles,
                "scopes": await scopes(session, actor, query)
                if roles
                else {"items": [], "truncated": False},
                "catalogue": catalogue() if roles else [],
                "authority": "CENTRAL_CLOUD",
                "as_of": db.now(),
            }

    @router.get("/people")
    async def people(request: Request):
        async with database.transaction() as session:
            service = await service_for(session, request)
            await active_member(service)
            rows = (
                await session.execute(
                    select(
                        db.accounts.c.id,
                        db.accounts.c.name,
                        db.grants.c.role,
                        db.grants.c.scope_type,
                        db.grants.c.scope_id,
                    )
                    .join(db.grants, db.grants.c.account_id == db.accounts.c.id)
                    .where(
                        db.accounts.c.active.is_(True),
                        db.grants.c.role.in_(s.ALL_ROLES),
                        db.grants.c.revoked.is_(False),
                        db.grants.c.valid_from <= db.now(),
                        db.grants.c.valid_until > db.now(),
                    )
                    .limit(1000)
                )
            ).mappings()
            permitted_scopes = (await scopes(session, service.actor))["items"]
            grouped = {}
            for row in rows:
                candidate = {
                    "grants": [
                        {
                            "role": row["role"],
                            "scope_type": row["scope_type"],
                            "scope_id": row["scope_id"],
                        }
                    ]
                }
                if not any(s.permits(candidate, s.ALL_ROLES, scope) for scope in permitted_scopes):
                    continue
                grouped.setdefault(row["id"], {"id": row["id"], "name": row["name"], "roles": []})[
                    "roles"
                ].append(row["role"])
            return {"items": list(grouped.values())}

    @router.get("/definitions")
    async def definitions(request: Request):
        async with database.transaction() as session:
            service = await service_for(session, request)
            await active_member(service)
            return {
                "items": [
                    dict(row)
                    for row in (
                        await session.execute(
                            select(t.definitions).order_by(t.definitions.c.metric_id).limit(500)
                        )
                    ).mappings()
                ]
            }

    @router.get("/policies")
    async def policies(request: Request):
        async with database.transaction() as session:
            service = await service_for(session, request)
            await active_member(service)
            revoked = set(
                (await session.execute(select(t.policy_revocations.c.policy_id))).scalars()
            )
            return {
                "items": [
                    {**dict(row), "revoked": row["id"] in revoked}
                    for row in (
                        await session.execute(
                            select(t.policies).order_by(t.policies.c.created_at.desc()).limit(200)
                        )
                    ).mappings()
                ]
            }

    @router.get("/obligations")
    async def obligations(request: Request, after: str = ""):
        async with database.transaction() as session:
            service = await service_for(session, request)
            rows = list(
                (
                    await session.execute(
                        select(t.obligations)
                        .where(
                            s.visibility(
                                service.actor, s.SOURCE_READERS | s.PROGRAMMES, t.obligations
                            ),
                            t.obligations.c.id > after,
                        )
                        .order_by(t.obligations.c.id)
                        .limit(101)
                    )
                ).mappings()
            )
            result = []
            for row in rows[:100]:
                report = (
                    (
                        await session.execute(
                            select(
                                t.returns.c.id,
                                t.returns.c.version,
                                t.returns.c.state,
                                t.returns.c.received_at,
                            ).where(t.returns.c.obligation_id == row["id"])
                        )
                    )
                    .mappings()
                    .first()
                )
                result.append(
                    {
                        **dict(row),
                        "return": dict(report) if report else None,
                        "receipt_state": report["state"] if report else "MISSING",
                        "overdue": row["due_at"] < db.now()
                        and (not report or not report["received_at"]),
                        "late": bool(
                            report
                            and report["received_at"]
                            and report["received_at"] > row["due_at"]
                        ),
                    }
                )
            return {
                "items": result,
                "next_cursor": rows[99]["id"] if len(rows) > 100 else None,
                "as_of": db.now(),
            }

    @router.get("/returns/{identifier}")
    async def return_detail(identifier: UUID, request: Request):
        async with database.transaction() as session:
            service = await service_for(session, request)
            row, obligation = await service.return_for(str(identifier))
            validation = (
                await s.load(session, t.validation_runs, row["validation_id"])
                if row["validation_id"]
                else None
            )
            await s.audit(
                session,
                service.actor,
                "reporting.return_read",
                obligation,
                str(identifier),
                request.state.correlation_id,
            )
            return {**s.opened(box, row), "obligation": obligation, "validation": validation}

    @router.get("/returns/{identifier}/history")
    async def return_history(identifier: UUID, request: Request):
        async with database.transaction() as session:
            service = await service_for(session, request)
            _, obligation = await service.return_for(str(identifier))
            items = [
                dict(row) | {"data": service.data(row)}
                for row in (
                    await session.execute(
                        select(t.versions)
                        .where(t.versions.c.return_id == str(identifier))
                        .order_by(t.versions.c.version)
                        .limit(500)
                    )
                ).mappings()
            ]
            for item in items:
                item.pop("payload_ciphertext", None)
            await s.audit(
                session,
                service.actor,
                "reporting.return_history_read",
                obligation,
                str(identifier),
                request.state.correlation_id,
            )
            return {"items": items}

    @router.get("/quality")
    async def quality(request: Request):
        async with database.transaction() as session:
            service = await service_for(session, request)
            rows = (
                await session.execute(
                    select(
                        t.returns,
                        t.obligations.c.scope_type,
                        t.obligations.c.scope_id,
                        t.obligations.c.region_id,
                        t.obligations.c.zone_id,
                        t.obligations.c.facility_id,
                    )
                    .join(t.obligations)
                    .where(
                        s.visibility(service.actor, s.SOURCE_READERS | s.PROGRAMMES, t.obligations),
                        t.returns.c.state.in_(["DRAFT", "SUBMITTED", "RETURNED_FOR_CORRECTION"]),
                    )
                    .order_by(t.returns.c.updated_at)
                    .limit(200)
                )
            ).mappings()
            items = []
            for row in rows:
                run = await s.load(session, t.validation_runs, row["validation_id"])
                items.append(
                    {
                        "id": row["id"],
                        "obligation_id": row["obligation_id"],
                        "version": row["version"],
                        "state": row["state"],
                        "findings": run["findings"],
                        "rule_version": run["rule_version"],
                        "source_hash": row["source_hash"],
                    }
                )
            return {"items": items, "as_of": db.now()}

    @router.get("/imports/{identifier}")
    async def import_detail(identifier: UUID, request: Request):
        async with database.transaction() as session:
            service = await service_for(session, request)
            row = await s.load(session, t.imports, identifier)
            obligation = await service.obligation(row["obligation_id"])
            await s.audit(
                session,
                service.actor,
                "reporting.import_evidence_read",
                obligation,
                str(identifier),
                request.state.correlation_id,
            )
            return {key: value for key, value in row.items() if key != "raw_ciphertext"} | {
                "raw_source": box.decrypt(row["raw_ciphertext"])
            }

    @router.get("/cohorts")
    async def cohorts(request: Request):
        async with database.transaction() as session:
            service = await service_for(session, request)
            rows = [
                dict(row)
                for row in (
                    await session.execute(
                        select(t.cohorts)
                        .where(
                            s.visibility(
                                service.actor,
                                s.ANALYSTS | s.REVIEWERS | s.GOVERNORS | s.LEADERS | s.PROGRAMMES,
                                t.cohorts,
                            )
                        )
                        .limit(200)
                    )
                ).mappings()
            ]
            return {"items": rows}

    @router.get("/snapshots")
    async def snapshots(request: Request):
        async with database.transaction() as session:
            service = await service_for(session, request)
            rows = (
                await session.execute(
                    select(t.snapshots, t.cohorts.c.name)
                    .join(t.cohorts)
                    .where(
                        s.visibility(
                            service.actor,
                            s.ANALYSTS | s.REVIEWERS | s.GOVERNORS | s.LEADERS | s.PROGRAMMES,
                            t.cohorts,
                        )
                    )
                    .order_by(t.snapshots.c.created_at.desc())
                    .limit(200)
                )
            ).mappings()
            items = []
            for row in rows:
                review = (
                    await session.execute(
                        select(t.snapshot_reviews.c.decision).where(
                            t.snapshot_reviews.c.snapshot_id == row["id"]
                        )
                    )
                ).scalar_one_or_none()
                stale = await session.scalar(
                    select(func.count())
                    .select_from(t.invalidations)
                    .where(t.invalidations.c.snapshot_id == row["id"])
                )
                if review != "RELEASE" and not s.permits(
                    service.actor,
                    s.ANALYSTS | s.REVIEWERS | s.GOVERNORS,
                    await s.load(session, t.cohorts, row["cohort_id"]),
                ):
                    continue
                items.append(
                    {key: value for key, value in row.items() if key != "payload_ciphertext"}
                    | {"state": review or "PREPARED", "stale": bool(stale)}
                )
            return {"items": items, "as_of": db.now()}

    @router.get("/snapshots/{identifier}")
    async def snapshot_detail(identifier: UUID, request: Request):
        async with database.transaction() as session:
            service = await service_for(session, request)
            return await service.snapshot_public(str(identifier))

    @router.get("/snapshots/{identifier}/reconciliation")
    async def snapshot_reconciliation(identifier: UUID, request: Request):
        async with database.transaction() as session:
            service = await service_for(session, request)
            row = await s.load(session, t.snapshots, identifier)
            cohort = await service.cohort_for(row["cohort_id"], s.ANALYSTS | s.REVIEWERS)
            await s.audit(
                session,
                service.actor,
                "analytics.source_reconciliation_read",
                cohort,
                str(identifier),
                request.state.correlation_id,
                purpose="SOURCE_QUALITY_REVIEW",
            )
            return {"id": row["id"], "source_hash": row["source_hash"], "data": service.data(row)}

    @router.get("/snapshots/{identifier}/export.csv")
    async def snapshot_export(identifier: UUID, request: Request):
        async with database.transaction() as session:
            service = await service_for(session, request)
            data = await service.export_snapshot(str(identifier))
            return Response(
                data,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename="lwh-snapshot-{identifier}.csv"',
                    "Cache-Control": "no-store",
                },
            )

    @router.get("/categories")
    async def categories(request: Request):
        async with database.transaction() as session:
            service = await service_for(session, request)
            await active_member(service)
            return {
                "items": [
                    dict(row)
                    for row in (
                        await session.execute(select(t.event_categories).limit(200))
                    ).mappings()
                ]
            }

    @router.get("/duty-windows")
    async def duty_windows(request: Request):
        async with database.transaction() as session:
            service = await service_for(session, request)
            roles = s.GOVERNORS | s.CASE_REVIEWERS | s.CASE_REPORTERS
            return {
                "items": [
                    dict(row)
                    for row in (
                        await session.execute(
                            select(t.duty_windows)
                            .where(s.visibility(service.actor, roles, t.duty_windows))
                            .order_by(t.duty_windows.c.valid_until.desc())
                            .limit(200)
                        )
                    ).mappings()
                ]
            }

    @router.get("/safety-cases")
    async def safety_cases(request: Request):
        async with database.transaction() as session:
            service = await service_for(session, request)
            rows = (
                await session.execute(
                    select(t.cases)
                    .where(
                        s.visibility(service.actor, s.CASE_REPORTERS | s.CASE_REVIEWERS, t.cases)
                    )
                    .order_by(t.cases.c.acknowledge_by)
                    .limit(200)
                )
            ).mappings()
            result = []
            for row in rows:
                if row["created_by"] != service.actor["id"] and not s.permits(
                    service.actor, s.CASE_REVIEWERS, row
                ):
                    continue
                result.append(
                    {key: value for key, value in row.items() if key != "payload_ciphertext"}
                )
            return {"items": result, "as_of": db.now()}

    @router.get("/safety-cases/{identifier}")
    async def safety_detail(identifier: UUID, request: Request):
        async with database.transaction() as session:
            service = await service_for(session, request)
            row = await service.case_for(str(identifier))
            await s.audit(
                session,
                service.actor,
                "quality.case_read",
                row,
                row["id"],
                request.state.correlation_id,
                purpose="RESTRICTED_SAFETY_REVIEW",
            )
            return service.case_view(row)

    @router.get("/actions")
    async def actions(request: Request):
        async with database.transaction() as session:
            service = await service_for(session, request)
            query = select(t.actions).where(
                s.visibility(
                    service.actor,
                    s.PROGRAMMES | s.ACTION_OWNERS | s.REVIEWERS | s.CASE_REVIEWERS,
                    t.actions,
                ),
                or_(
                    t.actions.c.created_by == service.actor["id"],
                    t.actions.c.owner_id == service.actor["id"],
                    t.actions.c.fallback_id == service.actor["id"],
                    t.actions.c.reviewer_id == service.actor["id"],
                    t.actions.c.handover_to == service.actor["id"],
                ),
            )
            result = []
            for row in (
                await session.execute(query.order_by(t.actions.c.due_at).limit(200))
            ).mappings():
                if row["protected"] and not s.permits(service.actor, s.CASE_REVIEWERS, row):
                    continue
                result.append(
                    s.opened(box, row)
                    | {"overdue": row["due_at"] < db.now() and row["state"] != "REVIEWED_COMPLETE"}
                )
            return {"items": result, "as_of": db.now()}

    @router.get("/actions/{identifier}")
    async def action_detail(identifier: UUID, request: Request):
        async with database.transaction() as session:
            service = await service_for(session, request)
            row = await service.action_for(str(identifier))
            return s.opened(box, row)

    @router.get("/exceptions")
    async def exceptions(request: Request):
        async with database.transaction() as session:
            service = await service_for(session, request)
            roles = s.GOVERNORS | s.PROGRAMMES | s.CASE_REVIEWERS | s.REPORTERS
            rows = (
                await session.execute(
                    select(
                        t.escalations, t.escalation_receipts.c.created_at.label("acknowledged_at")
                    )
                    .outerjoin(
                        t.escalation_receipts,
                        t.escalation_receipts.c.escalation_id == t.escalations.c.id,
                    )
                    .where(
                        or_(
                            s.visibility(service.actor, roles, t.escalations),
                            and_(
                                t.escalations.c.owner_id == service.actor["id"],
                                s.visibility(service.actor, s.ALL_ROLES, t.escalations),
                            ),
                        )
                    )
                    .order_by(t.escalations.c.due_at)
                    .limit(200)
                )
            ).mappings()
            return {
                "items": [dict(row) for row in rows],
                "as_of": db.now(),
                "scheduled_job_frequency": "DAILY_PLUS_AUTHENTICATED_MANUAL_RECONCILIATION",
            }

    @router.get("/audit")
    async def audit_history(request: Request):
        async with database.transaction() as session:
            service = await service_for(session, request)
            service.governor()
            return {
                "items": [
                    dict(row)
                    for row in (
                        await session.execute(
                            select(t.audit).order_by(t.audit.c.created_at.desc()).limit(200)
                        )
                    ).mappings()
                ]
            }

    def create_route(path, model, method, authorize):
        async def endpoint(payload: model, request: Request):
            async def apply(service, body):
                return await getattr(service, method)(body)

            return await command(request, payload, apply, authorize)

        endpoint.__name__ = "reporting_create_" + path.replace("-", "_")
        router.add_api_route("/" + path, endpoint, methods=["POST"])

    async def case_create_guard(service, body):
        await service.scope(body, s.CASE_REPORTERS)

    async def action_create_guard(service, body):
        await service.scope(body, s.PROGRAMMES | s.CASE_REVIEWERS)

    for path, model, method, guard in [
        ("definitions", c.Definition, "definition", governor),
        ("obligations", c.Obligation, "create_obligation", governor),
        ("policies", c.DisclosurePolicy, "policy", governor),
        ("cohorts", c.Cohort, "cohort", scoped_source),
        ("categories", c.EventCategory, "category", governor),
        ("duty-windows", c.DutyWindow, "duty", governor),
        ("safety-cases", c.SafetyCase, "safety_case", case_create_guard),
        ("actions", c.Action, "action", action_create_guard),
    ]:
        create_route(path, model, method, guard)

    @router.post("/snapshots")
    async def prepare_snapshot(payload: c.Snapshot, request: Request):
        async def guard(service, body):
            cohort = await service.cohort_for(body["cohort_id"], s.ANALYSTS)
            await service.active_policy(cohort["policy_id"])

        async def apply(service, body):
            return await service.build_snapshot(body["cohort_id"])

        return await command(request, payload, apply, guard)

    def resource_route(path, model, method, guard_kind):
        async def endpoint(identifier: UUID, payload: model, request: Request):
            async def guard(service, body):
                if guard_kind == "obligation":
                    await service.obligation(str(identifier), s.REPORTERS)
                elif guard_kind == "reporter":
                    await service.return_for(str(identifier), s.REPORTERS)
                elif guard_kind == "reviewer":
                    await service.return_for(str(identifier), s.REVIEWERS)
                elif guard_kind == "snapshot":
                    row = await s.load(service.session, t.snapshots, identifier)
                    cohort = await service.cohort_for(row["cohort_id"], s.REVIEWERS)
                    await service.active_policy(cohort["policy_id"])
                elif guard_kind == "case":
                    row = await service.case_for(
                        str(identifier), metadata=body["action"] == "ASSIGN"
                    )
                    s.require_role(service.actor, s.CASE_REVIEWERS, row)
                elif guard_kind == "action":
                    await service.action_for(str(identifier))
                elif guard_kind == "duty":
                    row = await s.load(service.session, t.duty_windows, identifier)
                    s.require_role(service.actor, s.CASE_REVIEWERS, row)
                    require(row["account_id"] == service.actor["id"])
                elif guard_kind == "exception":
                    row = await s.load(service.session, t.escalations, identifier)
                    s.require_role(service.actor, s.ALL_ROLES, row)
                    require(row["owner_id"] == service.actor["id"])
                else:
                    service.governor()

            async def apply(service, body):
                return await getattr(service, method)(str(identifier), body)

            return await command(request, payload, apply, guard)

        endpoint.__name__ = "reporting_" + method
        router.add_api_route("/" + path.replace("{id}", "{identifier}"), endpoint, methods=["POST"])

    for path, model, method, guard in [
        ("obligations/{id}/draft", c.ReturnDraft, "draft", "obligation"),
        ("obligations/{id}/imports", c.Import, "import_csv", "obligation"),
        ("returns/{id}/submit", c.Attest, "submit", "reporter"),
        ("returns/{id}/review", c.Review, "review", "reviewer"),
        ("returns/{id}/correction", c.Versioned, "correction", "reporter"),
        ("snapshots/{id}/review", c.SnapshotReview, "snapshot_review", "snapshot"),
        ("policies/{id}/revoke", c.Evidence, "revoke_policy", "governor"),
        ("duty-windows/{id}/accept", c.Evidence, "accept_duty", "duty"),
        ("safety-cases/{id}/actions", c.CaseAction, "case_action", "case"),
        ("actions/{id}/progress", c.ActionUpdate, "action_update", "action"),
        ("exceptions/{id}/acknowledge", c.Evidence, "acknowledge_exception", "exception"),
    ]:
        resource_route(path, model, method, guard)

    @router.post("/obligations/{identifier}/extract")
    async def extract(identifier: UUID, payload: c.StrictModel, request: Request):
        async def guard(service, body):
            await service.obligation(str(identifier), s.REPORTERS)

        async def apply(service, body):
            return await service.extract(str(identifier))

        return await command(request, payload, apply, guard)

    @router.post("/reconcile")
    async def reconcile(payload: c.StrictModel, request: Request):
        async def apply(service, body):
            return {"id": db.uid(), **await service.reconcile()}

        return await command(request, payload, apply, governor)

    app.include_router(router)
