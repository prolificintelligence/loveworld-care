"""Additive lifecycle projections and immutable decisions/source facts."""

from sqlalchemy import (
    JSON,
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
    return Table("institutional_" + name, metadata, identifier(), *columns)


changes = table(
    "changes",
    Column("kind", String(40), nullable=False),
    Column("resource_id", String(36), nullable=False),
    Column("facility_id", String(36)),
    Column("target_id", String(36)),
    Column("state", String(40), nullable=False),
    Column("version", Integer, nullable=False),
    Column("proposer_id", String(36), nullable=False),
    Column("reviewer_id", String(36)),
    Column("effective_at", String(40), nullable=False),
    Column("created_at", String(40), nullable=False),
    Column("active_key", String(90), unique=True),
    Column("payload_ciphertext", Text, nullable=False),
)
relationships = table(
    "relationships",
    Column("kind", String(20), nullable=False),
    Column("resource_id", String(36), nullable=False),
    Column("parent_id", String(36), nullable=False),
    Column("valid_from", String(40), nullable=False),
    Column("source_version", Integer, nullable=False),
    Column("change_id", String(36)),
    UniqueConstraint("kind", "resource_id", "valid_from"),
)
site_controls = Table(
    "institutional_site_controls",
    metadata,
    Column("facility_id", ForeignKey(f"{SCHEMA}.facilities.id"), primary_key=True),
    Column("state", String(30), nullable=False),
    Column("canonical_id", String(36)),
    Column("change_id", String(36), nullable=False),
    Column("recorded_at", String(40), nullable=False),
)
custody = table(
    "custody",
    Column("facility_id", String(36), nullable=False),
    Column("source_id", String(36), nullable=False),
    Column("custodian_id", String(36), nullable=False),
    Column("state", String(30), nullable=False),
    Column("version", Integer, nullable=False),
    Column("accepted_at", String(40)),
    Column("plan_ciphertext", Text, nullable=False),
    Column("open_record_count", Integer, nullable=False),
)
cases = table(
    "cases",
    Column("facility_id", ForeignKey(f"{SCHEMA}.facilities.id"), nullable=False),
    Column("kind", String(30), nullable=False),
    Column("state", String(40), nullable=False),
    Column("version", Integer, nullable=False),
    Column("criteria_id", String(36), nullable=False),
    Column("criteria_snapshot", JSON, nullable=False),
    Column("base_decision_id", String(36)),
    Column("created_by", String(36), nullable=False),
    Column("respondent_id", String(36), nullable=False),
    Column("inspector_id", String(36)),
    Column("reviewer_id", String(36)),
    Column("recommendation", String(30)),
    Column("pending_assignments", JSON, nullable=False, default=dict),
    Column("due_at", String(40), nullable=False),
    Column("created_at", String(40), nullable=False),
    Column("details_ciphertext", Text, nullable=False),
)
findings = table(
    "findings",
    Column("case_id", ForeignKey(f"{SCHEMA}.institutional_cases.id"), nullable=False),
    Column("criterion", String(120), nullable=False),
    Column("outcome", String(30), nullable=False),
    Column("state", String(30), nullable=False),
    Column("owner_id", String(36), nullable=False),
    Column("due_at", String(40), nullable=False),
    Column("version", Integer, nullable=False),
    Column("inspector_id", String(36), nullable=False),
    Column("details_ciphertext", Text, nullable=False),
)
responses = table(
    "responses",
    Column("finding_id", ForeignKey(f"{SCHEMA}.institutional_findings.id"), nullable=False),
    Column("author_id", String(36), nullable=False),
    Column("created_at", String(40), nullable=False),
    Column("details_ciphertext", Text, nullable=False),
)
case_files = table(
    "case_files",
    Column("case_id", ForeignKey(f"{SCHEMA}.institutional_cases.id"), nullable=False),
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
decisions = table(
    "decisions",
    Column("case_id", ForeignKey(f"{SCHEMA}.institutional_cases.id"), nullable=False),
    Column("facility_id", String(36), nullable=False),
    Column("decider_id", String(36), nullable=False),
    Column("action", String(30), nullable=False),
    Column("effective_at", String(40), nullable=False),
    Column("expires_at", String(40)),
    Column("created_at", String(40), nullable=False),
    Column("details_ciphertext", Text, nullable=False),
)
notices = table(
    "notices",
    Column("case_id", ForeignKey(f"{SCHEMA}.institutional_cases.id"), nullable=False),
    Column("recipient_id", String(36), nullable=False),
    Column("issuer_id", String(36), nullable=False),
    Column("response_due", String(40), nullable=False),
    Column("created_at", String(40), nullable=False),
    Column("details_ciphertext", Text, nullable=False),
)
receipts = table(
    "receipts",
    Column("resource_id", String(36), nullable=False),
    Column("actor_id", String(36), nullable=False),
    Column("kind", String(40), nullable=False),
    Column("recorded_at", String(40), nullable=False),
    Column("details_ciphertext", Text, nullable=False),
)
journal = table(
    "journal",
    Column("resource_id", String(36), nullable=False),
    Column("facility_id", String(36)),
    Column("action", String(80), nullable=False),
    Column("actor_id", String(80), nullable=False),
    Column("version", Integer, nullable=False),
    Column("recorded_at", String(40), nullable=False),
    Column("correlation_id", String(36), nullable=False),
    Column("payload_ciphertext", Text, nullable=False),
)
articles = table(
    "articles",
    Column("facility_id", String(36)),
    Column("created_by", String(36), nullable=False),
    Column("version", Integer, nullable=False),
    Column("latest_revision_id", String(36)),
    Column("published_revision_id", String(36)),
    Column("created_at", String(40), nullable=False),
)
revisions = table(
    "content_revisions",
    Column("article_id", ForeignKey(f"{SCHEMA}.institutional_articles.id"), nullable=False),
    Column("sequence", Integer, nullable=False),
    Column("author_id", String(36), nullable=False),
    Column("title", String(250), nullable=False),
    Column("kind", String(40), nullable=False),
    Column("audience", String(20), nullable=False),
    Column("language", String(40), nullable=False),
    Column("jurisdictions", JSON, nullable=False),
    Column("valid_from", String(40), nullable=False),
    Column("valid_until", String(40), nullable=False),
    Column("review_due_at", String(40), nullable=False),
    Column("sha256", String(64), nullable=False),
    Column("created_at", String(40), nullable=False),
    Column("content_ciphertext", Text, nullable=False),
    UniqueConstraint("article_id", "sequence"),
)
content_states = Table(
    "institutional_content_states",
    metadata,
    Column(
        "revision_id", ForeignKey(f"{SCHEMA}.institutional_content_revisions.id"), primary_key=True
    ),
    Column("state", String(30), nullable=False),
    Column("reviewer_id", String(36)),
    Column("publisher_id", String(36)),
    Column("published_at", String(40)),
    Column("withdrawal_reason", Text),
)
content_reviews = table(
    "content_reviews",
    Column(
        "revision_id", ForeignKey(f"{SCHEMA}.institutional_content_revisions.id"), nullable=False
    ),
    Column("reviewer_id", String(36), nullable=False),
    Column("decision", String(20), nullable=False),
    Column("qualification_reference", Text, nullable=False),
    Column("created_at", String(40), nullable=False),
    Column("evidence_ciphertext", Text, nullable=False),
    UniqueConstraint("revision_id", "reviewer_id"),
)
deliveries = table(
    "content_deliveries",
    Column("article_id", String(36), nullable=False),
    Column("revision_id", String(36), nullable=False),
    Column("recipient_id", ForeignKey(f"{SCHEMA}.accounts.id"), nullable=False),
    Column("created_by", String(36), nullable=False),
    Column("state", String(40), nullable=False),
    Column("successor_revision_id", String(36)),
    Column("created_at", String(40), nullable=False),
    UniqueConstraint("revision_id", "recipient_id"),
)
content_receipts = table(
    "content_receipts",
    Column(
        "delivery_id", ForeignKey(f"{SCHEMA}.institutional_content_deliveries.id"), nullable=False
    ),
    Column("revision_id", String(36), nullable=False),
    Column("actor_id", String(36), nullable=False),
    Column("kind", String(30), nullable=False),
    Column("recorded_at", String(40), nullable=False),
    Column("feedback_ciphertext", Text),
)
Index("ix_institutional_changes_due", changes.c.state, changes.c.effective_at)
Index("ix_institutional_case_scope", cases.c.facility_id, cases.c.state)
Index("ix_institutional_delivery_recipient", deliveries.c.recipient_id, deliveries.c.id)
IMMUTABLE = (
    relationships,
    responses,
    case_files,
    decisions,
    notices,
    receipts,
    journal,
    revisions,
    content_reviews,
    content_receipts,
)
