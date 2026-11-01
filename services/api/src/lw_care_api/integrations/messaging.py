"""
Secondary PHI-Free Messaging Adapters (§2.4 & §14.5):
- KingsChat Adapter (LoveWorld super-app messaging)
- Termii SMS Adapter (Nigerian DND-compliant transactional SMS)
- Resend / SMTP Email Adapter

Security & Clinical Privacy Invariant (§2.4 & §14.5):
1. Ordinary notifications MUST NOT contain medical detail, symptoms, diagnoses, or prescriptions.
2. Only pre-approved template IDs (`APPROVED_NOTIFICATION_TEMPLATES`) can be dispatched.
3. SMS/KingsChat delivery is NEVER treated as proof of clinician acknowledgement.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

NotificationChannel = Literal["KINGSCHAT", "TERMII_SMS", "RESEND_EMAIL"]

APPROVED_NOTIFICATION_TEMPLATES: dict[str, str] = {
    "OTP_VERIFICATION_V1": (
        "LoveWorld Care verification code: {otp_code}. Valid for 10 minutes. "
        "Do not share this code with anyone."
    ),
    "APPOINTMENT_BOOKED_V1": (
        "LoveWorld Care: Your appointment ({appointment_ref}) is scheduled for {slot_time}. "
        "Open the secure Care portal for details."
    ),
    "CARE_SUMMARY_READY_V1": (
        "LoveWorld Care: A signed update for your care request ({episode_ref}) is ready. "
        "Sign in to your secure Care portal to view it."
    ),
    "FOLLOW_UP_REMINDER_V1": (
        "LoveWorld Care: You have a scheduled CareContinuity follow-up check-in ({task_ref}). "
        "Sign in to your secure Care portal."
    ),
    "PAYMENT_RECEIPT_V1": (
        "LoveWorld Care: Payment reference {payment_ref} ({formatted_amount}) has been confirmed."
    ),
}

FORBIDDEN_TEMPLATE_VARIABLES: set[str] = {
    "symptom",
    "symptoms",
    "diagnosis",
    "clinical_note",
    "prescription",
    "medication",
    "chief_complaint",
    "hiv",
    "condition",
    "findings",
}


@dataclass(frozen=True)
class DispatchedNotificationReceipt:
    dispatch_id: str
    channel: NotificationChannel
    recipient: str
    template_id: str
    rendered_preview_phi_free: str
    proves_clinician_acknowledgement: Literal[False] = False
    dispatched_at_iso: str = ""


class PhiFreeNotificationDispatcher:
    """
    Routes PHI-free notifications across KingsChat, Termii SMS, and Resend Email.
    Rejects any payload containing clinical variables or unapproved template IDs.
    """

    def __init__(self) -> None:
        self._outbox_log: list[DispatchedNotificationReceipt] = []

    @property
    def dispatched_messages(self) -> list[DispatchedNotificationReceipt]:
        return list(self._outbox_log)

    def send_templated_notification(
        self,
        *,
        channel: NotificationChannel,
        recipient: str,
        template_id: str,
        template_vars: dict[str, str],
    ) -> DispatchedNotificationReceipt:
        if template_id not in APPROVED_NOTIFICATION_TEMPLATES:
            raise ValueError(f"Unapproved notification template_id: {template_id}")

        lower_keys = {k.lower() for k in template_vars.keys()}
        forbidden_overlap = lower_keys.intersection(FORBIDDEN_TEMPLATE_VARIABLES)
        if forbidden_overlap:
            raise ValueError(
                f"PHI Violation: Clinical variables {sorted(forbidden_overlap)} are forbidden in external notifications (§2.4)."
            )

        rendered = APPROVED_NOTIFICATION_TEMPLATES[template_id].format(**template_vars)
        receipt = DispatchedNotificationReceipt(
            dispatch_id=str(uuid4()),
            channel=channel,
            recipient=recipient,
            template_id=template_id,
            rendered_preview_phi_free=rendered,
            proves_clinician_acknowledgement=False,
            dispatched_at_iso=datetime.now(timezone.utc).isoformat(),
        )
        self._outbox_log.append(receipt)
        return receipt
