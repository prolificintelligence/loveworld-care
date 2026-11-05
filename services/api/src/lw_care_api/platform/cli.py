"""Explicit database release and one-time real administrator invitation."""

import argparse
import asyncio
import json
from datetime import datetime

from sqlalchemy import func, select

from . import db
from .config import get_platform_settings
from .contracts import Invite
from .operations import create_invitation, deliver_invitations
from .security import SecretBox


async def execute(args):
    cfg = get_platform_settings()
    cfg.validate_runtime()
    database = db.Database(cfg.database_url)
    try:
        if args.command == "migrate":
            await database.migrate()
            print(json.dumps({"schema_version": 1, "status": "MIGRATED", "seeded_records": 0}))
        elif args.command == "bootstrap":
            box = SecretBox(cfg.data_key_hex)
            async with database.transaction() as session:
                count = await session.scalar(select(func.count()).select_from(db.accounts))
                if count:
                    raise RuntimeError(
                        "Bootstrap requires an empty account registry; use an authenticated administrator"
                    )
                payload = Invite(
                    email=args.email,
                    name=args.name,
                    role="PLATFORM_ADMIN",
                    scope_type="GLOBAL",
                    valid_until=datetime.fromisoformat(args.valid_until),
                )
                result = await create_invitation(
                    session, cfg, box, payload, "INITIAL_DEPLOYMENT", db.uid()
                )
                # Registry stewardship is an independent, audited initial assignment.
                await session.execute(
                    db.grants.insert().values(
                        id=db.uid(),
                        account_id=result["account_id"],
                        role="REGISTRY_STEWARD",
                        scope_type="GLOBAL",
                        scope_id="GLOBAL",
                        valid_from=db.now(),
                        valid_until=payload.valid_until.isoformat(),
                        revoked=False,
                        grantor="INITIAL_DEPLOYMENT",
                    )
                )
            print(json.dumps(result))
            print(json.dumps(await deliver_invitations(database, cfg, box)))
        elif args.command == "deliver":
            print(json.dumps(await deliver_invitations(database, cfg, SecretBox(cfg.data_key_hex))))
    finally:
        await database.engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate")
    bootstrap = sub.add_parser("bootstrap")
    bootstrap.add_argument("--email", required=True)
    bootstrap.add_argument("--name", required=True)
    bootstrap.add_argument("--valid-until", required=True)
    sub.add_parser("deliver")
    asyncio.run(execute(parser.parse_args()))


if __name__ == "__main__":
    main()
