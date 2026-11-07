"""Verify live cloud routes and packaged source hashes without printing credentials."""

import argparse
import base64
import hashlib
import json

import httpx
from platform_cloud_release import checked, source_files, vercel_credential


def walk(nodes, parent=""):
    for node in nodes:
        path = parent + node.get("name", "")
        yield path, node
        if node.get("children"):
            yield from walk(node["children"], path + "/")


def verify(api_deployment, web_deployment):
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
                    path.startswith(("services/api/src/lw_care_api/platform/", "src/app/"))
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
                ("/v1/clinical/sites", 401),
                ("/v1/reporting/context", 401),
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
                    assert response.json()["schema_version"] == 3
                    record["schema_version"] = 3
                    record["reporting"] = response.json().get("reporting")
                print(json.dumps(record))
        for path in ("/", "/care", "/directorate", "/activate", "/directory"):
            response = client.get("https://lw-health-intelligence.vercel.app" + path)
            assert (
                response.status_code == 200 and "LW Health Intelligence Platform" in response.text
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
