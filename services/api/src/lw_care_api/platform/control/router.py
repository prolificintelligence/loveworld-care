"""Current-purpose control APIs and non-enumerating public recovery boundaries."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Request, Response
from sqlalchemy import and_, false, or_, select

from .. import db
from ..clinical import tables as clinical
from ..domain import RuleError, require
from ..security import digest
from . import contracts as c
from . import tables as t
from .jobs import OperationsService, run_tick
from .offboarding import OffboardingService
from .recovery import RecoveryService
from .service import ControlService, has, load, serial

GOVERNANCE = {"PLATFORM_ADMIN", "CLINICAL_GOVERNOR", "PRIVACY_OFFICER", "FINANCE_GOVERNOR"}


def facility_predicate(actor, roles, table, *, include_global=False):
    if has(actor, roles):
        return True
    identifiers = [
        g["scope_id"]
        for g in actor["grants"]
        if g["role"] in roles and g["scope_type"] == "FACILITY"
    ]
    clause = table.c.facility_id.in_(identifiers) if identifiers else false()
    return or_(clause, table.c.facility_id.is_(None)) if include_global and identifiers else clause


def install(app, cfg, database, box, actor_for, throttle, set_cookie):
    router = APIRouter()

    async def available():
        require(cfg.controls_enabled, "CONTROLS_PAUSED", "Operating controls are paused", 503)
        require(
            (await database.version() or 0) >= 4,
            "CONTROLS_MIGRATION_REQUIRED",
            "Operating controls await database migration",
            503,
        )

    async def command(request, payload, kind, callback, guard):
        actor = None
        try:
            await available()
            async with database.transaction() as session:
                await serial(session, database)
                actor = await actor_for(session, request)
                service = kind(session, cfg, box, actor, request.state.correlation_id)
                body = payload.model_dump(mode="json")
                await guard(service, body)

                async def apply():
                    return {
                        "resource": await callback(service, body),
                        "execution_state": "CENTRAL_COMMITTED",
                        "authority_node_id": cfg.authority_node_id,
                    }

                result = await service.idempotent(
                    request.url.path, request.headers.get("Idempotency-Key"), body, apply
                )
                if request.url.path.endswith("/recovery-codes"):
                    security = await service.security(actor["id"])
                    require(
                        security["recovery_set_id"] == result["resource"]["id"],
                        "RECOVERY_SET_REPLACED",
                        "The recovery code set was replaced; use the current set",
                        409,
                    )
                return result
        except RuleError:
            request.state.control_denial_recorded = True
            if (await database.version() or 0) >= 4:
                async with database.transaction() as session:
                    await ControlService(
                        session, cfg, box, actor, request.state.correlation_id
                    ).audit("control.command_denied", outcome="DENIED")
            raise

    async def public(request, payload, method):
        await available()
        body = payload.model_dump(mode="json")
        key = body.get("email", body.get("token", ""))
        async with database.transaction() as session:
            permitted = await throttle(
                session,
                "recovery:"
                + method
                + ":"
                + digest(key.lower() if method == "request_recovery" else key),
            )
        require(
            permitted,
            "RATE_LIMITED",
            "Too many recovery attempts. Try again after the rate limit window",
            429,
        )
        try:
            async with database.transaction() as session:
                await serial(session, database)
                service = RecoveryService(session, cfg, box, None, request.state.correlation_id)
                result = await getattr(service, method)(body)
                request.state.recovery_delivery_job_id = getattr(service, "delivery_job_id", None)
                return result
        except RuleError:
            async with database.transaction() as session:
                await ControlService(session, cfg, box, None, request.state.correlation_id).audit(
                    "identity.recovery_denied", outcome="DENIED"
                )
            raise

    @router.post("/v1/auth/recovery/request", status_code=202)
    async def request_recovery(
        payload: c.RecoveryRequest, request: Request, background_tasks: BackgroundTasks
    ):
        result = await public(request, payload, "request_recovery")
        if cfg.dispatch_recovery_after_commit:
            from .jobs import deliver_after_commit

            background_tasks.add_task(
                deliver_after_commit,
                database,
                cfg,
                box,
                getattr(request.state, "recovery_delivery_job_id", None),
            )
        return result

    @router.post("/v1/auth/recovery/prove")
    async def prove_recovery(payload: c.RecoveryProof, request: Request):
        return await public(request, payload, "prove")

    @router.post("/v1/auth/recovery/setup")
    async def setup_recovery(payload: c.RecoverySetup, request: Request):
        return await public(request, payload, "setup")

    @router.post("/v1/auth/recovery/complete")
    async def complete_recovery(payload: c.RecoveryFinish, request: Request, response: Response):
        token = await public(request, payload, "finish")
        set_cookie(response, token)
        return {
            "status": "AUTHENTICATED",
            "prior_sessions_revoked": True,
            "grants_changed": False,
            "instruction": "Generate a new set of one-use recovery codes after signing in.",
        }

    @router.post("/v1/auth/recovery-codes")
    async def backup_codes(payload: c.Factor, request: Request):
        async def guard(service, body):
            require(service.actor)

        return await command(
            request, payload, RecoveryService, lambda service, body: service.codes(body), guard
        )

    @router.get("/v1/operations/context")
    async def context(request: Request):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            return {
                "roles": sorted({g["role"] for g in actor["grants"]}),
                "authority_node_id": cfg.authority_node_id,
                "delivery": {
                    "email_configured": bool(cfg.resend_api_key and cfg.email_from),
                    "scanner_configured": bool(cfg.clamav_host),
                    "scheduler": "DAILY_AUTOMATIC_PLUS_AUTHENTICATED_MANUAL",
                    "continuous_worker_deployment": "DEFERRED_OUTSIDE_CURRENT_STACK",
                },
                "offline_care": {
                    "scope": "CORE",
                    "facility_runtime_deployment": "DEFERRED_OUTSIDE_CURRENT_STACK",
                    "current_cloud_requires_wan": True,
                },
                "as_of": db.now(),
            }

    @router.get("/v1/operations/facilities")
    async def facilities(request: Request, after: str = ""):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            ids = [
                g["scope_id"]
                for g in actor["grants"]
                if g["scope_type"] == "FACILITY" and g["role"] in GOVERNANCE | {"CLINICAL_STAFF"}
            ]
            allowed = True if has(actor, GOVERNANCE) else db.facilities.c.id.in_(ids)
            rows = list(
                (
                    await session.execute(
                        select(
                            db.facilities.c.id,
                            db.facilities.c.name,
                            db.facilities.c.jurisdiction,
                            db.facilities.c.services,
                        )
                        .where(allowed, db.facilities.c.id > after)
                        .order_by(db.facilities.c.id)
                        .limit(101)
                    )
                ).mappings()
            )
            return {
                "items": [dict(row) for row in rows[:100]],
                "next_cursor": rows[99]["id"] if len(rows) > 100 else None,
            }

    @router.get("/v1/operations/people")
    async def people(request: Request, query: str = "", after: str = ""):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            allowed_roles = GOVERNANCE | {"IDENTITY_REVIEWER", "CLINICAL_STAFF"}
            scopes = [
                g["scope_id"]
                for g in actor["grants"]
                if g["scope_type"] == "FACILITY" and g["role"] in allowed_roles
            ]
            allowed = (
                True
                if has(actor, GOVERNANCE | {"IDENTITY_REVIEWER"})
                else and_(db.grants.c.scope_type == "FACILITY", db.grants.c.scope_id.in_(scopes))
            )
            rows = list(
                (
                    await session.execute(
                        select(db.accounts.c.id, db.accounts.c.name)
                        .join(db.grants, db.grants.c.account_id == db.accounts.c.id)
                        .where(
                            allowed,
                            db.accounts.c.active.is_(True),
                            db.grants.c.role.in_(allowed_roles),
                            db.grants.c.revoked.is_(False),
                            db.grants.c.valid_from <= db.now(),
                            db.grants.c.valid_until > db.now(),
                            db.accounts.c.id > after,
                            db.accounts.c.name.ilike("%" + query[:160] + "%"),
                        )
                        .distinct()
                        .order_by(db.accounts.c.id)
                        .limit(101)
                    )
                ).mappings()
            )
            return {
                "items": [dict(row) for row in rows[:100]],
                "next_cursor": rows[99]["id"] if len(rows) > 100 else None,
            }

    @router.get("/v1/operations/recoveries")
    async def recovery_reviews(request: Request, after: str = ""):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            require(has(actor, {"IDENTITY_REVIEWER"}))
            await ControlService(session, cfg, box, actor, request.state.correlation_id).audit(
                "identity.recovery_queue_read"
            )
            rows = list(
                (
                    await session.execute(
                        select(
                            t.recoveries.c.id,
                            t.recoveries.c.state,
                            t.recoveries.c.created_at,
                            t.recoveries.c.expires_at,
                            db.accounts.c.name,
                            db.accounts.c.email,
                        )
                        .join(db.accounts, db.accounts.c.id == t.recoveries.c.account_id)
                        .where(
                            t.recoveries.c.state == "REVIEW_REQUIRED",
                            t.recoveries.c.expires_at > db.now(),
                            t.recoveries.c.account_id != actor["id"],
                            t.recoveries.c.id > after,
                        )
                        .order_by(t.recoveries.c.id)
                        .limit(101)
                    )
                ).mappings()
            )
            return {
                "items": [dict(row) for row in rows[:100]],
                "next_cursor": rows[99]["id"] if len(rows) > 100 else None,
            }

    @router.post("/v1/operations/recoveries/{identifier}/review")
    async def review_recovery(identifier: UUID, payload: c.RecoveryReview, request: Request):
        async def guard(service, body):
            require(has(service.actor, {"IDENTITY_REVIEWER"}))

        return await command(
            request,
            payload,
            RecoveryService,
            lambda service, body: service.review(str(identifier), body),
            guard,
        )

    @router.get("/v1/operations/policy-packages")
    async def packages(request: Request, after: str = ""):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            service = ControlService(session, cfg, box, actor, request.state.correlation_id)
            rows = list(
                (
                    await session.execute(
                        select(t.packages)
                        .where(
                            facility_predicate(actor, GOVERNANCE, t.packages, include_global=True),
                            t.packages.c.id > after,
                        )
                        .order_by(t.packages.c.id)
                        .limit(101)
                    )
                ).mappings()
            )
            return {
                "items": [dict(row) | await service.package_state(row) for row in rows[:100]],
                "next_cursor": rows[99]["id"] if len(rows) > 100 else None,
            }

    @router.post("/v1/operations/policy-packages")
    async def package_propose(payload: c.PolicyPackage, request: Request):
        async def guard(service, body):
            require(has(service.actor, GOVERNANCE, body.get("facility_id")))

        return await command(
            request,
            payload,
            ControlService,
            lambda service, body: service.policy_package(body),
            guard,
        )

    @router.post("/v1/operations/policy-packages/{identifier}/review")
    async def package_review(identifier: UUID, payload: c.PackageReview, request: Request):
        async def guard(service, body):
            row = await load(service.session, t.packages, identifier)
            role = {
                "TECHNICAL": "PLATFORM_ADMIN",
                "CLINICAL": "CLINICAL_GOVERNOR",
                "PRIVACY": "PRIVACY_OFFICER",
                "FINANCE": "FINANCE_GOVERNOR",
            }[body["review_kind"]]
            require(has(service.actor, {role}, row["facility_id"]))

        return await command(
            request,
            payload,
            ControlService,
            lambda service, body: service.package_review(str(identifier), body),
            guard,
        )

    @router.post("/v1/operations/policy-packages/{identifier}/withdraw")
    async def package_withdraw(identifier: UUID, payload: c.Evidence, request: Request):
        async def guard(service, body):
            row = await load(service.session, t.packages, identifier)
            require(has(service.actor, GOVERNANCE, row["facility_id"]))

        return await command(
            request,
            payload,
            ControlService,
            lambda service, body: service.revoke_package(str(identifier), body),
            guard,
        )

    @router.get("/v1/operations/coverage")
    async def coverage(request: Request, after: str = ""):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            rows = list(
                (
                    await session.execute(
                        select(t.coverage)
                        .where(
                            or_(
                                t.coverage.c.account_id == actor["id"],
                                facility_predicate(actor, {"CLINICAL_GOVERNOR"}, t.coverage),
                            ),
                            t.coverage.c.id > after,
                        )
                        .order_by(t.coverage.c.id)
                        .limit(101)
                    )
                ).mappings()
            )
            return {
                "items": [
                    {k: v for k, v in row.items() if not k.endswith("ciphertext")}
                    for row in rows[:100]
                ],
                "next_cursor": rows[99]["id"] if len(rows) > 100 else None,
            }

    @router.post("/v1/operations/coverage")
    async def coverage_offer(payload: c.Coverage, request: Request):
        async def guard(service, body):
            require(has(service.actor, {"CLINICAL_GOVERNOR"}, body["facility_id"]))

        return await command(
            request,
            payload,
            OperationsService,
            lambda service, body: service.offer_coverage(body),
            guard,
        )

    @router.post("/v1/operations/coverage/{identifier}/accept")
    async def coverage_accept(identifier: UUID, payload: c.Evidence, request: Request):
        async def guard(service, body):
            row = await load(service.session, t.coverage, identifier)
            require(row["account_id"] == service.actor["id"])

        return await command(
            request,
            payload,
            OperationsService,
            lambda service, body: service.accept_coverage(str(identifier), body),
            guard,
        )

    @router.get("/v1/operations/alerts")
    async def alerts(request: Request, after: str = ""):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            await ControlService(session, cfg, box, actor, request.state.correlation_id).audit(
                "operations.own_alerts_read"
            )
            rows = list(
                (
                    await session.execute(
                        select(t.alerts)
                        .where(
                            or_(
                                t.alerts.c.owner_id == actor["id"],
                                t.alerts.c.fallback_id == actor["id"],
                                facility_predicate(actor, {"CLINICAL_GOVERNOR"}, t.alerts),
                            ),
                            t.alerts.c.id > after,
                        )
                        .order_by(t.alerts.c.id)
                        .limit(101)
                    )
                ).mappings()
            )
            return {
                "items": [dict(row) for row in rows[:100]],
                "next_cursor": rows[99]["id"] if len(rows) > 100 else None,
                "interpretation": "Alert acknowledgement is separate from clinical task, result review and patient contact completion.",
            }

    @router.post("/v1/operations/alerts/{identifier}/acknowledge")
    async def alert_ack(identifier: UUID, payload: c.Evidence, request: Request):
        async def guard(service, body):
            row = await load(service.session, t.alerts, identifier)
            require(service.actor["id"] in {row["owner_id"], row["fallback_id"]})

        return await command(
            request,
            payload,
            OperationsService,
            lambda service, body: service.acknowledge(str(identifier), body),
            guard,
        )

    @router.get("/v1/operations/jobs")
    async def jobs(request: Request, after: str = ""):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            require(has(actor, {"PLATFORM_ADMIN"}))
            rows = list(
                (
                    await session.execute(
                        select(t.jobs).where(t.jobs.c.id > after).order_by(t.jobs.c.id).limit(101)
                    )
                ).mappings()
            )
            return {
                "items": [
                    {
                        k: v
                        for k, v in row.items()
                        if k not in {"payload_ciphertext", "lease_token_hash"}
                    }
                    for row in rows[:100]
                ],
                "next_cursor": rows[99]["id"] if len(rows) > 100 else None,
            }

    async def assurance_available():
        await available()
        require(
            (await database.version() or 0) >= 5,
            "ASSURANCE_MIGRATION_REQUIRED",
            "Recovery evidence awaits migration 5",
            503,
        )

    @router.get("/v1/operations/reliability")
    async def reliability(request: Request):
        await assurance_available()
        from .assurance import status

        async with database.transaction() as session:
            actor = await actor_for(session, request)
            require(has(actor, {"PLATFORM_ADMIN"}))
            await ControlService(session, cfg, box, actor, request.state.correlation_id).audit(
                "operations.reliability_read"
            )
            return await status(session, cfg)

    @router.get("/v1/operations/assurance-runs")
    async def assurance_runs(request: Request, after: str = ""):
        await assurance_available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            require(has(actor, {"PLATFORM_ADMIN"}))
            await ControlService(session, cfg, box, actor, request.state.correlation_id).audit(
                "operations.assurance_history_read"
            )
            rows = list(
                (
                    await session.execute(
                        select(t.assurance_runs)
                        .where(t.assurance_runs.c.id > after)
                        .order_by(t.assurance_runs.c.id)
                        .limit(101)
                    )
                ).mappings()
            )
            return {
                "items": [
                    {key: value for key, value in row.items() if key != "evidence_ciphertext"}
                    for row in rows[:100]
                ],
                "next_cursor": rows[99]["id"] if len(rows) > 100 else None,
            }

    @router.post("/v1/operations/reconciliation")
    async def reconciliation(payload: c.Evidence, request: Request):
        from .assurance import AssuranceService

        async def guard(service, body):
            require(has(service.actor, {"PLATFORM_ADMIN"}))
            require(
                (await database.version() or 0) >= 5,
                "ASSURANCE_MIGRATION_REQUIRED",
                "Recovery evidence awaits migration 5",
                503,
            )

        return await command(
            request, payload, AssuranceService, lambda service, body: service.reconcile(body), guard
        )

    @router.post("/v1/operations/jobs/process")
    async def process(payload: c.Evidence, request: Request):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            require(has(actor, {"PLATFORM_ADMIN"}))
            await ControlService(session, cfg, box, actor, request.state.correlation_id).audit(
                "operations.manual_batch_requested"
            )
        return await run_tick(database, cfg, box)

    @router.post("/v1/operations/jobs/{identifier}/retry")
    async def retry(identifier: UUID, payload: c.JobRetry, request: Request):
        async def guard(service, body):
            require(has(service.actor, {"PLATFORM_ADMIN"}))

        async def apply(service, body):
            from sqlalchemy import update

            row = await load(service.session, t.jobs, identifier, lock=True)
            require(
                row["state"] in {"DEAD", "RECONCILIATION_REQUIRED"},
                "INVALID_STATE",
                "Only dead or reconciliation-required work can be manually requeued",
                409,
            )
            require(
                body["provider_reconciled"],
                "PROVIDER_RECONCILIATION_REQUIRED",
                "Reconcile any prior provider acceptance before another dispatch",
                409,
            )
            await service.session.execute(
                update(t.jobs)
                .where(t.jobs.c.id == str(identifier))
                .values(
                    state="READY",
                    next_attempt_at=db.now(),
                    first_attempt_at=None,
                    dispatch_generation=row["dispatch_generation"] + 1,
                    last_outcome="MANUALLY_RECONCILED_RETRY",
                    updated_at=db.now(),
                )
            )
            await service.audit(
                "operations.job_requeued",
                str(identifier),
                details={"evidence_ciphertext": service.box.encrypt(body["evidence"])},
            )
            return {"id": str(identifier), "state": "READY", "provider_delivery_claimed": False}

        return await command(request, payload, ControlService, apply, guard)

    @router.post("/v1/operations/offboarding")
    async def offboard(payload: c.Offboard, request: Request):
        async def guard(service, body):
            require(has(service.actor, {"PLATFORM_ADMIN"}))

        return await command(
            request,
            payload,
            OffboardingService,
            lambda service, body: service.offboard(body),
            guard,
        )

    @router.get("/v1/operations/handovers")
    async def handovers(request: Request, after: str = ""):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            await ControlService(session, cfg, box, actor, request.state.correlation_id).audit(
                "identity.handover_queue_read"
            )
            allowed = (
                True
                if has(actor, {"PLATFORM_ADMIN"})
                else or_(
                    t.offboardings.c.coordinator_id == actor["id"],
                    t.handover_items.c.successor_id == actor["id"],
                )
            )
            rows = list(
                (
                    await session.execute(
                        select(
                            t.handover_items,
                            t.offboardings.c.coordinator_id,
                            t.offboardings.c.account_id.label("departing_account_id"),
                        )
                        .join(
                            t.offboardings, t.offboardings.c.id == t.handover_items.c.offboarding_id
                        )
                        .where(allowed, t.handover_items.c.id > after)
                        .order_by(t.handover_items.c.id)
                        .limit(101)
                    )
                ).mappings()
            )
            return {
                "items": [dict(row) for row in rows[:100]],
                "next_cursor": rows[99]["id"] if len(rows) > 100 else None,
            }

    @router.post("/v1/operations/handovers/{identifier}/offer")
    async def offer_handover(identifier: UUID, payload: c.HandoverOffer, request: Request):
        async def guard(service, body):
            row, case = await service.item(str(identifier))
            require(
                service.actor["id"] == case["coordinator_id"]
                and has(service.actor, {"CLINICAL_GOVERNOR"}, row["facility_id"])
            )

        return await command(
            request,
            payload,
            OffboardingService,
            lambda service, body: service.offer(str(identifier), body),
            guard,
        )

    @router.post("/v1/operations/handovers/{identifier}/accept")
    async def accept_handover(identifier: UUID, payload: c.HandoverAccept, request: Request):
        async def guard(service, body):
            row, _case = await service.item(str(identifier))
            require(service.actor["id"] == row["successor_id"])
            from ..clinical import store as clinical_store
            from .offboarding import FIELDS

            source = await load(service.session, clinical.records, row["source_id"])
            await clinical_store.privilege_for(
                service.session,
                service.actor["id"],
                row["facility_id"],
                FIELDS[row["owner_field"]],
                source["service"],
            )

        return await command(
            request,
            payload,
            OffboardingService,
            lambda service, body: service.accept(str(identifier), body),
            guard,
        )

    @router.get("/v1/operations/handovers/{identifier}/context")
    async def handover_context(identifier: UUID, request: Request):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            return await OffboardingService(
                session, cfg, box, actor, request.state.correlation_id
            ).preview(str(identifier))

    @router.get("/v1/operations/audit")
    async def audit(request: Request, after: str = ""):
        await available()
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            require(has(actor, {"PLATFORM_ADMIN"}))
            rows = list(
                (
                    await session.execute(
                        select(t.audit)
                        .where(t.audit.c.id > after)
                        .order_by(t.audit.c.id)
                        .limit(101)
                    )
                ).mappings()
            )
            return {
                "items": [dict(row) for row in rows[:100]],
                "next_cursor": rows[99]["id"] if len(rows) > 100 else None,
            }

    app.include_router(router)
