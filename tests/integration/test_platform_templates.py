"""Actual versioned template workflow with synthetic, explicitly non-adopted test sources."""

import pytest
from lw_care_api.platform import db
from lw_care_api.platform.reporting import tables as t
from sqlalchemy import select, update
from test_platform_reporting import grant, run, stamp
from test_platform_reporting import journey as fixture


@pytest.fixture
def reporting(tmp_path):
    yield from fixture.__wrapped__(tmp_path)


def proposal(j, definition, **changes):
    return {
        "name": "Synthetic institutional template",
        "source_version": "SYNTHETIC-1",
        "source_reference": "Synthetic source inspected only for engineering qualification",
        "source_sha256": "a" * 64,
        "stream": "FACILITY_ACTIVITY",
        "jurisdictions": ["TEST-ONLY"],
        "adoption_reference": "Synthetic authority; never real institutional adoption",
        "valid_from": stamp(-2),
        "valid_until": stamp(3),
        "fields": [
            {
                "code": "contacts",
                "label": "Synthetic service contacts",
                "required": True,
                "disposition": "MEASURE",
                "definition_id": definition["id"],
                "part": "VALUE",
                "rationale": "Synthetic exact adopted count mapping",
            }
        ],
        **changes,
    }


def action(j, row, event, actor="governor", **changes):
    return j.create(
        f"/templates/{row['id']}/actions",
        {
            "expected_version": row["version"],
            "action": event,
            "reason": "Synthetic actual decision",
            "evidence": "Synthetic independently examined original and complete field inventory",
            "intent_confirmed": True,
            **changes,
        },
        actor,
    )


def adopted(j, definition, **changes):
    row = j.create("/templates", proposal(j, definition, **changes), "governor")
    row = action(j, row, "SUBMIT")
    row = action(j, row, "REVIEW_ACCEPT", "reviewer")
    return action(j, row, "ADOPT")


def obligation_body(j, template):
    return {
        "scope_type": "FACILITY",
        "scope_id": j.facilities[0],
        "stream": "FACILITY_ACTIVITY",
        "period_start": j.start,
        "period_end": j.end,
        "due_at": j.due,
        "timezone": "Africa/Lagos",
        "definition_ids": template["definition_ids"],
        "adoption_reference": "Synthetic calendar and template authority",
        "template_id": template["id"],
        "template_version": template["version"],
    }


def test_independent_adoption_freezes_exact_mapping_on_obligation_and_withdrawal_stops_new_use(
    reporting,
):
    j = reporting
    definition = j.definition()
    template = adopted(j, definition, valid_from=stamp(-5))
    body = obligation_body(j, template)
    obligation = j.create("/obligations", body, "governor")
    frozen = j.get(f"/obligations/{obligation['id']}/template").json()
    assert frozen["template_binding"]["inventory_hash"] == template["inventory_hash"]
    assert frozen["template_binding"]["template_version"] == template["version"]
    assert frozen["template_binding"]["payload"]["fields"][0]["definition_id"] == definition["id"]
    assert j.get(f"/obligations/{obligation['id']}/template", "outsider").status_code == 404
    j.draft(obligation, definition)
    assert (
        j.get(f"/returns/{j.get('/obligations').json()['items'][0]['return']['id']}").json()[
            "template_binding"
        ]
        == frozen["template_binding"]
    )
    withdrawn = action(j, template, "WITHDRAW")
    assert withdrawn["state"] == "WITHDRAWN"
    assert j.get(f"/obligations/{obligation['id']}/template").json() == frozen
    assert (
        j.post("/obligations", body | {"scope_id": j.facilities[1]}, "governor").status_code == 409
    )
    history = j.get(f"/templates/{template['id']}/history", "reviewer").json()["items"]
    assert [item["version"] for item in history] == [1, 2, 3, 4, 5]
    assert history[3]["resource"]["state"] == "ADOPTED"


def test_template_author_cannot_review_even_with_both_roles_and_drafts_are_not_public(reporting):
    j = reporting
    template = j.create("/templates", proposal(j, j.definition()), "governor")
    assert j.get("/templates", "reporter").json()["items"] == []
    assert j.get(f"/templates/{template['id']}", "reporter").status_code == 404
    assert j.get("/templates", "executive").status_code == 403
    grant(j, "governor", "DATA_REVIEWER")
    submitted = action(j, template, "SUBMIT")
    body = {
        "expected_version": submitted["version"],
        "action": "REVIEW_ACCEPT",
        "reason": "Synthetic self review",
        "evidence": "Synthetic own work is not independent",
        "intent_confirmed": True,
    }
    assert j.post(f"/templates/{template['id']}/actions", body, "governor").status_code == 403
    reviewed = action(j, submitted, "REVIEW_ACCEPT", "reviewer")
    grant(j, "reviewer", "DATA_GOVERNOR")
    assert (
        j.post(
            f"/templates/{template['id']}/actions",
            body | {"expected_version": reviewed["version"], "action": "ADOPT"},
            "reviewer",
        ).status_code
        == 403
    )


def test_unresolved_fields_and_incomplete_ratios_cannot_be_accepted(reporting):
    j = reporting
    definition = j.definition(formula="RATIO", aggregation="RATIO_OF_SUMS", scale="100")
    mapped = proposal(j, definition)
    mapped["fields"][0]["part"] = "NUMERATOR"
    row = j.create("/templates", mapped, "governor")
    row = action(j, row, "SUBMIT")
    body = {
        "expected_version": row["version"],
        "action": "REVIEW_ACCEPT",
        "reason": "Synthetic review",
        "evidence": "Synthetic missing denominator observed",
        "intent_confirmed": True,
    }
    assert j.post(f"/templates/{row['id']}/actions", body, "reviewer").status_code == 422
    row = action(j, row, "RETURN_FOR_CORRECTION", "reviewer")
    mapped["fields"].append(
        {
            "code": "population",
            "label": "Synthetic denominator",
            "required": True,
            "disposition": "GAP",
            "rationale": "Synthetic denominator not yet reconciled",
        }
    )
    row = j.create(
        f"/templates/{row['id']}/edit",
        mapped | {"expected_version": row["version"], "reason": "Synthetic retained correction"},
        "governor",
    )
    row = action(j, row, "SUBMIT")
    assert (
        j.post(
            f"/templates/{row['id']}/actions",
            body | {"expected_version": row["version"]},
            "reviewer",
        ).status_code
        == 409
    )


def test_template_stream_jurisdiction_version_and_indicator_sets_are_checked(reporting):
    j = reporting
    definition = j.definition()
    template = adopted(
        j, definition, valid_from=stamp(-5), jurisdictions=["DIFFERENT-TEST-JURISDICTION"]
    )
    body = obligation_body(j, template)
    assert j.post("/obligations", body, "governor").status_code == 422
    template = adopted(j, definition, valid_from=stamp(-5), jurisdictions=["GLOBAL"])
    body = obligation_body(j, template)
    assert (
        j.post(
            "/obligations", body | {"template_version": template["version"] - 1}, "governor"
        ).status_code
        == 412
    )
    assert (
        j.post("/obligations", body | {"definition_ids": [db.uid()]}, "governor").status_code == 422
    )
    assert j.post("/obligations", body | {"template_version": None}, "governor").status_code == 422
    assert (
        j.post(
            f"/templates/{template['id']}/edit",
            proposal(j, definition)
            | {"expected_version": template["version"], "reason": "Synthetic forbidden overwrite"},
            "governor",
        ).status_code
        == 409
    )


def test_legacy_obligations_keep_original_receipts_and_absent_binding_is_explicit(reporting):
    j = reporting
    definition = j.definition()
    template = proposal(j, definition)
    template["fields"].append(dict(template["fields"][0]))
    assert j.post("/templates", template, "governor").status_code == 422
    body = {
        "scope_type": "FACILITY",
        "scope_id": j.facilities[0],
        "stream": "FACILITY_ACTIVITY",
        "period_start": j.start,
        "period_end": j.end,
        "due_at": j.due,
        "timezone": "Africa/Lagos",
        "definition_ids": [definition["id"]],
        "adoption_reference": "Synthetic existing calendar authority",
    }
    key = db.uid()
    response = j.post("/obligations", body, "governor", key)
    assert response.status_code == 200
    assert (
        j.post(
            "/obligations", body | {"template_id": None, "template_version": None}, "governor", key
        ).json()
        == response.json()
    )
    identifier = response.json()["resource"]["id"]
    assert (
        j.get(f"/obligations/{identifier}/template").json()["state"]
        == "DEFINITION_BASED_WITHOUT_TEMPLATE_BINDING"
    )


def test_current_authority_is_checked_before_template_receipt_replay(reporting):
    j = reporting
    body = proposal(j, j.definition())
    key = db.uid()
    original = j.post("/templates", body, "governor", key)
    assert original.status_code == 200
    assert j.post("/templates", body, "governor", key).json() == original.json()

    async def revoke():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                update(db.grants)
                .where(db.grants.c.account_id == j.actors["governor"][0])
                .values(revoked=True)
            )
            assert (
                len(
                    list(
                        (
                            await session.execute(
                                select(t.history).where(
                                    t.history.c.resource_type == "REPORTING_TEMPLATE"
                                )
                            )
                        ).mappings()
                    )
                )
                == 1
            )

    run(revoke())
    assert j.post("/templates", body, "governor", key).status_code == 404


@pytest.mark.parametrize("form_code", ["FACILITY-MONTHLY", "ZONE-MONTHLY", "REGION-MONTHLY"])
def test_working_forms_require_real_governor_configuration_and_independent_adoption(
    reporting, form_code
):
    j = reporting
    assert j.get("/template-proposals", "executive").status_code == 404
    pack = j.get("/template-proposals", "reviewer").json()
    assert pack["status"] == "PROPOSED_FOR_DIRECTOR_REVIEW" and len(pack["sources"]) == 6
    assert j.get("/templates", "governor").json()["items"] == []
    body = {
        "edition": pack["edition"],
        "form_code": form_code,
        "valid_from": stamp(-5),
        "valid_until": stamp(5),
        "authority_reference": "Synthetic provisional configuration only; not Director approval",
        "intent_confirmed": True,
    }
    assert j.post("/template-proposals/prepare", body, "reviewer").status_code == 404
    key = db.uid()
    response = j.post("/template-proposals/prepare", body, "governor", key)
    assert response.status_code == 200, response.text
    assert j.post("/template-proposals/prepare", body, "governor", key).json() == response.json()
    template = response.json()["resource"]
    assert template["state"] == "DRAFT"
    definitions = j.get(f"/templates/{template['id']}", "governor").json()["definitions"]
    form = next(item for item in pack["forms"] if item["code"] == form_code)
    assert len(definitions) == len(form["measures"])
    assert {row["metric_id"] for row in definitions} == {
        row["metric_id"] for row in form["measures"]
    }
    template = action(j, template, "SUBMIT")
    template = action(j, template, "REVIEW_ACCEPT", "reviewer")
    template = action(j, template, "ADOPT")
    assert template["state"] == "ADOPTED"
    body = obligation_body(j, template)
    if template["payload"]["stream"] != "FACILITY_ACTIVITY":
        scope_type = "ZONE" if form_code == "ZONE-MONTHLY" else "REGION"
        scope = next(
            row
            for row in j.get("/context", "governor").json()["scopes"]["items"]
            if row["scope_type"] == scope_type
        )
        body.update(scope_type=scope_type, scope_id=scope["scope_id"])
    body["stream"] = template["payload"]["stream"]
    obligation = j.create("/obligations", body, "governor")
    draft = j.create(
        f"/obligations/{obligation['id']}/draft",
        {
            "expected_version": 0,
            "values": [
                {
                    "definition_id": row["id"],
                    "completeness": "UNKNOWN",
                    "explanation": "Synthetic absent source; do not fabricate values",
                }
                for row in definitions
            ],
            "source_method": "Synthetic source review",
            "reconciliation": "No source values fabricated",
            "reason": "Synthetic complete missingness declaration",
        },
    )
    assert draft["state"] == "DRAFT"
    assert (
        j.get(f"/obligations/{obligation['id']}/template").json()["template_binding"]["template_id"]
        == template["id"]
    )


def test_definition_paging_and_exact_embedded_mapping_do_not_lose_old_versions(reporting):
    j = reporting
    original = j.definition()
    template = j.create("/templates", proposal(j, original), "governor")

    async def many():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                t.definitions.insert(),
                [
                    dict(
                        original,
                        id=db.uid(),
                        metric_id="LWH-MET-001",
                        definition_version=f"SYNTHETIC-{index:03}",
                        name=f"Synthetic version {index:03}",
                    )
                    for index in range(501)
                ],
            )

    run(many())
    first = j.get("/definitions", "governor").json()
    assert len(first["items"]) == 500 and first["next_cursor"]
    assert original["id"] not in {row["id"] for row in first["items"]}
    second = j.get("/definitions?after=" + first["next_cursor"], "governor").json()
    assert len(second["items"]) == 2 and not second["next_cursor"]
    assert j.get("/definitions?query=LWH-MET-010", "governor").json()["items"] == [original]
    assert j.get("/definitions?query=%25", "governor").json()["items"] == []
    assert j.get(f"/templates/{template['id']}", "governor").json()["definitions"] == [original]


def test_all_mapping_authors_are_excluded_from_independent_review(reporting):
    j = reporting
    definition = j.definition()
    draft = j.create("/templates", proposal(j, definition), "governor")
    grant(j, "reviewer", "DATA_GOVERNOR")
    draft = j.create(
        f"/templates/{draft['id']}/edit",
        proposal(j, definition) | {"expected_version": 1, "reason": "Synthetic second contributor"},
        "reviewer",
    )
    submitted = action(j, draft, "SUBMIT")
    assert set(submitted["author_ids"]) == {j.actors["governor"][0], j.actors["reviewer"][0]}
    assert (
        j.post(
            f"/templates/{draft['id']}/actions",
            {
                "expected_version": submitted["version"],
                "action": "REVIEW_ACCEPT",
                "reason": "Synthetic self review",
                "evidence": "Synthetic contributor cannot be independent",
                "intent_confirmed": True,
            },
            "reviewer",
        ).status_code
        == 403
    )
