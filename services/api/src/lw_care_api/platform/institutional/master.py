"""Reviewed, dated projections; original IDs, returns and care records stay intact."""

from sqlalchemy import func, select, update

from .. import db
from ..control.service import has
from ..domain import expected, record_change, require
from . import tables as t
from .base import Service, serial


class MasterService(Service):
    async def cancel(self, identifier, body):
        row = await self.row(t.changes, identifier)
        require(
            has(
                self.actor,
                {"PLATFORM_ADMIN"} if row["kind"] == "ZONE_REGION" else {"REGISTRY_STEWARD"},
            )
        )
        expected(row, body["expected_version"])
        require(
            row["state"] in {"PROPOSED", "SCHEDULED"},
            "INVALID_STATE",
            "An applied change needs a separately reviewed reversal",
            409,
        )
        row = await self.change(t.changes, row, {"state": "CANCELLED", "active_key": None})
        await self.emit("registry.pending_change_cancelled", row, body)
        return {key: value for key, value in row.items() if key != "payload_ciphertext"}

    async def propose(self, body):
        kind = body["kind"]
        roles = {"PLATFORM_ADMIN"} if kind == "ZONE_REGION" else {"REGISTRY_STEWARD"}
        require(has(self.actor, roles))
        table = db.units if kind == "ZONE_REGION" else db.facilities
        source = await self.row(table, body["resource_id"])
        expected(source, body["expected_version"])
        require(
            body["effective_at"] is None or body["effective_at"] >= db.now(),
            "VALIDATION_FAILED",
            "Changes must be prospective, or take effect on approval",
            422,
        )
        effect = body["effective_at"] or db.now()
        if kind == "ZONE_REGION":
            target = await self.row(db.units, body["target_id"])
            require(
                source["kind"] == "ZONE"
                and target["kind"] == "REGION"
                and source["id"] != target["id"],
                "INVALID_HIERARCHY",
                "A zone can report only to a distinct region",
                409,
            )
            require(
                source["valid_from"],
                "BASELINE_REQUIRED",
                "Record the actual initial hierarchy validity before transferring this legacy unit",
                409,
            )
            body["prior_parent_id"] = source["parent_id"]
        elif kind == "FACILITY_ZONE":
            target = await self.row(db.units, body["target_id"])
            require(target["kind"] == "ZONE", "INVALID_HIERARCHY", "Select an actual zone", 409)
            body["prior_parent_id"] = source["zone_id"]
        elif kind in {"CLOSE_SITE", "LINK_DUPLICATE"}:
            facility = await self.facility(source["id"])
            require(
                body["custody_owner_id"] and len(body["continuity_plan"]) >= 5,
                "CONTINUITY_REQUIRED",
                "Nominate a clinical custodian and an actual continuity/records plan",
                409,
            )
            await self.person(body["custody_owner_id"], {"CLINICAL_GOVERNOR"}, facility)
            if kind == "LINK_DUPLICATE":
                target = await self.row(db.facilities, body["target_id"])
                require(
                    body["same_site_verified"]
                    and source["id"] != target["id"]
                    and target["identity_status"] == "VERIFIED"
                    and source["operator_id"] == target["operator_id"]
                    and source["jurisdiction"] == target["jurisdiction"],
                    "DUPLICATE_REVIEW_REQUIRED",
                    "A distinct verified canonical site, same operator/jurisdiction and actual same-site evidence are required",
                    409,
                )
        elif kind == "SITE_PROFILE":
            require(
                any(
                    body.get(key) is not None
                    for key in ("site_name", "address", "public_contact", "services")
                ),
                "VALIDATION_FAILED",
                "Supply a material profile change",
                422,
            )
            require(
                not body.get("services")
                or all(0 < len(value.strip()) <= 120 for value in body["services"]),
                "VALIDATION_FAILED",
                "Service names must be actual bounded values",
                422,
            )
        if kind in {"ZONE_REGION", "FACILITY_ZONE"}:
            require(
                target.get("valid_from")
                and target["valid_from"] <= effect
                and (not target["valid_until"] or target["valid_until"] > effect),
                "INVALID_HIERARCHY",
                "The target must be effective when the transfer takes effect",
                409,
            )
            require(
                body["prior_parent_id"] != body["target_id"],
                "NO_CHANGE",
                "The assignment is already current",
                409,
            )
        body["source_snapshot"] = source
        row = {
            "id": db.uid(),
            "kind": kind,
            "resource_id": source["id"],
            "facility_id": None if kind == "ZONE_REGION" else source["id"],
            "target_id": body["target_id"],
            "state": "PROPOSED",
            "version": 1,
            "proposer_id": self.actor["id"],
            "reviewer_id": None,
            "effective_at": effect,
            "created_at": db.now(),
            "active_key": f"{'UNIT' if kind == 'ZONE_REGION' else 'SITE'}:{source['id']}",
            "payload_ciphertext": self.seal(body),
        }
        await self.session.execute(t.changes.insert().values(**row))
        await self.emit("registry.change_proposed", row)
        return {key: value for key, value in row.items() if key != "payload_ciphertext"}

    async def review(self, identifier, body):
        row = await self.row(t.changes, identifier)
        require(
            has(
                self.actor,
                {"PLATFORM_ADMIN"} if row["kind"] == "ZONE_REGION" else {"REGISTRY_STEWARD"},
            )
        )
        require(
            row["proposer_id"] != self.actor["id"],
            "INDEPENDENT_REVIEW_REQUIRED",
            "Another authorised steward must review this change",
            409,
        )
        expected(row, body["expected_version"])
        require(
            row["state"] == "PROPOSED",
            "INVALID_STATE",
            "This change has already been reviewed",
            409,
        )
        row = await self.change(
            t.changes,
            row,
            {
                "state": "SCHEDULED" if body["decision"] == "APPROVE" else "REJECTED",
                "reviewer_id": self.actor["id"],
                "effective_at": max(row["effective_at"], db.now()),
                **({"active_key": None} if body["decision"] == "REJECT" else {}),
            },
        )
        await self.emit("registry.change_reviewed", row, body)
        return {key: value for key, value in row.items() if key != "payload_ciphertext"}

    async def apply_due(self):
        due = list(
            (
                await self.session.execute(
                    select(t.changes)
                    .where(t.changes.c.state == "SCHEDULED", t.changes.c.effective_at <= db.now())
                    .order_by(t.changes.c.effective_at, t.changes.c.id)
                    .limit(100)
                    .with_for_update()
                )
            ).mappings()
        )
        for value in due:
            change = dict(value)
            body = self.open(change["payload_ciphertext"])
            kind = change["kind"]
            table = db.units if kind == "ZONE_REGION" else db.facilities
            source = await self.row(table, change["resource_id"])
            column = "parent_id" if kind == "ZONE_REGION" else "zone_id"
            invalid = (
                kind in {"ZONE_REGION", "FACILITY_ZONE"}
                and source[column] != body["prior_parent_id"]
            )
            if kind in {"ZONE_REGION", "FACILITY_ZONE"}:
                target = await self.row(db.units, change["target_id"])
                invalid = invalid or bool(
                    target["valid_until"] and target["valid_until"] <= change["effective_at"]
                )
            if kind == "LINK_DUPLICATE":
                target = await self.row(db.facilities, change["target_id"])
                invalid = (
                    invalid
                    or target["identity_status"] != "VERIFIED"
                    or target["operator_id"] != source["operator_id"]
                    or target["jurisdiction"] != source["jurisdiction"]
                )
            if kind in {"CLOSE_SITE", "LINK_DUPLICATE"}:
                try:
                    await self.person(
                        body["custody_owner_id"],
                        {"CLINICAL_GOVERNOR"},
                        await self.facility(source["id"]),
                    )
                except Exception as exc:
                    from ..domain import RuleError

                    if not isinstance(exc, RuleError):
                        raise
                    invalid = True
            if invalid:
                if kind in {"CLOSE_SITE", "LINK_DUPLICATE"}:
                    source = await self.change(
                        db.facilities,
                        source,
                        {
                            "publication_status": "WITHDRAWN",
                            "readiness_status": "UNAVAILABLE",
                            "updated_at": db.now(),
                        },
                    )
                    existing = await self.session.scalar(
                        select(t.site_controls.c.facility_id).where(
                            t.site_controls.c.facility_id == source["id"]
                        )
                    )
                    control = {
                        "state": "CONTINUITY_REVIEW_REQUIRED",
                        "canonical_id": None,
                        "change_id": change["id"],
                        "recorded_at": db.now(),
                    }
                    if existing:
                        await self.session.execute(
                            update(t.site_controls)
                            .where(t.site_controls.c.facility_id == source["id"])
                            .values(**control)
                        )
                    else:
                        await self.session.execute(
                            t.site_controls.insert().values(facility_id=source["id"], **control)
                        )
                    await record_change(
                        self.session,
                        self.actor,
                        "Facility",
                        source,
                        "registry.continuity_exception_restricted",
                        self.correlation,
                    )
                change = await self.change(
                    t.changes,
                    change,
                    {"state": "BLOCKED_SOURCE_OR_AUTHORITY_CHANGED", "active_key": None},
                )
                await self.emit("registry.change_blocked", change)
                continue
            if kind in {"ZONE_REGION", "FACILITY_ZONE"}:
                prior = await self.session.scalar(
                    select(t.relationships.c.id)
                    .where(
                        t.relationships.c.kind == kind,
                        t.relationships.c.resource_id == source["id"],
                    )
                    .limit(1)
                )
                if not prior:
                    await self.session.execute(
                        t.relationships.insert().values(
                            id=db.uid(),
                            kind=kind,
                            resource_id=source["id"],
                            parent_id=source[column],
                            valid_from=source["valid_from"]
                            if kind == "ZONE_REGION"
                            else source["created_at"],
                            source_version=source["version"],
                            change_id=None,
                        )
                    )
                await self.session.execute(
                    t.relationships.insert().values(
                        id=db.uid(),
                        kind=kind,
                        resource_id=source["id"],
                        parent_id=change["target_id"],
                        valid_from=change["effective_at"],
                        source_version=source["version"] + 1,
                        change_id=change["id"],
                    )
                )
                values = {column: change["target_id"]}
            elif kind == "SITE_PROFILE":
                values = {
                    key: body[field]
                    for field, key in (
                        ("site_name", "name"),
                        ("address", "address"),
                        ("public_contact", "public_contact"),
                        ("services", "services"),
                    )
                    if body.get(field) is not None
                }
                values["publication_status"] = "WITHDRAWN"
            else:
                values = {
                    "identity_status": "CLOSED" if kind == "CLOSE_SITE" else "LINKED",
                    "publication_status": "WITHDRAWN",
                    "readiness_status": "UNAVAILABLE",
                }
                existing = await self.session.scalar(
                    select(t.site_controls.c.facility_id).where(
                        t.site_controls.c.facility_id == source["id"]
                    )
                )
                control = {
                    "state": "CLOSED" if kind == "CLOSE_SITE" else "DUPLICATE",
                    "canonical_id": change["target_id"] if kind == "LINK_DUPLICATE" else None,
                    "change_id": change["id"],
                    "recorded_at": db.now(),
                }
                if existing:
                    await self.session.execute(
                        update(t.site_controls)
                        .where(t.site_controls.c.facility_id == source["id"])
                        .values(**control)
                    )
                else:
                    await self.session.execute(
                        t.site_controls.insert().values(facility_id=source["id"], **control)
                    )
                await self.create_custody(
                    source["id"], change["id"], body["custody_owner_id"], body["continuity_plan"]
                )
            if table is db.facilities:
                values["updated_at"] = db.now()
            source = await self.change(table, source, values)
            await record_change(
                self.session,
                self.actor,
                "Organisation" if table is db.units else "Facility",
                source,
                "registry.reviewed_change_applied",
                self.correlation,
            )
            change = await self.change(t.changes, change, {"state": "APPLIED", "active_key": None})
            await self.emit(
                "registry.change_applied", change, {"source_version": source["version"]}
            )
        return len(due)

    async def create_custody(self, facility_id, source_id, owner_id, plan):
        from ..clinical import tables as clinical

        count = await self.session.scalar(
            select(func.count())
            .select_from(clinical.records)
            .where(
                clinical.records.c.facility_id == facility_id,
                clinical.records.c.kind.in_(
                    ["encounter", "stay", "task", "order", "referral", "procedure", "programme"]
                ),
                clinical.records.c.status.not_in(
                    ["COMPLETED", "CANCELLED", "DISCHARGED", "CLOSED", "RECEIVED", "TRANSFERRED"]
                ),
            )
        )
        row = {
            "id": db.uid(),
            "facility_id": facility_id,
            "source_id": source_id,
            "custodian_id": owner_id,
            "state": "AWAITING_ACCEPTANCE",
            "version": 1,
            "accepted_at": None,
            "plan_ciphertext": self.seal({"plan": plan}),
            "open_record_count": count,
        }
        await self.session.execute(t.custody.insert().values(**row))
        await self.emit("registry.custody_offered", row)
        return row["id"]

    async def accept_custody(self, identifier, body):
        row = await self.row(t.custody, identifier)
        require(row["custodian_id"] == self.actor["id"])
        await self.person(
            self.actor["id"], {"CLINICAL_GOVERNOR"}, await self.facility(row["facility_id"])
        )
        expected(row, body["expected_version"])
        require(
            row["state"] == "AWAITING_ACCEPTANCE",
            "INVALID_STATE",
            "This custody offer is not pending",
            409,
        )
        row = await self.change(t.custody, row, {"state": "ACCEPTED", "accepted_at": db.now()})
        await self.emit("registry.custody_accepted", row, body)
        return {
            "id": row["id"],
            "state": row["state"],
            "version": row["version"],
            "clinical_tasks_closed": False,
        }


async def refresh(database, cfg, box):
    async with database.transaction() as session:
        version = await session.scalar(select(func.max(db.schema_versions.c.version)))
        if not version or version < 6:
            return
        due = await session.scalar(
            select(t.changes.c.id)
            .where(t.changes.c.state == "SCHEDULED", t.changes.c.effective_at <= db.now())
            .limit(1)
        )
        expired = await session.scalar(
            select(db.facilities.c.id)
            .where(
                db.facilities.c.affiliation_status.in_(["ACTIVE", "CONDITIONAL"]),
                db.facilities.c.affiliation_expires_at <= db.now(),
            )
            .limit(1)
        )
        if not due and not expired:
            return
        await serial(session)
        actor = {
            "id": "INSTITUTIONAL_CLOCK",
            "authority_node_id": cfg.authority_node_id,
            "grants": [],
        }
        service = MasterService(session, cfg, box, actor, db.uid())
        await service.apply_due()
        rows = list(
            (
                await session.execute(
                    select(db.facilities)
                    .where(
                        db.facilities.c.affiliation_status.in_(["ACTIVE", "CONDITIONAL"]),
                        db.facilities.c.affiliation_expires_at <= db.now(),
                    )
                    .limit(100)
                    .with_for_update()
                )
            ).mappings()
        )
        for row in rows:
            updated = await service.change(
                db.facilities,
                dict(row),
                {
                    "affiliation_status": "EXPIRED",
                    "publication_status": "WITHDRAWN",
                    "updated_at": db.now(),
                },
            )
            await record_change(
                session, actor, "Facility", updated, "affiliation.expired", service.correlation
            )
        pending = await session.scalar(
            select(t.changes.c.id)
            .where(t.changes.c.state == "SCHEDULED", t.changes.c.effective_at <= db.now())
            .limit(1)
        )
        pending_expiry = await session.scalar(
            select(db.facilities.c.id)
            .where(
                db.facilities.c.affiliation_status.in_(["ACTIVE", "CONDITIONAL"]),
                db.facilities.c.affiliation_expires_at <= db.now(),
            )
            .limit(1)
        )
    require(
        not pending and not pending_expiry,
        "MASTER_PROJECTION_PENDING",
        "Dated changes are still reconciling; retry before using current scope",
        503,
    )


async def historical_parent(session, kind, identifier, at, fallback):
    version = await session.scalar(select(func.max(db.schema_versions.c.version)))
    if not version or version < 6:
        return fallback
    rows = list(
        (
            await session.execute(
                select(t.relationships)
                .where(t.relationships.c.kind == kind, t.relationships.c.resource_id == identifier)
                .order_by(t.relationships.c.valid_from.desc())
            )
        ).mappings()
    )
    if not rows:
        return fallback
    row = next((row for row in rows if row["valid_from"] <= at), None)
    require(
        row,
        "HISTORICAL_SCOPE_UNRESOLVED",
        "No evidenced assignment covers this historical instant",
        409,
    )
    return row["parent_id"]


async def accepting_new_care(session, facility_id):
    version = await session.scalar(select(func.max(db.schema_versions.c.version)))
    if version and version >= 6:
        control = await session.scalar(
            select(t.site_controls.c.state).where(t.site_controls.c.facility_id == facility_id)
        )
        require(
            control is None,
            "SITE_NOT_ACCEPTING_NEW_CARE",
            "The site is closed or linked; continue existing care under the accepted custody plan",
            409,
        )
