"""Recipient discovery over intersecting current assignments, before account paging."""

from sqlalchemy import and_, or_, select

from .. import db
from .store import ALL_ROLES


async def eligible_grants(session, actor):
    g = db.grants.c
    clauses = [g.scope_type == "GLOBAL"]
    for grant in actor["grants"]:
        if grant["role"] not in ALL_ROLES:
            continue
        kind, identifier = grant["scope_type"], grant["scope_id"]
        if kind == "GLOBAL":
            clauses = [True]
            break
        clauses.append(and_(g.scope_type == kind, g.scope_id == identifier))
        if kind == "REGION":
            zones = select(db.units.c.id).where(db.units.c.parent_id == identifier)
            facilities = select(db.facilities.c.id).where(db.facilities.c.zone_id.in_(zones))
            clauses.extend(
                [
                    and_(g.scope_type == "ZONE", g.scope_id.in_(zones)),
                    and_(g.scope_type == "FACILITY", g.scope_id.in_(facilities)),
                ]
            )
        else:
            zone = (
                identifier
                if kind == "ZONE"
                else await session.scalar(
                    select(db.facilities.c.zone_id).where(db.facilities.c.id == identifier)
                )
            )
            if not zone:
                continue
            region = await session.scalar(select(db.units.c.parent_id).where(db.units.c.id == zone))
            clauses.extend(
                [
                    and_(g.scope_type == "ZONE", g.scope_id == zone),
                    and_(g.scope_type == "REGION", g.scope_id == region),
                ]
            )
            if kind == "ZONE":
                clauses.append(
                    and_(
                        g.scope_type == "FACILITY",
                        g.scope_id.in_(
                            select(db.facilities.c.id).where(db.facilities.c.zone_id == zone)
                        ),
                    )
                )
    return and_(
        g.role.in_(ALL_ROLES),
        g.revoked.is_(False),
        g.valid_from <= db.now(),
        g.valid_until > db.now(),
        or_(*clauses),
    )
