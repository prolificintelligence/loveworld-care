"""Verify live cloud routes and packaged source hashes without printing credentials."""

import argparse
import base64
import hashlib
import json
from time import monotonic
from uuid import uuid4

import httpx
from platform_cloud_release import checked, source_files, vercel_credential


def walk(nodes, parent=""):
    for node in nodes:
        path = parent + node.get("name", "")
        yield path, node
        if node.get("children"):
            yield from walk(node["children"], path + "/")


def verify(api_deployment, web_deployment, expected_schema=9):
    with httpx.Client(
        headers={"Authorization": "Bearer " + vercel_credential()},
        transport=httpx.HTTPTransport(retries=1),
        timeout=httpx.Timeout(45, connect=10),
    ) as client:
        for target, identifier in (("api", api_deployment), ("web", web_deployment)):
            status = checked(
                client.get(f"https://api.vercel.com/v13/deployments/{identifier}"),
                "deployment_status",
            )
            assert status.get("readyState") == "READY"
            tree = checked(
                client.get(f"https://api.vercel.com/v6/deployments/{identifier}/files"),
                "deployment_files",
            )
            entries = dict(walk(tree if isinstance(tree, list) else tree.get("files", [])))
            sources = source_files(target)
            verified = 0
            for source in sources:
                path = source["file"]
                if not (
                    path.startswith(("services/api/src/lw_care_api/platform/", "src/app/", "public/"))
                    or path == "api/index.py"
                ):
                    continue
                entry = entries.get("src/" + path) or entries.get(path)
                expected = hashlib.sha1(base64.b64decode(source["data"])).hexdigest()
                assert entry and entry.get("uid") == expected, (
                    "Deployed source hash mismatch: " + path
                )
                verified += 1
            assert verified > 5
            print(
                json.dumps(
                    {
                        "target": target,
                        "deployment_id": identifier,
                        "state": "READY",
                        "actual_source_hashes_verified": verified,
                    }
                )
            )
    with httpx.Client(
        transport=httpx.HTTPTransport(retries=1),
        timeout=httpx.Timeout(45, connect=10),
        follow_redirects=True,
    ) as client:
        for origin in (
            "https://lw-health-intelligence-api.vercel.app",
            "https://lw-health-intelligence.vercel.app",
        ):
            for path, expected in (
                ("/v1/health", 200),
                ("/v1/ready", 200),
                ("/v1/auth/me", 401),
                ("/v1/service-capabilities", 401),
                ("/v1/clinical/sites", 401),
                ("/v1/reporting/context", 401),
                ("/v1/reporting/templates", 401),
                ("/v1/reporting/template-proposals", 401),
                ("/v1/operations/context", 401),
                ("/v1/operations/jobs", 401),
                ("/v1/operations/reliability", 401),
                ("/v1/operations/assurance-runs", 401),
                ("/v1/institutional/context", 401),
                ("/v1/institutional/cases", 401),
                ("/v1/institutional/articles", 401),
                ("/v1/knowledge", 200),
                ("/v1/reporting/safety-cases", 401),
                ("/v1/reporting/snapshots", 401),
            ):
                response = client.get(origin + path)
                assert response.status_code == expected, (path, response.status_code)
                assert "no-store" in response.headers.get("cache-control", "")
                record = {
                    "origin": origin,
                    "path": path,
                    "http": response.status_code,
                    "cache_control": response.headers.get("cache-control"),
                }
                if path.endswith("/ready"):
                    assert response.json()["schema_version"] == expected_schema
                    record["schema_version"] = expected_schema
                    record["reporting"] = response.json().get("reporting")
                print(json.dumps(record))
            # Validate the actual POST path and proxy, not only signed-out GETs.
            # A reserved invalid subject cannot authenticate or affect a real account.
            started = monotonic()
            login = client.post(
                origin + "/v1/auth/login",
                headers={"Origin": "https://lw-health-intelligence.vercel.app"},
                json={
                    "email": "login-probe-" + uuid4().hex + "@example.invalid",
                    "password": "Invalid connectivity probe only",
                    "otp": "000000",
                },
            )
            assert login.status_code == 401
            assert login.json()["error"]["code"] == "AUTH_REQUIRED"
            assert "set-cookie" not in login.headers
            assert "no-store" in login.headers.get("cache-control", "")
            print(
                json.dumps(
                    {
                        "origin": origin,
                        "path": "/v1/auth/login",
                        "method": "POST",
                        "http": 401,
                        "elapsed_seconds": round(monotonic() - started, 3),
                        "invalid_credentials_rejected": True,
                        "session_created": False,
                    }
                )
            )
        for path in (
            "/",
            "/care",
            "/directorate",
            "/reporting-templates",
            "/operations",
            "/recover",
            "/governance",
            "/learn",
            "/activate",
            "/directory",
            "/my-health",
            "/patient-access",
        ):
            response = client.get("https://lw-health-intelligence.vercel.app" + path)
            assert (
                response.status_code == 200 and ("LW Health Intelligence Platform" in response.text or (path == "/my-health" and "My LW Health Care" in response.text))
            )
            print(json.dumps({"frontend_page": path, "http": 200, "platform_title_verified": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-deployment", required=True)
    parser.add_argument("--web-deployment", required=True)
    args = parser.parse_args()
    try:
        verify(args.api_deployment, args.web_deployment)
    except Exception as exc:  # noqa: BLE001 -- never render a credential-bearing response/exception
        print(json.dumps({"cloud_verification": "FAILED", "error_type": type(exc).__name__}))
        raise SystemExit(1) from None
