"""Disposable preview entrypoint, never a production entrypoint or operating service.

Uploaded only by verify_capacity_cloud.py. Business code and NullPool are unchanged;
schema translation, service exclusion and measurement are qualification instrumentation.
"""

import os
import re
import sys
from pathlib import Path
from time import perf_counter

from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.responses import JSONResponse

for base in (Path(__file__).resolve().parents[1], Path.cwd()):
    source = base / "services/api/src"
    if (source / "lw_care_api/platform").is_dir():
        sys.path.insert(0, str(source))
        break

from lw_care_api.platform import db
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.main import create_platform_app


def candidate(settings, namespace, *, provider_environment):
    if provider_environment != "preview" or not re.fullmatch(
        r"lwh_native_verify_[0-9a-f]{32}", namespace
    ):
        raise ValueError("Capacity instrumentation requires a disposable preview/schema")
    isolated = settings.model_copy(
        update={
            "environment": "test",
            "resend_api_key": "",
            "email_from": "",
            "s3_endpoint": "",
            "s3_access_key": "",
            "s3_secret_key": "",
            "s3_bucket": "",
            "clamav_host": "",
            "jobs_secret": "",
            "openrouter_api_key": "",
            "openrouter_model": "",
            "upstash_rest_url": "",
            "upstash_rest_token": "",
            "dispatch_recovery_after_commit": False,
            "enforce_activation_dossiers": False,
        }
    )
    app = create_platform_app(isolated)
    database = app.state.database
    database.engine = database.engine.execution_options(schema_translate_map={db.SCHEMA: namespace})
    database.session = async_sessionmaker(database.engine, expire_on_commit=False)

    @app.middleware("http")
    async def qualify(request, call_next):
        if not (request.url.path == "/v1/ready" or request.url.path.startswith("/v1/reporting/")):
            return JSONResponse(
                {"error": {"code": "QUALIFICATION_SERVICE_EXCLUDED"}}, status_code=403
            )
        started = perf_counter()
        response = await call_next(request)
        response.headers["X-Qualification-Elapsed-Ms"] = str(
            round((perf_counter() - started) * 1000, 3)
        )
        try:
            import resource

            # Linux process lifetime high-water RSS, not per-request allocated memory.
            response.headers["X-Qualification-Process-Maxrss-Kib"] = str(
                resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            )
        except ImportError:
            pass
        response.headers["X-Qualification-Pool"] = type(database.engine.pool).__name__
        return response

    return app


app = (
    candidate(
        PlatformSettings(),
        os.environ["LWH_CAPACITY_SCHEMA"],
        provider_environment=os.environ.get("VERCEL_ENV"),
    )
    if os.environ.get("LWH_CAPACITY_SCHEMA")
    else None
)
