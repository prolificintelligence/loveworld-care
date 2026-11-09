"""Aggregate operating evidence, kept separate from clinical fulfilment and approval."""

import asyncio
import json

from sqlalchemy import func, or_, select

from .. import db
from ..clinical import tables as clinical
from ..domain import RuleError, require
from . import tables as t
from .service import ControlService, has


async def observe(session):
    """Count actual exceptions; never return patient, source, amount or contact identifiers."""

    async def count(table, *conditions):
        return await session.scalar(select(func.count()).select_from(table).where(*conditions))

    unbalanced = (
        select(clinical.ledger.c.source_id, clinical.ledger.c.currency)
        .group_by(clinical.ledger.c.source_id, clinical.ledger.c.currency)
        .having(or_(func.sum(clinical.ledger.c.amount_minor) != 0, func.count() < 2))
        .subquery()
    )
    movements = (
        select(
            clinical.movements.c.lot_id, func.sum(clinical.movements.c.quantity).label("quantity")
        )
        .group_by(clinical.movements.c.lot_id)
        .subquery()
    )
    stock = clinical.lots.outerjoin(movements, movements.c.lot_id == clinical.lots.c.id)
    indexes = t.obligations.outerjoin(
        clinical.records, clinical.records.c.id == t.obligations.c.source_id
    )
    checks = {
        "unbalanced_ledger_groups": await count(unbalanced),
        "stock_movement_mismatches": await count(
            stock, clinical.lots.c.quantity != func.coalesce(movements.c.quantity, 0)
        ),
        "negative_stock_lots": await count(clinical.lots, clinical.lots.c.quantity < 0),
        "stale_task_indexes": await count(
            indexes,
            or_(
                clinical.records.c.id.is_(None),
                clinical.records.c.version != t.obligations.c.source_version,
            ),
        ),
        "missing_task_indexes": await count(
            clinical.records.outerjoin(
                t.obligations, clinical.records.c.id == t.obligations.c.source_id
            ),
            clinical.records.c.kind == "task",
            t.obligations.c.source_id.is_(None),
        ),
        "unowned_active_alerts": await count(
            t.alerts,
            t.alerts.c.owner_id.is_(None),
            t.alerts.c.fallback_id.is_(None),
            t.alerts.c.source_resolved_at.is_(None),
            t.alerts.c.superseded_at.is_(None),
        ),
        "delivery_reconciliation_required": await count(
            t.jobs, t.jobs.c.state.in_(["DEAD", "RECONCILIATION_REQUIRED"])
        ),
        "expired_job_leases": await count(
            t.jobs, t.jobs.c.state == "RUNNING", t.jobs.c.lease_until < db.now()
        ),
        "incomplete_staff_handovers": await count(
            t.handover_items, t.handover_items.c.state != "ACCEPTED"
        ),
    }
    context = {
        "clinical_records": await count(clinical.records),
        "stock_lots": await count(clinical.lots),
        "ledger_entries": await count(clinical.ledger),
        "unprocessed_jobs": await count(t.jobs, t.jobs.c.state.in_(["READY", "RETRY", "RUNNING"])),
        "open_indexed_tasks": await count(t.obligations, t.obligations.c.is_open.is_(True)),
    }
    version = await session.scalar(select(func.max(db.schema_versions.c.version)))
    if version and version >= 7:
        from ..clinical.flow_index import index

        checks["clinical_work_projection_mismatches"] = await count(
            clinical.records.outerjoin(index, clinical.records.c.id == index.c.record_id),
            or_(
                index.c.record_id.is_(None),
                index.c.indexed_version != clinical.records.c.version,
                index.c.facility_id != clinical.records.c.facility_id,
                index.c.kind != clinical.records.c.kind,
                index.c.status != clinical.records.c.status,
            ),
        )
    if version and version >= 8:
        from ..personal import tables as personal
        checks["personal_requests_with_inactive_owner"] = await count(
            personal.requests.join(db.accounts, db.accounts.c.id == personal.requests.c.owner_id),
            personal.requests.c.state != "CLOSED", db.accounts.c.active.is_(False))
        context["open_personal_requests"] = await count(personal.requests, personal.requests.c.state != "CLOSED")
    return {
        "checks": checks,
        "population": context,
        "integrity_outcome": "EXCEPTIONS"
        if any(checks.values())
        else "NO_EXCEPTIONS_IN_EXECUTED_CHECKS",
        "clinical_fulfilment_inferred": False,
        "service_approval_inferred": False,
        "scope": "CENTRAL_DATABASE_AGGREGATE",
        "as_of": db.now(),
        "observation_consistency": "PER_STATEMENT_NOT_SIMULTANEOUS_FULL_AUDIT",
    }


async def record(
    database,
    box,
    *,
    kind,
    outcome,
    actor_id,
    started_at,
    summary,
    evidence,
    source_id=None,
    identifier=None,
):
    identifier = identifier or db.uid()
    async with database.transaction() as session:
        await session.execute(
            t.assurance_runs.insert().values(
                id=identifier,
                kind=kind,
                outcome=outcome,
                actor_id=actor_id,
                source_id=source_id,
                started_at=started_at,
                completed_at=db.now(),
                summary=summary,
                evidence_ciphertext=box.encrypt(json.dumps(evidence)),
            )
        )
    return identifier


class AssuranceService(ControlService):
    async def reconcile(self, body):
        require(has(self.actor, {"PLATFORM_ADMIN"}))
        if self.session.bind.dialect.name == "postgresql":
            # Stable observations share one statement snapshot per check. This
            # report explicitly does not certify a simultaneous full-ledger audit.
            from sqlalchemy import text

            await self.session.execute(text("SET LOCAL statement_timeout = '8s'"))
        started = db.now()
        try:
            async with asyncio.timeout(20):
                summary = await observe(self.session)
        except TimeoutError as exc:
            raise RuleError(
                "AUTHORITY_UNAVAILABLE",
                "Reconciliation exceeded its time budget; no successful observation was recorded",
                503,
            ) from exc
        identifier = db.uid()
        await self.session.execute(
            t.assurance_runs.insert().values(
                id=identifier,
                kind="RECONCILIATION",
                outcome=summary["integrity_outcome"],
                actor_id=self.actor["id"],
                source_id=None,
                started_at=started,
                completed_at=db.now(),
                summary=summary,
                evidence_ciphertext=self.box.encrypt(body["evidence"]),
            )
        )
        await self.audit("operations.integrity_observed", identifier)
        return {"id": identifier, **summary}


async def status(session, cfg):
    latest = {}
    for kind in ("BACKUP", "RESTORE", "RECONCILIATION"):
        row = (
            (
                await session.execute(
                    select(t.assurance_runs)
                    .where(t.assurance_runs.c.kind == kind)
                    .order_by(t.assurance_runs.c.completed_at.desc(), t.assurance_runs.c.id.desc())
                    .limit(1)
                )
            )
            .mappings()
            .first()
        )
        latest[kind.lower()] = (
            None
            if row is None
            else {
                key: row[key]
                for key in ("id", "source_id", "outcome", "started_at", "completed_at", "summary")
            }
        )
    return {
        "latest": latest,
        "as_of": db.now(),
        "schema_version": await session.scalar(select(func.max(db.schema_versions.c.version))),
        "backup_cadence": "OPERATOR_EXECUTED_NO_AUTOMATIC_BACKUP_CLAIM",
        "recovery_targets": "NOT_ADOPTED",
        "independent_off_account_copy": "NOT_QUALIFIED",
        "offline_care": "CORE_LOCAL_DEPLOYMENT_DEFERRED",
        "scanner_configured": bool(cfg.clamav_host),
        "operating_acceptance": "REQUIRES_NAMED_OWNERS_AND_OBSERVED_DRILLS",
    }
