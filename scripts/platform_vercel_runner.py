"""Exact-source Vercel deployment through the existing GitHub runner; no DB/key setup."""

import argparse
import contextlib
import io
import json
import os
import time
from pathlib import Path

import httpx
from platform_cloud_release import checked, deploy, http_client, promote, vercel_credential
from verify_reporting_cloud import verify


def execute(args):
    if not os.environ.get("LWH_VERCEL_DEPLOY_TOKEN"):
        raise ValueError("A protected deployment secret is required")
    result = {"target": args.target, "source_commit": os.environ.get("GITHUB_SHA")}
    if args.target == "verify":
        if args.schema_version != 9 or not args.api_deployment or not args.web_deployment:
            raise ValueError("Verification requires both actual deployments and a supported schema")
        verify(args.api_deployment, args.web_deployment, args.schema_version)
        result["verification"] = "PASSED"
    else:
        if args.action == "promote":
            identifier = args.api_deployment if args.target == "api" else args.web_deployment
            if not identifier or not args.expected_current:
                raise ValueError("Promotion requires a staged deployment and expected-current")
            promote(args.target, identifier, args.expected_current)
            result.update(deployment_id=identifier, promotion="REQUESTED_WITHOUT_REBUILD")
            folder = Path(".release-evidence")
            folder.mkdir(exist_ok=True)
            (folder / (args.target + ".json")).write_text(json.dumps(result, indent=2), encoding="utf-8")
            return
        # Refuse the UI rollout before the operator has migrated the cloud authority.
        if args.target == "web":
            ready = httpx.get("https://lw-health-intelligence-api.vercel.app/v1/ready", timeout=60)
            assert ready.status_code == 200 and ready.json()["schema_version"] == args.schema_version
        if args.target == "api" and args.api_deployment:
            deployment = {"deployment_id": args.api_deployment, "state": "CHECKING_EXISTING"}
        else:
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
        result.update(state="STAGED_READY", promotion="NOT_PROMOTED", schema_version=args.schema_version)
    folder = Path(".release-evidence")
    folder.mkdir(exist_ok=True)
    (folder / (args.target + ".json")).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("api", "web", "verify"), required=True)
    parser.add_argument("--schema-version", type=int, choices=(9,), required=True)
    parser.add_argument("--action", choices=("stage", "promote"), default="stage")
    parser.add_argument("--expected-current", default="")
    parser.add_argument("--api-deployment", default="")
    parser.add_argument("--web-deployment", default="")
    try:
        execute(parser.parse_args())
    except Exception as exc:  # noqa: BLE001 -- no provider bodies, credentials or response reprs
        print(json.dumps({"vercel_runner": "FAILED", "error_type": type(exc).__name__}), flush=True)
        raise SystemExit(1) from None
