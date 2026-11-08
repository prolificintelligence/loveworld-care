"""Current scope, protected facts and versioned lifecycle projections."""

import json

from sqlalchemy import false, or_, select, text, update

from .. import db
from ..control.service import ControlService, canonical, has
from ..domain import require, scoped
from . import tables as t


async def serial(session):
    if session.bind.dialect.name == "postgresql":
        await session.execute(text("SELECT pg_advisory_xact_lock(782025014)"))


def predicate(actor, roles, table=db.facilities, column="id"):
    clauses = []
    for grant in actor["grants"]:
        if grant["role"] not in roles:
            continue
        if grant["scope_type"] == "GLOBAL":
            return True
        key = table.c[column]
        if grant["scope_type"] == "FACILITY":
            clauses.append(key == grant["scope_id"])
        if grant["scope_type"] == "ZONE":
            clauses.append(
                key.in_(
                    select(db.facilities.c.id).where(db.facilities.c.zone_id == grant["scope_id"])
                )
            )
        if grant["scope_type"] == "REGION":
            clauses.append(
                key.in_(
                    select(db.facilities.c.id).where(
                        db.facilities.c.zone_id.in_(
                            select(db.units.c.id).where(db.units.c.parent_id == grant["scope_id"])
                        )
                    )
                )
            )
    return or_(*clauses) if clauses else false()


class Service(ControlService):
    def open(self, value):
        return json.loads(self.box.decrypt(value))

    def seal(self, value):
        return self.box.encrypt(canonical(value))

    async def row(self, table, identifier, *, lock=True):
        query = select(table).where(table.c.id == str(identifier))
        row = (
            (await self.session.execute(query.with_for_update() if lock else query))
            .mappings()
            .first()
        )
        require(row, "NOT_FOUND_OR_NOT_PERMITTED", "Record unavailable", 404)
        return dict(row)

    async def facility(self, identifier, roles=None, *, lock=False):
        row = await self.row(db.facilities, identifier, lock=lock)
        row["region_id"] = await self.session.scalar(
            select(db.units.c.parent_id).where(db.units.c.id == row["zone_id"])
        )
        if roles is not None:
            require(scoped(self.actor, roles, row))
        return row

    async def person(self, identifier, roles, facility=None):
        account = await self.session.scalar(
            select(db.accounts.c.id).where(
                db.accounts.c.id == str(identifier), db.accounts.c.active.is_(True)
            )
        )
        require(account, "INVALID_ASSIGNEE", "The named person must have an active account", 409)
        grants = list(
            (
                await self.session.execute(
                    select(db.grants).where(
                        db.grants.c.account_id == str(identifier),
                        db.grants.c.role.in_(roles),
                        db.grants.c.revoked.is_(False),
                        db.grants.c.valid_from <= db.now(),
                        db.grants.c.valid_until > db.now(),
                    )
                )
            ).mappings()
        )
        actor = {"grants": grants}
        require(
            scoped(actor, roles, facility) if facility else has(actor, roles),
            "INVALID_ASSIGNEE",
            "Current authority for this scope is required",
            409,
        )

    async def change(self, table, row, values):
        values = {**values, "version": row["version"] + 1}
        result = await self.session.execute(
            update(table)
            .where(table.c.id == row["id"], table.c.version == row["version"])
            .values(**values)
        )
        require(
            result.rowcount == 1, "VERSION_CONFLICT", "The record changed; reload and review", 412
        )
        return {**row, **values}

    async def emit(self, action, row, details=None, facility_id=None):
        await self.session.execute(
            t.journal.insert().values(
                id=db.uid(),
                resource_id=row["id"],
                facility_id=facility_id or row.get("facility_id"),
                action=action,
                actor_id=self.actor["id"],
                version=row.get("version", 1),
                recorded_at=db.now(),
                correlation_id=self.correlation,
                payload_ciphertext=self.seal(
                    {
                        "snapshot": row,
                        "details": details,
                        "authority_node_id": self.cfg.authority_node_id,
                        "contract": "LWH-EXT-INSTITUTIONAL-001",
                    }
                ),
            )
        )
        await self.audit(action, row["id"])

    async def case(self, identifier, *, write=False):
        row = await self.row(t.cases, identifier, lock=write)
        facility = await self.facility(row["facility_id"], lock=write)
        assigned = (
            self.actor["id"]
            in {
                row["inspector_id"],
                row["reviewer_id"],
                row["respondent_id"],
            }
            or self.actor["id"] in row["pending_assignments"].values()
        )
        roles = {
            "REGISTRY_STEWARD",
            "FACILITY_ADMIN",
            "STANDARDS_REVIEWER",
            "STANDARDS_DECIDER",
            "ZONE_COORDINATOR",
            "REGIONAL_COORDINATOR",
        }
        require(
            assigned or scoped(self.actor, roles, facility),
            "NOT_FOUND_OR_NOT_PERMITTED",
            "Case unavailable",
            404,
        )
        for kind, person in row["pending_assignments"].items():
            if person == self.actor["id"]:
                await self.person(
                    person,
                    {
                        {
                            "RESPONDENT": "FACILITY_ADMIN",
                            "INSPECTOR": "INSPECTOR",
                            "REVIEWER": "STANDARDS_REVIEWER",
                        }[kind]
                    },
                    facility,
                )
        if self.actor["id"] == row["inspector_id"]:
            await self.person(self.actor["id"], {"INSPECTOR"}, facility)
        if self.actor["id"] == row["reviewer_id"]:
            await self.person(self.actor["id"], {"STANDARDS_REVIEWER"}, facility)
        if self.actor["id"] == row["respondent_id"]:
            await self.person(self.actor["id"], {"FACILITY_ADMIN"}, facility)
        return row, facility

    async def article(self, identifier, roles=None):
        row = await self.row(t.articles, identifier)
        if row["facility_id"]:
            await self.facility(row["facility_id"], roles)
        elif roles:
            require(has(self.actor, roles))
        return row

    async def valid_files(self, case, identifiers, criterion=None):
        for identifier in identifiers:
            record = (
                (
                    await self.session.execute(
                        select(t.case_files).where(t.case_files.c.id == str(identifier))
                    )
                )
                .mappings()
                .first()
            )
            if record:
                require(
                    record["case_id"] == case["id"],
                    "EVIDENCE_SCOPE_MISMATCH",
                    "Evidence belongs to another case",
                    409,
                )
            else:
                record = (
                    (
                        await self.session.execute(
                            select(db.evidence).where(db.evidence.c.id == str(identifier))
                        )
                    )
                    .mappings()
                    .first()
                )
                application = (
                    await self.session.scalar(
                        select(db.applications.c.facility_id).where(
                            db.applications.c.id == record["application_id"]
                        )
                    )
                    if record
                    else None
                )
                require(
                    record and application == case["facility_id"],
                    "EVIDENCE_SCOPE_MISMATCH",
                    "Evidence belongs to another facility",
                    409,
                )
            require(
                record["scan_status"] == "CLEAN" and record["expires_at"] > db.now(),
                "EVIDENCE_NOT_CURRENT",
                "Current scanned evidence is required",
                409,
            )
            require(
                criterion is None or record["criterion"] == criterion,
                "EVIDENCE_SCOPE_MISMATCH",
                "Evidence does not address this criterion",
                409,
            )
