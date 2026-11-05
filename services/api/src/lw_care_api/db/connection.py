"""Shared secure PostgreSQL URL normalisation for legacy and institutional runtimes."""

import ssl
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def normalize_async_database_url(raw_url: str) -> tuple[str, dict[str, Any]]:
    url = raw_url.strip()
    if url.startswith("sqlite"):
        return url, {}
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query))
    secure = query.pop("sslmode", None) in ("require", "verify-full", "verify-ca") or (
        "neon.tech" in (parsed.hostname or "")
    )
    query.pop("channel_binding", None)
    query.pop("ssl", None)
    return urlunparse(parsed._replace(query=urlencode(query))), (
        {"ssl": ssl.create_default_context()} if secure else {}
    )
