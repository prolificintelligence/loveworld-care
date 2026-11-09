"""Production institutional API. All state and authorisation come from PostgreSQL."""

import hashlib
import hmac
import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import perf_counter
from uuid import UUID

import pyotp
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from . import contracts as c
from . import db
from .config import PlatformSettings, get_platform_settings
from .domain import (
    RuleError,
    amend,
    application_for,
    current_criteria,
    expected,
    facility_for,
    global_role,
    idempotent,
    public_profile,
    publication_eligible,
    record_audit,
    record_change,
    require,
    scoped,
    valid_interval,
    visibility,
)
from .security import (
    SecretBox,
    accept_totp,
    digest,
    hash_password,
    issue_session,
    resolve_session,
    verify_password,
)

COOKIE = "lwh_session"


def create_platform_app(settings: PlatformSettings | None = None) -> FastAPI:
    cfg = settings or get_platform_settings()
    cfg.validate_runtime()
    database = db.Database(cfg.database_url)
    box = SecretBox(cfg.data_key_hex)

    @asynccontextmanager
    async def lifespan(app):
        yield
        await database.engine.dispose()

    app = FastAPI(
        title="LW Health Intelligence Platform",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None if cfg.production else "/v1/docs",
    )
    app.state.database, app.state.settings, app.state.box = database, cfg, box
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[cfg.web_origin.rstrip("/")],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization", "Idempotency-Key", "If-Match"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        request.state.correlation_id = db.uid()
        if (
            request.url.path.startswith(
                (
                    "/v1/clinical/",
                    "/v1/reporting/",
                    "/v1/operations/",
                    "/v1/auth/recovery",
                    "/v1/institutional/",
                    "/v1/personal/",
                )
            )
            and request.method == "POST"
            and not request.url.path.endswith("/files")
        ):
            body = await request.body()
            if len(body) > 1_048_576:
                return JSONResponse(
                    {
                        "error": {
                            "code": "PAYLOAD_TOO_LARGE",
                            "message": "Care, reporting and operating commands are limited to 1 MiB",
                        }
                    },
                    status_code=413,
                )
        if (
            request.method == "POST"
            and not request.headers.get("authorization")
            and request.headers.get("origin") != cfg.web_origin.rstrip("/")
        ):
            return JSONResponse(
                {
                    "error": {
                        "code": "ACCESS_DENIED",
                        "message": "A same-origin request is required",
                    }
                },
                status_code=403,
            )
        if request.url.path.startswith("/v1/") and not request.url.path.startswith(
            ("/v1/auth/", "/v1/health", "/v1/ready", "/v1/internal/")
        ):
            from .institutional.master import refresh

            try:
                await refresh(database, cfg, box)
            except (RuleError, SQLAlchemyError):
                return JSONResponse(
                    {
                        "error": {
                            "code": "CURRENT_SCOPE_UNAVAILABLE",
                            "message": "Current dated authority is reconciling; retry before using this workspace",
                        }
                    },
                    status_code=503,
                    headers={"Cache-Control": "no-store"},
                )
        response = await call_next(request)
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "no-referrer",
                "X-Request-ID": request.state.correlation_id,
            }
        )
        return response

    @app.middleware("http")
    async def authentication_observation(request: Request, call_next):
        # Fixed route labels only: never log query strings, identity, request bodies,
        # headers, exception messages or credentials. Vercel retains stdout events.
        observed = request.url.path in {
            "/v1/auth/login",
            "/v1/auth/me",
            "/v1/auth/enrol",
            "/v1/auth/activate",
            "/v1/auth/logout",
        }
        if not observed:
            return await call_next(request)
        started, status = perf_counter(), 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            print(
                json.dumps(
                    {
                        "event": "authentication_request",
                        "route": request.url.path,
                        "status": status,
                        "elapsed_ms": round((perf_counter() - started) * 1000, 2),
                        "correlation_id": getattr(request.state, "correlation_id", None),
                    }
                ),
                flush=True,
            )

    @app.exception_handler(RuleError)
    async def rule_error(request, exc):
        if request.url.path.startswith("/v1/personal/") and (await database.version() or 0) >= 8:
            from .personal.service import PersonalService
            async with database.transaction() as session:
                identity = getattr(request.state, "actor_id", None)
                await PersonalService(session, cfg, box, {"id":identity} if identity else None,
                                      request.state.correlation_id).audit("personal.request_denied", outcome="DENIED")
        if (
            request.url.path.startswith(("/v1/operations/", "/v1/institutional/"))
            and (await database.version() or 0) >= 4
            and not getattr(request.state, "control_denial_recorded", False)
        ):
            from .control.service import ControlService

            async with database.transaction() as session:
                identity = getattr(request.state, "actor_id", None)
                await ControlService(
                    session,
                    cfg,
                    box,
                    {"id": identity} if identity else None,
                    request.state.correlation_id,
                ).audit(
                    "institutional.request_denied"
                    if request.url.path.startswith("/v1/institutional/")
                    else "control.request_denied",
                    outcome="DENIED",
                )
        if (
            request.url.path.startswith("/v1/reporting/")
            and getattr(request.state, "reporting_ready", False)
            and not getattr(request.state, "reporting_denial_recorded", False)
        ):
            from .reporting import store as reporting_store

            actor_id = getattr(request.state, "actor_id", None)
            async with database.transaction() as session:
                await reporting_store.audit(
                    session,
                    {"id": actor_id} if actor_id else None,
                    "reporting.request_denied",
                    None,
                    None,
                    request.state.correlation_id,
                    outcome="DENIED",
                )
        if request.url.path.startswith("/v1/clinical/") and not getattr(
            request.state, "clinical_denial_recorded", False
        ):
            from .clinical import store as clinical_store

            actor_id = getattr(request.state, "actor_id", None)
            parts = request.url.path.split("/")
            facility_id = parts[3] if len(parts) > 3 and len(parts[3]) == 36 else None
            async with database.transaction() as session:
                await clinical_store.audit(
                    session,
                    {"id": actor_id} if actor_id else None,
                    facility_id,
                    None,
                    "clinical.request_denied",
                    request.state.correlation_id,
                    "DENIED",
                )
        return JSONResponse(
            {
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "correlation_id": request.state.correlation_id,
                }
            },
            status_code=exc.status,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Pydantic's default includes submitted passwords/tokens as `input`.
        return JSONResponse(
            {
                "error": {
                    "code": "VALIDATION_FAILED",
                    "message": "Check the supplied fields",
                    "field_errors": [
                        {"field": ".".join(map(str, e["loc"])), "message": e["msg"]}
                        for e in exc.errors()
                    ],
                    "correlation_id": request.state.correlation_id,
                }
            },
            status_code=422,
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error(request, exc):
        return JSONResponse(
            {
                "error": {
                    "code": "VERSION_CONFLICT",
                    "message": "A record or reference already exists; reload and review before retrying",
                    "correlation_id": request.state.correlation_id,
                }
            },
            status_code=409,
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):
        return JSONResponse(
            {
                "error": {
                    "code": "AUTHORITY_UNAVAILABLE",
                    "message": "The authoritative database is unavailable. Your action is not confirmed.",
                    "correlation_id": request.state.correlation_id,
                }
            },
            status_code=503,
        )

    @app.exception_handler(BotoCoreError)
    @app.exception_handler(ClientError)
    async def storage_error(request, exc):
        return JSONResponse(
            {
                "error": {
                    "code": "AUTHORITY_UNAVAILABLE",
                    "message": "Private evidence storage is unavailable; the operation is not confirmed",
                    "correlation_id": request.state.correlation_id,
                }
            },
            status_code=503,
        )

    def token(request):
        authorization = request.headers.get("authorization", "")
        if authorization.startswith("Bearer "):
            return authorization[7:]
        return request.cookies.get(COOKIE)

    async def actor_for(session, request):
        actor = await resolve_session(session, token(request))
        require(
            actor is not None, "AUTH_REQUIRED", "Sign in with your account and authenticator", 401
        )
        actor["authority_node_id"] = cfg.authority_node_id
        request.state.actor_id = actor["id"]
        return actor

    async def command(request, payload, action, callback):
        actor = None
        try:
            async with database.transaction() as session:
                actor = await actor_for(session, request)

                async def replay_guard(response):
                    # Replayed receipts are protected records too. Revoked/expired grants
                    # must not retrieve a cached private response through an old operation key.
                    if action in ("account.invite", "grant.revoke", "organisation.created"):
                        require(global_role(actor, "PLATFORM_ADMIN"))
                        return
                    if action == "operator.created":
                        require(global_role(actor, "REGISTRY_STEWARD"))
                        return
                    if action == "criteria.adopted":
                        require(global_role(actor, "STANDARDS_DECIDER"))
                        return
                    result = response["resource"]
                    if "application_id" in result:
                        _, facility = await application_for(
                            session, actor, result["application_id"]
                        )
                    elif "facility_id" in result:
                        facility = await facility_for(session, actor, result["facility_id"])
                    else:
                        facility = await facility_for(session, actor, result["id"])
                    roles_by_action = {
                        "facility.created": {"REGISTRY_STEWARD"},
                        "facility.verified": {"REGISTRY_STEWARD"},
                        "directory.changed": {"REGISTRY_STEWARD"},
                        "application.created": {"REGISTRY_STEWARD", "FACILITY_ADMIN"},
                        "application.submitted": {"REGISTRY_STEWARD", "FACILITY_ADMIN"},
                        "evidence.stored": {"REGISTRY_STEWARD", "FACILITY_ADMIN"},
                        "inspection.assigned": {"REGISTRY_STEWARD", "STANDARDS_REVIEWER"},
                        "inspection.recorded": {"INSPECTOR"},
                        "application.recommended": {"STANDARDS_REVIEWER"},
                        "affiliation.decided": {"STANDARDS_DECIDER"},
                    }
                    require(scoped(actor, roles_by_action.get(action, set()), facility))

                return await idempotent(
                    session,
                    actor,
                    request.url.path,
                    request.headers.get("Idempotency-Key"),
                    payload,
                    lambda: callback(session, actor),
                    database.postgres,
                    replay_guard,
                )
        except RuleError:
            async with database.transaction() as session:
                await record_audit(
                    session,
                    actor["id"] if actor else None,
                    action,
                    request.url.path,
                    "DENIED",
                    request.state.correlation_id,
                )
            raise

    def receipt(row):
        return {
            "resource": row,
            "execution_state": "CENTRAL_COMMITTED",
            "authority_node_id": cfg.authority_node_id,
        }

    def set_cookie(response, value):
        response.set_cookie(
            COOKIE,
            value,
            max_age=cfg.session_minutes * 60,
            secure=cfg.production,
            httponly=True,
            samesite="strict",
            path="/",
        )

    async def throttle(session, key):
        key = digest(key)
        if database.postgres:
            lock_key = int.from_bytes(
                hashlib.sha256(("rate-limit:" + key).encode()).digest()[:8], signed=True
            )
            await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
        moment = datetime.now(UTC)
        row = (
            (
                await session.execute(
                    select(db.rate_limits).where(db.rate_limits.c.key == key).with_for_update()
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            await session.execute(
                db.rate_limits.insert().values(key=key, attempts=1, window_start=moment.isoformat())
            )
            return True
        recent = datetime.fromisoformat(row["window_start"]) > moment - timedelta(minutes=15)
        await session.execute(
            update(db.rate_limits)
            .where(db.rate_limits.c.key == key)
            .values(
                attempts=row["attempts"] + 1 if recent else 1,
                window_start=row["window_start"] if recent else moment.isoformat(),
            )
        )
        return not recent or row["attempts"] < 8

    @app.get("/v1/health")
    async def health():
        return {"service": "LW Health Intelligence Platform", "status": "RUNNING"}

    @app.get("/v1/ready")
    async def ready():
        version = await database.version()
        require(
            version in (2, 3, 4, 5, 6, 7, 8),
            "AUTHORITY_UNAVAILABLE",
            "Database migration required",
            503,
        )
        if version >= 7:
            require(
                await database.ready(),
                "CLINICAL_WORK_INDEX_RECONCILIATION_REQUIRED",
                "Clinical work index reconciliation required",
                503,
            )
        return {
            "status": "READY",
            "schema_version": version,
            "personal_care": "READY" if version >= 8 and cfg.personal_enabled else "PAUSED_OR_AWAITING_MIGRATION",
            "advanced_clinical": "READY"
            if version >= 7 and cfg.advanced_clinical_enabled
            else "PAUSED_OR_AWAITING_MIGRATION",
            "reporting": "READY"
            if version >= 3 and cfg.reporting_enabled
            else "PAUSED_OR_AWAITING_MIGRATION",
            "controls": "READY"
            if version >= 4 and cfg.controls_enabled
            else "PAUSED_OR_AWAITING_MIGRATION",
        }

    @app.post("/v1/auth/login")
    async def login(payload: c.Login, request: Request, response: Response):
        # Rate-limit attempts commit even when authentication is unsuccessful.
        async with database.transaction() as session:
            permitted = await throttle(session, "login:" + payload.email.lower())
        require(
            permitted, "RATE_LIMITED", "Too many sign-in attempts. Try again in 15 minutes.", 429
        )
        success = False
        async with database.transaction() as session:
            account = (
                (
                    await session.execute(
                        select(db.accounts)
                        .where(db.accounts.c.email == payload.email.lower())
                        .with_for_update()
                    )
                )
                .mappings()
                .first()
            )
            correct = await run_in_threadpool(
                verify_password, payload.password, account["password_hash"] if account else None
            )
            if account and account["active"] and correct:
                success = await accept_totp(session, dict(account), payload.otp, box)
            await record_audit(
                session,
                account["id"] if account else None,
                "account.login",
                None,
                "SUCCESS" if success else "DENIED",
                request.state.correlation_id,
            )
            if success:
                session_token = await issue_session(session, account["id"], cfg.session_minutes)
        require(success, "AUTH_REQUIRED", "The sign-in details could not be verified", 401)
        set_cookie(response, session_token)
        return {"status": "AUTHENTICATED"}

    @app.post("/v1/auth/enrol")
    async def enrol(payload: c.Enrol, request: Request):
        async with database.transaction() as session:
            permitted = await throttle(session, "enrol:" + digest(payload.token))
        require(permitted, "RATE_LIMITED", "Too many attempts. Try again in 15 minutes.", 429)
        async with database.transaction() as session:
            invitation = (
                (
                    await session.execute(
                        select(db.invitations)
                        .where(
                            db.invitations.c.token_hash == digest(payload.token),
                            db.invitations.c.used.is_(False),
                            db.invitations.c.expires_at > db.now(),
                        )
                        .with_for_update()
                    )
                )
                .mappings()
                .first()
            )
            require(invitation, "AUTH_REQUIRED", "Invitation is invalid or expired", 401)
            account = (
                (
                    await session.execute(
                        select(db.accounts)
                        .where(db.accounts.c.id == invitation["account_id"])
                        .with_for_update()
                    )
                )
                .mappings()
                .one()
            )
            require(
                not account["active"], "INVALID_TRANSITION", "Account is already activated", 409
            )
            secret = pyotp.random_base32()
            password_hash = await run_in_threadpool(hash_password, payload.password)
            await session.execute(
                update(db.accounts)
                .where(db.accounts.c.id == account["id"])
                .values(
                    password_hash=password_hash,
                    totp_ciphertext=box.encrypt(secret),
                    totp_last_step=-1,
                )
            )
            return {
                "authenticator_uri": pyotp.TOTP(secret).provisioning_uri(
                    name=account["email"], issuer_name="LW Health Intelligence Platform"
                ),
                "setup_key": secret,
            }

    @app.post("/v1/auth/activate")
    async def activate(payload: c.ConfirmEnrolment, request: Request, response: Response):
        success = False
        async with database.transaction() as session:
            permitted = await throttle(session, "activate:" + digest(payload.token))
        require(permitted, "RATE_LIMITED", "Too many attempts. Try again in 15 minutes.", 429)
        async with database.transaction() as session:
            invitation = (
                (
                    await session.execute(
                        select(db.invitations)
                        .where(
                            db.invitations.c.token_hash == digest(payload.token),
                            db.invitations.c.used.is_(False),
                            db.invitations.c.expires_at > db.now(),
                        )
                        .with_for_update()
                    )
                )
                .mappings()
                .first()
            )
            require(invitation, "AUTH_REQUIRED", "Invitation is invalid or expired", 401)
            account = (
                (
                    await session.execute(
                        select(db.accounts)
                        .where(db.accounts.c.id == invitation["account_id"])
                        .with_for_update()
                    )
                )
                .mappings()
                .one()
            )
            require(
                not account["active"], "INVALID_TRANSITION", "Account is already activated", 409
            )
            success = await accept_totp(session, dict(account), payload.otp, box)
            if success:
                await session.execute(
                    update(db.accounts).where(db.accounts.c.id == account["id"]).values(active=True)
                )
                await session.execute(
                    update(db.invitations)
                    .where(db.invitations.c.id == invitation["id"])
                    .values(used=True)
                )
                session_token = await issue_session(session, account["id"], cfg.session_minutes)
                await record_audit(
                    session,
                    account["id"],
                    "account.activate",
                    account["id"],
                    "SUCCESS",
                    request.state.correlation_id,
                )
        require(success, "AUTH_REQUIRED", "Authenticator code could not be verified", 401)
        set_cookie(response, session_token)
        return {"status": "ACTIVE"}

    @app.get("/v1/auth/me")
    async def me(request: Request):
        async with database.transaction() as session:
            return await actor_for(session, request)

    @app.post("/v1/auth/logout", status_code=204)
    async def logout(request: Request):
        async with database.transaction() as session:
            await actor_for(session, request)
            await session.execute(
                update(db.sessions)
                .where(db.sessions.c.token_hash == digest(token(request)))
                .values(revoked=True)
            )
        response = Response(status_code=204)
        response.delete_cookie(
            COOKIE, path="/", secure=cfg.production, httponly=True, samesite="strict"
        )
        return response

    @app.post("/v1/invitations")
    async def invite(payload: c.Invite, request: Request):
        async def apply(session, actor):
            require(global_role(actor, "PLATFORM_ADMIN"))
            from .operations import create_invitation

            return await create_invitation(
                session, cfg, box, payload, actor["id"], request.state.correlation_id
            )

        result = await command(request, payload.model_dump(mode="json"), "account.invite", apply)
        if result.get("status") == "INVITATION_QUEUED":
            from .operations import deliver_invitations

            result = {**result, "delivery": await deliver_invitations(database, cfg, box)}
        return result

    @app.post("/v1/grants/{grant_id}/revoke")
    async def revoke_grant(grant_id: UUID, request: Request):
        async def apply(session, actor):
            require(global_role(actor, "PLATFORM_ADMIN"))
            grant = (
                (
                    await session.execute(
                        select(db.grants).where(db.grants.c.id == str(grant_id)).with_for_update()
                    )
                )
                .mappings()
                .first()
            )
            require(grant is not None, "NOT_FOUND_OR_NOT_PERMITTED", "Grant unavailable", 404)
            require(
                grant["account_id"] != actor["id"],
                "ACCESS_DENIED",
                "Another administrator must revoke your own grant",
            )
            await session.execute(
                update(db.grants).where(db.grants.c.id == str(grant_id)).values(revoked=True)
            )
            await record_audit(
                session,
                actor["id"],
                "grant.revoke",
                str(grant_id),
                "SUCCESS",
                request.state.correlation_id,
            )
            return {"status": "REVOKED"}

        return await command(request, {"grant_id": str(grant_id)}, "grant.revoke", apply)

    @app.get("/v1/accounts")
    async def list_accounts(request: Request):
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            require(global_role(actor, "PLATFORM_ADMIN", "REGISTRY_STEWARD", "STANDARDS_REVIEWER"))
            rows = (
                await session.execute(
                    select(
                        db.accounts.c.id,
                        db.accounts.c.name,
                        db.accounts.c.email,
                        db.accounts.c.active,
                    )
                    .order_by(db.accounts.c.name)
                    .limit(100)
                )
            ).mappings()
            return {"items": [dict(r) for r in rows]}

    @app.get("/v1/grants")
    async def list_grants(request: Request):
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            require(global_role(actor, "PLATFORM_ADMIN"))
            query = (
                select(db.grants, db.accounts.c.name, db.accounts.c.email)
                .join(db.accounts)
                .order_by(db.grants.c.valid_from.desc())
                .limit(100)
            )
            return {"items": [dict(r) for r in (await session.execute(query)).mappings()]}

    @app.get("/v1/organisation-units")
    async def list_units(request: Request):
        async with database.transaction() as session:
            await actor_for(session, request)
            return {
                "items": [
                    dict(r)
                    for r in (
                        await session.execute(
                            select(db.units).order_by(db.units.c.kind, db.units.c.name).limit(1000)
                        )
                    ).mappings()
                ]
            }

    @app.get("/v1/organisation-research")
    async def organisation_research(request: Request):
        async with database.transaction() as session:
            await actor_for(session, request)
        return json.loads(
            Path(__file__).with_name("organisation_sources.json").read_text(encoding="utf-8")
        )

    @app.post("/v1/organisation-units")
    async def create_unit(payload: c.Unit, request: Request):
        async def apply(session, actor):
            require(global_role(actor, "PLATFORM_ADMIN"))
            if payload.valid_until:
                valid_interval(payload.valid_from, payload.valid_until)
            require(
                payload.valid_from.tzinfo is not None,
                "VALIDATION_FAILED",
                "Use a dated authority reference",
                422,
            )
            if payload.kind == "ZONE":
                parent = (
                    (
                        await session.execute(
                            select(db.units).where(
                                db.units.c.id == str(payload.parent_id), db.units.c.kind == "REGION"
                            )
                        )
                    )
                    .mappings()
                    .first()
                )
                require(
                    parent is not None,
                    "VALIDATION_FAILED",
                    "A zone must belong to an existing region",
                    422,
                )
            else:
                require(
                    payload.parent_id is None,
                    "VALIDATION_FAILED",
                    "A region has no zone parent",
                    422,
                )
            row = {**payload.model_dump(mode="json"), "id": db.uid(), "version": 1}
            await session.execute(db.units.insert().values(**row))
            await record_change(
                session,
                actor,
                "Organisation",
                row,
                "organisation.created",
                request.state.correlation_id,
            )
            return receipt(row)

        return await command(
            request, payload.model_dump(mode="json"), "organisation.created", apply
        )

    @app.get("/v1/operators")
    async def list_operators(request: Request):
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            query = select(db.operators).order_by(db.operators.c.name).limit(100)
            if not global_role(actor, "PLATFORM_ADMIN", "REGISTRY_STEWARD"):
                query = query.where(
                    db.operators.c.id.in_(
                        select(db.facilities.c.operator_id).where(visibility(actor))
                    )
                )
            return {"items": [dict(r) for r in (await session.execute(query)).mappings()]}

    @app.post("/v1/operators")
    async def create_operator(payload: c.Operator, request: Request):
        async def apply(session, actor):
            require(global_role(actor, "REGISTRY_STEWARD"))
            row = {**payload.model_dump(), "id": db.uid(), "created_at": db.now()}
            await session.execute(db.operators.insert().values(**row))
            await record_audit(
                session,
                actor["id"],
                "operator.created",
                row["id"],
                "SUCCESS",
                request.state.correlation_id,
            )
            return receipt(row)

        return await command(request, payload.model_dump(), "operator.created", apply)

    @app.get("/v1/facilities")
    async def list_facilities(request: Request, after: str = "", limit: int = 50):
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            rows = [
                dict(r)
                for r in (
                    await session.execute(
                        select(db.facilities)
                        .where(visibility(actor), db.facilities.c.id > after)
                        .order_by(db.facilities.c.id)
                        .limit(min(max(limit, 1), 100))
                    )
                ).mappings()
            ]
            return {
                "items": rows,
                "next_cursor": rows[-1]["id"] if len(rows) == min(max(limit, 1), 100) else None,
                "as_of": db.now(),
            }

    @app.get("/v1/facilities/{facility_id}")
    async def get_facility(facility_id: UUID, request: Request):
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            return await facility_for(session, actor, str(facility_id))

    @app.post("/v1/facilities")
    async def create_facility(payload: c.Facility, request: Request):
        async def apply(session, actor):
            zone = (
                (
                    await session.execute(
                        select(db.units).where(
                            db.units.c.id == str(payload.zone_id),
                            db.units.c.kind == "ZONE",
                            db.units.c.valid_from <= db.now(),
                            (db.units.c.valid_until.is_(None))
                            | (db.units.c.valid_until > db.now()),
                        )
                    )
                )
                .mappings()
                .first()
            )
            require(zone is not None, "VALIDATION_FAILED", "Choose a currently effective zone", 422)
            require(
                scoped(
                    actor,
                    {"REGISTRY_STEWARD"},
                    {"id": "", "zone_id": zone["id"], "region_id": zone["parent_id"]},
                )
            )
            require(
                await session.scalar(
                    select(db.operators.c.id).where(
                        db.operators.c.id == str(payload.operator_org_id)
                    )
                ),
                "VALIDATION_FAILED",
                "Choose an existing operator",
                422,
            )
            row = {
                "id": db.uid(),
                "operator_id": str(payload.operator_org_id),
                "zone_id": str(payload.zone_id),
                "name": payload.site_name,
                "site_type": payload.site_type,
                "ownership": payload.ownership_category,
                "jurisdiction": payload.jurisdiction_profile,
                "external_reference": payload.external_reference,
                "address": payload.address,
                "public_contact": payload.public_contact,
                "private_contact": payload.private_contact,
                "services": payload.services,
                "identity_status": "PROVISIONAL",
                "statutory_status": "PENDING",
                "affiliation_status": "APPLICANT",
                "publication_status": "DRAFT",
                "capability_status": "DECLARED",
                "readiness_status": "UNKNOWN",
                "affiliation_expires_at": None,
                "affiliation_scope": None,
                "conditions": None,
                "created_by": actor["id"],
                "created_at": db.now(),
                "updated_at": db.now(),
                "version": 1,
            }
            await session.execute(db.facilities.insert().values(**row))
            await record_change(
                session,
                actor,
                "Facility",
                row,
                "network.facility_registered",
                request.state.correlation_id,
            )
            return receipt(row)

        return await command(request, payload.model_dump(mode="json"), "facility.created", apply)

    @app.post("/v1/facilities/{facility_id}/verification")
    async def verify_facility(facility_id: UUID, payload: c.Verification, request: Request):
        async def apply(session, actor):
            row = await facility_for(session, actor, str(facility_id), lock=True)
            require(scoped(actor, {"REGISTRY_STEWARD"}, row))
            expected(row, payload.expected_version)
            require(
                row["identity_status"] not in {"CLOSED", "LINKED"},
                "LIFECYCLE_REVIEW_REQUIRED",
                "Closed or linked sites require their own reviewed lifecycle; verification cannot reopen them",
                409,
            )
            row.pop("region_id")
            row = await amend(
                session,
                db.facilities,
                row,
                {
                    "identity_status": payload.identity_status,
                    "statutory_status": payload.statutory_status,
                    "updated_at": db.now(),
                },
            )
            await record_change(
                session,
                actor,
                "Facility",
                row,
                "facility.verified",
                request.state.correlation_id,
                {"reason": payload.reason},
            )
            return receipt(row)

        return await command(request, payload.model_dump(mode="json"), "facility.verified", apply)

    @app.get("/v1/criteria")
    async def list_criteria(request: Request):
        async with database.transaction() as session:
            await actor_for(session, request)
            return {
                "items": [
                    dict(r)
                    for r in (
                        await session.execute(
                            select(db.criteria)
                            .order_by(db.criteria.c.name, db.criteria.c.version)
                            .limit(100)
                        )
                    ).mappings()
                ]
            }

    @app.post("/v1/criteria")
    async def create_criteria(payload: c.CriteriaSet, request: Request):
        async def apply(session, actor):
            require(global_role(actor, "STANDARDS_DECIDER"))
            valid_interval(payload.valid_from, payload.valid_until)
            require(
                len({r.code for r in payload.requirements}) == len(payload.requirements),
                "VALIDATION_FAILED",
                "Criterion codes must be unique",
                422,
            )
            row = {**payload.model_dump(mode="json"), "id": db.uid(), "adopted_by": actor["id"]}
            await session.execute(db.criteria.insert().values(**row))
            await record_audit(
                session,
                actor["id"],
                "criteria.adopted",
                row["id"],
                "SUCCESS",
                request.state.correlation_id,
            )
            return receipt(row)

        return await command(request, payload.model_dump(mode="json"), "criteria.adopted", apply)

    @app.post("/v1/applications")
    async def create_application(payload: c.Application, request: Request):
        async def apply(session, actor):
            facility = await facility_for(session, actor, str(payload.facility_id), lock=True)
            require(scoped(actor, {"FACILITY_ADMIN", "REGISTRY_STEWARD"}, facility))
            criterion = (
                (
                    await session.execute(
                        select(db.criteria).where(db.criteria.c.id == str(payload.criteria_id))
                    )
                )
                .mappings()
                .first()
            )
            require(
                criterion
                and current_criteria(criterion)
                and criterion["jurisdiction"] == facility["jurisdiction"]
                and criterion["site_type"] == facility["site_type"],
                "POLICY_NOT_ACTIVE",
                "An adopted, current criterion set matching this facility is required",
                409,
            )
            row = {
                **payload.model_dump(mode="json"),
                "id": db.uid(),
                "state": "DRAFT",
                "created_by": actor["id"],
                "version": 1,
                "inspector_id": None,
                "reviewer_id": None,
                "recommendation": None,
            }
            await session.execute(db.applications.insert().values(**row))
            await record_change(
                session,
                actor,
                "Application",
                row,
                "application.created",
                request.state.correlation_id,
            )
            return receipt(row)

        return await command(request, payload.model_dump(mode="json"), "application.created", apply)

    @app.get("/v1/applications")
    async def list_applications(request: Request):
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            rows = (
                await session.execute(
                    select(db.applications)
                    .where(
                        db.applications.c.facility_id.in_(
                            select(db.facilities.c.id).where(visibility(actor))
                        )
                    )
                    .order_by(db.applications.c.id)
                    .limit(100)
                )
            ).mappings()
            return {"items": [dict(r) for r in rows]}

    @app.get("/v1/applications/{application_id}")
    async def get_application(application_id: UUID, request: Request):
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            application, facility = await application_for(session, actor, str(application_id))
            result = {"application": application, "facility": facility}
            for name, table in (
                ("evidence", db.evidence),
                ("inspections", db.inspections),
                ("decisions", db.decisions),
            ):
                result[name] = [
                    dict(r)
                    for r in (
                        await session.execute(
                            select(table).where(table.c.application_id == str(application_id))
                        )
                    ).mappings()
                ]
            result["criteria"] = dict(
                (
                    await session.execute(
                        select(db.criteria).where(db.criteria.c.id == application["criteria_id"])
                    )
                )
                .mappings()
                .one()
            )
            return result

    @app.post("/v1/applications/{application_id}/submit")
    async def submit_application(application_id: UUID, payload: c.Versioned, request: Request):
        async def apply(session, actor):
            row, facility = await application_for(session, actor, str(application_id), lock=True)
            require(scoped(actor, {"FACILITY_ADMIN", "REGISTRY_STEWARD"}, facility))
            expected(row, payload.expected_version)
            require(
                row["state"] == "DRAFT", "INVALID_TRANSITION", "Only a draft can be submitted", 409
            )
            criterion = (
                (
                    await session.execute(
                        select(db.criteria).where(db.criteria.c.id == row["criteria_id"])
                    )
                )
                .mappings()
                .one()
            )
            require(
                current_criteria(criterion),
                "POLICY_NOT_ACTIVE",
                "The adopted criteria have expired",
                409,
            )
            available = set(
                (
                    await session.execute(
                        select(db.evidence.c.criterion).where(
                            db.evidence.c.application_id == row["id"],
                            db.evidence.c.expires_at > db.now(),
                        )
                    )
                ).scalars()
            )
            required = {r["code"] for r in criterion["requirements"] if r["required"]}
            require(
                required <= available,
                "VALIDATION_FAILED",
                "Upload current evidence for every required criterion",
                422,
            )
            row = await amend(session, db.applications, row, {"state": "SUBMITTED"})
            await record_change(
                session,
                actor,
                "Application",
                row,
                "application.submitted",
                request.state.correlation_id,
            )
            return receipt(row)

        return await command(request, payload.model_dump(), "application.submitted", apply)

    @app.post("/v1/applications/{application_id}/evidence")
    async def upload_evidence(
        application_id: UUID,
        request: Request,
        criterion: str,
        filename: str,
        source: str,
        expires_at: datetime,
    ):
        from . import storage

        require(
            2 <= len(criterion) <= 120 and 1 <= len(filename) <= 200 and 3 <= len(source) <= 3000,
            "VALIDATION_FAILED",
            "Supply the criterion, original filename and evidence source",
            422,
        )
        require(
            expires_at.tzinfo is not None and expires_at > datetime.now(UTC),
            "VALIDATION_FAILED",
            "Evidence must have an explicit future expiry",
            422,
        )
        # Authenticate scope before accepting a potentially large request body.
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            _row, facility = await application_for(session, actor, str(application_id))
            require(scoped(actor, {"FACILITY_ADMIN", "REGISTRY_STEWARD"}, facility))
        chunks, total = [], 0
        async for chunk in request.stream():
            total += len(chunk)
            require(
                total <= storage.MAX_EVIDENCE_BYTES,
                "VALIDATION_FAILED",
                "Evidence exceeds 10 MiB",
                413,
            )
            chunks.append(chunk)
        content = b"".join(chunks)
        require(bool(content), "VALIDATION_FAILED", "The file is empty", 422)
        media_type = request.headers.get("content-type", "").split(";")[0]
        payload = {
            "criterion": criterion,
            "filename": filename,
            "source": source,
            "expires_at": expires_at.isoformat(),
            "sha256": hashlib.sha256(content).hexdigest(),
        }

        async def apply(session, actor):
            row, facility = await application_for(session, actor, str(application_id), lock=True)
            require(scoped(actor, {"FACILITY_ADMIN", "REGISTRY_STEWARD"}, facility))
            require(
                row["state"] == "DRAFT",
                "INVALID_TRANSITION",
                "Submitted evidence remains immutable",
                409,
            )
            rule = (
                (
                    await session.execute(
                        select(db.criteria).where(db.criteria.c.id == row["criteria_id"])
                    )
                )
                .mappings()
                .one()
            )
            require(
                criterion in {r["code"] for r in rule["requirements"]},
                "VALIDATION_FAILED",
                "Unknown criterion",
                422,
            )
            evidence_id = db.uid()
            key = f"institutional-evidence/{row['id']}/{evidence_id}"
            await run_in_threadpool(storage.store, cfg, key, content, media_type)
            item = {
                "id": evidence_id,
                "application_id": row["id"],
                "criterion": criterion,
                "object_key": key,
                "sha256": payload["sha256"],
                "filename": filename,
                "source": source,
                "expires_at": expires_at.astimezone(UTC).isoformat(),
                "media_type": media_type,
                "size": len(content),
                "uploaded_by": actor["id"],
                "created_at": db.now(),
                "scan_status": "CLEAN",
            }
            await session.execute(db.evidence.insert().values(**item))
            await record_audit(
                session,
                actor["id"],
                "evidence.stored",
                evidence_id,
                "SUCCESS",
                request.state.correlation_id,
            )
            return receipt(item)

        return await command(request, payload, "evidence.stored", apply)

    @app.get("/v1/evidence/{evidence_id}/download")
    async def download_evidence(evidence_id: UUID, request: Request):
        from . import storage

        async with database.transaction() as session:
            actor = await actor_for(session, request)
            row = (
                (
                    await session.execute(
                        select(db.evidence).where(db.evidence.c.id == str(evidence_id))
                    )
                )
                .mappings()
                .first()
            )
            require(row is not None, "NOT_FOUND_OR_NOT_PERMITTED", "Evidence unavailable", 404)
            await application_for(session, actor, row["application_id"])
            content = await run_in_threadpool(storage.read, cfg, row["object_key"])
            require(
                hashlib.sha256(content).hexdigest() == row["sha256"],
                "INTEGRITY_FAILURE",
                "The stored evidence failed its integrity check",
                503,
            )
            await record_audit(
                session,
                actor["id"],
                "evidence.read",
                row["id"],
                "SUCCESS",
                request.state.correlation_id,
            )
            return Response(
                content,
                media_type="application/octet-stream",
                headers={
                    "Content-Disposition": f'attachment; filename="evidence-{row["id"]}"',
                    "Content-Security-Policy": "sandbox; default-src 'none'",
                },
            )

    @app.post("/v1/applications/{application_id}/assignment")
    async def assign_inspection(application_id: UUID, payload: c.Assignment, request: Request):
        async def apply(session, actor):
            row, facility = await application_for(session, actor, str(application_id), lock=True)
            require(scoped(actor, {"REGISTRY_STEWARD", "STANDARDS_REVIEWER"}, facility))
            expected(row, payload.expected_version)
            require(
                row["state"] == "SUBMITTED",
                "INVALID_TRANSITION",
                "The application must be submitted",
                409,
            )
            require(
                len({str(payload.inspector_id), str(payload.reviewer_id), row["created_by"]}) == 3,
                "ACCESS_DENIED",
                "Applicant, inspector and reviewer must be independent",
            )
            for account_id, role in (
                (str(payload.inspector_id), "INSPECTOR"),
                (str(payload.reviewer_id), "STANDARDS_REVIEWER"),
            ):
                grant_rows = [
                    dict(g)
                    for g in (
                        await session.execute(
                            select(db.grants)
                            .join(db.accounts)
                            .where(
                                db.grants.c.account_id == account_id,
                                db.accounts.c.active.is_(True),
                                db.grants.c.revoked.is_(False),
                                db.grants.c.valid_from <= db.now(),
                                db.grants.c.valid_until > db.now(),
                            )
                        )
                    ).mappings()
                ]
                require(
                    scoped({"grants": grant_rows}, {role}, facility),
                    "ACCESS_DENIED",
                    "Assigned inspectors and reviewers need current grants covering this facility",
                )
            row = await amend(
                session,
                db.applications,
                row,
                {
                    "state": "INSPECTION",
                    "inspector_id": str(payload.inspector_id),
                    "reviewer_id": str(payload.reviewer_id),
                },
            )
            await record_change(
                session,
                actor,
                "Application",
                row,
                "inspection.assigned",
                request.state.correlation_id,
            )
            return receipt(row)

        return await command(request, payload.model_dump(mode="json"), "inspection.assigned", apply)

    @app.post("/v1/applications/{application_id}/inspections")
    async def inspect(application_id: UUID, payload: c.Inspection, request: Request):
        async def apply(session, actor):
            row, facility = await application_for(session, actor, str(application_id), lock=True)
            require(actor["id"] == row["inspector_id"] and scoped(actor, {"INSPECTOR"}, facility))
            expected(row, payload.expected_version)
            require(
                row["state"] == "INSPECTION", "INVALID_TRANSITION", "Inspection is not pending", 409
            )
            require(
                not payload.conflict_declared,
                "ACCESS_DENIED",
                "A conflicted inspector must be reassigned",
            )
            require(
                payload.observed_at.tzinfo is not None and payload.observed_at <= datetime.now(UTC),
                "VALIDATION_FAILED",
                "Observation time must be a real past time with time zone",
                422,
            )
            criterion = (
                (
                    await session.execute(
                        select(db.criteria).where(db.criteria.c.id == row["criteria_id"])
                    )
                )
                .mappings()
                .one()
            )
            codes = {r["code"] for r in criterion["requirements"]}
            require(
                {f.criterion for f in payload.findings} <= codes,
                "VALIDATION_FAILED",
                "Unknown criterion",
                422,
            )
            evidence_ids = set(
                (
                    await session.execute(
                        select(db.evidence.c.id).where(db.evidence.c.application_id == row["id"])
                    )
                ).scalars()
            )
            require(
                all(str(e) in evidence_ids for f in payload.findings for e in f.evidence_ids),
                "VALIDATION_FAILED",
                "Every finding must reference this application's actual evidence",
                422,
            )
            await session.execute(
                db.inspections.insert().values(
                    id=db.uid(),
                    application_id=row["id"],
                    inspector_id=actor["id"],
                    findings=[f.model_dump(mode="json") for f in payload.findings],
                    conflict_declared=False,
                    observed_at=payload.observed_at.isoformat(),
                    recorded_at=db.now(),
                )
            )
            row = await amend(session, db.applications, row, {"state": "EVIDENCE_REVIEW"})
            await record_change(
                session,
                actor,
                "Application",
                row,
                "inspection.recorded",
                request.state.correlation_id,
            )
            return receipt(row)

        return await command(request, payload.model_dump(mode="json"), "inspection.recorded", apply)

    @app.post("/v1/applications/{application_id}/recommendation")
    async def recommend(application_id: UUID, payload: c.Recommendation, request: Request):
        async def apply(session, actor):
            row, facility = await application_for(session, actor, str(application_id), lock=True)
            require(
                actor["id"] == row["reviewer_id"]
                and scoped(actor, {"STANDARDS_REVIEWER"}, facility)
            )
            expected(row, payload.expected_version)
            require(
                row["state"] == "EVIDENCE_REVIEW",
                "INVALID_TRANSITION",
                "Inspection evidence must be reviewed first",
                409,
            )
            row = await amend(
                session,
                db.applications,
                row,
                {
                    "state": "RECOMMENDED",
                    "recommendation": {**payload.model_dump(), "reviewer_id": actor["id"]},
                },
            )
            await record_change(
                session,
                actor,
                "Application",
                row,
                "application.recommended",
                request.state.correlation_id,
            )
            return receipt(row)

        return await command(request, payload.model_dump(), "application.recommended", apply)

    @app.post("/v1/applications/{application_id}/decisions")
    async def decide(application_id: UUID, payload: c.Decision, request: Request):
        async def apply(session, actor):
            row, facility = await application_for(session, actor, str(application_id), lock=True)
            require(global_role(actor, "STANDARDS_DECIDER"))
            require(
                actor["id"]
                not in (
                    row["created_by"],
                    row["inspector_id"],
                    row["reviewer_id"],
                    facility["created_by"],
                ),
                "ACCESS_DENIED",
                "The final Directorate decider must be independent of this case",
            )
            expected(row, payload.expected_version)
            require(
                row["state"] == "RECOMMENDED",
                "INVALID_TRANSITION",
                "An independent recommendation is required",
                409,
            )
            criterion = (
                (
                    await session.execute(
                        select(db.criteria).where(db.criteria.c.id == row["criteria_id"])
                    )
                )
                .mappings()
                .one()
            )
            require(
                current_criteria(criterion),
                "POLICY_NOT_ACTIVE",
                "The adopted criterion set is no longer current",
                409,
            )
            valid_interval(payload.effective_at, payload.expires_at)
            require(
                payload.effective_at <= datetime.now(UTC) < payload.expires_at,
                "VALIDATION_FAILED",
                "A current decision interval is required",
                422,
            )
            if payload.decision == "CONDITIONAL":
                require(
                    bool(payload.conditions.strip()),
                    "VALIDATION_FAILED",
                    "Specify the actual conditions",
                    422,
                )
            await session.execute(
                db.decisions.insert().values(
                    id=db.uid(),
                    application_id=row["id"],
                    decider_id=actor["id"],
                    decision=payload.decision,
                    reason=payload.reason,
                    scope=payload.scope,
                    conditions=payload.conditions,
                    effective_at=payload.effective_at.isoformat(),
                    expires_at=payload.expires_at.isoformat(),
                    created_at=db.now(),
                )
            )
            row = await amend(session, db.applications, row, {"state": "DECIDED"})
            facility.pop("region_id")
            facility = await amend(
                session,
                db.facilities,
                facility,
                {
                    "affiliation_status": {
                        "APPROVE": "ACTIVE",
                        "CONDITIONAL": "CONDITIONAL",
                        "REJECT": "REJECTED",
                    }[payload.decision],
                    "affiliation_expires_at": payload.expires_at.isoformat(),
                    "affiliation_scope": payload.scope,
                    "conditions": payload.conditions,
                    "updated_at": db.now(),
                },
            )
            await record_change(
                session,
                actor,
                "Facility",
                facility,
                "affiliation.decided",
                request.state.correlation_id,
            )
            await record_change(
                session,
                actor,
                "Application",
                row,
                "application.decided",
                request.state.correlation_id,
            )
            return receipt(row)

        return await command(request, payload.model_dump(mode="json"), "affiliation.decided", apply)

    @app.post("/v1/facilities/{facility_id}/publication")
    async def publish(facility_id: UUID, payload: c.Publication, request: Request):
        async def apply(session, actor):
            row = await facility_for(session, actor, str(facility_id), lock=True)
            require(scoped(actor, {"REGISTRY_STEWARD"}, row))
            expected(row, payload.expected_version)
            if payload.action == "PUBLISH":
                from .institutional.master import accepting_new_care

                await accepting_new_care(session, str(facility_id))
                require(
                    publication_eligible(row),
                    "INVALID_TRANSITION",
                    "Publication requires verified identity and a current Directorate affiliation decision",
                    409,
                )
            row.pop("region_id")
            row = await amend(
                session,
                db.facilities,
                row,
                {
                    "publication_status": "PUBLISHED"
                    if payload.action == "PUBLISH"
                    else "WITHDRAWN",
                    "updated_at": db.now(),
                },
            )
            await record_change(
                session,
                actor,
                "Facility",
                row,
                "directory.changed",
                request.state.correlation_id,
                {"reason": payload.reason},
            )
            return receipt(row)

        return await command(request, payload.model_dump(), "directory.changed", apply)

    @app.get("/v1/directory")
    async def directory(
        service: str = "", jurisdiction: str = "", after: str = "", limit: int = 50
    ):
        async with database.transaction() as session:
            query = select(db.facilities).where(
                db.facilities.c.publication_status == "PUBLISHED",
                db.facilities.c.identity_status == "VERIFIED",
                db.facilities.c.affiliation_status.in_(["ACTIVE", "CONDITIONAL"]),
                db.facilities.c.affiliation_expires_at > db.now(),
                db.facilities.c.id > after,
            )
            if jurisdiction:
                query = query.where(db.facilities.c.jurisdiction == jurisdiction)
            # Apply exact service membership in SQL before pagination on PostgreSQL.
            if service:
                if database.postgres:
                    query = query.where(db.facilities.c.services.cast(JSONB).contains([service]))
                else:
                    query = query.where(
                        db.facilities.c.id.in_(
                            select(db.facilities.c.id).where(
                                func.json_array_length(db.facilities.c.services) > 0
                            )
                        )
                    )
            rows = [
                dict(r)
                for r in (
                    await session.execute(
                        query.order_by(db.facilities.c.id).limit(min(max(limit, 1), 100))
                    )
                ).mappings()
            ]
            if service and not database.postgres:
                rows = [r for r in rows if service in r["services"]]
            return {
                "items": [public_profile(r) for r in rows],
                "as_of": db.now(),
                "next_cursor": rows[-1]["id"] if len(rows) == min(max(limit, 1), 100) else None,
            }

    @app.get("/v1/audit")
    async def audit_history(request: Request):
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            require(global_role(actor, "PLATFORM_ADMIN"))
            return {
                "items": [
                    dict(r)
                    for r in (
                        await session.execute(
                            select(db.audit)
                            .order_by(db.audit.c.recorded_at.desc(), db.audit.c.id)
                            .limit(100)
                        )
                    ).mappings()
                ]
            }

    @app.get("/v1/internal/jobs")
    async def deliver_jobs(request: Request):
        require(
            bool(cfg.jobs_secret)
            and hmac.compare_digest(
                request.headers.get("authorization", ""), "Bearer " + cfg.jobs_secret
            ),
            "AUTH_REQUIRED",
            "Job authentication required",
            401,
        )
        from .operations import deliver_invitations

        result = {}
        if cfg.controls_enabled and (await database.version() or 0) >= 4:
            from .control.jobs import run_tick

            result["controls"] = await run_tick(database, cfg, box, limit=2, seconds=20)
        if cfg.resend_api_key and cfg.email_from:
            result["invitations"] = await deliver_invitations(
                database, cfg, box, limit=1, timeout=10
            )
        else:
            result["invitations"] = {"status": "DELIVERY_DEPENDENCY_UNAVAILABLE"}
        if cfg.reporting_enabled and (await database.version() or 0) >= 3:
            from .reporting.operations import DirectorateService

            async with database.transaction() as session:
                if database.postgres:
                    await session.execute(text("SELECT pg_advisory_xact_lock(782025011)"))
                # This job records overdue exceptions only. It cannot accept
                # responsibility, release evidence or sign a human review.
                service = DirectorateService(
                    session,
                    cfg,
                    box,
                    {"id": "REPORTING_SCHEDULER", "grants": []},
                    request.state.correlation_id,
                )
                result["reporting"] = await service.reconcile()
        return result

    @app.get("/v1/integrations")
    async def integration_status(request: Request):
        from .integrations import AI_DISABLED_KEY, redis_command

        async with database.transaction() as session:
            actor = await actor_for(session, request)
            require(global_role(actor, "PLATFORM_ADMIN"))
        control = await redis_command(cfg, ["GET", AI_DISABLED_KEY])
        return {
            "openrouter": {
                "model": cfg.openrouter_model,
                "credential_configured": bool(cfg.openrouter_api_key),
                "ai_enabled": control == "0",
                "verification_scope": "FIXED_PUBLIC_PROBE_ONLY",
            },
            "upstash": {"reachable": True},
            "email": {"configured": bool(cfg.resend_api_key and cfg.email_from)},
        }

    @app.post("/v1/integrations/openrouter/verify")
    async def verify_openrouter(payload: c.StrictModel, request: Request):
        from .integrations import verify_free_model

        async with database.transaction() as session:
            actor = await actor_for(session, request)
            require(global_role(actor, "PLATFORM_ADMIN"))
            permitted = await throttle(session, "provider-probe:" + actor["id"])
        require(
            permitted,
            "RATE_LIMITED",
            "Too many verification requests. Try again in 15 minutes.",
            429,
        )
        result = await verify_free_model(cfg)
        async with database.transaction() as session:
            await record_audit(
                session,
                actor["id"],
                "integration.openrouter_verified",
                None,
                "SUCCESS",
                request.state.correlation_id,
                result,
            )
        return result

    @app.post("/v1/integrations/ai-control")
    async def ai_control(payload: c.AiControl, request: Request):
        from .integrations import AI_DISABLED_KEY, redis_command

        async with database.transaction() as session:
            actor = await actor_for(session, request)
            require(global_role(actor, "PLATFORM_ADMIN"))
        await redis_command(cfg, ["SET", AI_DISABLED_KEY, "0" if payload.enabled else "1"])
        async with database.transaction() as session:
            await record_audit(
                session,
                actor["id"],
                "integration.ai_control_changed",
                None,
                "SUCCESS",
                request.state.correlation_id,
                payload.model_dump(),
            )
        return {"status": "AI_ENABLED" if payload.enabled else "AI_DISABLED"}

    @app.post("/v1/invitations/deliver")
    async def retry_invitations(request: Request):
        async with database.transaction() as session:
            actor = await actor_for(session, request)
            require(global_role(actor, "PLATFORM_ADMIN"))
        from .operations import deliver_invitations

        return await deliver_invitations(database, cfg, box)

    from .clinical.router import install as install_clinical

    install_clinical(app, cfg, database, box, actor_for)
    from .reporting.router import install as install_reporting

    install_reporting(app, cfg, database, box, actor_for)
    from .control.router import install as install_controls

    install_controls(app, cfg, database, box, actor_for, throttle, set_cookie)
    from .institutional.router import install as install_institutional

    install_institutional(app, cfg, database, box, actor_for)
    from .personal.router import install as install_personal

    install_personal(app, cfg, database, box, actor_for, throttle)
    return app
