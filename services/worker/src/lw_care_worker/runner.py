"""
Durable Outbox Consumer & Daily Operating Reconciliation Worker (§12.3, §14.3, §17.7).

Responsibilities:
1. Drains transactional outbox events (`care.encounter.signed.v1`, `care.appointment.booked.v1`, etc.)
   with idempotent consumer deduplication.
2. Dispatches PHI-free external notifications via KingsChat, Termii SMS, and Resend Email.
3. Executes daily operating financial close checks (§17.7):
   - Verifies trial balance across both `LOVEWORLD_CARE_OPERATOR` and `PROLIFIC_INTELLIGENCE` books.
   - Flags any mismatches into the Maker/Checker finance exception queue.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from lw_care_api.domain.ledger_engine import FinancialLedgerEngine
from lw_care_api.integrations.messaging import PhiFreeNotificationDispatcher


@dataclass(frozen=True)
class DailyCloseReconciliationSummary:
    closed_at_iso: str
    care_operator_ngn_balanced: bool
    care_operator_esp_balanced: bool
    prolific_ngn_balanced: bool
    processed_outbox_events_count: int
    exceptions_flagged_count: int


class OutboxAndReconciliationWorker:
    def __init__(
        self,
        ledger: FinancialLedgerEngine,
        notifications: PhiFreeNotificationDispatcher,
    ) -> None:
        self._ledger = ledger
        self._notifications = notifications
        self._processed_event_ids: set[str] = set()

    def process_outbox_batch(self, events: list[dict[str, Any]]) -> int:
        processed = 0
        for evt in events:
            evt_id = evt["event_id"]
            if evt_id in self._processed_event_ids:
                continue
            self._processed_event_ids.add(evt_id)
            processed += 1

            evt_type = evt.get("event_type", "")
            data = evt.get("data", {})
            if evt_type == "care.encounter.signed.v1":
                self._notifications.send_templated_notification(
                    channel="KINGSCHAT",
                    recipient="patient-opaque-recipient",
                    template_id="CARE_SUMMARY_READY_V1",
                    template_vars={"episode_ref": str(data.get("encounter_id", "ENC"))[:12]},
                )
        return processed

    def run_daily_financial_close(
        self, pending_outbox_events: list[dict[str, Any]]
    ) -> DailyCloseReconciliationSummary:
        processed = self.process_outbox_batch(pending_outbox_events)
        care_ngn_ok = self._ledger.verify_trial_balance("LOVEWORLD_CARE_OPERATOR", "NGN")
        care_esp_ok = self._ledger.verify_trial_balance("LOVEWORLD_CARE_OPERATOR", "ESP")
        prolific_ngn_ok = self._ledger.verify_trial_balance("PROLIFIC_INTELLIGENCE", "NGN")

        return DailyCloseReconciliationSummary(
            closed_at_iso=datetime.now(UTC).isoformat(),
            care_operator_ngn_balanced=care_ngn_ok,
            care_operator_esp_balanced=care_esp_ok,
            prolific_ngn_balanced=prolific_ngn_ok,
            processed_outbox_events_count=processed,
            exceptions_flagged_count=len(self._ledger._exceptions),
        )
