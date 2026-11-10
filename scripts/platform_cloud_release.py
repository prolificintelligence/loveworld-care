"""Release the institutional service to the authorised Vercel/Neon accounts.

Credentials are read in memory from the existing secrets directory. Secret values,
provider response bodies and invitation tokens are never printed. `inspect` is read-only.
`configure` writes a gitignored local runtime file and production Vercel environment;
`deploy` uploads exact workspace source and does not push or rewrite Git history.
"""

import argparse
import asyncio
import base64
import contextlib
import json
import os
import re
import secrets
import sys
from pathlib import Path
from uuid import uuid4

import httpx
from cloud_credentials import (
    database_url,
    email_token,
    openrouter_token,
    read_secret,
    upstash_credentials,
    vercel_token,
)
from dotenv import dotenv_values, set_key

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".env.platform.local"
WEB = "lw-health-intelligence"
API = "lw-health-intelligence-api"


def vercel_credential():
    return os.environ.get("LWH_VERCEL_DEPLOY_TOKEN") or vercel_token()


def http_client(credential):
    return httpx.Client(
        headers={"Authorization": "Bearer " + credential},
        transport=httpx.HTTPTransport(retries=3),
        timeout=30,
    )


def checked(response, action):
    if not response.is_success:
        error = (
            response.json().get("error", {})
            if "json" in response.headers.get("content-type", "")
            else {}
        )
        print(
            json.dumps(
                {
                    "action": action,
                    "http_status": response.status_code,
                    "code": error.get("code") if isinstance(error, dict) else None,
                }
            )
        )
        raise RuntimeError(f"Cloud operation failed: {action}")
    return response.json()


def inspect():
    with http_client(vercel_credential()) as client:
        data = checked(
            client.get("https://api.vercel.com/v9/projects", params={"limit": 100}), "list_projects"
        )
        print(
            json.dumps(
                {
                    "projects": [
                        {k: p.get(k) for k in ("name", "id", "framework", "rootDirectory")}
                        for p in data["projects"]
                        if "health-intelligence" in p["name"]
                    ]
                }
            )
        )
    with http_client(email_token()) as client:
        domains = checked(client.get("https://api.resend.com/domains"), "email_domains")
        print(
            json.dumps(
                {
                    "email_domains": [
                        {k: d.get(k) for k in ("name", "status")} for d in domains.get("data", [])
                    ]
                }
            )
        )


def configure():
    existing = dotenv_values(RUNTIME) if RUNTIME.exists() else {}
    connection = database_url()
    key = read_secret("lw-health-auth-secret.md")
    if len(bytes.fromhex(key)) != 32:
        raise RuntimeError("The platform data-encryption key must be 32 bytes")
    storage = {}
    for line in read_secret("lw-health-R2.md").splitlines():
        match = re.match(r"\s*([A-Z0-9_]+)\s*[:=]\s*(.+)", line)
        if match:
            storage[match[1]] = match[2].strip(" `\"'")
    with http_client(email_token()) as client:
        response = client.get("https://api.resend.com/domains")
        domains = response.json() if response.status_code == 200 else {}
        domain = next(
            (
                d["name"]
                for d in domains.get("data", [])
                if d.get("status") == "verified" and d["name"].endswith("prolificintelligence.co")
            ),
            None,
        )
        restricted_sender = (
            response.status_code == 401 and domains.get("name") == "restricted_api_key"
        )
        if response.status_code == 401:
            restricted_sender = response.json().get("name") == "restricted_api_key"
        if restricted_sender:
            # The owner's nominated administrator uses this domain. A send-only key
            # cannot list verified domains; Resend validates the sender at send time.
            domain = "prolificintelligence.co"
        print(
            json.dumps(
                {
                    "email_configuration": "SEND_ONLY_KEY"
                    if restricted_sender
                    else "VERIFIED"
                    if domain
                    else "UNAVAILABLE",
                    "http_status": response.status_code,
                }
            )
        )
    import secrets

    jobs_secret = existing.get("LWH_JOBS_SECRET") or secrets.token_urlsafe(48)
    environment = {
        "LWH_RUNTIME": "institutional",
        "LWH_ENVIRONMENT": "production",
        "LWH_DATABASE_URL": connection,
        "LWH_DATA_KEY_HEX": key,
        "LWH_AUTHORITY_NODE_ID": existing.get("LWH_AUTHORITY_NODE_ID") or str(uuid4()),
        "LWH_WEB_ORIGIN": f"https://{WEB}.vercel.app",
        "LWH_S3_ENDPOINT": f"https://{storage['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        "LWH_S3_ACCESS_KEY": storage["R2_ACCESS_KEY_ID"],
        "LWH_S3_SECRET_KEY": storage["R2_SECRET_ACCESS_KEY"],
        "LWH_S3_BUCKET": storage["R2_BUCKET_NAME"],
        "LWH_JOBS_SECRET": jobs_secret,
        "CRON_SECRET": jobs_secret,
    }
    if domain:
        environment["LWH_RESEND_API_KEY"] = email_token()
        environment["LWH_EMAIL_FROM"] = f"LW Health Directorate <health-directorate@{domain}>"
    model_record = json.loads((ROOT / ".toolchain/openrouter-model.json").read_text())
    rest_url, rest_token = upstash_credentials()
    environment.update(
        {
            "LWH_OPENROUTER_API_KEY": openrouter_token(),
            "LWH_OPENROUTER_MODEL": model_record["model"],
            "LWH_UPSTASH_REST_URL": rest_url,
            "LWH_UPSTASH_REST_TOKEN": rest_token,
        }
    )
    with http_client(rest_token) as control_client:
        checked(
            control_client.post(rest_url, json=["SET", "lwh:platform:ai-disabled", "0", "NX"]),
            "initialise_ai_control",
        )
    # A real, reachable scanner is required for evidence acceptance, not a default fake service.
    if existing.get("LWH_CLAMAV_HOST"):
        environment["LWH_CLAMAV_HOST"] = existing["LWH_CLAMAV_HOST"]
    RUNTIME.touch(exist_ok=True)
    for name, value in environment.items():
        set_key(RUNTIME, name, value)
    with http_client(vercel_credential()) as client:
        for name, settings in (
            (API, {"framework": None, "rootDirectory": None}),
            (
                WEB,
                {
                    "framework": "nextjs",
                    "rootDirectory": None,
                    "installCommand": "pnpm install --frozen-lockfile",
                    "buildCommand": "pnpm run build",
                },
            ),
        ):
            response = client.get(f"https://api.vercel.com/v9/projects/{name}")
            if response.status_code == 404:
                project = checked(
                    client.post(
                        "https://api.vercel.com/v10/projects", json={"name": name, **settings}
                    ),
                    f"create_project:{name}",
                )
            else:
                project = checked(response, f"get_project:{name}")
                checked(
                    client.patch(
                        f"https://api.vercel.com/v9/projects/{project['id']}", json=settings
                    ),
                    f"configure_project:{name}",
                )
            values = environment if name == API else {"LWH_API_ORIGIN": f"https://{API}.vercel.app"}
            for variable, value in values.items():
                checked(
                    client.post(
                        f"https://api.vercel.com/v10/projects/{project['id']}/env",
                        params={"upsert": "true"},
                        json={
                            "key": variable,
                            "value": value,
                            "type": "encrypted",
                            "target": ["production"],
                        },
                    ),
                    f"set_environment:{name}:{variable}",
                )
            print(
                json.dumps(
                    {"project": name, "configuration": "APPLIED", "environment_keys": list(values)}
                )
            )


def source_files(target):
    files = {}
    if target == "api":
        for path in (ROOT / "services/api/src").rglob("*.py"):
            relative = path.relative_to(ROOT / "services/api/src/lw_care_api")
            if "__pycache__" not in path.parts and (
                relative.parts[0] == "platform"
                or relative.as_posix() in ("__init__.py", "db/__init__.py", "db/connection.py")
            ):
                files[path.relative_to(ROOT).as_posix()] = path.read_bytes()
        for path in (ROOT / "services/api/src/lw_care_api/platform").rglob("*.json"):
            files[path.relative_to(ROOT).as_posix()] = path.read_bytes()
        files["api/index.py"] = (ROOT / "api/platform.py").read_bytes()
        files["requirements.txt"] = (ROOT / "requirements.platform.txt").read_bytes()
        files["vercel.json"] = (ROOT / "vercel.platform.json").read_bytes()
    else:
        web_root = ROOT / "apps/platform-web"
        for path in web_root.rglob("*"):
            if not path.is_file() or any(
                part in path.parts for part in ("node_modules", ".next", ".vercel")
            ):
                continue
            if path.suffix in (".ts", ".tsx", ".css", ".mjs", ".json") or ("public" in path.relative_to(web_root).parts and path.suffix in (".js", ".png", ".svg", ".webmanifest")):
                files[path.relative_to(web_root).as_posix()] = path.read_bytes()
        # Preserve the verified pnpm graph while producing a self-contained
        # deployment root for this independently hosted workspace.
        lock = (ROOT / "pnpm-lock.yaml").read_text()
        importer = re.search(r"(?ms)^  apps/platform-web:\n(.*?)(?=^  [^ ]|^packages:|\Z)", lock)
        if not importer:
            raise RuntimeError("The platform workspace is missing from the verified lockfile")
        standalone = lock[: lock.index("importers:")] + "importers:\n\n  .:\n" + importer.group(1)
        standalone += "\n" + lock[lock.index("packages:") :]
        files["pnpm-lock.yaml"] = standalone.encode()
    return [
        {"file": name, "data": base64.b64encode(content).decode(), "encoding": "base64"}
        for name, content in sorted(files.items())
    ]


def deploy(target):
    from release_guard import committed_source, successful_ci

    commit = committed_source(ROOT)
    ci = successful_ci(commit)
    name = API if target == "api" else WEB
    with http_client(vercel_credential()) as client:
        result = checked(
            client.post(
                "https://api.vercel.com/v13/deployments",
                json={
                    "name": name,
                    "project": name,
                    "target": "production",
                    "autoAssignCustomDomains": False,
                    "meta": {"lwhSourceCommit": commit, "lwhCiRun": str(ci["run_id"])},
                    "files": source_files(target),
                },
            ),
            "deploy:" + name,
        )
        print(
            json.dumps(
                {
                    "project": name,
                    "deployment_id": result["id"],
                    "url": result.get("url"),
                    "state": result.get("readyState"),
                    "source_commit": commit,
                    "promotion": "STAGED_REQUIRES_VERIFICATION",
                }
            )
        )


def active_deployment(client, name):
    alias = checked(client.get(f"https://api.vercel.com/v4/aliases/{name}.vercel.app"), "active_alias")
    return alias["deploymentId"]


@contextlib.contextmanager
def candidate_probe_access(client, project, identifier):
    """Short-lived provider authentication, never application authorisation.

    The credential stays in memory, travels only in a request header and is
    revoked before promotion. Existing SSO protection is never disabled.
    """
    if not project.get("ssoProtection") and not project.get("passwordProtection"):
        yield {}
        return
    secret = secrets.token_urlsafe(32)
    endpoint = f"https://api.vercel.com/v1/projects/{project['id']}/protection-bypass"
    try:
        checked(client.patch(endpoint, json={"generate": {
            "secret": secret, "note": "Temporary release probe " + identifier,
        }}), "create_temporary_probe_access")
        yield {"x-vercel-protection-bypass": secret}
    finally:
        checked(client.patch(endpoint, json={"revoke": {
            "secret": secret, "regenerate": False,
        }}), "revoke_temporary_probe_access")
        remaining = checked(client.get(f"https://api.vercel.com/v9/projects/{project['id']}"), "probe_access_cleanup")
        if secret in (remaining.get("protectionBypass") or {}):
            raise ValueError("Temporary probe access was not revoked; promotion stopped")


def promote(target, identifier, expected_current):
    from release_guard import committed_source, manifest, successful_ci, verify_source_tree

    commit = committed_source(ROOT)
    ci = successful_ci(commit)
    name = API if target == "api" else WEB
    with http_client(vercel_credential()) as client:
        project = checked(client.get(f"https://api.vercel.com/v9/projects/{name}"), "project")
        active = active_deployment(client, name)
        if not expected_current or active != expected_current:
            raise ValueError("Production deployment changed; reconcile before promotion")
        deployment = checked(client.get(f"https://api.vercel.com/v13/deployments/{identifier}"), "candidate")
        if (deployment.get("readyState") != "READY" or deployment.get("target") != "production"
            or deployment.get("projectId") != project["id"]
            or deployment.get("meta", {}).get("lwhSourceCommit") != commit):
            raise ValueError("A READY staged production candidate from this commit/project is required")
        tree = checked(client.get(f"https://api.vercel.com/v6/deployments/{identifier}/files"), "candidate_sources")
        count = verify_source_tree(manifest(source_files(target)), tree)
        # Only signed-out read probes run against a production-backed candidate.
        origin = "https://" + deployment["url"]
        with candidate_probe_access(client, project, identifier) as headers, httpx.Client(
            timeout=60, follow_redirects=False, headers=headers,
        ) as probe:
            if target == "api":
                response = probe.get(origin + "/v1/ready")
                if response.status_code != 200 or response.json().get("schema_version") != 9:
                    raise ValueError("Staged candidate readiness did not verify")
                for path in ("/v1/auth/me", "/v1/service-capabilities", "/v1/reporting/snapshots"):
                    response = probe.get(origin + path)
                    if response.status_code != 401 or "no-store" not in response.headers.get("cache-control", ""):
                        raise ValueError("Staged candidate authentication did not verify")
            else:
                response = probe.get(origin + "/")
                if response.status_code != 200 or "LW Health Intelligence Platform" not in response.text:
                    raise ValueError("Staged frontend did not verify")
        # Compare production again after source/HTTP checks; do not overwrite
        # an intervening release. Provider promotion reuses this build ID.
        if active_deployment(client, name) != expected_current:
            raise ValueError("Production changed during candidate qualification")
        checked(client.post(f"https://api.vercel.com/v10/projects/{project['id']}/promote/{identifier}"), "promote")
        print(json.dumps({"project": name, "deployment_id": identifier, "source_commit": commit,
                          "ci": ci, "verified_source_files": count, "previous_deployment": expected_current,
                          "temporary_provider_probe_access": "REVOKED_BEFORE_PROMOTION",
                          "promotion": "REQUESTED_WITHOUT_REBUILD"}))


def status(identifier):
    with http_client(vercel_credential()) as client:
        result = checked(
            client.get(f"https://api.vercel.com/v13/deployments/{identifier}"), "deployment_status"
        )
        print(json.dumps({k: result.get(k) for k in ("id", "url", "readyState", "errorCode")}))


def migrate():
    sys.path.insert(0, str(ROOT / "services/api/src"))
    from lw_care_api.platform.config import PlatformSettings
    from lw_care_api.platform.db import Database

    settings = PlatformSettings(_env_file=RUNTIME)
    settings.validate_runtime()

    async def apply():
        database = Database(settings.database_url)
        try:
            await database.migrate()
            from lw_care_api.platform.clinical.flow_index import rebuild
            from lw_care_api.platform.security import SecretBox

            indexed = await rebuild(database, SecretBox(settings.data_key_hex), settings)
            from lw_care_api.platform.reporting.source_index import rebuild as rebuild_sources

            source_indexed = await rebuild_sources(database, SecretBox(settings.data_key_hex))
            print(
                json.dumps(
                    {
                        "migration": "APPLIED",
                        "schema_version": await database.version(),
                        "seeded_records": 0,
                        "existing_records_indexed": indexed,
                        "existing_reporting_sources_indexed": source_indexed,
                    }
                )
            )
        finally:
            await database.engine.dispose()

    asyncio.run(apply())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inspect", "configure", "migrate", "deploy", "promote", "status"))
    parser.add_argument("--target", choices=("api", "web"))
    parser.add_argument("--deployment-id")
    parser.add_argument("--expected-current")
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            inspect()
        elif args.command == "configure":
            configure()
        elif args.command == "migrate":
            migrate()
        elif args.command == "deploy":
            if not args.target:
                parser.error("deploy requires --target")
            deploy(args.target)
        elif args.command == "promote":
            if not args.target or not args.deployment_id or not args.expected_current:
                parser.error("promote requires target, deployment-id and expected-current")
            promote(args.target, args.deployment_id, args.expected_current)
        elif args.command == "status":
            if not args.deployment_id:
                parser.error("status requires --deployment-id")
            status(args.deployment_id)
    except Exception as exc:  # noqa: BLE001 -- secret-safe CLI boundary, never print exception values
        # Never render exception reprs that may carry a DSN or response body.
        print(json.dumps({"status": "FAILED", "error_type": type(exc).__name__}), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
