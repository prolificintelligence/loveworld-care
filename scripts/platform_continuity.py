"""Operator-only encrypted archive and isolated recovery verification on existing services.

Recovery keys, data keys, row contents and provider exceptions are never printed.
No archive download or production restore endpoint is exposed by the web API.
"""

import argparse
import asyncio
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api/src"))
from lw_care_api.platform import db
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.control.assurance import observe, record
from lw_care_api.platform.control.continuity import create_archive, fingerprint, rehearse_restore
from lw_care_api.platform.db import Database
from lw_care_api.platform.security import SecretBox


def recovery_key(path):
    value = dotenv_values(path).get("LWH_BACKUP_RECOVERY_KEY_HEX", "")
    key = bytes.fromhex(value)
    fingerprint(key)
    return key


def keygen(path):
    # Keep generated credentials outside tracked source. Operators may separately
    # escrow this file on their approved independent protected medium.
    path = path.resolve()
    if not path.is_relative_to((ROOT / ".toolchain").resolve()):
        raise ValueError("Generate into the ignored operator directory, then use approved escrow")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        output.write("LWH_BACKUP_RECOVERY_KEY_HEX=" + secrets.token_hex(32) + "\n")
    if os.name == "nt":
        import csv

        identity = subprocess.check_output(["whoami", "/user", "/fo", "csv", "/nh"], text=True)
        sid = next(csv.reader([identity.strip()]))[1]
        subprocess.run(
            ["icacls", str(path), "/inheritance:r", "/grant:r", f"*{sid}:(F)"],
            check=True,
            capture_output=True,
        )
    print(
        json.dumps(
            {
                "recovery_key": "CREATED_IN_IGNORED_OPERATOR_FILE",
                "independent_custody": "REQUIRES_OPERATOR_ESCROW",
                "key_printed": False,
            }
        )
    )


async def operate(args):
    cfg = PlatformSettings(_env_file=args.env_file)
    cfg.validate_runtime()
    if not cfg.production:
        raise ValueError("This command requires explicit production cloud settings")
    database = Database(cfg.database_url)
    try:
        if await database.version() != 5:
            raise ValueError("Schema 5 must be installed first")
        if args.command == "reconcile":
            started = db.now()
            async with database.transaction() as session:
                value = await observe(session)
            await record(
                database,
                SecretBox(cfg.data_key_hex),
                kind="RECONCILIATION",
                outcome=value["integrity_outcome"],
                actor_id="SERVICE:CONTINUITY_OPERATOR_TOOL",
                started_at=started,
                summary=value,
                evidence={
                    "execution": "PRIVILEGED_OPERATOR_COMMAND",
                    "human_approval_inferred": False,
                },
            )
        elif args.command == "backup":
            key = recovery_key(args.escrow_file)
            value = await create_archive(database, cfg, key)
        else:
            key = recovery_key(args.escrow_file)
            if not args.backup_id:
                raise ValueError("An actual archive identity is required")
            value = await rehearse_restore(database, cfg, key, args.backup_id)
        print(json.dumps({"command": args.command, "result": value}))
    finally:
        await database.engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("keygen", "backup", "rehearse", "reconcile"))
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env.platform.local")
    parser.add_argument("--escrow-file", type=Path)
    parser.add_argument("--backup-id")
    arguments = parser.parse_args()
    if arguments.command != "reconcile" and arguments.escrow_file is None:
        parser.error("--escrow-file is required for key generation, archive or rehearsal")
    try:
        if arguments.command == "keygen":
            keygen(arguments.escrow_file)
        else:
            asyncio.run(operate(arguments))
    except Exception as exc:  # noqa: BLE001 -- never print provider bodies, keys, DSNs or data
        print(json.dumps({"continuity": "FAILED", "error_type": type(exc).__name__}))
        raise SystemExit(1) from None
