"""Read the project owner's credential files without logging their contents."""

import re
from pathlib import Path

SECRET_ROOT = Path("D:/Projects/secrets")


def read_secret(filename: str) -> str:
    return (SECRET_ROOT / filename).read_text(encoding="utf-8-sig").strip()


def token(filename: str, pattern: str | None = None) -> str:
    content = read_secret(filename)
    if pattern:
        match = re.search(pattern, content)
        if match:
            return match.group()
    for line in content.splitlines():
        line = line.strip(" `\"'")
        labelled = re.search(
            r"(?:token|key)\s*[:=]\s*[`\"']?([A-Za-z0-9_.-]{20,})", line, re.IGNORECASE
        )
        if labelled:
            return labelled.group(1)
        if re.fullmatch(r"[A-Za-z0-9_.-]{20,}", line):
            return line
    raise ValueError(f"No credential found in {filename}")


def github_token() -> str:
    return token("Prolific-Intelligence-GitHub.md", r"(?:github_pat_|ghp_)[A-Za-z0-9_]+")


def vercel_token() -> str:
    return token("Prolific-Intelligence-Vercel.md")


def database_url() -> str:
    match = re.search(
        r"postgres(?:ql)?://[^\s\x22\x27`<>]+", read_secret("lw-health-neondb-connection-string.md")
    )
    if not match:
        raise ValueError("No PostgreSQL connection string found")
    return match.group()


def openrouter_token() -> str:
    return token("prolific-engines- openrouter-kk.md", r"sk-or-v1-[A-Za-z0-9_-]+")


def email_token() -> str:
    return token("lw-health-resend.md", r"re_[A-Za-z0-9_]+")


def upstash_credentials() -> tuple[str, str]:
    content = read_secret("lw-health-upstash.md")
    url = re.search(r"https://[^\s\x22\x27`<>]+\.upstash\.io", content)
    secret = re.search(
        r"UPSTASH_REDIS_REST_TOKEN\s*[:=]\s*[`\"']?([A-Za-z0-9_.=-]+)", content, re.IGNORECASE
    )
    if not secret:
        secret = re.search(r"\b(?:AX|ey)[A-Za-z0-9_.=-]{30,}", content)
    if not url or not secret:
        raise ValueError("Incomplete Upstash REST credentials")
    return url.group(), secret.group(1) if secret.lastindex else secret.group()
