"""Authoritative administrative coverage; never a disclosure route for clinical measures."""

from datetime import UTC

from sqlalchemy import case, func, select

from .. import db
from ..domain import require
from . import store as s
from . import tables as t

ROLES = s.SOURCE_READERS | s.PROGRAMMES


async def coverage(session, actor, start=None, end=None):
    require(
        any(g["role"] in ROLES for g in actor["grants"]),
        "REPORTING_ASSIGNMENT_REQUIRED",
        "Reporting coverage requires a current source reporting or programme assignment",
        403,
    )
    require(
        (start is None) == (end is None),
        "VALIDATION_FAILED",
        "Select both reporting-period bounds",
        422,
    )
    if start is not None:
        require(
            start.tzinfo and end.tzinfo and start < end,
            "VALIDATION_FAILED",
            "Use an ordered reporting period with explicit time zones",
            422,
        )
        start, end = (
            value.astimezone(UTC).isoformat(timespec="microseconds") for value in (start, end)
        )
    stamp = db.now()
    receipt = t.returns.c.state.in_(["SUBMITTED", "VERIFIED"]) & t.returns.c.received_at.is_not(
        None
    )
    conditions = {
        "missing": t.returns.c.id.is_(None),
        "draft": t.returns.c.state == "DRAFT",
        "submitted": t.returns.c.state == "SUBMITTED",
        "returned_for_correction": t.returns.c.state == "RETURNED_FOR_CORRECTION",
        "verified": t.returns.c.state == "VERIFIED",
        "current_received": receipt,
        "on_time_current_receipt": receipt & (t.returns.c.received_at <= t.obligations.c.due_at),
        "late_current_receipt": receipt & (t.returns.c.received_at > t.obligations.c.due_at),
        "overdue_submission": (t.obligations.c.due_at < stamp)
        & (t.returns.c.id.is_(None) | t.returns.c.state.not_in(["SUBMITTED", "VERIFIED"])),
    }
    query = (
        select(
            t.obligations.c.stream,
            t.obligations.c.scope_type,
            func.count().label("expected"),
            *(
                func.sum(case((predicate, 1), else_=0)).label(name)
                for name, predicate in conditions.items()
            ),
        )
        .select_from(
            t.obligations.outerjoin(t.returns, t.returns.c.obligation_id == t.obligations.c.id)
        )
        .where(s.visibility(actor, ROLES, t.obligations))
    )
    if start is not None:
        query = query.where(
            t.obligations.c.period_start == start, t.obligations.c.period_end == end
        )
    rows = (
        await session.execute(
            query.group_by(t.obligations.c.stream, t.obligations.c.scope_type).order_by(
                t.obligations.c.stream, t.obligations.c.scope_type
            )
        )
    ).mappings()
    totals = {key: 0 for key in ("expected", *conditions)}
    items = []
    for row in rows:
        values = {key: int(row[key] or 0) for key in totals}
        for key in totals:
            totals[key] += values[key]
        items.append({"stream": row["stream"], "scope_type": row["scope_type"], **values})
    return {
        "totals": totals,
        "items": items,
        "as_of": stamp,
        "period_start": start,
        "period_end": end,
        "configuration_state": "CONFIGURED_OBLIGATIONS"
        if totals["expected"]
        else "NO_CONFIGURED_OBLIGATIONS_IN_VIEW",
        "receipt_fraction": totals["current_received"] / totals["expected"]
        if totals["expected"]
        else None,
        "verification_fraction": totals["verified"] / totals["expected"]
        if totals["expected"]
        else None,
        "interpretation": "Administrative unit-period obligations across current permitted scope; not distinct facilities, patient counts, disease incidence or a released clinical snapshot. Current receipt excludes drafts and returned corrections. No configured obligations does not establish reporting completeness.",
        "selection": "EXACT_PERIOD" if start is not None else "ALL_CONFIGURED_PERIODS",
    }
