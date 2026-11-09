"""Rebuildable clinical work/resource projection. Signed events remain authoritative."""

from decimal import Decimal

from sqlalchemy import Column, ForeignKey, Index, Integer, Numeric, String, Table, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .. import db

index = Table(
    "clinical_flow_index",
    db.metadata,
    Column("record_id", ForeignKey(f"{db.SCHEMA}.clinical_records.id"), primary_key=True),
    Column("facility_id", String(36), nullable=False),
    Column("patient_id", String(36)),
    Column("encounter_id", String(36)),
    Column("kind", String(32), nullable=False),
    Column("service", String(80), nullable=False),
    Column("status", String(32), nullable=False),
    Column("accountable_id", String(36)),
    Column("recipient_id", String(36)),
    Column("source_id", String(36)),
    Column("starts_at", String(40)),
    Column("ends_at", String(40)),
    Column("due_at", String(40)),
    Column("quantity", Numeric(20, 6)),
    Column("unit", String(160)),
    Column("trace_hash", String(64)),
    Column("indexed_version", Integer, nullable=False),
)
Index(
    "ix_clinical_flow_owner",
    index.c.facility_id,
    index.c.kind,
    index.c.accountable_id,
    index.c.status,
)
Index("ix_clinical_flow_recipient", index.c.facility_id, index.c.recipient_id, index.c.status)
Index("ix_clinical_flow_trace", index.c.facility_id, index.c.kind, index.c.trace_hash)
Index(
    "ix_clinical_flow_resource",
    index.c.facility_id,
    index.c.kind,
    index.c.source_id,
    index.c.ends_at,
)

FROZEN = {
    "nursing_assessment",
    "fluid_entry",
    "birth",
    "labour_observation",
    "child_measurement",
    "immunisation",
    "medicine_reconciliation",
    "anaesthesia_observation",
    "device_use",
    "care_instructions",
    "infusion_event",
    "infusion_witness",
    "birth_link",
}


async def project(session, row, content, cfg=None, *, write=True):
    version = session.info.get("platform_schema_version")
    if version is None:
        version = await session.scalar(
            select(db.schema_versions.c.version)
            .order_by(db.schema_versions.c.version.desc())
            .limit(1)
        )
        session.info["platform_schema_version"] = version
    if not version or version < 7:
        return
    values = {
        "record_id": row["id"],
        "facility_id": row["facility_id"],
        "patient_id": row["patient_id"],
        "encounter_id": row["encounter_id"],
        "kind": row["kind"],
        "service": row["service"],
        "status": row["status"],
        "accountable_id": content.get("owner_id")
        or content.get("account_id")
        or content.get("responsible_clinician_id"),
        "recipient_id": content.get("recipient_id")
        or content.get("handover_to")
        or (
            content.get("responsible_nurse_id")
            if row["kind"] == "stay" and content.get("nursing_responsibility_state") != "ACCEPTED"
            else None
        ),
        "source_id": content.get("source_id") or content.get("bed_id") or content.get("lot_id"),
        "starts_at": content.get("starts_at"),
        "ends_at": content.get("ends_at") or content.get("expires_at"),
        "due_at": content.get("due_at"),
        "quantity": Decimal(str(content["quantity"]))
        if content.get("quantity") is not None
        else None,
        "unit": content.get("unit"),
        "indexed_version": row["version"],
    }
    if cfg is not None:
        from .store import keyed_hash

        trace = content.get("serial_or_lot") or content.get("component_identifier")
        values["trace_hash"] = keyed_hash(cfg, "trace", trace.strip()) if trace else None
    if not write:
        return values
    insert = pg_insert if session.bind.dialect.name == "postgresql" else sqlite_insert
    statement = insert(index).values(**values)
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[index.c.record_id],
            set_=values,
            where=index.c.indexed_version <= row["version"],
        )
    )


async def rebuild(database, box, cfg=None):
    from . import tables as t
    from .store import opened

    count, after = 0, ""
    while True:
        async with database.transaction() as session:
            rows = list(
                (
                    await session.execute(
                        select(t.records)
                        .where(t.records.c.id > after)
                        .order_by(t.records.c.id)
                        .limit(200)
                        .with_for_update()
                    )
                ).mappings()
            )
            for row in rows:
                await project(session, row, opened(box, row)["data"], cfg)
                count += 1
        if len(rows) < 200:
            return count
        after = rows[-1]["id"]


async def ready(session, facility_id=None):
    """Contain projection failure to its source and claimed facility.

    Omitting facility_id retains global reconciliation for operating assurance.
    A wrongly assigned row blocks both facilities until repaired from its source.
    """
    from .tables import records

    mismatch = await session.scalar(
        select(records.c.id)
        .outerjoin(index, index.c.record_id == records.c.id)
        .where(
            or_(
                index.c.record_id.is_(None),
                index.c.indexed_version != records.c.version,
                index.c.status != records.c.status,
                index.c.kind != records.c.kind,
                index.c.facility_id != records.c.facility_id,
            )
        )
        .where(
            or_(records.c.facility_id == facility_id, index.c.facility_id == facility_id)
            if facility_id
            else True
        )
        .limit(1)
    )
    return mismatch is None
