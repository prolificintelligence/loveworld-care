"""Frozen reviewed text, current publication and attributable portal distribution."""

import hashlib

from sqlalchemy import select, update

from .. import db
from ..control.service import canonical, has
from ..domain import expected, require, scoped
from . import tables as t
from .base import Service

EDITORS = {"CONTENT_EDITOR"}
PUBLISHERS = {"CONTENT_PUBLISHER"}
REVIEWERS = {"CLINICAL_GOVERNOR", "POLICY_OWNER"}


def reviewer_roles(kind):
    return (
        {"CLINICAL_GOVERNOR"}
        if kind in {"HEALTH_EDUCATION", "CLINICAL_GUIDANCE"}
        else {"POLICY_OWNER"}
    )


class KnowledgeService(Service):
    async def revise(self, body, identifier=None):
        require(
            body["valid_from"] < body["valid_until"]
            and body["valid_from"] < body["review_due_at"] <= body["valid_until"]
            and body["valid_until"] > db.now(),
            "INVALID_VALIDITY",
            "Use explicit content, review and expiry dates",
            422,
        )
        require(
            all(0 < len(value.strip()) <= 80 for value in body["jurisdictions"])
            and len(set(body["jurisdictions"])) == len(body["jurisdictions"]),
            "INVALID_APPLICABILITY",
            "Use unique actual jurisdiction identifiers",
            422,
        )
        require(
            all(str(source["url"]).startswith("https://") for source in body["sources"])
            and str(body["support_url"]).startswith("https://"),
            "INVALID_REFERENCE",
            "Source and support links must use HTTPS",
            422,
        )
        if identifier:
            article = await self.article(identifier, EDITORS)
            expected(article, body["expected_version"])
            require(
                not article["published_revision_id"] or len(body["correction_summary"]) >= 5,
                "CORRECTION_SUMMARY_REQUIRED",
                "A replacement publication needs a reviewed public explanation of the change",
                409,
            )
            require(
                body["facility_id"] == article["facility_id"],
                "SCOPE_IMMUTABLE",
                "Create a separately reviewed item for a different scope",
                409,
            )
            previous = await self.row(t.revisions, article["latest_revision_id"], lock=False)
            sequence = previous["sequence"] + 1
        else:
            if body["facility_id"]:
                await self.facility(body["facility_id"], EDITORS)
            else:
                require(has(self.actor, EDITORS))
            article = {
                "id": db.uid(),
                "facility_id": body["facility_id"],
                "created_by": self.actor["id"],
                "version": 0,
                "latest_revision_id": None,
                "published_revision_id": None,
                "created_at": db.now(),
            }
            await self.session.execute(t.articles.insert().values(**article))
            sequence = 1
        revision = {
            "id": db.uid(),
            "article_id": article["id"],
            "sequence": sequence,
            "author_id": self.actor["id"],
            "title": body["title"],
            "kind": body["kind"],
            "audience": body["audience"],
            "language": body["language"],
            "jurisdictions": body["jurisdictions"],
            "valid_from": body["valid_from"],
            "valid_until": body["valid_until"],
            "review_due_at": body["review_due_at"],
            "sha256": hashlib.sha256(canonical(body).encode()).hexdigest(),
            "created_at": db.now(),
            "content_ciphertext": self.seal(body),
        }
        await self.session.execute(t.revisions.insert().values(**revision))
        await self.session.execute(
            t.content_states.insert().values(revision_id=revision["id"], state="DRAFT")
        )
        article = await self.change(t.articles, article, {"latest_revision_id": revision["id"]})
        await self.emit("knowledge.revision_created", article, {"revision": revision})
        return {
            **article,
            "revision_id": revision["id"],
            "sequence": sequence,
            "state": "DRAFT",
            "prior_publication_preserved": bool(article["published_revision_id"]),
        }

    async def revision(self, article, identifier=None):
        row = await self.row(t.revisions, identifier or article["latest_revision_id"], lock=False)
        require(
            row["article_id"] == article["id"],
            "CONTENT_INTEGRITY_FAILURE",
            "The article and frozen revision do not agree",
            503,
        )
        state = (
            (
                await self.session.execute(
                    select(t.content_states).where(t.content_states.c.revision_id == row["id"])
                )
            )
            .mappings()
            .one()
        )
        return row, dict(state)

    async def submit(self, identifier, body):
        article = await self.article(identifier, EDITORS)
        expected(article, body["expected_version"])
        revision, state = await self.revision(article)
        require(
            state["state"] == "DRAFT", "INVALID_STATE", "Only a frozen draft can be submitted", 409
        )
        await self.session.execute(
            update(t.content_states)
            .where(t.content_states.c.revision_id == revision["id"])
            .values(state="IN_REVIEW")
        )
        article = await self.change(t.articles, article, {})
        await self.emit("knowledge.submitted", article, body)
        return {**article, "state": "IN_REVIEW"}

    async def review_content(self, identifier, body):
        article = await self.article(identifier, REVIEWERS)
        expected(article, body["expected_version"])
        revision, state = await self.revision(article)
        await self.authorise(article, reviewer_roles(revision["kind"]))
        require(
            state["state"] == "IN_REVIEW" and revision["author_id"] != self.actor["id"],
            "INDEPENDENT_REVIEW_REQUIRED",
            "Review the submitted frozen version independently",
            409,
        )
        review = {
            "id": db.uid(),
            "revision_id": revision["id"],
            "reviewer_id": self.actor["id"],
            "decision": body["decision"],
            "qualification_reference": body["qualification_reference"],
            "created_at": db.now(),
            "evidence_ciphertext": self.seal(body),
        }
        await self.session.execute(t.content_reviews.insert().values(**review))
        await self.session.execute(
            update(t.content_states)
            .where(t.content_states.c.revision_id == revision["id"])
            .values(
                state="APPROVED" if body["decision"] == "APPROVE" else "REJECTED",
                reviewer_id=self.actor["id"],
            )
        )
        article = await self.change(t.articles, article, {})
        await self.emit("knowledge.review_recorded", article, {"review": review})
        return {**article, "state": "APPROVED" if body["decision"] == "APPROVE" else "REJECTED"}

    async def authorise(self, article, roles):
        if article["facility_id"]:
            await self.facility(article["facility_id"], roles)
        else:
            require(has(self.actor, roles))

    async def publish(self, identifier, body):
        article = await self.article(identifier, PUBLISHERS)
        expected(article, body["expected_version"])
        revision, state = await self.revision(article)
        require(
            state["state"] == "APPROVED"
            and self.actor["id"] not in {revision["author_id"], state["reviewer_id"]},
            "INDEPENDENT_PUBLICATION_REQUIRED",
            "The exact approved version needs a distinct authorised publisher",
            409,
        )
        require(
            min(revision["valid_until"], revision["review_due_at"]) > db.now(),
            "CONTENT_EXPIRED",
            "The approved version is expired or due for review",
            409,
        )
        await self.person(
            state["reviewer_id"],
            reviewer_roles(revision["kind"]),
            await self.facility(article["facility_id"]) if article["facility_id"] else None,
        )
        old = article["published_revision_id"]
        if old:
            await self.session.execute(
                update(t.content_states)
                .where(t.content_states.c.revision_id == old)
                .values(state="SUPERSEDED")
            )
            await self.session.execute(
                update(t.deliveries)
                .where(t.deliveries.c.article_id == article["id"])
                .values(state="UPDATE_REQUIRED", successor_revision_id=revision["id"])
            )
        await self.session.execute(
            update(t.content_states)
            .where(t.content_states.c.revision_id == revision["id"])
            .values(state="PUBLISHED", publisher_id=self.actor["id"], published_at=db.now())
        )
        article = await self.change(t.articles, article, {"published_revision_id": revision["id"]})
        await self.emit("knowledge.published", article, body)
        return {
            **article,
            "state": "PUBLISHED",
            "valid_from": revision["valid_from"],
            "outcome_inferred": False,
        }

    async def withdraw(self, identifier, body):
        article = await self.article(identifier, PUBLISHERS)
        expected(article, body["expected_version"])
        require(
            article["published_revision_id"],
            "INVALID_STATE",
            "No current publication is recorded",
            409,
        )
        revision, state = await self.revision(article, article["published_revision_id"])
        require(
            state["state"] == "PUBLISHED", "INVALID_STATE", "This version is already withdrawn", 409
        )
        await self.session.execute(
            update(t.content_states)
            .where(t.content_states.c.revision_id == revision["id"])
            .values(
                state="WITHDRAWN",
                withdrawal_reason="Withdrawn by the authorised publisher; review current approved alternatives.",
            )
        )
        await self.session.execute(
            update(t.deliveries)
            .where(t.deliveries.c.article_id == article["id"])
            .values(state="WITHDRAWN", successor_revision_id=None)
        )
        article = await self.change(t.articles, article, {})
        await self.emit("knowledge.withdrawn", article, body)
        return {**article, "state": "WITHDRAWN", "original_body_public": False}

    async def distribute(self, identifier, body):
        article = await self.article(identifier, PUBLISHERS)
        expected(article, body["expected_version"])
        revision, state = await self.revision(article, article["published_revision_id"])
        require(
            current(revision, state),
            "CONTENT_NOT_CURRENT",
            "Distribute only the current approved and effective version",
            409,
        )
        count = 0
        for recipient in set(body["recipient_ids"]):
            if article["facility_id"]:
                await self.person(
                    recipient, STAFF_ROLES, await self.facility(article["facility_id"])
                )
            else:
                eligible = await self.session.scalar(
                    select(db.accounts.c.id)
                    .join(db.grants)
                    .where(
                        db.accounts.c.id == recipient,
                        db.accounts.c.active.is_(True),
                        db.grants.c.role.in_(STAFF_ROLES),
                        db.grants.c.revoked.is_(False),
                        db.grants.c.valid_from <= db.now(),
                        db.grants.c.valid_until > db.now(),
                    )
                    .limit(1)
                )
                require(
                    eligible,
                    "INVALID_RECIPIENT",
                    "Select an active, currently authorised staff recipient",
                    409,
                )
            existing = await self.session.scalar(
                select(t.deliveries.c.id).where(
                    t.deliveries.c.revision_id == revision["id"],
                    t.deliveries.c.recipient_id == recipient,
                )
            )
            if existing:
                continue
            await self.session.execute(
                t.deliveries.insert().values(
                    id=db.uid(),
                    article_id=article["id"],
                    revision_id=revision["id"],
                    recipient_id=recipient,
                    created_by=self.actor["id"],
                    state="AVAILABLE_IN_PORTAL",
                    successor_revision_id=None,
                    created_at=db.now(),
                )
            )
            count += 1
        article = await self.change(t.articles, article, {})
        await self.emit("knowledge.portal_distribution_created", article, body)
        return {
            **article,
            "new_portal_deliveries": count,
            "external_delivery_attempted": False,
            "engagement_or_health_outcome_inferred": False,
        }

    async def content_receipt(self, identifier, body):
        delivery = await self.row(t.deliveries, identifier)
        require(
            delivery["recipient_id"] == self.actor["id"],
            "NOT_FOUND_OR_NOT_PERMITTED",
            "Delivery unavailable",
            404,
        )
        article = await self.article(delivery["article_id"])
        await self.reader(article)
        require(
            body["revision_id"] == article["published_revision_id"],
            "CONTENT_CHANGED",
            "Review and acknowledge the actual current replacement version",
            409,
        )
        revision, state = await self.revision(article, body["revision_id"])
        require(
            revision["kind"] != "CLINICAL_GUIDANCE"
            or body["jurisdiction"] in revision["jurisdictions"],
            "APPLICABILITY_REQUIRED",
            "Check the explicit applicable jurisdiction for this guidance",
            409,
        )
        require(
            current(revision, state),
            "CONTENT_NOT_CURRENT",
            "Expired, superseded or withdrawn content cannot be acknowledged as current",
            409,
        )
        value = {
            "id": db.uid(),
            "delivery_id": delivery["id"],
            "revision_id": revision["id"],
            "actor_id": self.actor["id"],
            "kind": body["kind"],
            "recorded_at": db.now(),
            "feedback_ciphertext": self.seal(
                {"feedback": body["feedback"], "evidence": body["evidence"]}
            ),
        }
        await self.session.execute(t.content_receipts.insert().values(**value))
        await self.session.execute(
            update(t.deliveries)
            .where(t.deliveries.c.id == delivery["id"])
            .values(
                state="ACKNOWLEDGED"
                if body["kind"] == "ACKNOWLEDGED"
                else "READ"
                if body["kind"] == "READ"
                else delivery["state"]
            )
        )
        await self.emit("knowledge.recipient_receipt", value, facility_id=article["facility_id"])
        return {
            "id": value["id"],
            "state": body["kind"],
            "revision_id": revision["id"],
            "understanding_self_reported": body["kind"] == "SELF_REPORTED_UNDERSTANDING",
            "clinical_outcome_inferred": False,
        }

    async def reader(self, article):
        if article["facility_id"]:
            facility = await self.facility(article["facility_id"])
            require(scoped(self.actor, STAFF_ROLES, facility))
        else:
            require(any(grant["role"] in STAFF_ROLES for grant in self.actor["grants"]))


STAFF_ROLES = {
    "PLATFORM_ADMIN",
    "REGISTRY_STEWARD",
    "FACILITY_ADMIN",
    "REGIONAL_COORDINATOR",
    "ZONE_COORDINATOR",
    "INSPECTOR",
    "STANDARDS_REVIEWER",
    "STANDARDS_DECIDER",
    "CLINICAL_GOVERNOR",
    "CLINICAL_STAFF",
    "DATA_GOVERNOR",
    "REPORTING_OFFICER",
    "DATA_REVIEWER",
    "DATA_ANALYST",
    "EXECUTIVE_VIEWER",
    "PROGRAMME_OWNER",
    "SAFETY_REPORTER",
    "SAFETY_REVIEWER",
    "PRIVACY_OFFICER",
    "FINANCE_GOVERNOR",
    "IDENTITY_REVIEWER",
    "CONTENT_EDITOR",
    "POLICY_OWNER",
    "CONTENT_PUBLISHER",
}


def current(revision, state):
    return state["state"] == "PUBLISHED" and revision["valid_from"] <= db.now() < min(
        revision["valid_until"], revision["review_due_at"]
    )
