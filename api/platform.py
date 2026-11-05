"""Dedicated Vercel entrypoint for the durable institutional runtime."""

import sys
from pathlib import Path

for base in (Path(__file__).resolve().parent, Path(__file__).resolve().parents[1], Path.cwd()):
    source = base / "services/api/src"
    if (source / "lw_care_api/platform").is_dir():
        sys.path.insert(0, str(source))
        break
else:
    raise RuntimeError("The institutional runtime source was not included in the deployment")

from lw_care_api.platform.main import create_platform_app

app = create_platform_app()
