"""
Verified bearer-token identity for the four LoveWorld Care audiences (ADR-0002, ADR-0003).

Tokens are EdDSA (Ed25519) signed JWTs. Identity is derived ONLY from a verified token;
client-supplied identity headers are never trusted.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

AUD_PATIENT = "lwc:patient"
AUD_CLINICIAN = "lwc:clinician"
AUD_COMMAND = "lwc:command"
AUD_SPONSOR = "lwc:sponsor"

# Each audience may only carry roles from its allow-list. A sponsor role can never ride in a
# patient token, and a patient role can never ride in a staff token.
AUDIENCE_ROLES: dict[str, frozenset[str]] = {
    AUD_PATIENT: frozenset({"PATIENT", "AUTHORIZED_PROXY"}),
    AUD_CLINICIAN: frozenset({"CLINICIAN_GP", "CLINICIAN_SPECIALIST", "CLINICAL_GOVERNANCE_LEAD"}),
    AUD_COMMAND: frozenset(
        {
            "CLINICAL_OPS",
            "CLINICAL_GOVERNANCE_LEAD",
            "EXECUTIVE_DIRECTOR",
            "FINANCE_CONTROLLER",
            "SUPPORT_AGENT",
            "PLATFORM_SRE",
        }
    ),
    AUD_SPONSOR: frozenset({"SPONSOR_ADMIN", "INSTITUTION_ADMIN"}),
}
STAFF_AUDIENCES: frozenset[str] = frozenset({AUD_CLINICIAN, AUD_COMMAND})
ALGORITHM = "EdDSA"


class TokenError(Exception):
    """Raised when a token is missing, malformed, expired, revoked or out of scope."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class TokenClaims:
    sub: str
    aud: str
    roles: tuple[str, ...]
    mfa: bool
    sid: str
    jti: str
    org: str | None
    expires_at: datetime


class TokenService:
    def __init__(
        self,
        *,
        signing_seed_hex: str,
        issuer: str,
        default_ttl: timedelta = timedelta(minutes=30),
    ) -> None:
        seed = bytes.fromhex(signing_seed_hex)
        if len(seed) != 32:
            raise ValueError("Token signing seed must be exactly 32 bytes (64 hex chars).")
        self._private_key = Ed25519PrivateKey.from_private_bytes(seed)
        self._public_key = self._private_key.public_key()
        self._issuer = issuer
        self._default_ttl = default_ttl
        # Revoked session IDs. Replace with a shared Redis set when running multiple replicas.
        self._revoked_sids: set[str] = set()

    @staticmethod
    def generate_seed_hex() -> str:
        return secrets.token_hex(32)

    def issue(
        self,
        *,
        sub: str,
        audience: str,
        roles: list[str] | tuple[str, ...],
        mfa: bool,
        org: str | None = None,
        ttl: timedelta | None = None,
        sid: str | None = None,
    ) -> str:
        self._assert_roles_allowed(audience, roles)
        now = datetime.now(timezone.utc)
        payload: dict[str, object] = {
            "iss": self._issuer,
            "aud": audience,
            "sub": sub,
            "roles": sorted(set(roles)),
            "mfa": bool(mfa),
            "sid": sid or str(uuid4()),
            "jti": str(uuid4()),
            "iat": now,
            "nbf": now,
            "exp": now + (ttl or self._default_ttl),
        }
        if org:
            payload["org"] = org
        return jwt.encode(payload, self._private_key, algorithm=ALGORITHM)

    def verify(self, token: str, allowed_audiences: frozenset[str] | set[str]) -> TokenClaims:
        if not token:
            raise TokenError("TOKEN_MISSING")
        try:
            data = jwt.decode(
                token,
                self._public_key,
                algorithms=[ALGORITHM],
                audience=list(allowed_audiences),
                issuer=self._issuer,
                options={"require": ["iss", "aud", "sub", "exp", "nbf", "iat", "jti", "sid"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise TokenError("TOKEN_EXPIRED") from exc
        except jwt.InvalidAudienceError as exc:
            raise TokenError("TOKEN_AUDIENCE_NOT_PERMITTED") from exc
        except jwt.PyJWTError as exc:
            raise TokenError("TOKEN_INVALID") from exc

        aud = data["aud"]
        if not isinstance(aud, str):
            raise TokenError("TOKEN_INVALID")
        roles = data.get("roles")
        if not isinstance(roles, list) or not roles or not all(isinstance(r, str) for r in roles):
            raise TokenError("TOKEN_INVALID")
        try:
            self._assert_roles_allowed(aud, roles)
        except ValueError as exc:
            raise TokenError("TOKEN_ROLE_NOT_PERMITTED_FOR_AUDIENCE") from exc
        if data["sid"] in self._revoked_sids:
            raise TokenError("TOKEN_REVOKED")

        org = data.get("org")
        return TokenClaims(
            sub=str(data["sub"]),
            aud=aud,
            roles=tuple(roles),
            mfa=data.get("mfa") is True,
            sid=str(data["sid"]),
            jti=str(data["jti"]),
            org=str(org) if org else None,
            expires_at=datetime.fromtimestamp(int(data["exp"]), tz=timezone.utc),
        )

    def revoke_session(self, sid: str) -> None:
        self._revoked_sids.add(sid)

    def identify_for_audit(self, token: str) -> tuple[str, tuple[str, ...]] | None:
        """
        Return (sub, roles) for a token whose signature, issuer and expiry are valid but whose
        audience may be out of scope. Used ONLY to attribute denied attempts in the audit trail;
        never to grant access.
        """
        try:
            data = jwt.decode(
                token,
                self._public_key,
                algorithms=[ALGORITHM],
                issuer=self._issuer,
                options={"verify_aud": False, "require": ["iss", "sub", "exp"]},
            )
        except jwt.PyJWTError:
            return None
        roles = data.get("roles")
        role_tuple = tuple(r for r in roles if isinstance(r, str)) if isinstance(roles, list) else ()
        return str(data["sub"]), role_tuple

    def public_jwk(self) -> dict[str, str]:
        """RFC 8037 OKP JWK so the apps/edge can verify tokens without the private seed."""
        import base64

        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        raw = self._public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
        x = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
        return {"kty": "OKP", "crv": "Ed25519", "alg": ALGORITHM, "use": "sig", "x": x}

    @staticmethod
    def _assert_roles_allowed(audience: str, roles: list[str] | tuple[str, ...]) -> None:
        allowed = AUDIENCE_ROLES.get(audience)
        if allowed is None:
            raise ValueError(f"Unknown audience: {audience}")
        if not roles or not set(roles) <= allowed:
            raise ValueError(f"Roles {sorted(roles)} are not permitted for audience {audience}")
