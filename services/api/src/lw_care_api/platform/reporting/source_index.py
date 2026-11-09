"""Rebuildable occurrence projection; encrypted records/signed events remain authoritative.

One row per relevant record, including noncontributing and malformed records, makes
missing/stale projection detection independent of the requested reporting period.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Table, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .. import db

KINDS = ("encounter", "stay", "referral", "note", "record_error")
index = Table(
    "reporting_source_index",
    db.metadata,
    Column("record_id", ForeignKey(f"{db.SCHEMA}.clinical_records.id"), primary_key=True),
    Column("facility_id", String(36), nullable=False),
    Column("kind", String(32), nullable=False),
    Column("status", String(32), nullable=False),
    Column("indexed_version", Integer, nullable=False),
    Column("uncertain", Boolean, nullable=False),
    Column("first_at", String(40)),
    Column("last_at", String(40)),
    Column("target_id", String(36)),
)
Index("ix_reporting_source_period", index.c.facility_id, index.c.uncertain, index.c.first_at)
Index("ix_reporting_source_target", index.c.facility_id, index.c.target_id)


def instant(value):
    try:
        result = datetime.fromisoformat(value)
        return result.astimezone(UTC) if result.tzinfo else None
    except (AttributeError, TypeError, ValueError):
        return None


def occurrence_times(row, content):
    if row["kind"] == "encounter" and row["status"] == "COMPLETED":
        return [instant(content.get("disposition", {}).get("occurred_at"))]
    if row["kind"] == "stay":
        times = [
            instant(event.get("occurred_at"))
            for event in content.get("history", [])
            if event.get("action") in {"DEATH", "DISCHARGE", "SELF_DISCHARGE"}
        ]
        return times or (
            [None] if row["status"] in {"DECEASED", "DISCHARGED", "SELF_DISCHARGED"} else []
        )
    if row["kind"] == "referral":
        times = [
            instant(event.get("occurred_at"))
            for event in content.get("history", [])
            if event.get("action") == "REQUEST"
        ]
        return times or ([None] if row["status"] not in {"DRAFT", "CANCELLED"} else [])
    return []


def projection(row, content):
    times = occurrence_times(row, content)
    known = [value.isoformat() for value in times if value is not None]
    return {
        "record_id": row["id"],
        "facility_id": row["facility_id"],
        "kind": row["kind"],
        "status": row["status"],
        "indexed_version": row["version"],
        "uncertain": None in times,
        "first_at": min(known) if known else None,
        "last_at": max(known) if known else None,
        "target_id": content.get("target_id") if row["kind"] == "record_error" else None,
    }


async def project(session, row, content):
    if row["kind"] not in KINDS or (session.info.get("platform_schema_version") or 0) < 9:
        return
    values = projection(row, content)
    insert = pg_insert if session.bind.dialect.name == "postgresql" else sqlite_insert
    statement = insert(index).values(**values)
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[index.c.record_id],
            set_=values,
            where=index.c.indexed_version <= row["version"],
        )
    )


async def ready(session, facility=None):
    from ..clinical.tables import records

    mismatch = await session.scalar(
        select(records.c.id)
        .outerjoin(index, index.c.record_id == records.c.id)
        .where(
            records.c.kind.in_(KINDS),
            or_(
                records.c.facility_id == facility,
                index.c.facility_id == facility,
            )
            if facility
            else True,
        )
        .where(
            or_(
                index.c.record_id.is_(None),
                index.c.indexed_version != records.c.version,
                index.c.facility_id != records.c.facility_id,
                index.c.kind != records.c.kind,
                index.c.status != records.c.status,
            )
        )
        .limit(1)
    )
    return mismatch is None


async def rebuild(database, box):
    from ..clinical import store, tables

    count, after = 0, ""
    while True:
        async with database.transaction() as session:
            session.info["platform_schema_version"] = await database.version()
            rows = list(
                (
                    await session.execute(
                        select(tables.records)
                        .where(tables.records.c.kind.in_(KINDS), tables.records.c.id > after)
                        .order_by(tables.records.c.id)
                        .limit(200)
                        .with_for_update()
                    )
                ).mappings()
            )
            for row in rows:
                await project(session, row, store.opened(box, row)["data"])
                count += 1
        if len(rows) < 200:
            return count
        after = rows[-1]["id"]
