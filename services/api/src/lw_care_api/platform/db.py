"""Transactional storage. Schema installation is an explicit release operation."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    event,
    func,
    text,
)
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from ..db.connection import normalize_async_database_url

SCHEMA = "health_platform"
SCHEMA_VERSION = 4
metadata = MetaData(schema=SCHEMA)


def identifier():
    return Column("id", String(36), primary_key=True)


def uid() -> str:
    return str(uuid4())


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


accounts = Table(
    "accounts",
    metadata,
    identifier(),
    Column("email", String(254), unique=True, nullable=False),
    Column("name", String(160), nullable=False),
    Column("password_hash", Text),
    Column("totp_ciphertext", Text),
    Column("totp_last_step", Integer, default=-1, nullable=False),
    Column("active", Boolean, nullable=False, default=False),
    Column("created_at", String(40)),
)
sessions = Table(
    "sessions",
    metadata,
    identifier(),
    Column("token_hash", String(64), unique=True, nullable=False),
    Column("account_id", ForeignKey(f"{SCHEMA}.accounts.id"), nullable=False),
    Column("expires_at", String(40), nullable=False),
    Column("revoked", Boolean, default=False),
)
invitations = Table(
    "invitations",
    metadata,
    identifier(),
    Column("account_id", ForeignKey(f"{SCHEMA}.accounts.id"), nullable=False),
    Column("token_hash", String(64), unique=True),
    Column("expires_at", String(40)),
    Column("used", Boolean, default=False),
    Column("created_by", String(36)),
)
grants = Table(
    "grants",
    metadata,
    identifier(),
    Column("account_id", ForeignKey(f"{SCHEMA}.accounts.id"), nullable=False),
    Column("role", String(40), nullable=False),
    Column("scope_type", String(16), nullable=False),
    Column("scope_id", String(36), nullable=False),
    Column("valid_from", String(40), nullable=False),
    Column("valid_until", String(40), nullable=False),
    Column("revoked", Boolean, default=False),
    Column("grantor", String(36), nullable=False),
)
units = Table(
    "units",
    metadata,
    identifier(),
    Column("name", String(160), nullable=False),
    Column("kind", String(20), nullable=False),
    Column("parent_id", ForeignKey(f"{SCHEMA}.units.id")),
    Column("code", String(80), unique=True, nullable=False),
    Column("valid_from", String(40)),
    Column("valid_until", String(40)),
    Column("version", Integer, nullable=False, default=1),
)
operators = Table(
    "operators",
    metadata,
    identifier(),
    Column("name", String(160), nullable=False),
    Column("external_reference", String(160), unique=True, nullable=False),
    Column("created_at", String(40)),
)
facilities = Table(
    "facilities",
    metadata,
    identifier(),
    Column("operator_id", ForeignKey(f"{SCHEMA}.operators.id"), nullable=False),
    Column("zone_id", ForeignKey(f"{SCHEMA}.units.id"), nullable=False),
    Column("name", String(200), nullable=False),
    Column("site_type", String(40), nullable=False),
    Column("ownership", String(20), nullable=False),
    Column("jurisdiction", String(80), nullable=False),
    Column("external_reference", String(200), unique=True, nullable=False),
    Column("address", Text, nullable=False),
    Column("public_contact", String(200), nullable=False),
    Column("private_contact", String(254), nullable=False),
    Column("services", JSON, nullable=False),
    Column("identity_status", String(20), default="PROVISIONAL", nullable=False),
    Column("statutory_status", String(20), default="PENDING", nullable=False),
    Column("affiliation_status", String(20), default="APPLICANT", nullable=False),
    Column("publication_status", String(20), default="DRAFT", nullable=False),
    Column("capability_status", String(20), default="DECLARED", nullable=False),
    Column("readiness_status", String(20), default="UNKNOWN", nullable=False),
    Column("affiliation_expires_at", String(40)),
    Column("affiliation_scope", Text),
    Column("conditions", Text),
    Column("created_by", String(36), nullable=False),
    Column("created_at", String(40), nullable=False),
    Column("updated_at", String(40), nullable=False),
    Column("version", Integer, nullable=False, default=1),
)
criteria = Table(
    "criteria",
    metadata,
    identifier(),
    Column("name", String(200), nullable=False),
    Column("version", String(40), nullable=False),
    Column("jurisdiction", String(80), nullable=False),
    Column("site_type", String(40), nullable=False),
    Column("requirements", JSON, nullable=False),
    Column("adoption_reference", Text, nullable=False),
    Column("adopted_by", String(36), nullable=False),
    Column("valid_from", String(40), nullable=False),
    Column("valid_until", String(40), nullable=False),
    UniqueConstraint("name", "version", "jurisdiction", "site_type"),
)
applications = Table(
    "applications",
    metadata,
    identifier(),
    Column("facility_id", ForeignKey(f"{SCHEMA}.facilities.id"), unique=True, nullable=False),
    Column("criteria_id", ForeignKey(f"{SCHEMA}.criteria.id"), nullable=False),
    Column("state", String(30), nullable=False, default="DRAFT"),
    Column("inspector_id", ForeignKey(f"{SCHEMA}.accounts.id")),
    Column("reviewer_id", ForeignKey(f"{SCHEMA}.accounts.id")),
    Column("recommendation", JSON),
    Column("created_by", String(36), nullable=False),
    Column("version", Integer, nullable=False),
)
evidence = Table(
    "evidence",
    metadata,
    identifier(),
    Column("application_id", ForeignKey(f"{SCHEMA}.applications.id"), nullable=False),
    Column("criterion", String(120), nullable=False),
    Column("object_key", Text, nullable=False),
    Column("sha256", String(64), nullable=False),
    Column("filename", String(200), nullable=False),
    Column("media_type", String(100), nullable=False),
    Column("size", Integer, nullable=False),
    Column("source", Text, nullable=False),
    Column("expires_at", String(40), nullable=False),
    Column("scan_status", String(20), nullable=False),
    Column("uploaded_by", String(36), nullable=False),
    Column("created_at", String(40), nullable=False),
)
inspections = Table(
    "inspections",
    metadata,
    identifier(),
    Column("application_id", ForeignKey(f"{SCHEMA}.applications.id"), nullable=False),
    Column("inspector_id", String(36), nullable=False),
    Column("findings", JSON, nullable=False),
    Column("conflict_declared", Boolean, nullable=False),
    Column("observed_at", String(40), nullable=False),
    Column("recorded_at", String(40), nullable=False),
)
decisions = Table(
    "decisions",
    metadata,
    identifier(),
    Column("application_id", ForeignKey(f"{SCHEMA}.applications.id"), nullable=False),
    Column("decider_id", String(36), nullable=False),
    Column("decision", String(20), nullable=False),
    Column("reason", Text, nullable=False),
    Column("scope", Text, nullable=False),
    Column("conditions", Text),
    Column("effective_at", String(40), nullable=False),
    Column("expires_at", String(40), nullable=False),
    Column("created_at", String(40), nullable=False),
)
revisions = Table(
    "revisions",
    metadata,
    identifier(),
    Column("resource_id", String(36), nullable=False),
    Column("resource_type", String(40), nullable=False),
    Column("version", Integer, nullable=False),
    Column("payload", JSON, nullable=False),
    Column("actor_id", String(36), nullable=False),
    Column("recorded_at", String(40), nullable=False),
    UniqueConstraint("resource_type", "resource_id", "version"),
)
audit = Table(
    "audit",
    metadata,
    identifier(),
    Column("actor_id", String(36)),
    Column("action", String(120), nullable=False),
    Column("resource_id", String(200)),
    Column("outcome", String(20), nullable=False),
    Column("correlation_id", String(36)),
    Column("purpose", String(50), nullable=False),
    Column("recorded_at", String(40), nullable=False),
    Column("details", JSON),
)
outbox = Table(
    "outbox",
    metadata,
    identifier(),
    Column("event_type", String(80), nullable=False),
    Column("resource_id", String(36), nullable=False),
    Column("payload", JSON, nullable=False),
    Column("created_at", String(40), nullable=False),
    Column("delivered_at", String(40)),
    Column("attempts", Integer, default=0),
    Column("provider_receipt", String(160)),
)
operations = Table(
    "operations",
    metadata,
    identifier(),
    Column("actor_id", String(36), nullable=False),
    Column("operation", String(200), nullable=False),
    Column("key", String(160), nullable=False),
    Column("request_hash", String(64), nullable=False),
    Column("response", JSON, nullable=False),
    UniqueConstraint("actor_id", "operation", "key"),
)
rate_limits = Table(
    "rate_limits",
    metadata,
    Column("key", String(64), primary_key=True),
    Column("attempts", Integer, nullable=False),
    Column("window_start", String(40), nullable=False),
)
schema_versions = Table(
    "schema_versions",
    metadata,
    Column("version", Integer, primary_key=True),
    Column("applied_at", String(40), nullable=False),
)


class Database:
    def __init__(self, url: str):
        normalized, connect_args = normalize_async_database_url(url)
        self.postgres = normalized.startswith("postgresql")
        options = {} if self.postgres else {"schema_translate_map": {SCHEMA: None}}
        self.engine = create_async_engine(
            normalized,
            connect_args=connect_args,
            poolclass=NullPool,
            execution_options=options,
        )
        self.session = async_sessionmaker(self.engine, expire_on_commit=False)
        if not self.postgres:

            @event.listens_for(self.engine.sync_engine, "connect")
            def enforce_foreign_keys(connection, _record):
                connection.execute("PRAGMA foreign_keys=ON")

    @asynccontextmanager
    async def transaction(self):
        async with self.session() as session, session.begin():
            yield session

    async def migrate(self):
        from .clinical import tables as clinical_tables
        from .control import tables as control_tables
        from .reporting import tables as reporting_tables

        async with self.engine.begin() as connection:
            if self.postgres:
                await connection.execute(text("SELECT pg_advisory_xact_lock(718540119)"))
                await connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
            await connection.run_sync(metadata.create_all)
            present = await connection.scalar(
                schema_versions.select().with_only_columns(func.max(schema_versions.c.version))
            )
            if present is None:
                await connection.execute(
                    schema_versions.insert().values(version=1, applied_at=now())
                )
            if present is None or present < 2:
                await connection.execute(
                    schema_versions.insert().values(version=2, applied_at=now())
                )
            if present is None or present < 3:
                await connection.execute(
                    schema_versions.insert().values(version=3, applied_at=now())
                )
            if present is None or present < 4:
                await connection.execute(
                    schema_versions.insert().values(version=4, applied_at=now())
                )
            if self.postgres:
                await connection.execute(
                    text(f"""
                    CREATE OR REPLACE FUNCTION {SCHEMA}.reject_history_mutation()
                    RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
                    RAISE EXCEPTION 'Append-only institutional history'; END; $$
                """)
                )
                for table in (
                    audit,
                    revisions,
                    decisions,
                    inspections,
                    criteria,
                    evidence,
                    *clinical_tables.IMMUTABLE,
                    *reporting_tables.IMMUTABLE,
                    *control_tables.IMMUTABLE,
                ):
                    await connection.execute(
                        text(f"DROP TRIGGER IF EXISTS immutable_history ON {SCHEMA}.{table.name}")
                    )
                    await connection.execute(
                        text(
                            f"CREATE TRIGGER immutable_history BEFORE UPDATE OR DELETE "
                            f"ON {SCHEMA}.{table.name} FOR EACH ROW "
                            f"EXECUTE FUNCTION {SCHEMA}.reject_history_mutation()"
                        )
                    )
                await connection.execute(
                    text(f"""
                    CREATE OR REPLACE FUNCTION {SCHEMA}.protect_clinical_records()
                    RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
                    IF TG_OP = 'DELETE' THEN
                        RAISE EXCEPTION 'Clinical source records cannot be deleted';
                    END IF;
                    IF OLD.kind = 'note' AND OLD.status = 'SIGNED' THEN
                        RAISE EXCEPTION 'Signed clinical content is immutable; append an addendum';
                    END IF;
                    RETURN NEW; END; $$
                """)
                )
                await connection.execute(
                    text(
                        f"DROP TRIGGER IF EXISTS protect_clinical_records ON {SCHEMA}.clinical_records"
                    )
                )
                await connection.execute(
                    text(
                        f"CREATE TRIGGER protect_clinical_records BEFORE UPDATE OR DELETE ON {SCHEMA}.clinical_records FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.protect_clinical_records()"
                    )
                )

    async def version(self) -> int | None:
        async with self.transaction() as session:
            return await session.scalar(
                schema_versions.select().with_only_columns(func.max(schema_versions.c.version))
            )

    async def ready(self) -> bool:
        # Version 2 remains supported during the staged reporting rollout.
        return await self.version() in (2, 3, 4)
