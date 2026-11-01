"""
Standards-Compliant Identity, MFA, ProxyAuthority, Credential Expiry & RBAC/ABAC Engine
Plus Tamper-Evident HMAC-SHA256 Hash-Chained Audit Logger (§8.1, §12.4, §16.2–16.5).
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import uuid4

import jwt
import pyotp


@dataclass(frozen=True)
class BreakGlassGrant:
    grant_id: str
    clinician_id: str
    target_patient_id: str
    reason: str
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class ProxyAuthorityGrant:
    proxy_grant_id: str
    patient_id: str
    representative_user_id: str
    allowed_scopes: tuple[str, ...]
    valid_until: datetime
    revoked: bool = False


@dataclass
class AuthenticatedActor:
    actor_id: str
    full_name: str
    roles: list[str]
    mfa_verified: bool = True
    session_id: str = field(default_factory=lambda: str(uuid4()))
    session_locked: bool = False
    clinician_status: str | None = None
    clinician_mdcn_licence: str | None = None
    credential_expires_at: datetime | None = None
    active_proxy_grants: list[ProxyAuthorityGrant] = field(default_factory=list)
    active_break_glass: BreakGlassGrant | None = None

    def is_clinician_credential_active(self, now: datetime | None = None) -> bool:
        """§8.1 & AT-07: Credential expiry automatically blocks clinical case claiming/signing."""
        check_now = now or datetime.now(timezone.utc)
        if self.clinician_status != "APPROVED_ACTIVE":
            return False
        if not self.clinician_mdcn_licence:
            return False
        if self.credential_expires_at and self.credential_expires_at <= check_now:
            return False
        return True


@dataclass(frozen=True)
class AuditRecord:
    audit_id: str
    sequence_number: int
    occurred_at_iso: str
    request_id: str
    actor_id: str
    actor_roles: list[str]
    purpose: str
    action: str
    resource_type: str
    resource_opaque_id: str
    data_tier: str
    outcome: Literal["SUCCESS", "DENIED", "ERROR"]
    reason_code: str
    break_glass_grant_id: str | None
    previous_entry_hash: str
    entry_hash: str


class TamperEvidentAuditLogger:
    """
    Append-only HMAC-SHA256 hash-chained audit trail (§16.3 & FR-SEC-01).
    Every access check (allowed or denied) is cryptographically chained to the prior entry.
    """

    def __init__(self, hmac_key: str) -> None:
        self._hmac_key = hmac_key.encode("utf-8")
        self._entries: list[AuditRecord] = []
        self._last_hash = "0" * 64

    @property
    def entries(self) -> list[AuditRecord]:
        return list(self._entries)

    def record(
        self,
        *,
        request_id: str,
        actor: AuthenticatedActor,
        purpose: str,
        action: str,
        resource_type: str,
        resource_opaque_id: str,
        data_tier: str,
        outcome: Literal["SUCCESS", "DENIED", "ERROR"],
        reason_code: str,
    ) -> AuditRecord:
        seq = len(self._entries) + 1
        now_iso = datetime.now(timezone.utc).isoformat()
        bg_id = actor.active_break_glass.grant_id if actor.active_break_glass else None

        canonical = json.dumps(
            {
                "seq": seq,
                "occurred_at_iso": now_iso,
                "request_id": request_id,
                "actor_id": actor.actor_id,
                "actor_roles": sorted(actor.roles),
                "purpose": purpose,
                "action": action,
                "resource_type": resource_type,
                "resource_opaque_id": resource_opaque_id,
                "data_tier": data_tier,
                "outcome": outcome,
                "reason_code": reason_code,
                "break_glass_grant_id": bg_id,
                "previous_entry_hash": self._last_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        digest = hmac.new(self._hmac_key, canonical, hashlib.sha256).hexdigest()
        rec = AuditRecord(
            audit_id=str(uuid4()),
            sequence_number=seq,
            occurred_at_iso=now_iso,
            request_id=request_id,
            actor_id=actor.actor_id,
            actor_roles=list(actor.roles),
            purpose=purpose,
            action=action,
            resource_type=resource_type,
            resource_opaque_id=resource_opaque_id,
            data_tier=data_tier,
            outcome=outcome,
            reason_code=reason_code,
            break_glass_grant_id=bg_id,
            previous_entry_hash=self._last_hash,
            entry_hash=digest,
        )
        self._entries.append(rec)
        self._last_hash = digest
        return rec

    def verify_chain_integrity(self) -> bool:
        prev = "0" * 64
        for rec in self._entries:
            if rec.previous_entry_hash != prev:
                return False
            canonical = json.dumps(
                {
                    "seq": rec.sequence_number,
                    "occurred_at_iso": rec.occurred_at_iso,
                    "request_id": rec.request_id,
                    "actor_id": rec.actor_id,
                    "actor_roles": sorted(rec.actor_roles),
                    "purpose": rec.purpose,
                    "action": rec.action,
                    "resource_type": rec.resource_type,
                    "resource_opaque_id": rec.resource_opaque_id,
                    "data_tier": rec.data_tier,
                    "outcome": rec.outcome,
                    "reason_code": rec.reason_code,
                    "break_glass_grant_id": rec.break_glass_grant_id,
                    "previous_entry_hash": rec.previous_entry_hash,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            expected = hmac.new(self._hmac_key, canonical, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, rec.entry_hash):
                return False
            prev = rec.entry_hash
        return True


class IdentityAndSessionManager:
    """
    Manages revocable sessions, shared-device session locks (AT-13), TOTP MFA step-up,
    Break-Glass elevation, and RBAC+ABAC policy enforcement.
    """

    def __init__(self, jwt_secret: str, audit_logger: TamperEvidentAuditLogger) -> None:
        self._jwt_secret = jwt_secret
        self._audit = audit_logger
        self._sessions: dict[str, AuthenticatedActor] = {}
        self._totp_secrets: dict[str, str] = {}

    def register_session(
        self, actor: AuthenticatedActor, totp_secret: str | None = None
    ) -> str:
        self._sessions[actor.session_id] = actor
        if totp_secret:
            self._totp_secrets[actor.actor_id] = totp_secret
        elif actor.actor_id not in self._totp_secrets:
            self._totp_secrets[actor.actor_id] = pyotp.random_base32()

        payload = {
            "sub": actor.actor_id,
            "sid": actor.session_id,
            "roles": actor.roles,
            "mfa": actor.mfa_verified,
            "exp": datetime.now(timezone.utc) + timedelta(hours=8),
        }
        return jwt.encode(payload, self._jwt_secret, algorithm="HS256")

    def get_totp_code_for_actor(self, actor_id: str) -> str:
        secret = self._totp_secrets.get(actor_id)
        if not secret:
            secret = pyotp.random_base32()
            self._totp_secrets[actor_id] = secret
        return pyotp.TOTP(secret).now()

    def verify_totp_step_up(self, actor_id: str, code: str) -> bool:
        secret = self._totp_secrets.get(actor_id)
        if not secret:
            return False
        totp = pyotp.TOTP(secret)
        return bool(totp.verify(code, valid_window=1))

    def lock_shared_device_session(self, session_id: str, request_id: str) -> None:
        """AT-13: Shared-device lock immediately blocks session access until re-authenticated."""
        actor = self._sessions.get(session_id)
        if actor:
            actor.session_locked = True
            self._audit.record(
                request_id=request_id,
                actor=actor,
                purpose="PATIENT_SELF_SERVICE",
                action="LOCK_SHARED_DEVICE_SESSION",
                resource_type="SESSION",
                resource_opaque_id=session_id,
                data_tier="T2_PERSONAL",
                outcome="SUCCESS",
                reason_code="SESSION_LOCKED",
            )

    def unlock_shared_device_session(
        self, session_id: str, mfa_or_pin_verified: bool, request_id: str
    ) -> bool:
        actor = self._sessions.get(session_id)
        if not actor or not mfa_or_pin_verified:
            return False
        actor.session_locked = False
        self._audit.record(
            request_id=request_id,
            actor=actor,
            purpose="PATIENT_SELF_SERVICE",
            action="UNLOCK_SHARED_DEVICE_SESSION",
            resource_type="SESSION",
            resource_opaque_id=session_id,
            data_tier="T2_PERSONAL",
            outcome="SUCCESS",
            reason_code="SESSION_UNLOCKED",
        )
        return True

    def issue_break_glass_grant(
        self,
        clinician: AuthenticatedActor,
        target_patient_id: str,
        reason: str,
        request_id: str,
        duration_minutes: int = 30,
    ) -> BreakGlassGrant:
        if not clinician.is_clinician_credential_active():
            self._audit.record(
                request_id=request_id,
                actor=clinician,
                purpose="BREAK_GLASS_EMERGENCY_REVIEW",
                action="ISSUE_BREAK_GLASS",
                resource_type="CLINICAL_RECORD_T3",
                resource_opaque_id=target_patient_id,
                data_tier="T3_SENSITIVE_CLINICAL",
                outcome="DENIED",
                reason_code="DENIED_CLINICIAN_CREDENTIAL_EXPIRED_OR_INACTIVE",
            )
            raise PermissionError("Active clinician credential required for break-glass access.")

        now = datetime.now(timezone.utc)
        grant = BreakGlassGrant(
            grant_id=str(uuid4()),
            clinician_id=clinician.actor_id,
            target_patient_id=target_patient_id,
            reason=reason,
            issued_at=now,
            expires_at=now + timedelta(minutes=duration_minutes),
        )
        clinician.active_break_glass = grant
        self._audit.record(
            request_id=request_id,
            actor=clinician,
            purpose="BREAK_GLASS_EMERGENCY_REVIEW",
            action="ISSUE_BREAK_GLASS",
            resource_type="CLINICAL_RECORD_T3",
            resource_opaque_id=target_patient_id,
            data_tier="T3_SENSITIVE_CLINICAL",
            outcome="SUCCESS",
            reason_code="BREAK_GLASS_ISSUED",
        )
        return grant

    def authorize_clinical_t3_access(
        self,
        *,
        request_id: str,
        actor: AuthenticatedActor,
        action: Literal["READ", "WRITE", "CLAIM", "SIGN"],
        purpose: str,
        patient_id: str,
        assigned_clinician_id: str | None,
        now: datetime | None = None,
    ) -> None:
        check_now = now or datetime.now(timezone.utc)

        # AT-13: Shared device session lock check
        if actor.session_locked:
            self._audit.record(
                request_id=request_id,
                actor=actor,
                purpose=purpose,
                action=action,
                resource_type="CLINICAL_RECORD_T3",
                resource_opaque_id=patient_id,
                data_tier="T3_SENSITIVE_CLINICAL",
                outcome="DENIED",
                reason_code="DENIED_SESSION_LOCKED",
            )
            raise PermissionError("DENIED_SESSION_LOCKED")

        # AT-06: Sponsors, Institutions, Support, Ops, Finance, SRE can NEVER read T3 clinical records
        forbidden_roles = {
            "SPONSOR_ADMIN",
            "INSTITUTION_ADMIN",
            "SUPPORT_AGENT",
            "CLINICAL_OPS",
            "FINANCE_CONTROLLER",
            "PLATFORM_SRE",
        }
        if any(r in forbidden_roles for r in actor.roles) and not any(
            r in {"CLINICIAN_GP", "CLINICIAN_SPECIALIST", "CLINICAL_GOVERNANCE_LEAD"}
            for r in actor.roles
        ):
            self._audit.record(
                request_id=request_id,
                actor=actor,
                purpose=purpose,
                action=action,
                resource_type="CLINICAL_RECORD_T3",
                resource_opaque_id=patient_id,
                data_tier="T3_SENSITIVE_CLINICAL",
                outcome="DENIED",
                reason_code="DENIED_ROLE_FORBIDDEN_FROM_T3_CLINICAL",
            )
            raise PermissionError("DENIED_ROLE_FORBIDDEN_FROM_T3_CLINICAL")

        # Clinician check
        if any(r in {"CLINICIAN_GP", "CLINICIAN_SPECIALIST"} for r in actor.roles):
            if not actor.mfa_verified:
                self._audit.record(
                    request_id=request_id,
                    actor=actor,
                    purpose=purpose,
                    action=action,
                    resource_type="CLINICAL_RECORD_T3",
                    resource_opaque_id=patient_id,
                    data_tier="T3_SENSITIVE_CLINICAL",
                    outcome="DENIED",
                    reason_code="DENIED_MFA_REQUIRED",
                )
                raise PermissionError("DENIED_MFA_REQUIRED")

            # AT-07: Active & non-expired medical licence check
            if not actor.is_clinician_credential_active(check_now):
                self._audit.record(
                    request_id=request_id,
                    actor=actor,
                    purpose=purpose,
                    action=action,
                    resource_type="CLINICAL_RECORD_T3",
                    resource_opaque_id=patient_id,
                    data_tier="T3_SENSITIVE_CLINICAL",
                    outcome="DENIED",
                    reason_code="DENIED_CLINICIAN_CREDENTIAL_EXPIRED_OR_INACTIVE",
                )
                raise PermissionError("DENIED_CLINICIAN_CREDENTIAL_EXPIRED_OR_INACTIVE")

            if action == "CLAIM" and assigned_clinician_id is None:
                self._audit.record(
                    request_id=request_id,
                    actor=actor,
                    purpose=purpose,
                    action=action,
                    resource_type="CLINICAL_RECORD_T3",
                    resource_opaque_id=patient_id,
                    data_tier="T3_SENSITIVE_CLINICAL",
                    outcome="SUCCESS",
                    reason_code="ALLOWED_CASE_CLAIM",
                )
                return

            is_assigned = assigned_clinician_id == actor.actor_id
            has_break_glass = (
                actor.active_break_glass is not None
                and actor.active_break_glass.target_patient_id == patient_id
                and actor.active_break_glass.expires_at > check_now
            )
            if not is_assigned and not has_break_glass:
                self._audit.record(
                    request_id=request_id,
                    actor=actor,
                    purpose=purpose,
                    action=action,
                    resource_type="CLINICAL_RECORD_T3",
                    resource_opaque_id=patient_id,
                    data_tier="T3_SENSITIVE_CLINICAL",
                    outcome="DENIED",
                    reason_code="DENIED_UNASSIGNED_CLINICIAN_WITHOUT_BREAK_GLASS",
                )
                raise PermissionError("DENIED_UNASSIGNED_CLINICIAN_WITHOUT_BREAK_GLASS")

            self._audit.record(
                request_id=request_id,
                actor=actor,
                purpose=purpose,
                action=action,
                resource_type="CLINICAL_RECORD_T3",
                resource_opaque_id=patient_id,
                data_tier="T3_SENSITIVE_CLINICAL",
                outcome="SUCCESS",
                reason_code="ALLOWED_CLINICIAN",
            )
            return

        # Patient / Proxy check
        if "PATIENT" in actor.roles and actor.actor_id == patient_id and action in {"READ", "WRITE"}:
            self._audit.record(
                request_id=request_id,
                actor=actor,
                purpose=purpose,
                action=action,
                resource_type="CLINICAL_RECORD_T3",
                resource_opaque_id=patient_id,
                data_tier="T3_SENSITIVE_CLINICAL",
                outcome="SUCCESS",
                reason_code="ALLOWED_PATIENT_OWNER",
            )
            return

        if "AUTHORIZED_PROXY" in actor.roles and action in {"READ", "WRITE"}:
            valid_proxy = next(
                (
                    g
                    for g in actor.active_proxy_grants
                    if g.patient_id == patient_id and not g.revoked and g.valid_until > check_now
                ),
                None,
            )
            if valid_proxy:
                self._audit.record(
                    request_id=request_id,
                    actor=actor,
                    purpose="GUARDIAN_PROXY_CARE",
                    action=action,
                    resource_type="CLINICAL_RECORD_T3",
                    resource_opaque_id=patient_id,
                    data_tier="T3_SENSITIVE_CLINICAL",
                    outcome="SUCCESS",
                    reason_code="ALLOWED_VERIFIED_PROXY",
                )
                return

        self._audit.record(
            request_id=request_id,
            actor=actor,
            purpose=purpose,
            action=action,
            resource_type="CLINICAL_RECORD_T3",
            resource_opaque_id=patient_id,
            data_tier="T3_SENSITIVE_CLINICAL",
            outcome="DENIED",
            reason_code="DENIED_UNAUTHORIZED_PATIENT_OR_PROXY",
        )
        raise PermissionError("DENIED_UNAUTHORIZED_PATIENT_OR_PROXY")
