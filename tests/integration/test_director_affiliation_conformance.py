"""Initial Directorate affiliation proofs using isolated, labelled metadata fixtures.

The synthetic CLEAN metadata below qualifies workflow guards only. No file is
uploaded/scanned and no malware service or institutional decision is qualified.
"""

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from lw_care_api.platform import db
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.main import create_platform_app
from lw_care_api.platform.security import issue_session
from sqlalchemy import func, select

ORIGIN = "http://localhost:3004"
SCENARIOS = (
    "missing",
    "duplicate",
    "wrong_criterion",
    "expired_inspection",
    "unscanned_submit",
    "expired_decision",
    "expired_recommendation",
    "expired_rejection",
    "unmet_approval",
    "truthful_unobserved",
    "positive_replay",
)


def stamp(days=0):
    return (datetime.now(UTC) + timedelta(days=days)).isoformat(timespec="microseconds")


@contextmanager
def evidence_expired():
    """Advance the authoritative metadata clock; never edit immutable evidence."""
    original, future = (
        db.now,
        (datetime.now(UTC) + timedelta(minutes=20)).isoformat(timespec="microseconds"),
    )
    db.now = lambda: future
    try:
        yield
    finally:
        db.now = original


async def actors(app):
    values = {}
    async with app.state.database.transaction() as session:
        for name, roles in {
            "creator": ["REGISTRY_STEWARD", "PLATFORM_ADMIN"],
            "inspector": ["INSPECTOR"],
            "reviewer": ["STANDARDS_REVIEWER"],
            "decider": ["STANDARDS_DECIDER"],
        }.items():
            identifier = db.uid()
            await session.execute(
                db.accounts.insert().values(
                    id=identifier,
                    email=identifier + "@synthetic.invalid",
                    name="Synthetic conformance " + name,
                    active=True,
                    created_at=stamp(),
                )
            )
            for role in roles:
                await session.execute(
                    db.grants.insert().values(
                        id=db.uid(),
                        account_id=identifier,
                        role=role,
                        scope_type="GLOBAL",
                        scope_id="GLOBAL",
                        valid_from=stamp(-10),
                        valid_until=stamp(30),
                        revoked=False,
                        grantor="ISOLATED_SYNTHETIC_PROOF",
                    )
                )
            values[name] = (identifier, await issue_session(session, identifier, 30))
    return values


async def advance_review(fixture, assigned, reviewer="reviewer", *, stop_after_screening=False):
    create, path = fixture["create"], fixture["path"]
    screened = await create(path + "/screening", {
        "expected_version": assigned["version"], "reason": "Synthetic actual dossier screening",
        "intent_confirmed": True,
    }, reviewer)
    if stop_after_screening:
        return screened
    return await create(path + "/evidence-review", {
        "expected_version": screened["version"], "reason": "Synthetic evidence assessment before inspection",
        "intent_confirmed": True, "assessments": [
            {"criterion": code, "assessment": "Synthetic evidence sufficient for inspection, not a MET finding",
             "evidence_ids": [identifier]} for code, identifier in fixture["proofs"].items()
        ],
    }, reviewer)


async def exercise(app, client, scenario, *, fixture_state=None, evidence_valid_minutes=10, criteria_valid_until=None):
    identity = await actors(app)

    async def post(path, body, actor="creator", key=None):
        return await client.post(
            "/v1" + path,
            json=body,
            headers={
                "Origin": ORIGIN,
                "Authorization": "Bearer " + identity[actor][1],
                "Idempotency-Key": key or db.uid(),
            },
        )

    async def create(path, body, actor="creator", key=None):
        response = await post(path, body, actor, key)
        assert response.status_code == 200, (
            path,
            response.status_code,
            response.json().get("error", {}).get("code"),
        )
        return response.json()["resource"]

    async def effects():
        async with app.state.database.transaction() as session:
            counts = [
                await session.scalar(select(func.count()).select_from(t))
                for t in (
                    db.facilities,
                    db.applications,
                    db.inspections,
                    db.decisions,
                    db.revisions,
                    db.outbox,
                    db.operations,
                )
            ]
            applications = (
                await session.execute(
                    select(
                        db.applications.c.id, db.applications.c.version, db.applications.c.state
                    ).order_by(db.applications.c.id)
                )
            ).all()
            facilities = (
                await session.execute(
                    select(
                        db.facilities.c.id,
                        db.facilities.c.version,
                        db.facilities.c.affiliation_status,
                    ).order_by(db.facilities.c.id)
                )
            ).all()
            return counts, applications, facilities

    async def refused(path, body, actor, status, code=None):
        before = await effects()
        response = await post(path, body, actor)
        assert response.status_code == status, (scenario, response.status_code, status)
        if code:
            assert response.json()["error"]["code"] == code
        assert await effects() == before, "Refusal changed consequential records/receipts"
        return response

    region = await create(
        "/organisation-units",
        {"name": "Synthetic region", "code": db.uid(), "kind": "REGION", "valid_from": stamp(-10)},
    )
    zone = await create(
        "/organisation-units",
        {
            "name": "Synthetic zone",
            "code": db.uid(),
            "kind": "ZONE",
            "parent_id": region["id"],
            "valid_from": stamp(-10),
        },
    )
    operator = await create(
        "/operators", {"name": "Synthetic operator", "external_reference": db.uid()}
    )
    registration = {
        "operator_org_id": operator["id"],
        "zone_id": zone["id"],
        "site_name": "Synthetic scoped clinic",
        "site_type": "COMMUNITY_PRIMARY",
        "ownership_category": "MEMBER_OWNED",
        "jurisdiction_profile": "SYNTHETIC-ONLY",
        "external_reference": db.uid(),
        "address": "Synthetic manual address, no inferred coordinates",
        "public_contact": "public@synthetic.invalid",
        "private_contact": "PRIVATE_SYNTHETIC_CONTACT",
        "services": ["Synthetic declared service"],
    }
    if scenario == "positive_replay":
        await refused("/facilities", registration, "reviewer", 403)
        await refused("/facilities", registration | {"site_name": ""}, "creator", 422)
        await refused(
            "/facilities", registration | {"ownership_category": "UNKNOWN"}, "creator", 422
        )
        await refused("/facilities", registration | {"services": []}, "creator", 422)
        await refused("/facilities", registration | {"operator_org_id": db.uid()}, "creator", 422)
    facility = await create("/facilities", registration)
    async with app.state.database.transaction() as session:
        saved = (
            (
                await session.execute(
                    select(db.facilities).where(db.facilities.c.id == facility["id"])
                )
            )
            .mappings()
            .one()
        )
        for source, target in (
            ("site_name", "name"),
            ("operator_org_id", "operator_id"),
            ("ownership_category", "ownership"),
            ("jurisdiction_profile", "jurisdiction"),
            ("services", "services"),
        ):
            assert saved[target] == registration[source] == facility[target]
    assert "PRIVATE_SYNTHETIC_CONTACT" not in (await client.get("/v1/directory")).text
    criteria = await create(
        "/criteria",
        {
            "name": "Synthetic proof criteria",
            "version": db.uid(),
            "jurisdiction": "SYNTHETIC-ONLY",
            "site_type": "COMMUNITY_PRIMARY",
            "requirements": [
                {"code": c, "description": "Synthetic required criterion " + c, "required": True}
                for c in ("SYN-A", "SYN-B")
            ],
            "adoption_reference": "ISOLATED SYNTHETIC AUTHORITY, NEVER OPERATING ADOPTION",
            "valid_from": stamp(-10),
            "valid_until": criteria_valid_until or stamp(30),
        },
        "decider",
    )
    application = await create(
        "/applications", {"facility_id": facility["id"], "criteria_id": criteria["id"]}
    )
    path = "/applications/" + application["id"]
    proofs = {}
    async with app.state.database.transaction() as session:
        for code in ("SYN-A", "SYN-B"):
            identifier = db.uid()
            await session.execute(
                db.evidence.insert().values(
                    id=identifier,
                    application_id=application["id"],
                    criterion=code,
                    object_key="SYNTHETIC_METADATA_ONLY_NO_OBJECT",
                    sha256="0" * 64,
                    filename="synthetic.txt",
                    media_type="text/plain",
                    size=1,
                    source="ISOLATED_METADATA_FIXTURE_NOT_SCANNER_QUALIFICATION",
                    expires_at=(datetime.now(UTC) + timedelta(minutes=evidence_valid_minutes)).isoformat(
                        timespec="microseconds"
                    ),
                    scan_status="UNVERIFIED" if scenario == "unscanned_submit" else "CLEAN",
                    uploaded_by=identity["creator"][0],
                    created_at=stamp(),
                )
            )
            proofs[code] = identifier
    fixture = {
        "actors": identity,
        "facility": facility,
        "application": application,
        "path": path,
        "post": post,
        "create": create,
        "refused": refused,
        "effects": effects,
        "proofs": proofs,
        "criteria": criteria,
        "registration": registration,
    }
    if fixture_state == "DRAFT":
        return fixture
    if scenario == "unscanned_submit":
        await refused(path + "/submit", {"expected_version": 1}, "creator", 422)
        return {"scenario": scenario, "result": "REFUSED_WITHOUT_DOMAIN_EFFECTS"}
    await create(path + "/submit", {"expected_version": 1})
    if fixture_state == "SUBMITTED":
        return fixture
    assigned = await create(
        path + "/assignment",
        {
            "expected_version": 2,
            "inspector_id": identity["inspector"][0],
            "reviewer_id": identity["reviewer"][0],
        },
    )
    finding = {
        "expected_version": 3,
        "conflict_declared": False,
        "observed_at": stamp(-1),
        "findings": [
            {
                "criterion": c,
                "observation": "Synthetic actual observation",
                "outcome": "MET",
                "evidence_ids": [proofs[c]],
            }
            for c in proofs
        ],
    }
    if fixture_state == "SCREENING":
        return fixture | {"finding": finding}
    ready = await advance_review(fixture, assigned, stop_after_screening=fixture_state == "EVIDENCE_REVIEW")
    finding["expected_version"] = ready["version"]
    if fixture_state == "EVIDENCE_REVIEW":
        return fixture | {"finding": finding}
    if fixture_state == "INSPECTION":
        return fixture | {"finding": finding}
    if scenario in {"missing", "duplicate", "wrong_criterion", "expired_inspection"}:
        if scenario == "missing":
            finding["findings"].pop()
        if scenario == "duplicate":
            finding["findings"].append(dict(finding["findings"][0]))
        if scenario == "wrong_criterion":
            finding["findings"][0]["evidence_ids"] = [proofs["SYN-B"]]
        if scenario == "expired_inspection":
            with evidence_expired():
                await refused(
                    path + "/inspections", finding, "inspector", 409, "EVIDENCE_NOT_CURRENT"
                )
        else:
            await refused(
                path + "/inspections",
                finding,
                "inspector",
                422 if scenario == "wrong_criterion" else 409,
            )
        return {"scenario": scenario, "result": "REFUSED_WITHOUT_DOMAIN_EFFECTS"}
    if scenario in {"unmet_approval", "truthful_unobserved"}:
        finding["findings"][0]["outcome"] = (
            "NOT_MET" if scenario == "unmet_approval" else "NOT_OBSERVED"
        )
        if scenario == "truthful_unobserved":
            finding["findings"][0]["evidence_ids"] = []
    await refused(path + "/inspections", finding, "creator", 403)
    if scenario == "positive_replay":
        await refused(
            path + "/inspections", finding | {"conflict_declared": True}, "inspector", 403
        )
    await create(path + "/inspections", finding, "inspector")
    async with app.state.database.transaction() as session:
        recorded = (
            (
                await session.execute(
                    select(db.inspections).where(
                        db.inspections.c.application_id == application["id"]
                    )
                )
            )
            .mappings()
            .one()
        )
        assert recorded["findings"] == finding["findings"]
        assert (
            recorded["inspector_id"] == identity["inspector"][0]
            and not recorded["conflict_declared"]
        )
    recommendation = {
        "expected_version": 6,
        "decision": "APPROVE",
        "reason": "Synthetic independent recommendation",
    }
    if scenario == "expired_recommendation":
        with evidence_expired():
            await refused(
                path + "/recommendation", recommendation, "reviewer", 409, "EVIDENCE_NOT_CURRENT"
            )
        return {"scenario": scenario, "result": "REFUSED_WITHOUT_DOMAIN_EFFECTS"}
    if scenario in {"unmet_approval", "truthful_unobserved"}:
        await refused(
            path + "/recommendation", recommendation, "reviewer", 409, "UNRESOLVED_FINDINGS"
        )
        recommendation["decision"] = "CONDITIONAL"
    await create(path + "/recommendation", recommendation, "reviewer")
    decision = {
        "expected_version": 7,
        "decision": recommendation["decision"],
        "reason": "Synthetic central decision, not actual institutional approval",
        "scope": "Synthetic declared service only",
        "conditions": "Synthetic follow-up condition",
        "effective_at": stamp(-1),
        "expires_at": stamp(10),
        "intent_confirmed": True,
    }
    if scenario == "expired_decision":
        with evidence_expired():
            await refused(path + "/decisions", decision, "decider", 409, "EVIDENCE_NOT_CURRENT")
        # Same immutable dossier becomes usable again under the original test clock.
        async with app.state.database.transaction() as session:
            assert (
                await session.scalar(
                    select(db.applications.c.state).where(db.applications.c.id == application["id"])
                )
                == "RECOMMENDED"
            )
        return {"scenario": scenario, "result": "REFUSED_WITHOUT_DOMAIN_EFFECTS"}
    if scenario == "expired_rejection":
        with evidence_expired():
            await create(path + "/decisions", decision | {"decision": "REJECT"}, "decider")
        async with app.state.database.transaction() as session:
            assert (
                await session.scalar(
                    select(db.facilities.c.affiliation_status).where(
                        db.facilities.c.id == facility["id"]
                    )
                )
                == "REJECTED"
            )
        return {"scenario": scenario, "result": "ADVERSE_HISTORY_RETAINED_WITHOUT_RECOGNITION"}
    await refused(path + "/decisions", decision, "reviewer", 403)
    await refused(path + "/decisions", decision | {"expected_version": 6}, "decider", 412)
    if decision["decision"] == "CONDITIONAL":
        await refused(
            path + "/decisions",
            decision | {"decision": "APPROVE"},
            "decider",
            409,
            "UNRESOLVED_FINDINGS",
        )
        await refused(path + "/decisions", decision | {"conditions": ""}, "decider", 422)
    key = db.uid()
    accepted = await create(path + "/decisions", decision, "decider", key)
    assert await create(path + "/decisions", decision, "decider", key) == accepted
    async with app.state.database.transaction() as session:
        decisions = (
            (
                await session.execute(
                    select(db.decisions).where(db.decisions.c.application_id == application["id"])
                )
            )
            .mappings()
            .all()
        )
        assert len(decisions) == 1
        for field in ("decision", "reason", "scope", "conditions", "effective_at", "expires_at"):
            assert decisions[0][field] == decision[field]
        assert decisions[0]["decider_id"] == identity["decider"][0]
        assert (
            await session.scalar(
                select(db.facilities.c.affiliation_status).where(
                    db.facilities.c.id == facility["id"]
                )
            )
        ) == ("CONDITIONAL" if decision["decision"] == "CONDITIONAL" else "ACTIVE")
    assert (await client.get("/v1/directory")).json()["items"] == []
    return {
        "scenario": scenario,
        "result": "INDEPENDENT_TYPED_COMMAND_GUARDS_AND_PERSISTENCE_VERIFIED",
    }


@pytest.mark.parametrize("scenario", SCENARIOS)
async def test_director_initial_affiliation_guards_and_evidence(tmp_path, scenario):
    cfg = PlatformSettings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'proof.db').as_posix()}",
        data_key_hex="03" * 32,
        web_origin=ORIGIN,
        authority_node_id=db.uid(),
        enforce_activation_dossiers=False,
        dispatch_recovery_after_commit=False,
    )
    app = create_platform_app(cfg)
    await app.state.database.migrate()
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=ORIGIN
        ) as client:
            await exercise(app, client, scenario)
    finally:
        await app.state.database.engine.dispose()
