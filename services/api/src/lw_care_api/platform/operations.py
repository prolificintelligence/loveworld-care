"""Real invitation delivery and release administration; no development token endpoints."""

import secrets
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select, update

from . import db
from .domain import record_audit, require
from .security import digest


async def create_invitation(session, cfg, box, payload, grantor, correlation_id):
    require(
        cfg.resend_api_key and cfg.email_from,
        "AUTHORITY_UNAVAILABLE",
        "Email delivery is not configured",
        503,
    )
    require(
        payload.valid_until.tzinfo is not None and payload.valid_until > datetime.now(UTC),
        "VALIDATION_FAILED",
        "The grant must have a future expiry with time zone",
        422,
    )
    if payload.role in (
        "PLATFORM_ADMIN",
        "STANDARDS_DECIDER",
        "DATA_GOVERNOR",
        "IDENTITY_REVIEWER",
        "POLICY_OWNER",
    ):
        require(
            payload.scope_type == "GLOBAL",
            "VALIDATION_FAILED",
            "This role requires central scope",
            422,
        )
    if payload.role == "CLINICAL_STAFF":
        require(
            payload.scope_type == "FACILITY",
            "VALIDATION_FAILED",
            "Clinical staff invitations require a facility scope",
            422,
        )
    if payload.role == "CLINICAL_GOVERNOR":
        require(
            payload.scope_type in {"GLOBAL", "FACILITY"},
            "VALIDATION_FAILED",
            "Clinical governance requires global or facility scope",
            422,
        )
    if payload.scope_type != "GLOBAL":
        require(
            payload.scope_id is not None,
            "VALIDATION_FAILED",
            "Select the actual resource scope",
            422,
        )
        table = db.facilities if payload.scope_type == "FACILITY" else db.units
        row = (
            (await session.execute(select(table).where(table.c.id == str(payload.scope_id))))
            .mappings()
            .first()
        )
        require(
            row and (payload.scope_type == "FACILITY" or row["kind"] == payload.scope_type),
            "VALIDATION_FAILED",
            "The selected scope does not exist or has the wrong type",
            422,
        )
    account = (
        (await session.execute(select(db.accounts).where(db.accounts.c.email == payload.email)))
        .mappings()
        .first()
    )
    if account:
        account_id = account["id"]
        require(
            account_id != grantor,
            "ACCESS_DENIED",
            "Another administrator must grant additional authority to you",
        )
    else:
        account_id = db.uid()
        await session.execute(
            db.accounts.insert().values(
                id=account_id,
                email=payload.email,
                name=payload.name,
                active=False,
                created_at=db.now(),
                totp_last_step=-1,
            )
        )
    await session.execute(
        db.grants.insert().values(
            id=db.uid(),
            account_id=account_id,
            role=payload.role,
            scope_type=payload.scope_type,
            scope_id=str(payload.scope_id) if payload.scope_id else "GLOBAL",
            valid_from=db.now(),
            valid_until=payload.valid_until.isoformat(),
            revoked=False,
            grantor=grantor,
        )
    )
    if account and account["active"]:
        await record_audit(session, grantor, "grant.created", account_id, "SUCCESS", correlation_id)
        return {"account_id": account_id, "status": "GRANT_ACTIVE"}
    # Supersede earlier enrolment invitations for an inactive account.
    await session.execute(
        update(db.invitations)
        .where(db.invitations.c.account_id == account_id, db.invitations.c.used.is_(False))
        .values(used=True)
    )
    raw = secrets.token_urlsafe(48)
    invitation_id = db.uid()
    await session.execute(
        db.invitations.insert().values(
            id=invitation_id,
            account_id=account_id,
            token_hash=digest(raw),
            expires_at=(datetime.now(UTC) + timedelta(hours=24)).isoformat(),
            used=False,
            created_by=grantor,
        )
    )
    await session.execute(
        db.outbox.insert().values(
            id=db.uid(),
            event_type="account.invitation",
            resource_id=account_id,
            payload={"invitation_id": invitation_id, "token_ciphertext": box.encrypt(raw)},
            created_at=db.now(),
            attempts=0,
        )
    )
    await record_audit(session, grantor, "account.invited", account_id, "SUCCESS", correlation_id)
    return {"account_id": account_id, "status": "INVITATION_QUEUED", "expires_in_hours": 24}


async def deliver_invitations(database, cfg, box, *, limit=2, timeout=20, account_id=None):
    require(
        cfg.resend_api_key and cfg.email_from,
        "AUTHORITY_UNAVAILABLE",
        "Email delivery is not configured",
        503,
    )
    sent, failed = 0, 0
    async with database.transaction() as session:
        items = [
            dict(r)
            for r in (
                await session.execute(
                    select(db.outbox)
                    .where(
                        db.outbox.c.event_type == "account.invitation",
                        db.outbox.c.delivered_at.is_(None),
                        db.outbox.c.attempts < 20,
                        db.outbox.c.resource_id == account_id if account_id else True,
                    )
                    .order_by(db.outbox.c.created_at)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            ).mappings()
        ]
        async with httpx.AsyncClient(timeout=timeout) as client:
            for item in items:
                account = (
                    (
                        await session.execute(
                            select(db.accounts).where(db.accounts.c.id == item["resource_id"])
                        )
                    )
                    .mappings()
                    .one()
                )
                invitation = (
                    (
                        await session.execute(
                            select(db.invitations).where(
                                db.invitations.c.id == item["payload"]["invitation_id"]
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                if invitation["used"] or invitation["expires_at"] <= db.now():
                    await session.execute(
                        update(db.outbox)
                        .where(db.outbox.c.id == item["id"])
                        .values(
                            delivered_at=db.now(),
                            provider_receipt="EXPIRED_OR_SUPERSEDED",
                            payload={"invitation_id": invitation["id"]},
                        )
                    )
                    continue
                url = (
                    cfg.web_origin.rstrip("/")
                    + ("/activate?next=my-health#" if item["payload"].get("purpose") == "PERSONAL_ENROLMENT" else "/activate#")
                    + box.decrypt(item["payload"]["token_ciphertext"])
                )
                try:
                    response = await client.post(
                        "https://api.resend.com/emails",
                        headers={
                            "Authorization": "Bearer " + cfg.resend_api_key,
                            "Idempotency-Key": item["id"],
                        },
                        json={
                            "from": cfg.email_from,
                            "to": [account["email"]],
                            "subject": "Your LW Health Intelligence Platform account invitation",
                            "text": f"Hello {account['name']},\n\nYou have been invited to LW Health Intelligence Platform. "
                            f"Set your password and register your authenticator using this private link:\n\n{url}\n\n"
                            "This link expires in 24 hours. Do not forward it. If you did not expect this invitation, "
                            "contact your care team or account administrator.\n",
                        },
                    )
                    receipt = (
                        response.json().get("id") if response.status_code in (200, 201) else None
                    )
                except (httpx.HTTPError, ValueError):
                    receipt = None
                values = {"attempts": item["attempts"] + 1}
                if receipt:
                    values.update(
                        delivered_at=db.now(),
                        provider_receipt=receipt,
                        payload={"invitation_id": invitation["id"]},
                    )
                    sent += 1
                else:
                    failed += 1
                await session.execute(
                    update(db.outbox).where(db.outbox.c.id == item["id"]).values(**values)
                )
    return {"provider_accepted": sent, "retry_pending": failed}
