"""Native source mapping against real persisted signed clinical histories."""

import pytest
from lw_care_api.platform import db
from lw_care_api.platform.clinical import store as cs
from lw_care_api.platform.clinical import tables as ct
from lw_care_api.platform.reporting import native
from sqlalchemy import select, update
from test_platform_reporting import journey as fixture
from test_platform_reporting import run, stamp
from test_platform_templates import action, obligation_body


@pytest.fixture
def reporting(tmp_path):
    yield from fixture.__wrapped__(tmp_path)


def setup_native(j):
    row = j.create(
        "/source-profiles/prepare",
        {
            "edition": native.EDITION,
            "valid_from": stamp(-10),
            "valid_until": stamp(10),
            "authority_reference": "Synthetic native source configuration, not institutional adoption",
            "intent_confirmed": True,
        },
        "governor",
    )
    row = action(j, row, "SUBMIT")
    row = action(j, row, "REVIEW_ACCEPT", "reviewer")
    row = action(j, row, "ADOPT")
    obligation = j.create("/obligations", obligation_body(j, row), "governor")
    definitions = j.get(f"/templates/{row['id']}", "governor").json()["definitions"]
    return obligation, definitions


async def seed_sources(app, facility, actor_id, *, at=None):
    """Synthetic source qualification, using actual encryption/Ed25519 journal code."""
    at = at or stamp(-2.5)
    site = {
        "id": db.uid(),
        "facility_id": facility,
        "authority_node_id": app.state.settings.authority_node_id,
        "authority_epoch": "SYNTHETIC-1",
        "services": ["SYNTHETIC"],
        "policy_reference": "Synthetic source policy only",
        "manual_medicine_policy": "Synthetic no prescribing",
        "valid_from": stamp(-30),
        "valid_until": stamp(30),
        "active": True,
        "version": 1,
        "approved_by": actor_id,
    }
    actor = {"id": actor_id}
    async with app.state.database.transaction() as session:
        await session.execute(ct.sites.insert().values(**site))
        patient = db.uid()
        await cs.create(
            session,
            app.state.settings,
            app.state.box,
            actor,
            site,
            "patient",
            {"synthetic": "PRIVATE_SYNTHETIC_PATIENT"},
            "SYNTHETIC",
            identifier=patient,
        )
        encounter, note = db.uid(), db.uid()

        async def create(kind, content, status, identifier=None):
            return await cs.create(
                session,
                app.state.settings,
                app.state.box,
                actor,
                site,
                kind,
                content,
                "SYNTHETIC",
                patient_id=patient,
                encounter_id=encounter if kind != "encounter" else None,
                service="SYNTHETIC",
                status=status,
                identifier=identifier,
            )

        await create(
            "encounter",
            {
                "disposition": {"occurred_at": at, "signed_summary_id": note},
                "private": "PRIVATE_SYNTHETIC_CHART",
            },
            "COMPLETED",
            encounter,
        )
        await create(
            "note",
            {
                "signed_by": actor_id,
                "intent_confirmed": True,
                "private": "PRIVATE_SYNTHETIC_SUMMARY",
            },
            "SIGNED",
            note,
        )
        deaths = []
        for event, status in [
            ("DEATH", "DECEASED"),
            ("DISCHARGE", "DISCHARGED"),
            ("SELF_DISCHARGE", "SELF_DISCHARGED"),
        ]:
            deaths.append(
                await create(
                    "stay",
                    {"history": [{"action": event, "occurred_at": at, "signed_summary_id": note}]},
                    status,
                )
            )
        await create("stay", {"history": [{"action": "LEAVE", "occurred_at": at}]}, "ON_LEAVE")
        for history, status in [
            (
                [
                    {"action": "REQUEST", "occurred_at": at},
                    {
                        "action": "RECORD_ACCEPTANCE",
                        "occurred_at": at,
                        "receiver_name": "PRIVATE_SYNTHETIC_RECEIVER",
                        "acceptance_evidence": "Actual synthetic receipt",
                    },
                ],
                "ACCEPTED",
            ),
            (
                [
                    {"action": "REQUEST", "occurred_at": at},
                    {
                        "action": "RECORD_ACCEPTANCE",
                        "occurred_at": stamp(-1.5),
                        "receiver_name": "Synthetic late receiver",
                        "acceptance_evidence": "Late actual synthetic receipt",
                    },
                ],
                "ACCEPTED",
            ),
            (
                [{"action": "REQUEST", "occurred_at": at}, {"action": "CANCEL", "occurred_at": at}],
                "CANCELLED",
            ),
            (
                [
                    {"action": "REQUEST", "occurred_at": at},
                    {
                        "action": "RECORD_ACCEPTANCE",
                        "occurred_at": at,
                        "receiver_name": "Synthetic actual receiver",
                        "acceptance_evidence": "Actual synthetic receipt",
                    },
                    {"action": "CANCEL", "occurred_at": at},
                ],
                "CANCELLED",
            ),
        ]:
            await create("referral", {"history": history, "summary_note_id": note}, status)
        return {"encounter": encounter, "note": note, "death": deaths[0]["id"], "patient": patient}


def values_by_metric(extract):
    return {value["metric_id"]: value for value in extract["data"]["values"].values()}


def declared_values(extract):
    return [
        {
            "definition_id": identifier,
            "completeness": item["completeness"],
            "value": item["value"],
            "numerator": item["numerator"],
            "denominator": item["denominator"],
            "explanation": item["explanation"],
            "extract_id": extract["id"],
        }
        for identifier, item in extract["data"]["values"].items()
    ]


def save(j, obligation, values):
    return j.create(
        f"/obligations/{obligation['id']}/draft",
        {
            "expected_version": 0,
            "values": values,
            "source_method": "Synthetic actual native source preparation",
            "reconciliation": "Synthetic native subset; manual activity not added",
            "reason": "Synthetic initial source review",
        },
    )


def test_native_profiles_exact_semantics_signed_sources_cutoffs_and_private_provenance(reporting):
    j = reporting
    obligation, definitions = setup_native(j)
    source = run(seed_sources(j.app, j.facilities[0], j.actors["reporter"][0]))
    extract = j.create(f"/obligations/{obligation['id']}/extract", {})
    values = values_by_metric(extract)
    assert values["LWH-MET-010"]["value"] == "1"
    assert values["LWH-MET-013"]["value"] == "1"
    assert values["LWH-MET-014"]["numerator"] == "1" and values["LWH-MET-014"]["denominator"] == "3"
    assert values["LWH-MET-014"]["value"] == "33.33333333"
    assert values["LWH-MET-025"]["numerator"] == "2" and values["LWH-MET-025"]["denominator"] == "3"
    assert extract["data"]["counts"]["cancelled_before_acceptance"] == 1
    assert all(value["completeness"] == "PARTIAL" for value in values.values())
    assert (
        "PRIVATE_SYNTHETIC" not in str(extract)
        and source["patient"] not in str(extract)
        and source["encounter"] not in str(extract)
    )
    draft = save(j, obligation, declared_values(extract))
    assert not any(row["severity"] == "BLOCKING" for row in draft["validation"]["findings"])
    assert len(definitions) == 4


def test_native_profile_cannot_be_attached_to_changed_semantics(reporting):
    j = reporting
    pack = j.get("/source-profiles", "governor").json()
    assert j.get("/source-profiles", "executive").status_code == 404
    measure = next(row for row in pack["measures"] if row["metric_id"] == "LWH-MET-014")
    body = measure | {
        "stream": "FACILITY_ACTIVITY",
        "definition_version": "SYNTHETIC-CHANGED",
        "adoption_reference": "Synthetic actual authority",
        "template_reconciliation": "Synthetic wrong denominator",
        "valid_from": stamp(-5),
        "valid_until": stamp(5),
        "intent_confirmed": True,
    }
    assert (
        j.post(
            "/definitions",
            body | {"denominator_definition": "Unrelated community population"},
            "governor",
        ).status_code
        == 422
    )
    assert (
        j.post("/definitions", body | {"stream": "ZONE_COMMUNITY"}, "governor").status_code == 422
    )


def test_absent_activation_or_zero_denominator_is_unknown_never_clinical_zero(reporting):
    j = reporting
    obligation, _ = setup_native(j)
    values = values_by_metric(j.create(f"/obligations/{obligation['id']}/extract", {}))
    assert all(
        value["value"] is None and value["completeness"] == "UNKNOWN" for value in values.values()
    )
    run(seed_sources(j.app, j.facilities[0], j.actors["reporter"][0], at=stamp(-1)))
    values = values_by_metric(j.create(f"/obligations/{obligation['id']}/extract", {}))
    assert (
        values["LWH-MET-010"]["value"] == "0" and values["LWH-MET-010"]["completeness"] == "PARTIAL"
    )
    assert values["LWH-MET-014"]["value"] is None and values["LWH-MET-025"]["value"] is None


def test_ratio_components_cannot_hide_a_discrepancy_with_an_equal_percentage(reporting):
    j = reporting
    obligation, _ = setup_native(j)
    run(seed_sources(j.app, j.facilities[0], j.actors["reporter"][0]))
    extract = j.create(f"/obligations/{obligation['id']}/extract", {})
    values = declared_values(extract)
    for value in values:
        if value["denominator"] is not None:
            value["numerator"] = str(int(value["numerator"]) * 2)
            value["denominator"] = str(int(value["denominator"]) * 2)
    draft = save(j, obligation, values)
    assert sum(row["code"] == "EXTRACT_DISCREPANCY" for row in draft["validation"]["findings"]) == 2


@pytest.mark.parametrize("mutation", ["projection", "signature"])
def test_tampered_native_source_fails_closed(reporting, mutation):
    j = reporting
    obligation, _ = setup_native(j)
    source = run(seed_sources(j.app, j.facilities[0], j.actors["reporter"][0]))

    async def corrupt():
        async with j.app.state.database.transaction() as session:
            if mutation == "projection":
                await session.execute(
                    update(ct.records)
                    .where(ct.records.c.id == source["death"])
                    .values(status="DISCHARGED")
                )
            else:
                await session.execute(
                    update(ct.events)
                    .where(ct.events.c.record_id == source["death"])
                    .values(signature="aW52YWxpZA==")
                )

    run(corrupt())
    assert j.post(f"/obligations/{obligation['id']}/extract", {}).status_code == 503


def test_late_clinical_change_blocks_submission_and_preserves_old_extract(reporting):
    j = reporting
    obligation, _ = setup_native(j)
    source = run(seed_sources(j.app, j.facilities[0], j.actors["reporter"][0]))
    extract = j.create(f"/obligations/{obligation['id']}/extract", {})
    draft = save(j, obligation, declared_values(extract))

    async def invalidate():
        async with j.app.state.database.transaction() as session:
            site = (
                (
                    await session.execute(
                        select(ct.sites).where(ct.sites.c.facility_id == j.facilities[0])
                    )
                )
                .mappings()
                .one()
            )
            await cs.create(
                session,
                j.app.state.settings,
                j.app.state.box,
                {"id": j.actors["reporter"][0]},
                site,
                "record_error",
                {"target_id": source["death"]},
                "SYNTHETIC",
                patient_id=source["patient"],
                status="ENTERED_IN_ERROR",
            )

    run(invalidate())
    assert (
        j.post(
            f"/returns/{draft['id']}/submit",
            {
                "expected_version": draft["version"],
                "reason": "Synthetic stale source must not pass",
                "intent_confirmed": True,
            },
        ).status_code
        == 409
    )
    fresh = j.create(f"/obligations/{obligation['id']}/extract", {})
    assert values_by_metric(fresh)["LWH-MET-013"]["value"] == "0"
    assert values_by_metric(extract)["LWH-MET-013"]["value"] == "1"


def test_source_scope_and_batch_bound_are_authoritative(reporting, monkeypatch):
    j = reporting
    obligation, _ = setup_native(j)
    run(seed_sources(j.app, j.facilities[0], j.actors["reporter"][0]))
    assert j.post(f"/obligations/{obligation['id']}/extract", {}, "outsider").status_code == 404
    monkeypatch.setattr(native, "MAX_RECORDS", 1)
    assert j.post(f"/obligations/{obligation['id']}/extract", {}).status_code == 409


def test_unrelated_future_care_does_not_stale_a_prior_period_extract(reporting):
    j = reporting
    obligation, _ = setup_native(j)
    source = run(seed_sources(j.app, j.facilities[0], j.actors["reporter"][0]))
    extract = j.create(f"/obligations/{obligation['id']}/extract", {})

    async def future():
        async with j.app.state.database.transaction() as session:
            site = (
                (
                    await session.execute(
                        select(ct.sites).where(ct.sites.c.facility_id == j.facilities[0])
                    )
                )
                .mappings()
                .one()
            )
            await cs.create(
                session,
                j.app.state.settings,
                j.app.state.box,
                {"id": j.actors["reporter"][0]},
                site,
                "encounter",
                {"disposition": {"occurred_at": stamp(-1)}},
                "SYNTHETIC",
                patient_id=source["patient"],
                status="COMPLETED",
            )

    run(future())
    detail = j.get(f"/extracts/{extract['id']}", "reviewer")
    assert detail.status_code == 200 and detail.json()["native_source_current"] is True
    assert j.get(f"/extracts/{extract['id']}", "executive").status_code == 404
    assert j.get(f"/extracts/{extract['id']}", "outsider").status_code == 404


def test_released_native_snapshot_keeps_history_but_loses_current_eligibility_after_source_change(
    reporting,
):
    j = reporting
    obligation, definitions = setup_native(j)
    source = run(seed_sources(j.app, j.facilities[0], j.actors["reporter"][0]))
    extract = j.create(f"/obligations/{obligation['id']}/extract", {})
    # The test explicitly attests this isolated source cohort is complete;
    # production never receives a fabricated coverage attestation.
    values = [value | {"completeness": "VALUE"} for value in declared_values(extract)]
    draft = save(j, obligation, values)
    submitted = j.create(
        f"/returns/{draft['id']}/submit",
        {
            "expected_version": draft["version"],
            "reason": "Synthetic actual attestation",
            "intent_confirmed": True,
        },
    )
    j.create(
        f"/returns/{draft['id']}/review",
        {
            "expected_version": submitted["version"],
            "decision": "VERIFY",
            "reason": "Synthetic independent source verification",
            "evidence_examined": "Synthetic signed source and cohort",
            "method": "Synthetic actual reconciliation",
            "verification_scope": "This isolated test cohort only",
            "warning_overrides": {},
            "intent_confirmed": True,
        },
        "reviewer",
    )
    policy = j.policy(allowed_metric_ids=[row["metric_id"] for row in definitions])
    cohort = j.cohort([obligation], policy)
    released = j.released(cohort)
    assert released["current_eligible"] is True

    async def correction():
        async with j.app.state.database.transaction() as session:
            site = (
                (
                    await session.execute(
                        select(ct.sites).where(ct.sites.c.facility_id == j.facilities[0])
                    )
                )
                .mappings()
                .one()
            )
            await cs.create(
                session,
                j.app.state.settings,
                j.app.state.box,
                {"id": j.actors["reporter"][0]},
                site,
                "record_error",
                {"target_id": source["death"]},
                "SYNTHETIC",
                patient_id=source["patient"],
                status="ENTERED_IN_ERROR",
            )

    run(correction())
    old = j.get(f"/snapshots/{released['snapshot_id']}", "executive").json()
    assert old["freshness"] == "STALE_CLINICAL_SOURCE_CHANGE" and old["current_eligible"] is False
    assert old["cells"] == released["cells"]
    exported = j.get(f"/snapshots/{released['snapshot_id']}/export.csv", "executive")
    assert exported.status_code == 200 and "STALE_CLINICAL_SOURCE_CHANGE" in exported.text
    assert j.post("/snapshots", {"cohort_id": cohort["id"]}, "analyst").status_code == 409
    assert j.get(f"/returns/{draft['id']}").json()["native_source_current"] is False
