"""Institutional permissions and atomic command execution (SPEC-003/004/009/010)."""

import hashlib
import json

from sqlalchemy import false, or_, select, text, update

from . import db


class RuleError(Exception):
    def __init__(self, code: str, message: str, status: int = 422):
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


def require(condition, code="ACCESS_DENIED", message="This action is not permitted", status=403):
    if not condition:
        raise RuleError(code, message, status)


def global_role(actor, *roles) -> bool:
    return any(g["role"] in roles and g["scope_type"] == "GLOBAL" for g in actor["grants"])


def scoped(actor, roles, facility) -> bool:
    for grant in actor["grants"]:
        if grant["role"] not in roles:
            continue
        if grant["scope_type"] == "GLOBAL":
            return True
        if grant["scope_type"] == "REGION" and grant["scope_id"] == facility.get("region_id"):
            return True
        if grant["scope_type"] == "ZONE" and grant["scope_id"] == facility["zone_id"]:
            return True
        if grant["scope_type"] == "FACILITY" and grant["scope_id"] == facility["id"]:
            return True
    return False


def visibility(actor):
    rules = []
    roles = {
        "REGISTRY_STEWARD",
        "FACILITY_ADMIN",
        "ZONE_COORDINATOR",
        "REGIONAL_COORDINATOR",
        "STANDARDS_REVIEWER",
        "STANDARDS_DECIDER",
    }
    for grant in actor["grants"]:
        if grant["role"] not in roles:
            continue
        scope = grant["scope_type"]
        if scope == "GLOBAL":
            return True
        if scope == "ZONE":
            rules.append(db.facilities.c.zone_id == grant["scope_id"])
        elif scope == "FACILITY":
            rules.append(db.facilities.c.id == grant["scope_id"])
        elif scope == "REGION":
            rules.append(
                db.facilities.c.zone_id.in_(
                    select(db.units.c.id).where(db.units.c.parent_id == grant["scope_id"])
                )
            )
    # An inspector sees only the explicitly assigned case's site.
    if any(g["role"] == "INSPECTOR" for g in actor["grants"]):
        rules.append(
            db.facilities.c.id.in_(
                select(db.applications.c.facility_id).where(
                    db.applications.c.inspector_id == actor["id"]
                )
            )
        )
    return or_(*rules) if rules else false()


async def facility_for(session, actor, resource_id, *, lock=False):
    query = select(db.facilities).where(
        db.facilities.c.id == resource_id,
        visibility(actor),
    )
    if lock:
        query = query.with_for_update()
    result = (await session.execute(query)).mappings().first()
    require(result is not None, "NOT_FOUND_OR_NOT_PERMITTED", "Resource unavailable", 404)
    facility = dict(result)
    facility["region_id"] = await session.scalar(
        select(db.units.c.parent_id).where(db.units.c.id == facility["zone_id"])
    )
    return facility


async def application_for(session, actor, resource_id, *, lock=False):
    query = select(db.applications).where(db.applications.c.id == resource_id)
    if lock:
        query = query.with_for_update()
    row = (await session.execute(query)).mappings().first()
    require(row is not None, "NOT_FOUND_OR_NOT_PERMITTED", "Resource unavailable", 404)
    return dict(row), await facility_for(session, actor, row["facility_id"], lock=lock)


def expected(record, version):
    require(
        record["version"] == version,
        "VERSION_CONFLICT",
        "This record changed. Reload it and review your saved draft before retrying.",
        412,
    )


def valid_interval(start, end):
    require(
        start.tzinfo is not None and end.tzinfo is not None and start < end,
        "VALIDATION_FAILED",
        "Supply ordered dates with explicit time zones",
        422,
    )


def current_criteria(row):
    return row["valid_from"] <= db.now() < row["valid_until"]


async def record_audit(
    session, actor_id, action, resource_id, outcome, correlation_id, details=None
):
    await session.execute(
        db.audit.insert().values(
            id=db.uid(),
            actor_id=actor_id,
            action=action,
            resource_id=resource_id,
            outcome=outcome,
            correlation_id=correlation_id,
            purpose="INSTITUTIONAL_OPERATIONS",
            recorded_at=db.now(),
            details=details,
        )
    )


async def record_change(session, actor, resource_type, row, action, correlation_id, details=None):
    event_contracts = {
        "facility.verified": ("LWH-EVT-002", "network.facility_verified"),
        "application.submitted": ("LWH-EVT-003", "standards.application_submitted"),
        "application.resubmitted": ("LWH-EVT-003", "standards.application_submitted"),
        "application.correction_requested": ("LWH-EXT-APPLICATION-001", "standards.application_correction_requested"),
        "application.withdrawn": ("LWH-EXT-APPLICATION-001", "standards.application_withdrawn"),
        "affiliation.decided": ("LWH-EVT-005", "standards.decision_recorded"),
    }
    contract = event_contracts.get(action)
    event_payload = {
        "resource_type": resource_type,
        "aggregate_id": row["id"],
        "version": row["version"],
        "schema_version": "1.0.0",
        "authority_node_id": actor["authority_node_id"],
        "correlation_id": correlation_id,
    }
    if contract:
        event_payload["event_contract_id"] = contract[0]
    await session.execute(
        db.revisions.insert().values(
            id=db.uid(),
            resource_id=row["id"],
            resource_type=resource_type,
            version=row["version"],
            payload={
                **row,
                "authority_node_id": actor["authority_node_id"],
                "schema_version": "1.0.0",
            },
            actor_id=actor["id"],
            recorded_at=db.now(),
        )
    )
    await record_audit(session, actor["id"], action, row["id"], "SUCCESS", correlation_id, details)
    await session.execute(
        db.outbox.insert().values(
            id=db.uid(),
            event_type=contract[1] if contract else action,
            resource_id=row["id"],
            payload=event_payload,
            created_at=db.now(),
            attempts=0,
        )
    )


async def amend(session, table, record, changes):
    values = {**changes, "version": record["version"] + 1}
    result = await session.execute(
        update(table)
        .where(
            table.c.id == record["id"],
            table.c.version == record["version"],
        )
        .values(**values)
    )
    require(result.rowcount == 1, "VERSION_CONFLICT", "The record changed; reload and review", 412)
    return {**record, **values}


async def idempotent(session, actor, operation, key, payload, callback, postgres, replay_guard):
    require(
        key and 8 <= len(key) <= 160,
        "VALIDATION_FAILED",
        "An Idempotency-Key of 8 to 160 characters is required",
        422,
    )
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    request_hash = hashlib.sha256(canonical.encode()).hexdigest()
    if postgres:
        lock_hash = hashlib.sha256(f"{actor['id']}:{operation}:{key}".encode()).digest()[:8]
        await session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": int.from_bytes(lock_hash, signed=True)},
        )
    previous = (
        (
            await session.execute(
                select(db.operations).where(
                    db.operations.c.actor_id == actor["id"],
                    db.operations.c.operation == operation,
                    db.operations.c.key == key,
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
            "This operation key was already used for different content",
            409,
        )
        await replay_guard(previous["response"])
        return previous["response"]
    response = await callback()
    await session.execute(
        db.operations.insert().values(
            id=db.uid(),
            actor_id=actor["id"],
            operation=operation,
            key=key,
            request_hash=request_hash,
            response=response,
        )
    )
    return response


def public_profile(row):
    """Explicit allow-list; evidence and private contacts never enter directory projections."""
    return {
        k: row[k]
        for k in (
            "id",
            "name",
            "site_type",
            "ownership",
            "jurisdiction",
            "address",
            "public_contact",
            "services",
            "affiliation_status",
            "affiliation_scope",
            "conditions",
            "affiliation_expires_at",
            "capability_status",
            "readiness_status",
            "updated_at",
        )
    }


def publication_eligible(row):
    return (
        row["identity_status"] == "VERIFIED"
        and row["affiliation_status"] in ("ACTIVE", "CONDITIONAL")
        and bool(row["affiliation_expires_at"])
        and row["affiliation_expires_at"] > db.now()
    )
