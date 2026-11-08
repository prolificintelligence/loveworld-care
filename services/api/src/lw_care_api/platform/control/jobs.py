"""Lease-based durable work, actual provider receipts and clinical obligation reconciliation."""

import hashlib
import json
import secrets
import time
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import func, or_, select, update

from .. import db
from ..clinical import tables as clinical
from ..clinical.store import privilege_for
from ..domain import RuleError, require
from . import tables as t
from .service import ControlService, canonical, later, load


async def enqueue(session, box, kind, effect_key, payload, *, owner_id=None, facility_id=None):
    existing = await session.scalar(select(t.jobs.c.id).where(t.jobs.c.effect_key == effect_key))
    if existing:
        return existing
    identifier = db.uid()
    await session.execute(
        t.jobs.insert().values(
            id=identifier,
            kind=kind,
            effect_key=effect_key,
            state="READY",
            owner_id=owner_id,
            facility_id=facility_id,
            payload_ciphertext=box.encrypt(canonical(payload)),
            attempts=0,
            dispatch_generation=0,
            next_attempt_at=db.now(),
            lease_until=None,
            lease_token_hash=None,
            first_attempt_at=None,
            provider_receipt=None,
            last_outcome=None,
            created_at=db.now(),
            updated_at=db.now(),
        )
    )
    return identifier


async def eligible(session, account_id, facility_id, service):
    if not account_id:
        return False
    try:
        await privilege_for(session, account_id, facility_id, "CARE", service)
    except RuleError as exc:
        if exc.code not in {"ACCESS_DENIED", "CLINICAL_PRIVILEGE_REQUIRED"}:
            raise
        return False
    return True


async def index_task(session, row, data):
    version = session.info.get("platform_schema_version")
    if version is None:
        version = await session.scalar(select(func.max(db.schema_versions.c.version)))
    if not version or version < 4:
        return
    current = (
        (
            await session.execute(
                select(t.obligations)
                .where(t.obligations.c.source_id == row["id"])
                .with_for_update()
            )
        )
        .mappings()
        .first()
    )
    values = {
        "facility_id": row["facility_id"],
        "source_version": row["version"],
        "owner_id": data.get("owner_id"),
        "due_at": data["due_at"],
        "is_open": row["status"] != "COMPLETED",
    }
    if current:
        if current["source_version"] < row["version"]:
            await session.execute(
                update(t.obligations)
                .where(
                    t.obligations.c.source_id == row["id"],
                    t.obligations.c.source_version < row["version"],
                )
                .values(**values)
            )
            await session.execute(
                update(t.alerts)
                .where(
                    t.alerts.c.source_id == row["id"],
                    t.alerts.c.source_version < row["version"],
                    t.alerts.c.source_resolved_at.is_(None),
                    t.alerts.c.superseded_at.is_(None),
                )
                .values(state="SOURCE_CHANGED", superseded_at=db.now())
            )
    else:
        await session.execute(
            t.obligations.insert().values(source_id=row["id"], alerted_version=0, **values)
        )


async def backfill(session, cfg, box):
    key = "clinical-backfill:" + cfg.authority_node_id
    state = (
        (
            await session.execute(
                select(t.worker_state).where(t.worker_state.c.key == key).with_for_update()
            )
        )
        .mappings()
        .first()
    )
    if state and state["complete"]:
        return True
    rows = list(
        (
            await session.execute(
                select(clinical.records)
                .where(
                    clinical.records.c.kind == "task",
                    clinical.records.c.id > (state["cursor"] if state else ""),
                )
                .order_by(clinical.records.c.id)
                .limit(101)
            )
        ).mappings()
    )
    for row in rows[:100]:
        await index_task(
            session, row, json.loads(box.decrypt(row["content_ciphertext"]))["content"]
        )
    values = {
        "cursor": rows[99]["id"]
        if len(rows) > 100
        else (rows[-1]["id"] if rows else (state["cursor"] if state else "")),
        "complete": len(rows) <= 100,
        "updated_at": db.now(),
    }
    if state:
        await session.execute(
            update(t.worker_state).where(t.worker_state.c.key == key).values(**values)
        )
    else:
        await session.execute(t.worker_state.insert().values(key=key, **values))
    return values["complete"]


async def clinical_reconciliation(session, cfg, box):
    backfill_complete = await backfill(session, cfg, box)
    await session.execute(
        update(t.alerts)
        .where(
            t.alerts.c.source_resolved_at.is_(None),
            t.alerts.c.superseded_at.is_(None),
            t.alerts.c.source_id.in_(
                select(t.obligations.c.source_id).where(t.obligations.c.is_open.is_(False))
            ),
        )
        .values(source_resolved_at=db.now(), state="SOURCE_RESOLVED")
    )
    candidates = (
        await session.execute(
            select(clinical.records)
            .join(t.obligations, t.obligations.c.source_id == clinical.records.c.id)
            .join(clinical.sites, clinical.sites.c.facility_id == clinical.records.c.facility_id)
            .where(
                t.obligations.c.is_open.is_(True),
                t.obligations.c.due_at <= db.now(),
                t.obligations.c.source_version > t.obligations.c.alerted_version,
                clinical.sites.c.authority_node_id == cfg.authority_node_id,
            )
            .order_by(t.obligations.c.due_at, t.obligations.c.source_id)
            .limit(25)
        )
    ).mappings()
    examined, created = 0, 0
    for row in candidates:
        # A current task projection never changes the clinical source here.
        data = json.loads(box.decrypt(row["content_ciphertext"]))["content"]
        if row["status"] == "COMPLETED":
            await session.execute(
                update(t.alerts)
                .where(t.alerts.c.source_id == row["id"], t.alerts.c.source_resolved_at.is_(None))
                .values(source_resolved_at=db.now(), state="SOURCE_RESOLVED")
            )
            continue
        due = data.get("due_at")
        if not due or due > db.now():
            continue
        examined += 1
        previous = await session.scalar(
            select(t.alerts.c.id).where(
                t.alerts.c.source_id == row["id"],
                t.alerts.c.source_version == row["version"],
                t.alerts.c.due_at == due,
            )
        )
        if previous:
            await session.execute(
                update(t.obligations)
                .where(t.obligations.c.source_id == row["id"])
                .values(alerted_version=row["version"])
            )
            continue
        owner = (
            data.get("owner_id")
            if await eligible(session, data.get("owner_id"), row["facility_id"], row["service"])
            else None
        )
        fallback = None
        windows = (
            await session.execute(
                select(t.coverage)
                .where(
                    t.coverage.c.facility_id == row["facility_id"],
                    t.coverage.c.accepted_at.is_not(None),
                    t.coverage.c.valid_from <= db.now(),
                    t.coverage.c.valid_until > db.now(),
                )
                .order_by(t.coverage.c.valid_until)
            )
        ).mappings()
        for window in windows:
            if (
                window["account_id"] != owner
                and row["service"] in window["services"]
                and await eligible(
                    session, window["account_id"], row["facility_id"], row["service"]
                )
            ):
                fallback = window["account_id"]
                break
        identifier = db.uid()
        await session.execute(
            t.alerts.insert().values(
                id=identifier,
                facility_id=row["facility_id"],
                source_id=row["id"],
                source_version=row["version"],
                source_kind="task",
                alert_type="HANDOVER_OVERDUE" if data.get("handover_to") else "CARE_TASK_OVERDUE",
                owner_id=owner,
                fallback_id=fallback,
                state="UNOWNED" if not owner and not fallback else "AWAITING_ACKNOWLEDGEMENT",
                due_at=due,
                acknowledged_at=None,
                acknowledged_by=None,
                source_resolved_at=None,
                superseded_at=None,
                created_at=db.now(),
            )
        )
        for account_id in {owner, fallback} - {None}:
            await enqueue(
                session,
                box,
                "CARE_NOTICE",
                f"alert:{identifier}:{account_id}",
                {"alert_id": identifier, "account_id": account_id},
                owner_id=account_id,
                facility_id=row["facility_id"],
            )
        created += 1
        await session.execute(
            update(t.obligations)
            .where(t.obligations.c.source_id == row["id"])
            .values(alerted_version=row["version"])
        )
    rerouted = await refresh_routes(session, cfg, box)
    return {
        "examined_due_tasks": examined,
        "new_alerts": created,
        "source_tasks_completed": 0,
        "initial_index_backfill_complete": backfill_complete,
        "batch_limit": 25,
        "changed_alert_routes": rerouted,
    }


async def refresh_routes(session, cfg, box, facility_id=None):
    key = "alert-routing:" + (facility_id or cfg.authority_node_id)
    state = (
        (
            await session.execute(
                select(t.worker_state).where(t.worker_state.c.key == key).with_for_update()
            )
        )
        .mappings()
        .first()
    )
    rows = list(
        (
            await session.execute(
                select(t.alerts)
                .where(
                    t.alerts.c.source_resolved_at.is_(None),
                    t.alerts.c.superseded_at.is_(None),
                    t.alerts.c.id > (state["cursor"] if state else ""),
                    t.alerts.c.facility_id == facility_id if facility_id else True,
                )
                .order_by(t.alerts.c.id)
                .limit(26)
                .with_for_update(skip_locked=True)
            )
        ).mappings()
    )
    changed = 0
    for alert in rows[:25]:
        source = await load(session, clinical.records, alert["source_id"])
        if source["version"] != alert["source_version"]:
            continue
        data = json.loads(box.decrypt(source["content_ciphertext"]))["content"]
        owner = (
            data.get("owner_id")
            if await eligible(
                session, data.get("owner_id"), source["facility_id"], source["service"]
            )
            else None
        )
        fallback = None
        windows = (
            await session.execute(
                select(t.coverage)
                .where(
                    t.coverage.c.facility_id == source["facility_id"],
                    t.coverage.c.accepted_at.is_not(None),
                    t.coverage.c.valid_from <= db.now(),
                    t.coverage.c.valid_until > db.now(),
                )
                .order_by(t.coverage.c.valid_until)
            )
        ).mappings()
        for window in windows:
            if (
                window["account_id"] != owner
                and source["service"] in window["services"]
                and await eligible(
                    session, window["account_id"], source["facility_id"], source["service"]
                )
            ):
                fallback = window["account_id"]
                break
        if (owner, fallback) == (alert["owner_id"], alert["fallback_id"]):
            continue
        acknowledged = alert["acknowledged_by"] in ({owner, fallback} - {None})
        version = alert["routing_version"] + 1
        await session.execute(
            update(t.alerts)
            .where(t.alerts.c.id == alert["id"])
            .values(
                owner_id=owner,
                fallback_id=fallback,
                routing_version=version,
                state="ACKNOWLEDGED"
                if acknowledged
                else "AWAITING_ACKNOWLEDGEMENT"
                if owner or fallback
                else "UNOWNED",
                acknowledged_at=alert["acknowledged_at"] if acknowledged else None,
                acknowledged_by=alert["acknowledged_by"] if acknowledged else None,
            )
        )
        if not acknowledged:
            for account_id in {owner, fallback} - {None}:
                await enqueue(
                    session,
                    box,
                    "CARE_NOTICE",
                    f"alert:{alert['id']}:{account_id}:routing:{version}",
                    {"alert_id": alert["id"], "account_id": account_id},
                    owner_id=account_id,
                    facility_id=source["facility_id"],
                )
        await ControlService(session, cfg, box, None, "scheduler").audit(
            "operations.alert_route_reassessed",
            alert["id"],
            details={
                "routing_version": version,
                "has_current_owner": bool(owner),
                "has_accepted_fallback": bool(fallback),
            },
        )
        changed += 1
    values = {
        "cursor": rows[24]["id"] if len(rows) > 25 else "",
        "complete": False,
        "updated_at": db.now(),
    }
    if state:
        await session.execute(
            update(t.worker_state).where(t.worker_state.c.key == key).values(**values)
        )
    else:
        await session.execute(t.worker_state.insert().values(key=key, **values))
    return changed


async def claim(database, identifier=None):
    raw = secrets.token_urlsafe(32)
    async with database.transaction() as session:
        row = (
            (
                await session.execute(
                    select(t.jobs)
                    .where(
                        or_(
                            t.jobs.c.state.in_(["READY", "RETRY"]),
                            (t.jobs.c.state == "RUNNING") & (t.jobs.c.lease_until < db.now()),
                        ),
                        t.jobs.c.next_attempt_at <= db.now(),
                        t.jobs.c.id == identifier if identifier else True,
                    )
                    .order_by(t.jobs.c.next_attempt_at, t.jobs.c.id)
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
            )
            .mappings()
            .first()
        )
        if not row:
            return None
        if (
            row["first_attempt_at"]
            and (
                datetime.now(UTC) - datetime.fromisoformat(row["first_attempt_at"])
            ).total_seconds()
            >= 23 * 3600
        ):
            await session.execute(
                update(t.jobs)
                .where(t.jobs.c.id == row["id"])
                .values(
                    state="RECONCILIATION_REQUIRED",
                    last_outcome="PROVIDER_IDEMPOTENCY_WINDOW_EXCEEDED",
                    lease_until=None,
                    lease_token_hash=None,
                    updated_at=db.now(),
                )
            )
            return None
        attempt = row["attempts"] + 1
        values = {
            "state": "RUNNING",
            "attempts": attempt,
            "lease_until": later(2),
            "lease_token_hash": hashlib.sha256(raw.encode()).hexdigest(),
            "first_attempt_at": row["first_attempt_at"] or db.now(),
            "updated_at": db.now(),
        }
        result = await session.execute(
            update(t.jobs)
            .where(t.jobs.c.id == row["id"], t.jobs.c.attempts == row["attempts"])
            .values(**values)
        )
        if result.rowcount != 1:
            return None
        return dict(row) | values | {"lease_token": raw}


async def dispatch(database, cfg, box, job):
    payload = json.loads(box.decrypt(job["payload_ciphertext"]))
    async with database.transaction() as session:
        account = (
            (
                await session.execute(
                    select(db.accounts).where(
                        db.accounts.c.id == payload["account_id"], db.accounts.c.active.is_(True)
                    )
                )
            )
            .mappings()
            .first()
        )
        if not account:
            return "CANCELLED_AUTHORITY", None
        if job["kind"] == "RECOVERY_EMAIL":
            recovery = await load(session, t.recoveries, payload["recovery_id"])
            if (
                recovery["state"] in {"COMPLETED", "REJECTED", "CANCELLED"}
                or recovery["expires_at"] <= db.now()
            ):
                return "CANCELLED_EXPIRED", None
            subject = "Recover your LW Health Intelligence account"
            message = (
                "Open your account recovery page: "
                + cfg.web_origin
                + "/recover#token="
                + payload["token"]
                + "\nThis link expires. Recovery also requires your authenticator, one saved recovery code, or independent identity review."
            )
        elif job["kind"] == "CARE_NOTICE":
            alert = await load(session, t.alerts, payload["alert_id"])
            if alert["source_resolved_at"] or alert["superseded_at"] or alert["acknowledged_at"]:
                return "CANCELLED_RESOLVED", None
            source = await load(session, clinical.records, alert["source_id"])
            if source["version"] != alert["source_version"]:
                return "CANCELLED_SOURCE_CHANGED", None
            if not await eligible(session, account["id"], alert["facility_id"], source["service"]):
                return "CANCELLED_AUTHORITY", None
            if account["id"] not in {alert["owner_id"], alert["fallback_id"]}:
                return "CANCELLED_AUTHORITY", None
            subject = "A work item needs your review"
            message = (
                "Review your assigned work securely at "
                + cfg.web_origin
                + "/operations\nDelivery of this message does not acknowledge or complete the underlying work."
            )
        else:
            return "DEAD_UNSUPPORTED_JOB", None
        email = account["email"]
    if not cfg.resend_api_key or not cfg.email_from:
        return "RETRY_DEPENDENCY_UNAVAILABLE", None
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10, connect=5), follow_redirects=False
        ) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": "Bearer " + cfg.resend_api_key,
                    "Idempotency-Key": f"lwh-control-{job['id']}-{job['dispatch_generation']}",
                },
                json={"from": cfg.email_from, "to": [email], "subject": subject, "text": message},
            )
    except httpx.HTTPError:
        return "RETRY_PROVIDER_UNKNOWN", None
    if response.is_success:
        try:
            identifier = response.json().get("id")
        except ValueError:
            return "RETRY_PROVIDER_UNKNOWN", None
        return (
            ("PROVIDER_ACCEPTED", identifier)
            if isinstance(identifier, str) and 1 <= len(identifier) <= 160
            else ("RETRY_PROVIDER_UNKNOWN", None)
        )
    if response.status_code in {408, 425, 429} or response.status_code >= 500:
        return "RETRY_HTTP_" + str(response.status_code), None
    return "DEAD_HTTP_" + str(response.status_code), None


async def finish(database, job, outcome, receipt):
    state = (
        "DONE"
        if outcome == "PROVIDER_ACCEPTED"
        else "CANCELLED"
        if outcome.startswith("CANCELLED")
        else "DEAD"
        if outcome.startswith("DEAD") or job["attempts"] >= 8
        else "RETRY"
    )
    delay = min(3600, 30 * (2 ** min(job["attempts"], 7)))
    async with database.transaction() as session:
        result = await session.execute(
            update(t.jobs)
            .where(
                t.jobs.c.id == job["id"],
                t.jobs.c.state == "RUNNING",
                t.jobs.c.lease_token_hash == job["lease_token_hash"],
            )
            .values(
                state=state,
                provider_receipt=receipt,
                last_outcome=outcome,
                lease_until=None,
                lease_token_hash=None,
                next_attempt_at=(datetime.now(UTC) + timedelta(seconds=delay)).isoformat(
                    timespec="microseconds"
                ),
                updated_at=db.now(),
            )
        )
        if result.rowcount != 1:
            return False
        await session.execute(
            t.job_attempts.insert().values(
                id=db.uid(),
                job_id=job["id"],
                attempt=job["attempts"],
                outcome=outcome,
                provider_receipt=receipt,
                created_at=db.now(),
            )
        )
        return True


async def run_tick(database, cfg, box, *, limit=2, seconds=25):
    started = time.monotonic()
    async with database.transaction() as session:
        if database.postgres:
            from sqlalchemy import text

            await session.execute(text("SELECT pg_advisory_xact_lock(782025013)"))
        reconciliation = await clinical_reconciliation(session, cfg, box)
    outcomes = []
    for _ in range(min(limit, 4)):
        if time.monotonic() - started > seconds:
            break
        job = await claim(database)
        if not job:
            break
        outcome, receipt = await dispatch(database, cfg, box, job)
        committed = await finish(database, job, outcome, receipt)
        outcomes.append({"job_id": job["id"], "outcome": outcome, "receipt_recorded": committed})
    return {
        "reconciliation": reconciliation,
        "outcomes": outcomes,
        "delivery_semantics": "PROVIDER_ACCEPTED_IS_NOT_DELIVERED_OR_CLINICAL_ACKNOWLEDGEMENT",
        "scheduler": "DAILY_AUTOMATIC_PLUS_AUTHENTICATED_MANUAL; continuous deployment deferred",
        "as_of": db.now(),
    }


async def deliver_after_commit(database, cfg, box, identifier):
    # FastAPI awaits this ASGI background operation after emitting the response.
    # Durable state exists first; interruption leaves a recoverable leased job.
    if not identifier:
        return
    try:
        job = await claim(database, identifier)
        if job:
            outcome, receipt = await dispatch(database, cfg, box, job)
            await finish(database, job, outcome, receipt)
    except Exception:  # noqa: BLE001 -- preserve queued work; never log recovery tokens or DSNs
        return


class OperationsService(ControlService):
    async def offer_coverage(self, body):
        from .service import has

        require(has(self.actor, {"CLINICAL_GOVERNOR"}, body["facility_id"]))
        require(
            body["valid_until"] > db.now(),
            "VALIDATION_FAILED",
            "Duty coverage must not be expired",
            422,
        )
        for service in body["services"]:
            require(
                await eligible(self.session, body["account_id"], body["facility_id"], service),
                "CLINICAL_PRIVILEGE_REQUIRED",
                "The reviewer requires current facility/service authority",
                422,
            )
        row = {
            "id": db.uid(),
            **{
                key: body[key]
                for key in (
                    "facility_id",
                    "account_id",
                    "services",
                    "valid_from",
                    "valid_until",
                    "adoption_reference",
                )
            },
            "offered_by": self.actor["id"],
            "accepted_at": None,
            "acceptance_ciphertext": None,
        }
        await self.session.execute(t.coverage.insert().values(**row))
        await self.audit("operations.coverage_offered", row["id"])
        return {k: v for k, v in row.items() if not k.endswith("ciphertext")}

    async def accept_coverage(self, identifier, body):
        row = await load(self.session, t.coverage, identifier, lock=True)
        require(
            row["account_id"] == self.actor["id"]
            and not row["accepted_at"]
            and row["valid_until"] > db.now(),
            "NOT_FOUND_OR_NOT_PERMITTED",
            "Current personal duty offer unavailable",
            404,
        )
        for service in row["services"]:
            require(await eligible(self.session, self.actor["id"], row["facility_id"], service))
        await self.session.execute(
            update(t.coverage)
            .where(t.coverage.c.id == identifier)
            .values(accepted_at=db.now(), acceptance_ciphertext=self.box.encrypt(body["evidence"]))
        )
        await self.audit("operations.coverage_accepted", identifier)
        changed = await refresh_routes(self.session, self.cfg, self.box, row["facility_id"])
        return {"id": identifier, "accepted_at": db.now(), "updated_alert_routes": changed}

    async def acknowledge(self, identifier, body):
        row = await load(self.session, t.alerts, identifier, lock=True)
        require(
            self.actor["id"] in {row["owner_id"], row["fallback_id"]},
            "NOT_FOUND_OR_NOT_PERMITTED",
            "Assigned work alert unavailable",
            404,
        )
        source = await load(self.session, clinical.records, row["source_id"])
        require(
            source["version"] == row["source_version"] and not row["superseded_at"],
            "SOURCE_CHANGED",
            "Review the current source responsibility before acknowledging",
            409,
        )
        require(
            await eligible(self.session, self.actor["id"], row["facility_id"], source["service"])
        )
        require(
            not row["acknowledged_at"] and not row["source_resolved_at"],
            "INVALID_STATE",
            "This alert is already acknowledged or resolved",
            409,
        )
        await self.session.execute(
            t.alert_receipts.insert().values(
                id=db.uid(),
                alert_id=identifier,
                actor_id=self.actor["id"],
                evidence_ciphertext=self.box.encrypt(body["evidence"]),
                created_at=db.now(),
            )
        )
        await self.session.execute(
            update(t.alerts)
            .where(t.alerts.c.id == identifier)
            .values(
                acknowledged_at=db.now(), acknowledged_by=self.actor["id"], state="ACKNOWLEDGED"
            )
        )
        await self.audit("operations.alert_acknowledged", identifier)
        return {"id": identifier, "acknowledged_at": db.now(), "clinical_task_completed": False}
