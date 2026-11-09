"""Patient/family API and separately authorised records/care-team operating boundary."""

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Request
from sqlalchemy import or_, select, text
from sqlalchemy.exc import IntegrityError

from .. import db
from ..clinical import store as cs
from ..clinical import tables as ct
from ..clinical.router import governor
from ..domain import RuleError, require
from ..paging import page
from ..security import digest
from . import contracts as c
from . import tables as t
from .care import SOURCE_STATES, CareService
from .service import load


def install(app, cfg, database, box, actor_for, throttle):
    router = APIRouter(prefix="/v1/personal")

    async def ready():
        require(
            cfg.personal_enabled and (await database.version() or 0) >= 8,
            "PERSONAL_CARE_UNAVAILABLE",
            "Personal care access is awaiting service readiness",
            503,
        )

    async def service_for(session, request):
        await ready()
        actor = await actor_for(session, request)
        return CareService(session, cfg, box, actor, request.state.correlation_id)

    async def command(request, payload, guard, apply):
        body = payload.model_dump(mode="json")
        actor = None
        try:
            async with database.transaction() as session:
                service = await service_for(session, request)
                if database.postgres:
                    await session.execute(text("SELECT pg_advisory_xact_lock(782025014)"))
                    service.actor = await actor_for(session, request)
                actor = service.actor
                await guard(service, body)
                key = request.headers.get("Idempotency-Key")
                require(
                    key and 8 <= len(key) <= 160,
                    "VALIDATION_FAILED",
                    "An Idempotency-Key is required",
                    422,
                )
                request_hash = hashlib.sha256(cs.canonical(body).encode()).hexdigest()
                previous = (
                    (
                        await session.execute(
                            select(t.operations).where(
                                t.operations.c.actor_id == actor["id"],
                                t.operations.c.operation == request.url.path,
                                t.operations.c.key == key,
                            )
                        )
                    )
                    .mappings()
                    .first()
                )
                if previous:
                    require(
                        previous["request_hash"] == request_hash,
                        "IDEMPOTENCY_KEY_REUSE",
                        "Use the original content with this operation key",
                        409,
                    )
                    return json.loads(box.decrypt(previous["response_ciphertext"]))
                resource = await apply(service, body)
                response = {
                    "resource": resource,
                    "execution_state": "CENTRAL_COMMITTED",
                    "recorded_at": db.now(),
                }
                await session.execute(
                    t.operations.insert().values(
                        id=db.uid(),
                        actor_id=actor["id"],
                        operation=request.url.path,
                        key=key,
                        request_hash=request_hash,
                        response_ciphertext=box.encrypt(cs.canonical(response)),
                    )
                )
                return response
        except RuleError:
            if (await database.version() or 0) >= 8:
                async with database.transaction() as session:
                    await CareService(session, cfg, box, actor, request.state.correlation_id).audit(
                        "personal.command_denied", outcome="DENIED"
                    )
            raise

    async def signed_in(service, body):
        return None

    @router.post("/enrolment", status_code=202)
    async def enrolment(payload: c.Enrolment, request: Request):
        await ready()
        email = c.Enrolment.normalised_email(payload.email)
        async with database.transaction() as session:
            allowed = await throttle(session, "personal-enrol:" + digest(email))
            network = await throttle(
                session,
                "personal-enrol-network:"
                + digest(request.client.host if request.client else "unknown"),
            )
        require(
            allowed and network, "RATE_LIMITED", "Try again after the current request window", 429
        )
        require(
            cfg.resend_api_key and cfg.email_from,
            "EMAIL_UNAVAILABLE",
            "Account verification is unavailable; retry later",
            503,
        )
        account_id = None
        try:
            async with database.transaction() as session:
                if database.postgres:
                    await session.execute(text("SELECT pg_advisory_xact_lock(782025014)"))
                existing = await session.scalar(
                    select(db.accounts.c.id).where(db.accounts.c.email == email)
                )
                if not existing:
                    account_id, invitation_id, token = db.uid(), db.uid(), secrets.token_urlsafe(48)
                    await session.execute(
                        db.accounts.insert().values(
                            id=account_id,
                            email=email,
                            name=payload.name,
                            active=False,
                            totp_last_step=-1,
                            created_at=db.now(),
                        )
                    )
                    await session.execute(
                        db.invitations.insert().values(
                            id=invitation_id,
                            account_id=account_id,
                            token_hash=digest(token),
                            expires_at=(datetime.now(UTC) + timedelta(hours=24)).isoformat(),
                            used=False,
                            created_by=account_id,
                        )
                    )
                    await session.execute(
                        db.outbox.insert().values(
                            id=db.uid(),
                            event_type="account.invitation",
                            resource_id=account_id,
                            payload={
                                "invitation_id": invitation_id,
                                "token_ciphertext": box.encrypt(token),
                                "purpose": "PERSONAL_ENROLMENT",
                            },
                            created_at=db.now(),
                            attempts=0,
                        )
                    )
        except IntegrityError:
            account_id = None
        if account_id and cfg.production:
            from ..operations import deliver_invitations

            await deliver_invitations(database, cfg, box, account_id=account_id, limit=1)
        return {
            "status": "VERIFICATION_REQUEST_RECEIVED",
            "message": "If eligible, a verification email has been queued. Existing accounts can sign in or use account recovery.",
        }

    @router.get("/context")
    async def context(request: Request, after: str = ""):
        async with database.transaction() as session:
            service = await service_for(session, request)
            rows, cursor = await page(
                session,
                select(t.links).where(t.links.c.account_id == service.actor["id"]),
                after,
                t.links.c.created_at,
                t.links.c.id,
                size=50,
            )
            pref = (
                (
                    await session.execute(
                        select(t.preferences).where(
                            t.preferences.c.account_id == service.actor["id"]
                        )
                    )
                )
                .mappings()
                .first()
            )
            return {
                "account": service.actor,
                "items": [await service.link_view(row) for row in rows],
                "next_cursor": cursor,
                "preferences": dict(pref) if pref else {"version": 0, "in_app_reminders": False},
                "as_of": db.now(),
            }

    @router.get("/facilities")
    async def facilities(request: Request, query: str = "", after: str = ""):
        async with database.transaction() as session:
            await service_for(session, request)
            rows, cursor = await page(
                session,
                select(db.facilities.c.id, db.facilities.c.name)
                .join(ct.sites, ct.sites.c.facility_id == db.facilities.c.id)
                .where(
                    db.facilities.c.publication_status == "PUBLISHED",
                    ct.sites.c.active.is_(True),
                    ct.sites.c.valid_from <= db.now(),
                    ct.sites.c.valid_until > db.now(),
                    db.facilities.c.name.icontains(query[:160], autoescape=True),
                ),
                after,
                db.facilities.c.name,
                db.facilities.c.id,
            )
            return {"items": [dict(row) for row in rows], "next_cursor": cursor}

    @router.post("/links")
    async def create_link(payload: c.LinkRequest, request: Request):
        return await command(
            request, payload, signed_in, lambda service, body: service.create_link(body)
        )

    @router.post("/links/{identifier}/share")
    async def share(identifier: UUID, payload: c.Share, request: Request):
        async def guard(service, body):
            await service.own_link(identifier, "SHARE")

        return await command(
            request, payload, guard, lambda service, body: service.share(identifier, body)
        )

    @router.post("/links/{identifier}/revoke")
    async def revoke(identifier: UUID, payload: c.Decision, request: Request):
        async def guard(service, body):
            row = await load(service.session, t.links, identifier)
            if row["account_id"] != service.actor["id"]:
                own = (
                    (
                        await service.session.execute(
                            select(t.links).where(
                                t.links.c.account_id == service.actor["id"],
                                t.links.c.patient_id == row["patient_id"],
                                t.links.c.relationship == "SELF",
                                t.links.c.state == "APPROVED",
                            )
                        )
                    )
                    .mappings()
                    .first()
                )
                require(
                    own and row["relationship"] == "REPRESENTATIVE",
                    "NOT_FOUND_OR_NOT_PERMITTED",
                    "Permission unavailable",
                    404,
                )
                await service.current_link(own, "SHARE")

        return await command(
            request, payload, guard, lambda service, body: service.revoke_link(identifier, body)
        )

    @router.get("/links/{identifier}/representatives")
    async def representatives(identifier: UUID, request: Request, after: str = ""):
        async with database.transaction() as session:
            service = await service_for(session, request)
            link = await service.own_link(identifier, "SHARE")
            require(link["relationship"] == "SELF")
            rows, cursor = await page(
                session,
                select(
                    t.links.c.id,
                    t.links.c.state,
                    t.links.c.version,
                    t.links.c.created_at,
                    t.links.c.permissions,
                    t.links.c.valid_until,
                    db.accounts.c.name,
                )
                .join(db.accounts, db.accounts.c.id == t.links.c.account_id)
                .where(
                    t.links.c.patient_id == link["patient_id"],
                    t.links.c.relationship == "REPRESENTATIVE",
                ),
                after,
                t.links.c.created_at,
                t.links.c.id,
            )
            return {"items": [dict(row) for row in rows], "next_cursor": cursor}

    @router.get("/links/{identifier}/care")
    async def care(identifier: UUID, request: Request, after: str = ""):
        async with database.transaction() as session:
            service = await service_for(session, request)
            link = await service.own_link(identifier, "READ")
            blocked = await service.source_blocks(link["facility_id"], link["patient_id"])
            query = (
                select(t.releases, ct.records.c.status.label("source_status"))
                .join(ct.records, ct.records.c.id == t.releases.c.source_id)
                .outerjoin(t.withdrawals, t.withdrawals.c.release_id == t.releases.c.id)
                .where(
                    t.releases.c.link_id == link["id"],
                    t.withdrawals.c.id.is_(None),
                    ct.records.c.facility_id == link["facility_id"],
                    ct.records.c.patient_id == link["patient_id"],
                    ct.records.c.version == t.releases.c.source_version,
                    ct.records.c.confidentiality == "STANDARD",
                )
            )
            if blocked:
                query = query.where(t.releases.c.source_id.not_in(blocked))
            permitted_states = or_(
                *(
                    (t.releases.c.kind == kind)
                    & (ct.records.c.kind == source_kind)
                    & ct.records.c.status.in_(states)
                    for kind, sources in SOURCE_STATES.items()
                    for source_kind, states in sources.items()
                )
            )
            rows, cursor = await page(
                session,
                query.where(permitted_states),
                after,
                t.releases.c.created_at,
                t.releases.c.id,
                size=25,
            )
            await service.audit("personal.released_care_read", link["id"])
            return {
                "items": [
                    {
                        k: row[k]
                        for k in (
                            "id",
                            "kind",
                            "source_id",
                            "source_version",
                            "source_status",
                            "created_at",
                            "due_at",
                        )
                    }
                    | {
                        "title": service.data(row)["title"],
                        "text": service.data(row)["readable_text"],
                        "source": "HUMAN_REVIEWED_RELEASE",
                    }
                    for row in rows
                ],
                "next_cursor": cursor,
                "as_of": db.now(),
                "subject": await service.link_view(link),
            }

    @router.get("/links/{identifier}/services")
    async def services(identifier: UUID, request: Request, after: str = ""):
        from ..domain import RuleError

        async with database.transaction() as session:
            service = await service_for(session, request)
            link = await service.own_link(identifier, "REQUEST")
            rows, cursor = await page(
                session,
                select(t.services).where(
                    t.services.c.facility_id == link["facility_id"],
                    t.services.c.active.is_(True),
                    t.services.c.valid_until > db.now(),
                    t.services.c.primary_accepted.is_(True),
                    t.services.c.fallback_accepted.is_(True),
                ),
                after,
                t.services.c.name,
                t.services.c.id,
                size=50,
            )
            items = []
            for row in rows:
                try:
                    await service.service_current(row)
                    items.append(
                        {k: row[k] for k in ("id", "name", "response_minutes", "valid_until")}
                    )
                except RuleError:
                    continue
            return {"items": items, "next_cursor": cursor}

    @router.get("/links/{identifier}/requests")
    async def requests(identifier: UUID, request: Request, after: str = ""):
        async with database.transaction() as session:
            service = await service_for(session, request)
            link = await service.own_link(identifier, "REQUEST")
            rows, cursor = await page(
                session,
                select(t.requests).where(
                    t.requests.c.link_id == link["id"],
                    t.requests.c.created_by == service.actor["id"],
                ),
                after,
                t.requests.c.due_at,
                t.requests.c.id,
                size=50,
            )
            return {
                "items": [await service.request_view(row) for row in rows],
                "next_cursor": cursor,
                "as_of": db.now(),
            }

    @router.post("/links/{identifier}/requests")
    async def request_care(identifier: UUID, payload: c.CareRequest, request: Request):
        async def guard(service, body):
            await service.own_link(identifier, "REQUEST")

        return await command(
            request, payload, guard, lambda service, body: service.create_request(identifier, body)
        )

    @router.get("/requests/{identifier}")
    async def request_detail(identifier: UUID, request: Request, after: str = ""):
        async with database.transaction() as session:
            service = await service_for(session, request)
            row = await load(session, t.requests, identifier)
            await service.own_link(row["link_id"], "REQUEST")
            require(
                row["created_by"] == service.actor["id"],
                "NOT_FOUND_OR_NOT_PERMITTED",
                "Request unavailable",
                404,
            )
            return await conversation(service, row, after)

    async def conversation(service, row, after):
        rows, cursor = await page(
            service.session,
            select(t.messages).where(t.messages.c.request_id == row["id"]),
            after,
            t.messages.c.created_at,
            t.messages.c.id,
            size=50,
        )
        await service.audit("personal.conversation_read", row["link_id"])
        return {
            "request": await service.request_view(row),
            "items": [
                {k: r[k] for k in ("id", "sender_type", "created_at")}
                | {"text": service.data(r)["text"]}
                for r in rows
            ],
            "next_cursor": cursor,
        }

    @router.post("/requests/{identifier}/reply")
    async def reply(identifier: UUID, payload: c.Reply, request: Request):
        async def guard(service, body):
            row = await load(service.session, t.requests, identifier)
            await service.own_link(row["link_id"], "REQUEST")
            require(row["created_by"] == service.actor["id"])

        return await command(
            request, payload, guard, lambda service, body: service.reply(identifier, body)
        )

    @router.get("/links/{identifier}/access-history")
    async def history(identifier: UUID, request: Request, after: str = ""):
        async with database.transaction() as session:
            service = await service_for(session, request)
            link = await service.own_link(identifier)
            rows, cursor = await page(
                session,
                select(
                    t.audit.c.id, t.audit.c.action, t.audit.c.outcome, t.audit.c.created_at
                ).where(t.audit.c.link_id == link["id"]),
                after,
                t.audit.c.created_at,
                t.audit.c.id,
            )
            return {"items": [dict(row) for row in rows], "next_cursor": cursor}

    @router.post("/preferences")
    async def preferences(payload: c.Preferences, request: Request):
        async def apply(service, body):
            row = (
                (
                    await service.session.execute(
                        select(t.preferences).where(
                            t.preferences.c.account_id == service.actor["id"]
                        )
                    )
                )
                .mappings()
                .first()
            )
            if row:
                current = await service.change(
                    t.preferences,
                    dict(row),
                    {"in_app_reminders": body["in_app_reminders"]},
                    body["expected_version"],
                    "personal.preferences_changed",
                    body,
                )
            else:
                require(
                    body["expected_version"] == 0, "VERSION_CONFLICT", "Refresh preferences", 412
                )
                current = {
                    "id": db.uid(),
                    "account_id": service.actor["id"],
                    "version": 1,
                    "in_app_reminders": body["in_app_reminders"],
                }
                await service.session.execute(t.preferences.insert().values(**current))
                await service.event(t.preferences, current, "personal.preferences_changed", body)
            return current

        return await command(request, payload, signed_in, apply)

    @router.get("/staff/{facility}/links")
    async def staff_links(facility: UUID, request: Request, after: str = ""):
        async with database.transaction() as session:
            service = await service_for(session, request)
            await service.staff(str(facility))
            rows, cursor = await page(
                session,
                select(t.links).where(t.links.c.facility_id == str(facility)),
                after,
                t.links.c.created_at,
                t.links.c.id,
                size=50,
            )
            await service.audit("personal.identity_queue_read")
            return {
                "items": [await service.link_view(row, staff=True) for row in rows],
                "next_cursor": cursor,
            }

    @router.post("/staff/{facility}/patient-search")
    async def patient_search(facility: UUID, payload: c.Search, request: Request):
        async with database.transaction() as session:
            service = await service_for(session, request)
            await service.staff(str(facility))
            tokens = cs.search_tokens(cfg, payload.query)
            require(tokens, "VALIDATION_FAILED", "Supply a searchable identity reference", 422)
            query = select(ct.records).where(
                ct.records.c.facility_id == str(facility),
                ct.records.c.kind == "patient",
                ct.records.c.id > payload.after,
            )
            if database.postgres:
                from sqlalchemy.dialects.postgresql import JSONB

                query = query.where(ct.records.c.search_tokens.cast(JSONB).contains(tokens))
            rows = list(
                (await session.execute(query.order_by(ct.records.c.id).limit(201))).mappings()
            )
            items = []
            for row in rows[:200]:
                if set(tokens).issubset(row["search_tokens"] or []):
                    data = cs.opened(box, row)["data"]
                    items.append(
                        {
                            "id": row["id"],
                            "version": row["version"],
                            "status": row["status"],
                            "name": data["display_name"],
                            "local_identifier": data["local_identifier"],
                        }
                    )
            await service.audit("personal.identity_candidates_read")
            return {"items": items, "next_cursor": rows[199]["id"] if len(rows) > 200 else None}

    @router.post("/staff/links/{identifier}/review")
    async def review(identifier: UUID, payload: c.LinkReview, request: Request):
        async def guard(service, body):
            row = await load(service.session, t.links, identifier)
            await service.staff(row["facility_id"], write=True)
            require(service.actor["id"] not in {row["account_id"], row["submitted_by"]})

        return await command(
            request, payload, guard, lambda service, body: service.review_link(identifier, body)
        )

    @router.post("/staff/links/{identifier}/revoke")
    async def staff_revoke(identifier: UUID, payload: c.Decision, request: Request):
        async def guard(service, body):
            row = await load(service.session, t.links, identifier)
            await service.staff(row["facility_id"], write=True)

        return await command(
            request,
            payload,
            guard,
            lambda service, body: service.revoke_link(identifier, body, staff=True),
        )

    @router.get("/staff/{facility}/subjects")
    async def subjects(facility: UUID, request: Request, patient_id: UUID, after: str = ""):
        async with database.transaction() as session:
            service = await service_for(session, request)
            await service.staff(str(facility), "CARE", patient=str(patient_id))
            rows, cursor = await page(
                session,
                select(t.links).where(
                    t.links.c.facility_id == str(facility),
                    t.links.c.patient_id == str(patient_id),
                    t.links.c.state == "APPROVED",
                ),
                after,
                t.links.c.created_at,
                t.links.c.id,
            )
            await service.audit("personal.release_recipients_read")
            return {"items": [await service.link_view(r) for r in rows], "next_cursor": cursor}

    @router.post("/staff/links/{identifier}/releases")
    async def release(identifier: UUID, payload: c.Release, request: Request):
        async def guard(service, body):
            row = await load(service.session, t.links, identifier)
            await service.staff(row["facility_id"], "CARE", patient=row["patient_id"], write=True)
            await service.current_link(row, "READ")

        return await command(
            request, payload, guard, lambda service, body: service.release(identifier, body)
        )

    @router.post("/staff/releases/{identifier}/withdraw")
    async def withdraw(identifier: UUID, payload: c.Withdrawal, request: Request):
        async def guard(service, body):
            release = await load(service.session, t.releases, identifier)
            link = await load(service.session, t.links, release["link_id"])
            await service.staff(link["facility_id"], "CARE", patient=link["patient_id"], write=True)

        return await command(
            request, payload, guard, lambda service, body: service.withdraw(identifier, body)
        )

    @router.get("/staff/{facility}/services")
    async def staff_services(facility: UUID, request: Request, after: str = ""):
        async with database.transaction() as session:
            service = await service_for(session, request)
            if not governor(service.actor, str(facility)):
                await cs.guard(
                    session, cfg, service.actor, str(facility), "CARE", relationship=False
                )
            rows, cursor = await page(
                session,
                select(t.services).where(t.services.c.facility_id == str(facility)),
                after,
                t.services.c.name,
                t.services.c.id,
            )
            return {
                "items": [
                    {k: v for k, v in r.items() if not k.endswith("ciphertext")} for r in rows
                ],
                "next_cursor": cursor,
            }

    @router.post("/staff/{facility}/services")
    async def create_service(facility: UUID, payload: c.Service, request: Request):
        async def guard(service, body):
            require(governor(service.actor, str(facility)))

        return await command(
            request,
            payload,
            guard,
            lambda service, body: service.create_service(body | {"facility_id": str(facility)}),
        )

    @router.post("/staff/services/{identifier}/actions")
    async def service_action(identifier: UUID, payload: c.ServiceAction, request: Request):
        async def guard(service, body):
            row = await load(service.session, t.services, identifier)
            require(
                governor(service.actor, row["facility_id"])
                or service.actor["id"] in {row["primary_id"], row["fallback_id"]}
            )
            if body["action"] == "ACCEPT_DUTY":
                await cs.privilege_for(
                    service.session, service.actor["id"], row["facility_id"], "CARE"
                )

        return await command(
            request, payload, guard, lambda service, body: service.service_action(identifier, body)
        )

    @router.get("/staff/{facility}/requests")
    async def staff_requests(facility: UUID, request: Request, after: str = ""):
        async with database.transaction() as session:
            service = await service_for(session, request)
            await cs.guard(session, cfg, service.actor, str(facility), "CARE", relationship=False)
            rows, cursor = await page(
                session,
                select(t.requests).where(
                    t.requests.c.facility_id == str(facility),
                    or_(
                        t.requests.c.owner_id == service.actor["id"],
                        t.requests.c.fallback_id == service.actor["id"],
                        t.requests.c.handover_to == service.actor["id"],
                    ),
                ),
                after,
                t.requests.c.due_at,
                t.requests.c.id,
                size=50,
            )
            return {"items": [await service.request_view(r) for r in rows], "next_cursor": cursor}

    @router.get("/staff/requests/{identifier}")
    async def staff_detail(identifier: UUID, request: Request, after: str = ""):
        async with database.transaction() as session:
            service = await service_for(session, request)
            row = await service.owned_request(identifier)
            return await conversation(service, row, after)

    @router.post("/staff/requests/{identifier}/actions")
    async def staff_action(identifier: UUID, payload: c.RequestAction, request: Request):
        async def guard(service, body):
            await service.owned_request(identifier)

        return await command(
            request, payload, guard, lambda service, body: service.request_action(identifier, body)
        )

    app.include_router(router)
