"""Exact-source Vercel deployment through the existing GitHub runner; no DB/key setup."""

import argparse
import contextlib
import io
import json
import os
import time
from pathlib import Path

import httpx
from platform_cloud_release import checked, deploy, http_client, vercel_credential
from verify_reporting_cloud import verify


def execute(args):
    if not os.environ.get("LWH_VERCEL_DEPLOY_TOKEN"):
        raise ValueError("A protected deployment secret is required")
    result = {"target": args.target, "source_commit": os.environ.get("GITHUB_SHA")}
    if args.target == "verify":
        if args.schema_version != 7 or not args.api_deployment or not args.web_deployment:
            raise ValueError("Verification requires both actual deployments and schema 7")
        verify(args.api_deployment, args.web_deployment)
        result["verification"] = "PASSED"
    else:
        # Refuse the UI rollout before the operator has migrated the cloud authority.
        if args.target == "web":
            ready = httpx.get("https://lw-health-intelligence-api.vercel.app/v1/ready", timeout=60)
            assert ready.status_code == 200 and ready.json()["schema_version"] == 7
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            deploy(args.target)
        deployment = json.loads(output.getvalue())
        result.update(deployment)
        print(json.dumps(result), flush=True)
        with http_client(vercel_credential()) as client:
            for _ in range(90):
                state = checked(
                    client.get(
                        "https://api.vercel.com/v13/deployments/" + deployment["deployment_id"]
                    ),
                    "deployment_status",
                )
                if state.get("readyState") == "READY":
                    break
                if state.get("readyState") in {"ERROR", "CANCELED"}:
                    raise RuntimeError("Vercel build did not become ready")
                time.sleep(10)
            else:
                raise TimeoutError("Vercel deployment did not become ready in the release window")
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            base = "https://lw-health-intelligence-api.vercel.app"
            ready = client.get(base + "/v1/ready")
            assert ready.status_code == 200
            assert ready.json()["schema_version"] == args.schema_version
            assert client.get(base + "/v1/operations/context").status_code == 401
            if args.target == "api" and args.schema_version == 6:
                response = client.post(
                    base + "/v1/clinical/00000000-0000-0000-0000-000000000001/workflows/capacity",
                    json={
                        "service": "READ_ONLY_DEPLOYMENT_GATE_PROBE",
                        "max_open_encounters": 0,
                        "resources_evidence": "Unauthenticated gate check; no operating authority",
                        "policy_reference": "No policy adoption asserted",
                        "starts_at": "2026-11-08T00:00:00Z",
                        "ends_at": "2026-11-09T00:00:00Z",
                        "require_roster": True,
                        "require_admission_order": True,
                        "intent_confirmed": True,
                    },
                )
                assert response.status_code == 503
                result["new_command_migration_gate"] = 503
            if args.target == "web":
                assert (
                    client.get("https://lw-health-intelligence.vercel.app/care").status_code == 200
                )
            result.update(
                state="READY", schema_version=args.schema_version, authentication="ENFORCED"
            )
    folder = Path(".release-evidence")
    folder.mkdir(exist_ok=True)
    (folder / (args.target + ".json")).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("api", "web", "verify"), required=True)
    parser.add_argument("--schema-version", type=int, choices=(6, 7), required=True)
    parser.add_argument("--api-deployment", default="")
    parser.add_argument("--web-deployment", default="")
    try:
        execute(parser.parse_args())
    except Exception as exc:  # noqa: BLE001 -- no provider bodies, credentials or response reprs
        print(json.dumps({"vercel_runner": "FAILED", "error_type": type(exc).__name__}), flush=True)
        raise SystemExit(1) from None
