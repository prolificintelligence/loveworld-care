"""Persistent opaque sessions, password verification and encrypted, replay-safe MFA."""

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import pyotp
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select, update

from . import db


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def hash_password(password: str) -> str:
    if not 14 <= len(password) <= 256:
        raise ValueError("Use a password with 14 to 256 characters")
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000).hex()
    return f"pbkdf2_sha256$600000${salt}${derived}"


def verify_password(password: str, stored: str | None) -> bool:
    fallback = "pbkdf2_sha256$600000$invalid$" + "0" * 64
    try:
        algorithm, rounds, salt, expected = (stored or fallback).split("$")
        if algorithm != "pbkdf2_sha256" or int(rounds) != 600_000:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(rounds)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


class SecretBox:
    def __init__(self, key: str):
        self.cipher = AESGCM(bytes.fromhex(key))

    def encrypt(self, value: str) -> str:
        nonce = secrets.token_bytes(12)
        encrypted = self.cipher.encrypt(nonce, value.encode(), b"lwh-platform-v1")
        return base64.urlsafe_b64encode(nonce + encrypted).decode()

    def decrypt(self, value: str) -> str:
        raw = base64.urlsafe_b64decode(value)
        return self.cipher.decrypt(raw[:12], raw[12:], b"lwh-platform-v1").decode()


async def accept_totp(session, account: dict, code: str, box: SecretBox) -> bool:
    if not account["totp_ciphertext"]:
        return False
    totp = pyotp.TOTP(box.decrypt(account["totp_ciphertext"]))
    current = totp.timecode(datetime.now(UTC))
    for step in (current, current - 1, current + 1):
        if step <= account["totp_last_step"] or not hmac.compare_digest(totp.at(step * 30), code):
            continue
        result = await session.execute(
            update(db.accounts)
            .where(
                db.accounts.c.id == account["id"],
                db.accounts.c.totp_last_step < step,
            )
            .values(totp_last_step=step)
        )
        return result.rowcount == 1
    return False


async def issue_session(session, account_id: str, minutes: int) -> str:
    token = secrets.token_urlsafe(48)
    await session.execute(
        db.sessions.insert().values(
            id=db.uid(),
            token_hash=digest(token),
            account_id=account_id,
            expires_at=(datetime.now(UTC) + timedelta(minutes=minutes)).isoformat(),
            revoked=False,
        )
    )
    return token


async def resolve_session(session, token: str | None) -> dict | None:
    if not token:
        return None
    row = (
        (
            await session.execute(
                select(db.accounts)
                .join(db.sessions)
                .where(
                    db.sessions.c.token_hash == digest(token),
                    db.sessions.c.revoked.is_(False),
                    db.sessions.c.expires_at > db.now(),
                    db.accounts.c.active.is_(True),
                )
            )
        )
        .mappings()
        .first()
    )
    if row is None:
        return None
    actor = {"id": row["id"], "name": row["name"], "email": row["email"]}
    actor["grants"] = [
        dict(g)
        for g in (
            await session.execute(
                select(db.grants).where(
                    db.grants.c.account_id == row["id"],
                    db.grants.c.revoked.is_(False),
                    db.grants.c.valid_from <= db.now(),
                    db.grants.c.valid_until > db.now(),
                )
            )
        ).mappings()
    ]
    return actor
