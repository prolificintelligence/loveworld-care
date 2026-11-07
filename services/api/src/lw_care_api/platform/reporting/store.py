"""Purpose/scoped access and atomic, encrypted reporting journals and receipts."""

import hashlib
import json

from sqlalchemy import false, or_, select, text, update

from .. import db
from ..domain import require
from . import tables as t

REPORTERS = {"REPORTING_OFFICER"}
REVIEWERS = {"DATA_REVIEWER"}
ANALYSTS = {"DATA_ANALYST"}
GOVERNORS = {"DATA_GOVERNOR"}
LEADERS = {"EXECUTIVE_VIEWER", "REGIONAL_COORDINATOR", "ZONE_COORDINATOR"}
CASE_REPORTERS = {"SAFETY_REPORTER"}
CASE_REVIEWERS = {"SAFETY_REVIEWER"}
PROGRAMMES = {"PROGRAMME_OWNER"}
ACTION_OWNERS = PROGRAMMES | {
    "FACILITY_ADMIN",
    "ZONE_COORDINATOR",
    "REGIONAL_COORDINATOR",
    "REPORTING_OFFICER",
}
ALL_ROLES = (
    REPORTERS
    | REVIEWERS
    | ANALYSTS
    | GOVERNORS
    | LEADERS
    | CASE_REPORTERS
    | CASE_REVIEWERS
    | PROGRAMMES
    | ACTION_OWNERS
)
SOURCE_READERS = REPORTERS | REVIEWERS | ANALYSTS | GOVERNORS


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def permits(actor, roles, resource):
    for grant in actor["grants"]:
        if grant["role"] not in roles:
            continue
        scope, identifier = grant["scope_type"], grant["scope_id"]
        if scope == "GLOBAL":
            return True
        if resource["scope_type"] == scope and resource["scope_id"] == identifier:
            return True
        if scope == "REGION" and resource.get("region_id") == identifier:
            return True
        if scope == "ZONE" and resource.get("zone_id") == identifier:
            return True
        if scope == "FACILITY" and resource.get("facility_id") == identifier:
            return True
    return False


def require_role(actor, roles, resource):
    require(
        permits(actor, roles, resource),
        "NOT_FOUND_OR_NOT_PERMITTED",
        "Reporting resource unavailable in your assigned purpose and scope",
        404,
    )


def visibility(actor, roles, table):
    clauses = []
    for grant in actor["grants"]:
        if grant["role"] not in roles:
            continue
        if grant["scope_type"] == "GLOBAL":
            return True
        clauses.append(
            (table.c.scope_type == grant["scope_type"]) & (table.c.scope_id == grant["scope_id"])
        )
        if grant["scope_type"] in {"REGION", "ZONE", "FACILITY"}:
            column = {"REGION": "region_id", "ZONE": "zone_id", "FACILITY": "facility_id"}[
                grant["scope_type"]
            ]
            clauses.append(table.c[column] == grant["scope_id"])
    return or_(*clauses) if clauses else false()


async def scope_for(session, scope_type, scope_id):
    result = {
        "scope_type": scope_type,
        "scope_id": str(scope_id) if scope_id else "GLOBAL",
        "region_id": None,
        "zone_id": None,
        "facility_id": None,
        "hierarchy_snapshot": [],
    }
    if scope_type == "GLOBAL":
        require(
            scope_id is None or str(scope_id) == "GLOBAL",
            "VALIDATION_FAILED",
            "Global scope has no unit identifier",
            422,
        )
        return result
    require(scope_id, "VALIDATION_FAILED", "Select an actual reporting unit", 422)
    if scope_type == "FACILITY":
        row = (
            (
                await session.execute(
                    select(db.facilities).where(db.facilities.c.id == str(scope_id))
                )
            )
            .mappings()
            .first()
        )
        require(row, "NOT_FOUND_OR_NOT_PERMITTED", "Reporting unit unavailable", 404)
        result["facility_id"], result["zone_id"] = row["id"], row["zone_id"]
        result["region_id"] = await session.scalar(
            select(db.units.c.parent_id).where(db.units.c.id == row["zone_id"])
        )
    else:
        row = (
            (
                await session.execute(
                    select(db.units).where(
                        db.units.c.id == str(scope_id), db.units.c.kind == scope_type
                    )
                )
            )
            .mappings()
            .first()
        )
        require(row, "NOT_FOUND_OR_NOT_PERMITTED", "Reporting unit unavailable", 404)
        result["region_id"] = row["id"] if scope_type == "REGION" else row["parent_id"]
        result["zone_id"] = row["id"] if scope_type == "ZONE" else None
    references = [
        (db.facilities, result["facility_id"]),
        (db.units, result["zone_id"]),
        (db.units, result["region_id"]),
    ]
    for table, identifier in references:
        if identifier:
            source = (
                (await session.execute(select(table).where(table.c.id == identifier)))
                .mappings()
                .one()
            )
            result["hierarchy_snapshot"].append(
                {key: source[key] for key in ("id", "name", "version")}
            )
    return result


def scope_values(resource):
    return {
        key: resource.get(key)
        for key in (
            "scope_type",
            "scope_id",
            "region_id",
            "zone_id",
            "facility_id",
            "hierarchy_snapshot",
        )
    }


async def load(session, table, identifier, lock=False):
    query = select(table).where(table.c.id == str(identifier))
    if lock:
        query = query.with_for_update()
    row = (await session.execute(query)).mappings().first()
    require(row, "NOT_FOUND_OR_NOT_PERMITTED", "Reporting resource unavailable", 404)
    return dict(row)


async def eligible_person(session, account_id, roles, scope):
    row = (
        (
            await session.execute(
                select(db.accounts).where(
                    db.accounts.c.id == account_id, db.accounts.c.active.is_(True)
                )
            )
        )
        .mappings()
        .first()
    )
    require(
        row,
        "OWNER_NOT_ELIGIBLE",
        "The named owner must have an active account and current scoped authority",
        422,
    )
    grants = [
        dict(g)
        for g in (
            await session.execute(
                select(db.grants).where(
                    db.grants.c.account_id == account_id,
                    db.grants.c.revoked.is_(False),
                    db.grants.c.valid_from <= db.now(),
                    db.grants.c.valid_until > db.now(),
                )
            )
        ).mappings()
    ]
    actor = {"id": account_id, "name": row["name"], "grants": grants}
    require(
        permits(actor, roles, scope),
        "OWNER_NOT_ELIGIBLE",
        "The named owner lacks current authority for this reporting scope",
        422,
    )
    return actor


async def audit(
    session,
    actor,
    action,
    scope,
    resource_id,
    correlation,
    *,
    outcome="SUCCESS",
    purpose="INSTITUTIONAL_REPORTING",
):
    await session.execute(
        t.audit.insert().values(
            id=db.uid(),
            actor_id=actor["id"] if actor else None,
            action=action,
            scope_type=scope.get("scope_type") if scope else None,
            scope_id=scope.get("scope_id") if scope else None,
            resource_id=resource_id,
            purpose=purpose,
            outcome=outcome,
            correlation_id=correlation,
            created_at=db.now(),
        )
    )


async def journal(
    session, cfg, box, actor, kind, row, action, scope, correlation, contract=None, content=None
):
    payload = {
        "schema_version": "3.0.0",
        "resource": row,
        "content": content,
        "authority_node_id": cfg.authority_node_id,
        "actor_id": actor["id"],
        "recorded_at": db.now(),
    }
    version = row.get("version", 1)
    await session.execute(
        t.history.insert().values(
            id=db.uid(),
            resource_type=kind,
            resource_id=row["id"],
            version=version,
            action=action,
            actor_id=actor["id"],
            payload_ciphertext=box.encrypt(canonical(payload)),
            payload_hash=digest(payload),
            created_at=db.now(),
        )
    )
    await audit(
        session,
        actor,
        action,
        scope,
        row["id"],
        correlation,
        purpose="RESTRICTED_SAFETY_REVIEW" if kind == "SAFETY_CASE" else "INSTITUTIONAL_REPORTING",
    )
    await session.execute(
        db.outbox.insert().values(
            id=db.uid(),
            event_type=action,
            resource_id=row["id"],
            payload={
                "event_contract_id": contract or "LWH-EXT-REPORTING-001",
                "resource_type": kind,
                "version": version,
                "authority_node_id": cfg.authority_node_id,
            },
            created_at=db.now(),
            attempts=0,
        )
    )


async def amend(session, table, row, values, expected_version):
    require(
        row["version"] == expected_version,
        "VERSION_CONFLICT",
        "The reporting record changed; reload and review your retained draft",
        412,
    )
    result = await session.execute(
        update(table)
        .where(table.c.id == row["id"], table.c.version == expected_version)
        .values(**values, version=expected_version + 1)
    )
    require(
        result.rowcount == 1,
        "VERSION_CONFLICT",
        "The reporting record changed; reload and review",
        412,
    )
    return {**row, **values, "version": expected_version + 1}


async def idempotent(session, database, box, actor, operation, key, payload, callback):
    require(
        key and 8 <= len(key) <= 160,
        "VALIDATION_FAILED",
        "An Idempotency-Key of 8 to 160 characters is required",
        422,
    )
    # Low-volume institutional commands are serialised across reporting resources,
    # so correction/invalidation and simultaneous disclosure releases cannot race.
    if database.postgres:
        await session.execute(text("SELECT pg_advisory_xact_lock(782025011)"))
    request_hash = digest(payload)
    previous = (
        (
            await session.execute(
                select(t.operations).where(
                    t.operations.c.actor_id == actor["id"],
                    t.operations.c.operation == operation,
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
            "This operation key was used for different content",
            409,
        )
        return json.loads(box.decrypt(previous["response_ciphertext"]))
    response = await callback()
    await session.execute(
        t.operations.insert().values(
            id=db.uid(),
            actor_id=actor["id"],
            operation=operation,
            key=key,
            request_hash=request_hash,
            response_ciphertext=box.encrypt(canonical(response)),
        )
    )
    return response


def envelope(cfg, resource):
    return {
        "resource": resource,
        "execution_state": "CENTRAL_COMMITTED",
        "authority_node_id": cfg.authority_node_id,
    }


def opened(box, row):
    return {key: value for key, value in row.items() if not key.endswith("ciphertext")} | {
        "data": json.loads(box.decrypt(row["payload_ciphertext"]))
    }
