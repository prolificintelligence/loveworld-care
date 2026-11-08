"""Run durable operating work once, or on an explicitly provisioned future worker host."""

import argparse
import asyncio
import json
from pathlib import Path

from ..config import PlatformSettings
from ..db import Database
from ..security import SecretBox
from .jobs import run_tick


async def main(args):
    settings = PlatformSettings(_env_file=Path(args.env_file) if args.env_file else None)
    settings.validate_runtime()
    if not settings.controls_enabled:
        raise RuntimeError("Operating controls are paused")
    database = Database(settings.database_url)
    try:
        if (await database.version() or 0) < 4:
            raise RuntimeError("Migration 4 is required")
        while True:
            print(
                json.dumps(await run_tick(database, settings, SecretBox(settings.data_key_hex))),
                flush=True,
            )
            if args.once:
                return
            await asyncio.sleep(args.interval)
    finally:
        await database.engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=30)
    arguments = parser.parse_args()
    if not 5 <= arguments.interval <= 3600:
        parser.error("Interval must be between 5 and 3600 seconds")
    try:
        asyncio.run(main(arguments))
    except KeyboardInterrupt:
        pass
    except Exception as exc:  # noqa: BLE001 -- avoid credentials in connection/settings exception values
        print(json.dumps({"worker": "FAILED", "error_type": type(exc).__name__}), flush=True)
        raise SystemExit(1) from None
