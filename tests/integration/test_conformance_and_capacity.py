"""Traceability integrity and isolation boundaries; no operating acceptance claims."""

import copy
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from lw_care_api.platform.config import PlatformSettings
from sqlalchemy.pool import NullPool

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from build_conformance_register import build, rendered, validate
from capacity_candidate import candidate


@pytest.fixture(scope="module")
def register():
    value = build()
    validate(value)
    return value


def test_canonical_inventory_has_explicit_gaps_and_preserves_baseline_meaning(register):
    assert register["controlled_documents_verified"] == 78
    assert register["acceptance"] == {
        "requirements": 200,
        "specified_cases": 111,
        "status": "NOT_RUN",
    }
    field = next(r for r in register["fields"] if r["id"] == "LWH-FRM-001.F001")
    assert field["name"] == "site_name" and field["required_on_capture_submission"]
    assert field["candidate_bindings"][0]["field"] == "site_name"
    assert field["formal_acceptance"] == "NOT_RUN" and field["missingness"].startswith(
        "UNQUALIFIED"
    )
    absent = next(r for r in register["forms"] if r["id"] == "LWH-FRM-046")
    assert absent["status"] == "OPEN_EXPLICIT_MAPPING_GAP"
    assert len(rendered(register)) == 6


@pytest.mark.parametrize(
    "corruption",
    ["duplicate", "orphan", "dangling", "missing_route", "false_acceptance", "false_parity"],
)
def test_crosswalk_rejects_silent_omissions_and_false_acceptance(register, corruption):
    value = copy.deepcopy(register)
    if corruption == "duplicate":
        value["fields"][1] = value["fields"][0]
    elif corruption == "orphan":
        value["fields"][0]["form_id"] = "LWH-FRM-999"
    elif corruption == "dangling":
        value["fields"][0]["candidate_bindings"][0]["field"] = "invented"
    elif corruption == "false_acceptance":
        value["fields"][0]["formal_acceptance"] = "PASSED"
    elif corruption == "missing_route":
        value["actual_routes"] = []
    else:
        value["screens"][0]["status"] = "CONFORMANT"
    with pytest.raises(ValueError):
        validate(value)


def settings():
    return PlatformSettings(
        environment="test",
        database_url="sqlite+aiosqlite://",
        data_key_hex="02" * 32,
        web_origin="http://localhost:3004",
        authority_node_id="synthetic-capacity",
        resend_api_key="must-be-removed",
        s3_access_key="must-be-removed",
        openrouter_api_key="must-be-removed",
        jobs_secret="must-be-removed",
    )


@pytest.mark.parametrize(
    "environment,namespace",
    [
        ("production", "lwh_native_verify_" + "a" * 32),
        ("preview", "health_platform"),
        ("preview", "lwh_native_verify_bad;DROP SCHEMA health_platform"),
    ],
)
def test_capacity_entrypoint_rejects_production_and_non_disposable_schema(environment, namespace):
    with pytest.raises(ValueError):
        candidate(settings(), namespace, provider_environment=environment)


def test_capacity_preview_excludes_jobs_and_outbound_providers_without_changing_pool():
    app = candidate(settings(), "lwh_native_verify_" + "a" * 32, provider_environment="preview")
    cfg = app.state.settings
    assert not any(
        (
            cfg.resend_api_key,
            cfg.jobs_secret,
            cfg.s3_access_key,
            cfg.openrouter_api_key,
            cfg.upstash_rest_token,
            cfg.dispatch_recovery_after_commit,
        )
    )
    assert isinstance(app.state.database.engine.pool, NullPool)
    with TestClient(app) as client:
        for path in (
            "/v1/internal/jobs",
            "/v1/auth/recovery/request",
            "/v1/clinical/fake/patients",
        ):
            response = client.post(path)
            assert response.status_code == 403
            assert response.json()["error"]["code"] == "QUALIFICATION_SERVICE_EXCLUDED"
