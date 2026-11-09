"""Personal access is separate from staff membership and from clinical source facts."""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)

from ..db import SCHEMA, identifier, metadata


def table(name, *columns):
    return Table("personal_" + name, metadata, identifier(), *columns)


links = table(
    "links",
    Column("account_id", ForeignKey(f"{SCHEMA}.accounts.id"), nullable=False),
    Column("submitted_by", String(36), nullable=False),
    Column("facility_id", ForeignKey(f"{SCHEMA}.facilities.id"), nullable=False),
    Column("patient_id", ForeignKey(f"{SCHEMA}.clinical_records.id")),
    Column("patient_version", Integer),
    Column("relationship", String(20), nullable=False),
    Column("state", String(24), nullable=False),
    Column("version", Integer, nullable=False),
    Column("permissions", JSON, nullable=False),
    Column("valid_until", String(40)),
    Column("review_at", String(40)),
    Column("reviewer_id", String(36)),
    Column("active_key", String(120), unique=True),
    Column("self_key", String(80), unique=True),
    Column("created_at", String(40), nullable=False),
    Column("updated_at", String(40), nullable=False),
    Column("payload_ciphertext", Text, nullable=False),
)
Index("ix_personal_link_owner", links.c.account_id, links.c.state, links.c.id)
Index("ix_personal_link_review", links.c.facility_id, links.c.state, links.c.created_at)

services = table(
    "services",
    Column("facility_id", ForeignKey(f"{SCHEMA}.facilities.id"), nullable=False),
    Column("name", String(160), nullable=False),
    Column("primary_id", ForeignKey(f"{SCHEMA}.accounts.id"), nullable=False),
    Column("fallback_id", ForeignKey(f"{SCHEMA}.accounts.id"), nullable=False),
    Column("primary_accepted", Boolean, nullable=False),
    Column("fallback_accepted", Boolean, nullable=False),
    Column("response_minutes", Integer, nullable=False),
    Column("valid_until", String(40), nullable=False),
    Column("active", Boolean, nullable=False),
    Column("version", Integer, nullable=False),
    Column("created_by", String(36), nullable=False),
    Column("created_at", String(40), nullable=False),
    Column("payload_ciphertext", Text, nullable=False),
)

requests = table(
    "requests",
    Column("link_id", ForeignKey(f"{SCHEMA}.personal_links.id"), nullable=False),
    Column("service_id", ForeignKey(f"{SCHEMA}.personal_services.id"), nullable=False),
    Column("facility_id", String(36), nullable=False),
    Column("patient_id", String(36), nullable=False),
    Column("created_by", String(36), nullable=False),
    Column("kind", String(24), nullable=False),
    Column("state", String(24), nullable=False),
    Column("version", Integer, nullable=False),
    Column("owner_id", String(36), nullable=False),
    Column("fallback_id", String(36), nullable=False),
    Column("handover_to", String(36)),
    Column("due_at", String(40), nullable=False),
    Column("created_at", String(40), nullable=False),
    Column("updated_at", String(40), nullable=False),
    Column("accepted_at", String(40)),
    Column("closed_at", String(40)),
)
Index("ix_personal_request_owner", requests.c.facility_id, requests.c.owner_id, requests.c.due_at)
messages = table(
    "messages",
    Column("request_id", ForeignKey(f"{SCHEMA}.personal_requests.id"), nullable=False),
    Column("actor_id", String(36), nullable=False),
    Column("sender_type", String(24), nullable=False),
    Column("created_at", String(40), nullable=False),
    Column("payload_ciphertext", Text, nullable=False),
)

releases = table(
    "releases",
    Column("link_id", ForeignKey(f"{SCHEMA}.personal_links.id"), nullable=False),
    Column("source_id", ForeignKey(f"{SCHEMA}.clinical_records.id"), nullable=False),
    Column("source_version", Integer, nullable=False),
    Column("kind", String(24), nullable=False),
    Column("created_by", String(36), nullable=False),
    Column("created_at", String(40), nullable=False),
    Column("due_at", String(40)),
    Column("payload_ciphertext", Text, nullable=False),
)
withdrawals = table(
    "withdrawals",
    Column("release_id", ForeignKey(f"{SCHEMA}.personal_releases.id"), nullable=False, unique=True),
    Column("actor_id", String(36), nullable=False),
    Column("created_at", String(40), nullable=False),
    Column("payload_ciphertext", Text, nullable=False),
)

events = table(
    "events",
    Column("resource_type", String(30), nullable=False),
    Column("resource_id", String(36), nullable=False),
    Column("version", Integer, nullable=False),
    Column("actor_id", String(36), nullable=False),
    Column("action", String(50), nullable=False),
    Column("created_at", String(40), nullable=False),
    Column("payload_ciphertext", Text, nullable=False),
    Column("payload_hash", String(64), nullable=False),
    UniqueConstraint("resource_type", "resource_id", "version"),
)
audit = table(
    "audit",
    Column("link_id", String(36)),
    Column("actor_id", String(36)),
    Column("action", String(60), nullable=False),
    Column("outcome", String(20), nullable=False),
    Column("created_at", String(40), nullable=False),
    Column("correlation_id", String(36), nullable=False),
)
preferences = table(
    "preferences",
    Column("account_id", ForeignKey(f"{SCHEMA}.accounts.id"), nullable=False, unique=True),
    Column("in_app_reminders", Boolean, nullable=False),
    Column("version", Integer, nullable=False),
)
operations = table(
    "operations",
    Column("actor_id", String(36), nullable=False),
    Column("operation", String(240), nullable=False),
    Column("key", String(160), nullable=False),
    Column("request_hash", String(64), nullable=False),
    Column("response_ciphertext", Text, nullable=False),
    UniqueConstraint("actor_id", "operation", "key"),
)

IMMUTABLE = (messages, releases, withdrawals, events, audit)
