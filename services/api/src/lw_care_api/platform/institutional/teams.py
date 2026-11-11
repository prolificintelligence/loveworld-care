"""Explicit delivery-team identity and accepted lead; protected journal facts, not accounts."""

from sqlalchemy import and_, func, select

from .. import db
from ..domain import expected, require
from . import tables as t
from .base import Service

CONTRACT = "LWH-EXT-DELIVERY-TEAM-001"
ACTIONS = ("standards.team_proposed", "standards.team_accepted", "standards.team_retired")
READERS = {"FACILITY_ADMIN", "INSPECTOR", "STANDARDS_REVIEWER", "STANDARDS_DECIDER"}


async def team_record(service, identifier, version=None):
    query = select(t.journal).where(
        t.journal.c.resource_id == str(identifier), t.journal.c.action.in_(ACTIONS)
    )
    if version is not None:
        query = query.where(t.journal.c.version == version)
    row = (
        (await service.session.execute(query.order_by(t.journal.c.version.desc()).limit(1)))
        .mappings()
        .first()
    )
    require(row, "NOT_FOUND_OR_NOT_PERMITTED", "Delivery team unavailable", 404)
    value = service.open(row["payload_ciphertext"])["snapshot"]
    require(
        value.get("contract") == CONTRACT,
        "TEAM_HISTORY_UNAVAILABLE",
        "Team contract unavailable",
        409,
    )
    return value


async def bound_team(service, finding, case, body):
    identifier, version = body.get("owner_team_id"), body.get("owner_team_version")
    require(
        bool(identifier) == bool(version),
        "VALIDATION_FAILED",
        "Choose both the actual team and its current version",
        422,
    )
    if not identifier:
        return None
    team = await team_record(service, identifier)
    require(
        team["facility_id"] == case["facility_id"],
        "NOT_FOUND_OR_NOT_PERMITTED",
        "Delivery team unavailable",
        404,
    )
    expected(team, version)
    require(
        team["state"] == "ACCEPTED"
        and team["lead_account_id"]
        == team.get("accepted_by")
        == finding["owner_id"]
        == case["respondent_id"],
        "TEAM_ACCEPTANCE_REQUIRED",
        "The actual current finding owner must personally accept leadership of this team",
        409,
    )
    await service.person(
        team["lead_account_id"], {"FACILITY_ADMIN"}, await service.facility(team["facility_id"])
    )
    return team


async def verify_plan_team(service, plan, finding, case, *, current=True):
    binding = plan.get("owner_team")
    if not binding:
        return
    # Completed facts retain the original accepted version; new work needs current acceptance.
    team = await team_record(service, binding["id"], None if current else binding["version"])
    require(
        team == binding
        and team["state"] == "ACCEPTED"
        and team["facility_id"] == case["facility_id"]
        and team["lead_account_id"] == team.get("accepted_by") == finding["owner_id"],
        "STALE_DELIVERY_TEAM",
        "Team changed; personally accept the current team and agree fresh corrective work",
        409,
    )
    if current:
        require(
            team["lead_account_id"] == case["respondent_id"],
            "STALE_DELIVERY_TEAM",
            "The current respondent must accept team accountability",
            409,
        )
        await service.person(
            team["lead_account_id"], {"FACILITY_ADMIN"}, await service.facility(team["facility_id"])
        )


class TeamService(Service):
    async def scope(self, identifier, *, write=False):
        team = await team_record(self, identifier)
        await self.facility(team["facility_id"], {"FACILITY_ADMIN"} if write else READERS)
        return team

    async def propose(self, body, identifier=None):
        facility = await self.facility(body["facility_id"], {"FACILITY_ADMIN"})
        if identifier:
            old = await self.scope(identifier, write=True)
            require(
                old["facility_id"] == facility["id"],
                "VALIDATION_FAILED",
                "A team cannot move to another facility",
                422,
            )
            expected(old, body["expected_version"])
            require(
                old["state"] != "RETIRED",
                "INVALID_STATE",
                "A retired team retains its original identity",
                409,
            )
        else:
            old = {"id": db.uid(), "version": 0}
        await self.person(body["lead_account_id"], {"FACILITY_ADMIN"}, facility)
        team = {
            "id": old["id"],
            "version": old["version"] + 1,
            "contract": CONTRACT,
            "facility_id": facility["id"],
            "name": body["name"],
            "purpose": body["purpose"],
            "authority_reference": body["authority_reference"],
            "lead_account_id": body["lead_account_id"],
            "proposed_by": self.actor["id"],
            "state": "PROPOSED",
        }
        await self.emit(ACTIONS[0], team, {"evidence": body["evidence"]}, facility["id"])
        return team

    async def accept(self, identifier, body):
        team = await self.scope(identifier, write=True)
        expected(team, body["expected_version"])
        require(self.actor["id"] == team["lead_account_id"])
        require(
            team["state"] == "PROPOSED",
            "INVALID_STATE",
            "Accept the exact current team proposal",
            409,
        )
        await self.person(
            self.actor["id"], {"FACILITY_ADMIN"}, await self.facility(team["facility_id"])
        )
        team = {
            **team,
            "version": team["version"] + 1,
            "state": "ACCEPTED",
            "accepted_by": self.actor["id"],
            "accepted_at": db.now(),
        }
        await self.emit(ACTIONS[1], team, {"evidence": body["evidence"]}, team["facility_id"])
        return team

    async def retire(self, identifier, body):
        team = await self.scope(identifier, write=True)
        expected(team, body["expected_version"])
        require(team["state"] != "RETIRED", "INVALID_STATE", "Team already retired", 409)
        team = {
            **team,
            "version": team["version"] + 1,
            "state": "RETIRED",
            "retired_by": self.actor["id"],
        }
        await self.emit(ACTIONS[2], team, {"evidence": body["evidence"]}, team["facility_id"])
        return team

    async def list(self, facility_id, after):
        await self.facility(facility_id, READERS)
        latest = (
            select(t.journal.c.resource_id, func.max(t.journal.c.version).label("version"))
            .where(t.journal.c.action.in_(ACTIONS), t.journal.c.facility_id == str(facility_id))
            .group_by(t.journal.c.resource_id)
            .subquery()
        )
        rows = (
            (
                await self.session.execute(
                    select(t.journal)
                    .join(
                        latest,
                        and_(
                            t.journal.c.resource_id == latest.c.resource_id,
                            t.journal.c.version == latest.c.version,
                        ),
                    )
                    .where(t.journal.c.resource_id > str(after or ""))
                    .order_by(t.journal.c.resource_id)
                    .limit(26)
                )
            )
            .mappings()
            .all()
        )
        return {
            "items": [self.open(row["payload_ciphertext"])["snapshot"] for row in rows[:25]],
            "next_cursor": rows[24]["resource_id"] if len(rows) > 25 else None,
        }


def install_team_routes(router, cfg, database, box, actor_for, available, command, contracts):
    from uuid import UUID

    from fastapi import Request

    async def guard(service, body, identifier=None, lead=False):
        team = await service.scope(identifier, write=True) if identifier else None
        if not team:
            await service.facility(body["facility_id"], {"FACILITY_ADMIN"})
        if lead:
            require(team["lead_account_id"] == service.actor["id"])

    @router.post("/v1/institutional/delivery-teams", status_code=201)
    async def propose(payload: contracts.DeliveryTeamProposal, request: Request):
        return await command(
            request, payload, TeamService, guard, lambda service, body: service.propose(body)
        )

    def action(suffix, model, method, lead=False):
        async def execute(identifier: UUID, payload, request: Request):
            return await command(
                request,
                payload,
                TeamService,
                lambda service, body: guard(service, body, identifier, lead),
                lambda service, body: getattr(service, method)(identifier, body),
            )

        execute.__annotations__["payload"] = model
        router.add_api_route(
            "/v1/institutional/delivery-teams/{identifier}/" + suffix,
            execute,
            methods=["POST"],
            status_code=201,
        )

    @router.post("/v1/institutional/delivery-teams/{identifier}/revise", status_code=201)
    async def revise(identifier: UUID, payload: contracts.DeliveryTeamRevision, request: Request):
        return await command(
            request,
            payload,
            TeamService,
            lambda service, body: guard(service, body, identifier),
            lambda service, body: service.propose(body, identifier),
        )

    action("accept", contracts.Versioned, "accept", True)
    action("retire", contracts.Versioned, "retire")

    @router.get("/v1/institutional/delivery-teams")
    async def listing(facility_id: UUID, request: Request, after: UUID | None = None):
        await available()
        async with database.transaction() as session:
            service = TeamService(
                session, cfg, box, await actor_for(session, request), request.state.correlation_id
            )
            result = await service.list(facility_id, after)
            await service.audit("standards.teams_read", str(facility_id))
            return result

    @router.get("/v1/institutional/delivery-teams/{identifier}/history")
    async def history(identifier: UUID, request: Request, before_version: int = 0):
        await available()
        require(before_version >= 0, "VALIDATION_FAILED", "Choose an actual version cursor", 422)
        async with database.transaction() as session:
            service = TeamService(
                session, cfg, box, await actor_for(session, request), request.state.correlation_id
            )
            await service.scope(identifier)
            query = select(t.journal).where(
                t.journal.c.resource_id == str(identifier), t.journal.c.action.in_(ACTIONS)
            )
            if before_version:
                query = query.where(t.journal.c.version < before_version)
            rows = (
                (await session.execute(query.order_by(t.journal.c.version.desc()).limit(51)))
                .mappings()
                .all()
            )
            await service.audit("standards.team_history_read", str(identifier))
            return {
                "items": [
                    {
                        "version": row["version"],
                        "action": row["action"],
                        "actor_id": row["actor_id"],
                        "recorded_at": row["recorded_at"],
                        **service.open(row["payload_ciphertext"]),
                    }
                    for row in rows[:50]
                ],
                "next_before_version": rows[49]["version"] if len(rows) > 50 else None,
            }
