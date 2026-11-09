"""Administrative completeness over all scoped unit-period obligations, beyond UI page caps."""

import pytest
from lw_care_api.platform import db
from lw_care_api.platform.reporting import tables as t
from sqlalchemy import select, update
from test_platform_reporting import journey as fixture
from test_platform_reporting import run, stamp


@pytest.fixture
def reporting(tmp_path):
    yield from fixture.__wrapped__(tmp_path)


def test_coverage_counts_all_obligations_and_current_receipts_not_loaded_pages(reporting):
    j = reporting
    definition = j.definition()
    obligation = j.obligation([definition])
    draft = j.draft(obligation, definition)

    async def populate():
        async with j.app.state.database.transaction() as session:
            source = dict(
                (
                    await session.execute(
                        select(t.obligations).where(t.obligations.c.id == obligation["id"])
                    )
                )
                .mappings()
                .one()
            )
            report = dict(
                (await session.execute(select(t.returns).where(t.returns.c.id == draft["id"])))
                .mappings()
                .one()
            )
            obligations, returns = [], []
            for number in range(205):
                identifier = db.uid()
                obligations.append(
                    source
                    | {
                        "id": identifier,
                        "period_start": stamp(-400 - number),
                        "period_end": stamp(-399 - number),
                        "due_at": stamp(-1),
                    }
                )
                if number < 200:
                    state = ["DRAFT", "SUBMITTED", "VERIFIED", "RETURNED_FOR_CORRECTION"][
                        number % 4
                    ]
                    returns.append(
                        report
                        | {
                            "id": db.uid(),
                            "obligation_id": identifier,
                            "state": state,
                            "received_at": stamp(-0.5),
                        }
                    )
            await session.execute(t.obligations.insert(), obligations)
            await session.execute(t.returns.insert(), returns)

    run(populate())
    result = j.get("/coverage")
    assert result.status_code == 200, result.text
    value = result.json()
    totals = value["totals"]
    assert totals == {
        "expected": 206,
        "missing": 5,
        "draft": 51,
        "submitted": 50,
        "returned_for_correction": 50,
        "verified": 50,
        "current_received": 100,
        "on_time_current_receipt": 0,
        "late_current_receipt": 100,
        "overdue_submission": 105,
    }
    assert value["receipt_fraction"] == 100 / 206
    assert value["verification_fraction"] == 50 / 206
    assert len(value["items"]) == 1 and value["selection"] == "ALL_CONFIGURED_PERIODS"
    assert "payload_ciphertext" not in result.text and "source_hash" not in result.text
    exact = j.client.get(
        "/v1/reporting/coverage",
        params={"period_start": obligation["period_start"], "period_end": obligation["period_end"]},
        headers={"Authorization": "Bearer " + j.actors["reporter"][1]},
    )
    assert exact.status_code == 200 and exact.json()["totals"]["expected"] == 1
    assert exact.json()["selection"] == "EXACT_PERIOD"


def test_coverage_does_not_treat_empty_configuration_as_complete_or_grant_leadership_access(
    reporting,
):
    j = reporting
    result = j.get("/coverage").json()
    assert result["configuration_state"] == "NO_CONFIGURED_OBLIGATIONS_IN_VIEW"
    assert result["receipt_fraction"] is None and result["verification_fraction"] is None
    for actor in ("admin", "executive", "owner"):
        assert j.get("/coverage", actor).status_code == 403
    assert j.client.get("/v1/reporting/coverage").status_code == 401
    assert j.get("/coverage?period_start=2026-01-01T00:00:00Z").status_code == 422
    assert (
        j.get(
            "/coverage?period_start=2026-01-01T00:00:00&period_end=2026-02-01T00:00:00"
        ).status_code
        == 422
    )


def test_coverage_applies_current_scope_before_aggregation_and_does_not_duplicate_grants(reporting):
    j = reporting
    j.obligation([j.definition()])
    assert j.get("/coverage", "outsider").json()["totals"]["expected"] == 0

    async def grants():
        async with j.app.state.database.transaction() as session:
            row = dict(
                (
                    await session.execute(
                        select(db.grants).where(db.grants.c.account_id == j.actors["reporter"][0])
                    )
                )
                .mappings()
                .one()
            )
            await session.execute(
                db.grants.insert().values(
                    row | {"id": db.uid(), "scope_type": "FACILITY", "scope_id": j.facilities[0]}
                )
            )

    run(grants())
    assert j.get("/coverage").json()["totals"]["expected"] == 1

    async def revoke():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                update(db.grants)
                .where(db.grants.c.account_id == j.actors["reporter"][0])
                .values(revoked=True)
            )

    run(revoke())
    assert j.get("/coverage").status_code == 403
