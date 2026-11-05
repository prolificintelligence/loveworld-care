"""Check the exact isolated deployment source, not only the monorepo import path."""

import base64
import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values
from platform_cloud_release import ROOT, source_files


def prepare():
    roots = {}
    for target in ("api", "web"):
        destination = ROOT / ".toolchain" / ("verified-" + target)
        destination.mkdir(parents=True, exist_ok=True)
        for entry in source_files(target):
            path = destination / entry["file"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(base64.b64decode(entry["data"]))
        roots[target] = str(destination)
    return roots


def verify():
    roots = prepare()
    environment = {**os.environ, **dotenv_values(ROOT / ".env.platform.local")}
    code = (
        "import runpy; from fastapi.testclient import TestClient; "
        f"app=runpy.run_path({str(Path(roots['api']) / 'api/index.py')!r})['app']; "
        "client=TestClient(app); "
        "assert client.get('/v1/health').status_code==200; "
        "assert client.get('/v1/ready').status_code==200; "
        "assert client.get('/v1/auth/me').status_code==401; "
        "print('ISOLATED_API_IMPORT_HEALTH_DATABASE_AUTH_PASSED')"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", code],
        cwd=roots["api"],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        # Return only the final exception category/name, never settings input or a DSN.
        failure = result.stderr.splitlines()[-1] if result.stderr else "Unknown artifact failure"
        for name, value in environment.items():
            if (
                value
                and len(value) > 12
                and any(term in name for term in ("KEY", "SECRET", "TOKEN", "DATABASE_URL"))
            ):
                failure = failure.replace(value, "[REDACTED]")
        print(json.dumps({"artifact_verification": "FAILED", "diagnostic": failure}))
        raise SystemExit(1)
    print(result.stdout.strip())
    print(
        json.dumps(
            {
                "artifact_roots": roots,
                "api_legacy_config_packaged": (
                    Path(roots["api"]) / "services/api/src/lw_care_api/config.py"
                ).exists(),
            }
        )
    )


if __name__ == "__main__":
    verify()
