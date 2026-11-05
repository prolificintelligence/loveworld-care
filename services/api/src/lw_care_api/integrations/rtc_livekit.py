"""
LiveKit WebRTC Provider Adapter behind RTCAdapter interface (§8.3, §12.3, §14.5, AT-09).

Enforces:
- Short-lived HMAC-SHA256 signed LiveKit access tokens scoped to the specific encounter room.
- `recording_enabled = False` by default (`FR-CNS-01`).
- Explicit low-bandwidth audio-only mode fallback (`AUDIO_FALLBACK` modality).
- AT-09 invariant: A brief RTC room connection or media disconnect NEVER automatically marks
  an encounter as clinically completed or billable; only `encounter.signed` by the clinician
  triggers completion/redemption.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt


@dataclass(frozen=True)
class RTCRoomSessionCredentials:
    encounter_id: str
    room_name: str
    server_url: str
    participant_identity: str
    participant_role: Literal["PATIENT", "CLINICIAN"]
    modality: Literal["VIDEO", "AUDIO_FALLBACK"]
    recording_enabled: bool
    access_token: str
    expires_at_iso: str


@dataclass(frozen=True)
class RTCWebhookDisposition:
    event_type: str
    room_name: str
    encounter_id: str
    connection_duration_seconds: int
    interrupted_early: bool
    triggers_billable_completion: Literal[False] = False
    recommended_clinical_action: str = "CLINICIAN_DISPOSITION_OR_AUDIO_FALLBACK_REQUIRED"


class LiveKitRTCAdapter:
    """Production LiveKit WebRTC token issuer and webhook verifier."""

    def __init__(
        self,
        *,
        livekit_url: str,
        api_key: str,
        api_secret: str,
        webhook_secret: str,
        recording_enabled_by_default: bool = False,
    ) -> None:
        self._url = livekit_url
        self._api_key = api_key
        self._api_secret = api_secret
        self._webhook_secret = webhook_secret
        self._recording_default = recording_enabled_by_default

    def create_encounter_room_token(
        self,
        *,
        encounter_id: str,
        participant_id: str,
        participant_role: Literal["PATIENT", "CLINICIAN"],
        modality: Literal["VIDEO", "AUDIO_FALLBACK"] = "VIDEO",
        explicit_recording_consent: bool = False,
        ttl_minutes: int = 45,
    ) -> RTCRoomSessionCredentials:
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=ttl_minutes)
        room_name = f"lw-care-enc-{encounter_id}"

        # FR-CNS-01: Recordings disabled by default; requires both platform setting & explicit consent
        recording_allowed = bool(self._recording_default and explicit_recording_consent)

        video_grant = {
            "roomJoin": True,
            "room": room_name,
            "canPublish": True,
            "canSubscribe": True,
            "canPublishData": True,
            "canPublishSources": (
                ["microphone"]
                if modality == "AUDIO_FALLBACK"
                else ["camera", "microphone", "screen_share"]
            ),
            "roomRecord": recording_allowed,
        }

        claims = {
            "iss": self._api_key,
            "sub": f"{participant_role}:{participant_id}",
            "nbf": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "video": video_grant,
            "metadata": f'{{"encounter_id":"{encounter_id}","modality":"{modality}","recording":{str(recording_allowed).lower()}}}',
        }

        token = jwt.encode(claims, self._api_secret, algorithm="HS256")
        return RTCRoomSessionCredentials(
            encounter_id=encounter_id,
            room_name=room_name,
            server_url=self._url,
            participant_identity=f"{participant_role}:{participant_id}",
            participant_role=participant_role,
            modality=modality,
            recording_enabled=recording_allowed,
            access_token=token,
            expires_at_iso=expires_at.isoformat(),
        )

    def verify_webhook_and_evaluate_session(
        self,
        *,
        raw_body: bytes,
        signature_header: str,
        event_type: str,
        encounter_id: str,
        connection_duration_seconds: int,
    ) -> RTCWebhookDisposition:
        expected_sig = hmac.new(
            self._webhook_secret.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected_sig, signature_header):
            raise ValueError("Invalid LiveKit webhook signature")

        # AT-09: Even if a room finishes or drops after a brief connection (< 180s or any duration),
        # RTC events NEVER auto-complete a billable encounter.
        interrupted = connection_duration_seconds < 180 or event_type == "participant_aborted"
        return RTCWebhookDisposition(
            event_type=event_type,
            room_name=f"lw-care-enc-{encounter_id}",
            encounter_id=encounter_id,
            connection_duration_seconds=connection_duration_seconds,
            interrupted_early=interrupted,
            triggers_billable_completion=False,
            recommended_clinical_action=(
                "OFFER_AUDIO_FALLBACK_OR_RESCHEDULE_NO_AUTO_CHARGE"
                if interrupted
                else "AWAIT_CLINICIAN_SIGNED_RECORD"
            ),
        )
