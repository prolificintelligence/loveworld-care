"""
Neon PostgreSQL Migration and Seed Runner.
Executes schema creation, tables, append-only triggers, and baseline seeding on Neon DB.
"""

import asyncio
import os
import sys

# Ensure services are in Python path
sys.path.insert(0, os.path.abspath("services/api/src"))
sys.path.insert(0, os.path.abspath("services/protocol-runtime/src"))
sys.path.insert(0, os.path.abspath("services/model-gateway/src"))
sys.path.insert(0, os.path.abspath("services/worker/src"))

from lw_care_api.db.neon_migrator import NeonDatabaseManager


async def main() -> None:
    secret_path = r"D:\Projects\secrets\lw-health-neondb-connection-string.md"
    with open(secret_path, "r", encoding="utf-8") as f:
        connection_string = f.read().strip()

    print(f"Connecting to Neon DB...")
    migrator = NeonDatabaseManager(connection_string)
    
    print("Running migrate_and_seed()...")
    result = await migrator.migrate_and_seed()
    print("Migration and seed result:", result)
    
    health = await migrator.get_health_summary()
    print("Health summary:", health)
    print("Neon Database Migration Complete!")


if __name__ == "__main__":
    asyncio.run(main())
