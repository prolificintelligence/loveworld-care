"""Authoritative clinical storage and permission checks; no process-local care state."""

import base64
import hashlib
import hmac
import json
import re
import unicodedata
from datetime import UTC, datetime

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import func, select, text, update

from .. import db
from ..domain import require
from . import tables as t


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def keyed_hash(cfg, namespace, value):
    return hmac.new(
        bytes.fromhex(cfg.data_key_hex), f"clinical:{namespace}:{value}".encode(), hashlib.sha256
    ).hexdigest()


def search_tokens(cfg, value):
    value = unicodedata.normalize("NFKC", value).casefold()
    words = {word for word in re.findall(r"\w+", value) if len(word) >= 2}
    return [keyed_hash(cfg, "search", word) for word in sorted(words)]


def signing_key(cfg):
    seed = hmac.new(
        bytes.fromhex(cfg.data_key_hex), b"clinical-event-attestation-v1", hashlib.sha256
    )
    return Ed25519PrivateKey.from_private_bytes(seed.digest())


def seal(box, identifier, content):
    return box.encrypt(canonical({"id": identifier, "content": content}))


def opened(box, row):
    value = json.loads(box.decrypt(row["content_ciphertext"]))
    require(value["id"] == row["id"], "INTEGRITY_FAILURE", "Record integrity check failed", 503)
    return {
        k: v
        for k, v in row.items()
        if k not in ("content_ciphertext", "search_tokens", "identifier_hash")
    } | {"data": value["content"]}


async def fetch(session, facility_id, identifier, kind=None, *, lock=False):
    query = select(t.records).where(
        t.records.c.id == str(identifier), t.records.c.facility_id == str(facility_id)
    )
    if kind:
        query = query.where(t.records.c.kind == kind)
    if lock:
        query = query.with_for_update()
    row = (await session.execute(query)).mappings().first()
    require(row is not None, "NOT_FOUND_OR_NOT_PERMITTED", "Clinical record unavailable", 404)
    return dict(row)


async def audit(
    session,
    actor,
    facility_id,
    patient_id,
    action,
    correlation,
    outcome="SUCCESS",
    purpose="DIRECT_CARE",
):
    await session.execute(
        t.audit.insert().values(
            id=db.uid(),
            actor_id=actor["id"] if actor else None,
            facility_id=facility_id,
            patient_id=patient_id,
            action=action,
            purpose=purpose,
            outcome=outcome,
            correlation_id=correlation,
            recorded_at=db.now(),
        )
    )


async def site_for(session, cfg, facility_id, *, write=False):
    row = (
        (
            await session.execute(
                select(t.sites).where(t.sites.c.facility_id == facility_id).with_for_update()
                if write
                else select(t.sites).where(t.sites.c.facility_id == facility_id)
            )
        )
        .mappings()
        .first()
    )
    require(
        row and row["active"] and row["valid_from"] <= db.now() < row["valid_until"],
        "CLINICAL_ACTIVATION_REQUIRED",
        "Current facility clinical activation is required",
        403,
    )
    if write:
        require(
            row["authority_node_id"] == cfg.authority_node_id,
            "WRONG_AUTHORITY",
            "This record belongs to another facility authority",
            409,
        )
        schema_version = await session.scalar(select(func.max(db.schema_versions.c.version)))
        session.info["platform_schema_version"] = schema_version
        if schema_version and schema_version >= 4:
            session.info["active_activation_package"] = None
            from ..control import tables as controls
            from ..control.service import ControlService, load

            link = (
                (
                    await session.execute(
                        select(controls.site_packages).where(
                            controls.site_packages.c.facility_id == facility_id,
                            controls.site_packages.c.site_version == row["version"],
                        )
                    )
                )
                .mappings()
                .first()
            )
            if link:
                package = await load(session, controls.packages, link["package_id"])
                session.info["active_activation_package"] = package
                require(
                    (
                        await ControlService(
                            session, cfg, None, None, "clinical-policy-check"
                        ).package_state(package)
                    )["state"]
                    == "ADOPTED",
                    "ACTIVATION_PACKAGE_UNAVAILABLE",
                    "The adopted activation package is expired, withdrawn or unavailable",
                    403,
                )
    return dict(row)


async def privilege_for(session, actor_id, facility_id, capability, service=None):
    active = await session.scalar(select(db.accounts.c.active).where(db.accounts.c.id == actor_id))
    require(active, "ACCESS_DENIED", "The clinical account is inactive", 403)
    membership = await session.scalar(
        select(db.grants.c.id)
        .where(
            db.grants.c.account_id == actor_id,
            db.grants.c.role == "CLINICAL_STAFF",
            db.grants.c.scope_type == "FACILITY",
            db.grants.c.scope_id == facility_id,
            db.grants.c.revoked.is_(False),
            db.grants.c.valid_from <= db.now(),
            db.grants.c.valid_until > db.now(),
        )
        .limit(1)
    )
    require(
        membership,
        "CLINICAL_PRIVILEGE_REQUIRED",
        "Current facility staff membership is required",
        403,
    )
    entries = (
        await session.execute(
            select(t.privileges).where(
                t.privileges.c.account_id == actor_id,
                t.privileges.c.facility_id == facility_id,
                t.privileges.c.revoked.is_(False),
                t.privileges.c.valid_from <= db.now(),
                t.privileges.c.valid_until > db.now(),
            )
        )
    ).mappings()
    privilege = next(
        (
            dict(p)
            for p in entries
            if capability in p["capabilities"] and (service is None or service in p["services"])
        ),
        None,
    )
    require(
        privilege,
        "CLINICAL_PRIVILEGE_REQUIRED",
        "Current facility and service privileges are required",
        403,
    )
    return privilege


async def member_for(session, actor_id, facility_id, patient_id):
    permitted = await session.scalar(
        select(t.memberships.c.id)
        .where(
            t.memberships.c.facility_id == facility_id,
            t.memberships.c.patient_id == patient_id,
            t.memberships.c.account_id == actor_id,
            t.memberships.c.active.is_(True),
            t.memberships.c.valid_until > db.now(),
        )
        .limit(1)
    )
    require(
        permitted,
        "TREATING_RELATIONSHIP_REQUIRED",
        "An accepted treating assignment is required",
        403,
    )


async def add_member(session, cfg, account_id, encounter, capability="CARE"):
    privilege = await privilege_for(
        session, account_id, encounter["facility_id"], capability, encounter["service"]
    )
    existing = (
        (
            await session.execute(
                select(t.memberships).where(
                    t.memberships.c.account_id == account_id,
                    t.memberships.c.encounter_id == encounter["id"],
                )
            )
        )
        .mappings()
        .first()
    )
    values = {"valid_until": privilege["valid_until"], "active": True}
    if existing:
        await session.execute(
            update(t.memberships).where(t.memberships.c.id == existing["id"]).values(**values)
        )
    else:
        await session.execute(
            t.memberships.insert().values(
                id=db.uid(),
                facility_id=encounter["facility_id"],
                patient_id=encounter["patient_id"],
                encounter_id=encounter["id"],
                account_id=account_id,
                **values,
            )
        )


async def guard(
    session,
    cfg,
    actor,
    facility_id,
    capability,
    *,
    patient_id=None,
    encounter_id=None,
    service=None,
    write=False,
    relationship=True,
):
    site = await site_for(session, cfg, facility_id, write=write)
    package = session.info.get("active_activation_package")
    if write and capability in {"FINANCE", "CASHIER"} and package:
        require(
            package["payload"].get("financial_policy_reference"),
            "FINANCIAL_ACTIVATION_REQUIRED",
            "Care finance requires the separately reviewed financial policy scope",
            403,
        )
    encounter = None
    if encounter_id:
        encounter = await fetch(session, facility_id, encounter_id, "encounter", lock=write)
        require(
            encounter["patient_id"] == str(patient_id),
            "PATIENT_CONTEXT_MISMATCH",
            "Check the patient and encounter",
            409,
        )
        service = encounter["service"]
    require(
        service is None or service in site["services"],
        "SERVICE_NOT_ACTIVATED",
        "The service is outside facility activation",
        403,
    )
    privilege = await privilege_for(session, actor["id"], facility_id, capability, service)
    if patient_id:
        await fetch(session, facility_id, patient_id, "patient")
        if relationship and capability in {
            "CARE",
            "NURSING",
            "PRESCRIBE",
            "PROCEDURE",
            "SENSITIVE",
        }:
            await member_for(session, actor["id"], facility_id, str(patient_id))
    return site, privilege, encounter


async def record_event(
    session, cfg, box, actor, row, content, action, contract, correlation, occurred_at=None
):
    prior = (
        await session.scalar(
            select(t.events.c.payload_hash)
            .where(t.events.c.record_id == row["id"])
            .order_by(t.events.c.version.desc())
            .limit(1)
        )
        or "0" * 64
    )
    stamp = db.now()
    envelope = {
        "schema_version": "2.0.0",
        "id": db.uid(),
        "record_id": row["id"],
        "facility_id": row["facility_id"],
        "patient_id": row["patient_id"],
        "version": row["version"],
        "kind": row["kind"],
        "status": row["status"],
        "actor_id": actor["id"],
        "authority_node_id": row["authority_node_id"],
        "authority_epoch": row["authority_epoch"],
        "previous_hash": prior,
        "occurred_at": occurred_at or content.get("occurred_at") or stamp,
        "recorded_at": stamp,
        "event_contract_id": contract,
        "action": action,
        "content": content,
    }
    policy = (
        (await session.execute(select(t.sites).where(t.sites.c.facility_id == row["facility_id"])))
        .mappings()
        .one()
    )
    professional = (
        await session.execute(
            select(t.privileges).where(
                t.privileges.c.facility_id == row["facility_id"],
                t.privileges.c.account_id == actor["id"],
                t.privileges.c.revoked.is_(False),
                t.privileges.c.valid_from <= stamp,
                t.privileges.c.valid_until > stamp,
            )
        )
    ).mappings()
    envelope["authority_context"] = {
        "policy_reference": policy["policy_reference"],
        "policy_version": policy["version"],
        "policy_valid_until": policy["valid_until"],
        "privileges": [
            {
                key: p[key]
                for key in (
                    "id",
                    "services",
                    "capabilities",
                    "professional_reference",
                    "valid_from",
                    "valid_until",
                    "approved_by",
                )
            }
            for p in professional
        ],
    }
    digest = hashlib.sha256(canonical(envelope).encode()).hexdigest()
    signature = base64.b64encode(signing_key(cfg).sign(bytes.fromhex(digest))).decode()
    await session.execute(
        t.events.insert().values(
            **{
                k: envelope[k]
                for k in (
                    "id",
                    "facility_id",
                    "patient_id",
                    "record_id",
                    "version",
                    "event_contract_id",
                    "action",
                    "actor_id",
                    "occurred_at",
                    "recorded_at",
                    "authority_node_id",
                    "authority_epoch",
                    "previous_hash",
                )
            },
            payload_hash=digest,
            signature=signature,
            payload_ciphertext=box.encrypt(canonical(envelope)),
        )
    )
    await audit(session, actor, row["facility_id"], row["patient_id"], action, correlation)
    # Event metadata only: external notification jobs never receive clinical text.
    await session.execute(
        db.outbox.insert().values(
            id=envelope["id"],
            event_type=action,
            resource_id=row["id"],
            payload={
                "event_contract_id": contract,
                "clinical_event_id": envelope["id"],
                "authority_node_id": row["authority_node_id"],
                "version": row["version"],
            },
            created_at=stamp,
            attempts=0,
        )
    )
    if row["kind"] == "task":
        from ..control.jobs import index_task

        await index_task(session, row, content)
    from .flow_index import project

    await project(session, row, content, cfg)


async def create(
    session,
    cfg,
    box,
    actor,
    site,
    kind,
    content,
    correlation,
    *,
    patient_id=None,
    encounter_id=None,
    service="REGISTRATION",
    status="RECORDED",
    contract="LWH-EXT-CLINICAL-001",
    action=None,
    identifier=None,
    unique_value=None,
    confidentiality="STANDARD",
    tokens=None,
):
    identifier = identifier or db.uid()
    stamp = db.now()
    row = {
        "id": identifier,
        "facility_id": site["facility_id"],
        "patient_id": str(patient_id) if patient_id else None,
        "encounter_id": str(encounter_id) if encounter_id else None,
        "kind": kind,
        "status": status,
        "service": service,
        "confidentiality": confidentiality,
        "authority_node_id": site["authority_node_id"],
        "authority_epoch": site["authority_epoch"],
        "version": 1,
        "created_by": actor["id"],
        "created_at": stamp,
        "updated_at": stamp,
        "content_ciphertext": seal(box, identifier, content),
        "identifier_hash": keyed_hash(cfg, kind, unique_value) if unique_value else None,
        "search_tokens": tokens,
    }
    await session.execute(t.records.insert().values(**row))
    await record_event(
        session,
        cfg,
        box,
        actor,
        row,
        content,
        action or f"clinical.{kind}_recorded",
        contract,
        correlation,
    )
    return opened(box, row)


async def change(
    session,
    cfg,
    box,
    actor,
    row,
    content,
    status,
    version,
    correlation,
    action,
    contract,
    *,
    tokens=None,
):
    require(
        row["version"] == version,
        "VERSION_CONFLICT",
        "The clinical record changed; review the latest version",
        412,
    )
    site = await site_for(session, cfg, row["facility_id"], write=True)
    require(
        row["authority_node_id"] == site["authority_node_id"]
        and row["authority_epoch"] == site["authority_epoch"],
        "AUTHORITY_EPOCH_CONFLICT",
        "The record authority needs reconciliation",
        409,
    )
    values = {
        "version": version + 1,
        "status": status,
        "updated_at": db.now(),
        "content_ciphertext": seal(box, row["id"], content),
    }
    if tokens is not None:
        values["search_tokens"] = tokens
    result = await session.execute(
        update(t.records)
        .where(t.records.c.id == row["id"], t.records.c.version == version)
        .values(**values)
    )
    require(result.rowcount == 1, "VERSION_CONFLICT", "The record changed; reload and review", 412)
    updated = {**row, **values}
    await record_event(session, cfg, box, actor, updated, content, action, contract, correlation)
    return opened(box, updated)


def receipt(cfg, resource):
    return {
        "resource": resource,
        "execution_state": "CENTRAL_COMMITTED",
        "authority_node_id": cfg.authority_node_id,
        "replication_state": "NOT_REPLICATED",
    }


async def idempotent(
    session, database, cfg, box, actor, facility_id, operation, key, payload, callback, replay_guard
):
    require(
        key and 8 <= len(key) <= 160, "VALIDATION_FAILED", "An Idempotency-Key is required", 422
    )
    request_hash = hashlib.sha256(canonical(payload).encode()).hexdigest()
    if database.postgres:
        lock_key = hashlib.sha256(f"clinical:{actor['id']}:{operation}:{key}".encode()).digest()[:8]
        await session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": int.from_bytes(lock_key, signed=True)},
        )
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
            "The operation key was used for different content",
            409,
        )
        response = json.loads(box.decrypt(previous["response_ciphertext"]))
        await replay_guard(response)
        return response
    response = await callback()
    await session.execute(
        t.operations.insert().values(
            id=db.uid(),
            actor_id=actor["id"],
            facility_id=facility_id,
            operation=operation,
            key=key,
            request_hash=request_hash,
            response_ciphertext=box.encrypt(canonical(response)),
        )
    )
    return response


def event_time(value):
    require(
        datetime.fromisoformat(value) <= datetime.now(UTC),
        "VALIDATION_FAILED",
        "An actual event cannot be dated in the future",
        422,
    )
