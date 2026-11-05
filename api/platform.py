"""Dedicated Vercel entrypoint for the durable institutional runtime."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/api/src"))

from lw_care_api.platform.main import create_platform_app

app = create_platform_app()
