"""Shared, hermetic fixtures: no .env, no network, ephemeral SQLite and signing keys."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from lw_care_api.config import Settings


def make_test_settings(tmp_dir: Path, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": "test",
        "database_url": f"sqlite+aiosqlite:///{(tmp_dir / 'lw_care_test.db').as_posix()}",
        "upstash_redis_rest_url": "",
        "upstash_redis_rest_token": "",
        "openrouter_api_key": "",
        "token_signing_seed_hex": "11" * 32,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return make_test_settings(tmp_path)


@pytest.fixture
def bearer() -> Callable[..., dict[str, str]]:
    """Build an Authorization header from an app's TokenService."""

    def _make(
        app: object,
        *,
        sub: str,
        audience: str,
        roles: list[str],
        mfa: bool = False,
        org: str | None = None,
    ) -> dict[str, str]:
        token = app.state.token_service.issue(  # type: ignore[attr-defined]
            sub=sub, audience=audience, roles=roles, mfa=mfa, org=org
        )
        return {"Authorization": f"Bearer {token}"}

    return _make
