r"""
Multi-Currency Double-Entry Financial Ledger, SponsorCare Entitlement State Machine,
Maker/Checker Exception Control, and Unit Economics Engine (§10, §11, §14.4, §17).

Key Invariants:
1. All amounts are integral minor units (`NGN` kobo, `ESP` minor units, `USD` cents).
2. Separate Economic Books (`LOVEWORLD_CARE_OPERATOR` vs `PROLIFIC_INTELLIGENCE`) (§17.1).
3. Uncollected sponsor pledges (`committed_unfunded_minor`) are NEVER spendable;
   `available_to_reserve = funded_cash_minor - active_reserved_minor - redeemed_minor` (§10.4).
4. Concurrency lock & idempotency guarantee zero overspend (`AT-03`) and zero duplicate charges (`AT-01`, `AT-04`).
5. Service revenue & clinician payables are recognized ONLY upon a clinician-signed encounter
   (`signed_encounter_id` + `signed_document_hash`), never merely on `appointment.booked` or `payment.authorised` (§6.3, §14.4).
6. Sponsor reporting enforces small-cohort privacy suppression ($k \ge 5$) and zero clinical narrative exposure (§10.5, `AT-14`).
7. Maker/Checker dual control (`maker_id != checker_id`) for all financial exception resolutions (§17.7).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from math import ceil
from typing import Any, Literal
from uuid import uuid4

CurrencyCode = Literal["NGN", "ESP", "USD"]
EconomicBook = Literal["LOVEWORLD_CARE_OPERATOR", "PROLIFIC_INTELLIGENCE"]
EntitlementState = Literal[
    "AVAILABLE",
    "RESERVED",
    "REDEEMED",
    "RELEASED",
    "EXPIRED",
    "SUSPENDED",
    "REVERSED",
]


def assert_minor_int(amount: int, label: str = "amount_minor") -> None:
    if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
        raise ValueError(f"{label} must be a non-negative integer minor unit; got {amount!r}")


@dataclass(frozen=True)
class JournalLine:
    line_id: str
    batch_id: str
    economic_book: EconomicBook
    account_code: str
    direction: Literal["DEBIT", "CREDIT"]
    amount_minor: int
    currency: CurrencyCode
    source_event_type: str
    source_reference_id: str
    actor_id: str
    occurred_at_iso: str


@dataclass
class SponsorPoolAccount:
    agreement_id: str
    sponsor_id: str
    sponsor_name: str
    funding_type: str
    currency: CurrencyCode
    committed_unfunded_minor: int = 0
    funded_cash_minor: int = 0
    active_reserved_minor: int = 0
    redeemed_minor: int = 0
    eligible_beneficiary_ids: set[str] = field(default_factory=set)
    completed_encounter_ids: set[str] = field(default_factory=set)
    beneficiaries_served_ids: set[str] = field(default_factory=set)
    version: int = 1

    @property
    def available_to_reserve_minor(self) -> int:
        return self.funded_cash_minor - self.active_reserved_minor - self.redeemed_minor


@dataclass
class EntitlementReservation:
    reservation_id: str
    agreement_id: str
    episode_id: str
    patient_id: str
    amount_minor: int
    currency: CurrencyCode
    state: EntitlementState
    idempotency_key: str
    created_at_iso: str
    redeemed_encounter_id: str | None = None
    redeemed_signed_doc_hash: str | None = None
    reversal_reason: str | None = None


@dataclass
class ProviderPayableRecord:
    payable_id: str
    encounter_id: str
    clinician_id: str
    signed_document_hash: str
    gross_encounter_revenue_minor: int
    clinician_payable_minor: int
    currency: CurrencyCode
    status: Literal["ACCRUED_PENDING_APPROVAL", "APPROVED_FOR_PAYOUT", "PAID", "HELD_EXCEPTION"]
    created_at_iso: str
    approved_by_checker_id: str | None = None


@dataclass
class FinanceExceptionItem:
    exception_id: str
    category: Literal[
        "DUPLICATE_CHARGE",
        "SETTLED_BUT_CANCELLED",
        "BOOKING_NO_ENCOUNTER",
        "REFUND_AFTER_REDEMPTION",
        "PROVIDER_DISPUTE",
        "MANUAL_ADJUSTMENT",
    ]
    reference_id: str
    amount_minor: int
    currency: CurrencyCode
    maker_actor_id: str
    maker_reason: str
    status: Literal["PENDING_CHECKER", "PENDING_REVIEW", "APPROVED", "REJECTED", "REMEDIATED"] = (
        "PENDING_REVIEW"
    )
    checker_actor_id: str | None = None
    checker_notes: str | None = None
    created_at_iso: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    resolved_at_iso: str | None = None


@dataclass(frozen=True)
class SponsorSafeUtilisationReport:
    agreement_id: str
    sponsor_name: str
    currency: CurrencyCode
    committed_unfunded_minor: int
    funded_cash_received_minor: int
    active_reserved_minor: int
    redeemed_settled_minor: int
    available_to_reserve_minor: int
    eligible_population_count: int | Literal["SUPPRESSED_SMALL_COHORT_K_LT_5"]
    beneficiaries_served_count: int | Literal["SUPPRESSED_SMALL_COHORT_K_LT_5"]
    completed_encounters_count: int
    k_anonymity_suppressed: bool
    clinical_details_included: Literal[False] = False


@dataclass(frozen=True)
class EncounterContributionBreakdown:
    encounter_id: str
    payer_cohort: str
    currency: CurrencyCode
    recognised_revenue_minor: int
    clinician_direct_cost_minor: int
    payment_processing_fee_minor: int
    communications_rtc_ai_cost_minor: int
    variable_support_cost_minor: int
    refund_quality_reserve_minor: int
    contribution_margin_minor: int
    contribution_margin_pct: float


class FinancialLedgerEngine:
    """
    Production Double-Entry Accounting & SponsorCare Entitlement Engine.
    """

    def __init__(self, small_cohort_min_k: int = 5) -> None:
        self._min_k = small_cohort_min_k
        self._lock = asyncio.Lock()
        self._journal: list[JournalLine] = []
        self._pools: dict[str, SponsorPoolAccount] = {}
        self._reservations: dict[str, EntitlementReservation] = {}
        self._idempotency_index: dict[str, str] = {}
        self._settled_payment_refs: dict[str, int] = {}
        self._refunded_payment_refs: set[str] = set()
        self._payables_by_encounter: dict[str, ProviderPayableRecord] = {}
        self._exceptions: dict[str, FinanceExceptionItem] = {}

    @property
    def journal_lines(self) -> list[JournalLine]:
        return list(self._journal)

    def _post_balanced_journal(
        self,
        *,
        economic_book: EconomicBook,
        debit_account: str,
        credit_account: str,
        amount_minor: int,
        currency: CurrencyCode,
        source_event_type: str,
        source_reference_id: str,
        actor_id: str,
    ) -> str:
        assert_minor_int(amount_minor, "journal_amount_minor")
        if amount_minor <= 0:
            raise ValueError("Journal entry amount_minor must be strictly positive.")
        batch_id = str(uuid4())
        now_iso = datetime.now(UTC).isoformat()
        self._journal.append(
            JournalLine(
                line_id=str(uuid4()),
                batch_id=batch_id,
                economic_book=economic_book,
                account_code=debit_account,
                direction="DEBIT",
                amount_minor=amount_minor,
                currency=currency,
                source_event_type=source_event_type,
                source_reference_id=source_reference_id,
                actor_id=actor_id,
                occurred_at_iso=now_iso,
            )
        )
        self._journal.append(
            JournalLine(
                line_id=str(uuid4()),
                batch_id=batch_id,
                economic_book=economic_book,
                account_code=credit_account,
                direction="CREDIT",
                amount_minor=amount_minor,
                currency=currency,
                source_event_type=source_event_type,
                source_reference_id=source_reference_id,
                actor_id=actor_id,
                occurred_at_iso=now_iso,
            )
        )
        return batch_id

    def verify_trial_balance(self, economic_book: EconomicBook, currency: CurrencyCode) -> bool:
        debits = sum(
            j.amount_minor
            for j in self._journal
            if j.economic_book == economic_book
            and j.currency == currency
            and j.direction == "DEBIT"
        )
        credits = sum(
            j.amount_minor
            for j in self._journal
            if j.economic_book == economic_book
            and j.currency == currency
            and j.direction == "CREDIT"
        )
        return debits == credits

    def create_or_fund_sponsor_pool(
        self,
        *,
        agreement_id: str,
        sponsor_id: str,
        sponsor_name: str,
        funding_type: str,
        currency: CurrencyCode,
        committed_unfunded_minor: int,
        funded_cash_minor: int,
        eligible_beneficiary_ids: list[str],
        actor_id: str,
    ) -> SponsorPoolAccount:
        assert_minor_int(committed_unfunded_minor, "committed_unfunded_minor")
        assert_minor_int(funded_cash_minor, "funded_cash_minor")
        pool = SponsorPoolAccount(
            agreement_id=agreement_id,
            sponsor_id=sponsor_id,
            sponsor_name=sponsor_name,
            funding_type=funding_type,
            currency=currency,
            committed_unfunded_minor=committed_unfunded_minor,
            funded_cash_minor=funded_cash_minor,
            eligible_beneficiary_ids=set(eligible_beneficiary_ids),
        )
        self._pools[agreement_id] = pool
        if funded_cash_minor > 0:
            self._post_balanced_journal(
                economic_book="LOVEWORLD_CARE_OPERATOR",
                debit_account="ASSET:BANK_RESTRICTED_SPONSOR_CASH",
                credit_account="LIABILITY:UNEARNED_SPONSOR_POOL",
                amount_minor=funded_cash_minor,
                currency=currency,
                source_event_type="sponsor.pool.funded",
                source_reference_id=agreement_id,
                actor_id=actor_id,
            )
        return pool

    async def reserve_entitlement_atomic(
        self,
        *,
        agreement_id: str,
        episode_id: str,
        patient_id: str,
        amount_minor: int,
        idempotency_key: str,
        actor_id: str,
    ) -> EntitlementReservation:
        """
        §10.3, §10.4 & AT-03:
        Atomically reserves a defined service unit from a funded sponsor pool.
        Never allows concurrent requests to overspend `available_to_reserve_minor`.
        """
        assert_minor_int(amount_minor, "amount_minor")
        if amount_minor <= 0:
            raise ValueError("Reservation amount_minor must be > 0")

        async with self._lock:
            if idempotency_key in self._idempotency_index:
                existing_id = self._idempotency_index[idempotency_key]
                return self._reservations[existing_id]

            pool = self._pools.get(agreement_id)
            if not pool:
                raise KeyError(f"Unknown sponsor agreement_id: {agreement_id}")

            if pool.available_to_reserve_minor < amount_minor:
                raise ValueError(
                    f"INSUFFICIENT_SPONSOR_FUNDS: available={pool.available_to_reserve_minor}, requested={amount_minor}"
                )

            pool.active_reserved_minor += amount_minor
            pool.version += 1

            res_id = str(uuid4())
            res = EntitlementReservation(
                reservation_id=res_id,
                agreement_id=agreement_id,
                episode_id=episode_id,
                patient_id=patient_id,
                amount_minor=amount_minor,
                currency=pool.currency,
                state="RESERVED",
                idempotency_key=idempotency_key,
                created_at_iso=datetime.now(UTC).isoformat(),
            )
            self._reservations[res_id] = res
            self._idempotency_index[idempotency_key] = res_id

            self._post_balanced_journal(
                economic_book="LOVEWORLD_CARE_OPERATOR",
                debit_account="LIABILITY:UNEARNED_SPONSOR_POOL",
                credit_account="LIABILITY:RESERVED_SPONSOR_ENTITLEMENT",
                amount_minor=amount_minor,
                currency=pool.currency,
                source_event_type="finance.entitlement.reserved",
                source_reference_id=res_id,
                actor_id=actor_id,
            )
            return res

    async def redeem_entitlement_on_signed_encounter(
        self,
        *,
        reservation_id: str,
        signed_encounter_id: str,
        signed_document_hash: str,
        clinician_id: str,
        clinician_payable_minor: int,
        actor_id: str,
    ) -> tuple[EntitlementReservation, ProviderPayableRecord]:
        """
        §6.3, §10.3 & §14.4:
        Redemption and clinician payable accrual occur ONLY when backed by a signed encounter
        (`signed_encounter_id` and `signed_document_hash`).
        """
        if not signed_encounter_id or not signed_document_hash:
            raise ValueError(
                "Entitlement redemption requires both signed_encounter_id and signed_document_hash."
            )

        async with self._lock:
            res = self._reservations.get(reservation_id)
            if not res:
                raise KeyError(f"Unknown reservation_id: {reservation_id}")

            # Idempotent return if already redeemed for the exact same signed encounter
            if res.state == "REDEEMED" and res.redeemed_encounter_id == signed_encounter_id:
                return res, self._payables_by_encounter[signed_encounter_id]

            if res.state != "RESERVED":
                raise ValueError(f"Cannot redeem entitlement in state {res.state}")

            if signed_encounter_id in self._payables_by_encounter:
                raise ValueError(f"Encounter {signed_encounter_id} has already been settled.")

            pool = self._pools[res.agreement_id]
            pool.active_reserved_minor -= res.amount_minor
            pool.redeemed_minor += res.amount_minor
            pool.completed_encounter_ids.add(signed_encounter_id)
            pool.beneficiaries_served_ids.add(res.patient_id)
            pool.version += 1

            res.state = "REDEEMED"
            res.redeemed_encounter_id = signed_encounter_id
            res.redeemed_signed_doc_hash = signed_document_hash

            # 1. Recognize Earned Service Revenue from Reserved Liability
            self._post_balanced_journal(
                economic_book="LOVEWORLD_CARE_OPERATOR",
                debit_account="LIABILITY:RESERVED_SPONSOR_ENTITLEMENT",
                credit_account="REVENUE:RECOGNISED_CLINICAL_ENCOUNTER",
                amount_minor=res.amount_minor,
                currency=res.currency,
                source_event_type="finance.entitlement.redeemed",
                source_reference_id=signed_encounter_id,
                actor_id=actor_id,
            )

            # 2. Accrue Clinician Payable Liability
            self._post_balanced_journal(
                economic_book="LOVEWORLD_CARE_OPERATOR",
                debit_account="EXPENSE:CLINICIAN_PROFESSIONAL_FEE",
                credit_account="LIABILITY:CLINICIAN_PAYABLE",
                amount_minor=clinician_payable_minor,
                currency=res.currency,
                source_event_type="finance.payable.accrued",
                source_reference_id=signed_encounter_id,
                actor_id=actor_id,
            )

            payable = ProviderPayableRecord(
                payable_id=str(uuid4()),
                encounter_id=signed_encounter_id,
                clinician_id=clinician_id,
                signed_document_hash=signed_document_hash,
                gross_encounter_revenue_minor=res.amount_minor,
                clinician_payable_minor=clinician_payable_minor,
                currency=res.currency,
                status="ACCRUED_PENDING_APPROVAL",
                created_at_iso=datetime.now(UTC).isoformat(),
            )
            self._payables_by_encounter[signed_encounter_id] = payable
            return res, payable

    async def release_reservation(
        self, *, reservation_id: str, reason: str, actor_id: str
    ) -> EntitlementReservation:
        """Releases a reserved entitlement back to the available sponsor pool on cancellation/expiry."""
        async with self._lock:
            res = self._reservations[reservation_id]
            if res.state == "RELEASED":
                return res
            if res.state != "RESERVED":
                raise ValueError(f"Cannot release entitlement in state {res.state}")

            pool = self._pools[res.agreement_id]
            pool.active_reserved_minor -= res.amount_minor
            pool.version += 1
            res.state = "RELEASED"
            res.reversal_reason = reason

            self._post_balanced_journal(
                economic_book="LOVEWORLD_CARE_OPERATOR",
                debit_account="LIABILITY:RESERVED_SPONSOR_ENTITLEMENT",
                credit_account="LIABILITY:UNEARNED_SPONSOR_POOL",
                amount_minor=res.amount_minor,
                currency=res.currency,
                source_event_type="finance.entitlement.released",
                source_reference_id=reservation_id,
                actor_id=actor_id,
            )
            return res

    async def process_payment_webhook_idempotent(
        self,
        *,
        provider: str,
        reference: str,
        amount_minor: int,
        currency: CurrencyCode,
        event_status: Literal["SETTLED", "FAILED", "REFUNDED"],
        actor_id: str = "webhook-worker",
    ) -> str:
        """
        AT-01 & AT-04: Handles duplicate or out-of-order payment gateway webhooks idempotently.
        Never double-credits settled funds or double-posts refunds.
        """
        async with self._lock:
            if event_status == "SETTLED":
                if reference in self._settled_payment_refs:
                    return "IDEMPOTENT_ALREADY_SETTLED"
                self._settled_payment_refs[reference] = amount_minor
                self._post_balanced_journal(
                    economic_book="LOVEWORLD_CARE_OPERATOR",
                    debit_account=f"ASSET:GATEWAY_CLEARING_{provider}",
                    credit_account="LIABILITY:PATIENT_UNEARNED_DEPOSIT",
                    amount_minor=amount_minor,
                    currency=currency,
                    source_event_type="finance.payment.settled",
                    source_reference_id=reference,
                    actor_id=actor_id,
                )
                return "SETTLED_RECORDED"

            if event_status == "REFUNDED":
                if reference in self._refunded_payment_refs:
                    return "IDEMPOTENT_ALREADY_REFUNDED"
                # If refund webhook arrives before settle webhook (out-of-order AT-04),
                # record both the settlement clearing and compensating refund entry so final net balance is 0.
                if reference not in self._settled_payment_refs:
                    self._settled_payment_refs[reference] = amount_minor
                    self._post_balanced_journal(
                        economic_book="LOVEWORLD_CARE_OPERATOR",
                        debit_account=f"ASSET:GATEWAY_CLEARING_{provider}",
                        credit_account="LIABILITY:PATIENT_UNEARNED_DEPOSIT",
                        amount_minor=amount_minor,
                        currency=currency,
                        source_event_type="finance.payment.settled_out_of_order",
                        source_reference_id=reference,
                        actor_id=actor_id,
                    )
                self._refunded_payment_refs.add(reference)
                self._post_balanced_journal(
                    economic_book="LOVEWORLD_CARE_OPERATOR",
                    debit_account="LIABILITY:PATIENT_UNEARNED_DEPOSIT",
                    credit_account=f"ASSET:GATEWAY_CLEARING_{provider}",
                    amount_minor=amount_minor,
                    currency=currency,
                    source_event_type="finance.payment.refunded",
                    source_reference_id=reference,
                    actor_id=actor_id,
                )
                return "REFUNDED_RECORDED"

            return "FAILED_IGNORED"

    def record_prolific_platform_service_invoice(
        self,
        *,
        invoice_id: str,
        amount_minor: int,
        currency: CurrencyCode,
        actor_id: str,
    ) -> None:
        """
        §17.1 Separate Economic Books:
        An invoice paid by LoveWorld Care to Prolific Intelligence is recorded as an
        EXPENSE in `LOVEWORLD_CARE_OPERATOR` and REVENUE in `PROLIFIC_INTELLIGENCE`.
        Never consolidated as additional healthcare clinical profit.
        """
        self._post_balanced_journal(
            economic_book="LOVEWORLD_CARE_OPERATOR",
            debit_account="EXPENSE:MANAGED_PLATFORM_AND_AI_SLA",
            credit_account="ASSET:OPERATING_CASH",
            amount_minor=amount_minor,
            currency=currency,
            source_event_type="finance.prolific_sla.paid",
            source_reference_id=invoice_id,
            actor_id=actor_id,
        )
        self._post_balanced_journal(
            economic_book="PROLIFIC_INTELLIGENCE",
            debit_account="ASSET:PROLIFIC_OPERATING_CASH",
            credit_account="REVENUE:MANAGED_PLATFORM_SLA",
            amount_minor=amount_minor,
            currency=currency,
            source_event_type="finance.prolific_sla.received",
            source_reference_id=invoice_id,
            actor_id=actor_id,
        )

    def create_finance_exception(
        self,
        *,
        category: Literal[
            "DUPLICATE_CHARGE",
            "SETTLED_BUT_CANCELLED",
            "BOOKING_NO_ENCOUNTER",
            "REFUND_AFTER_REDEMPTION",
            "PROVIDER_DISPUTE",
            "MANUAL_ADJUSTMENT",
        ],
        reference_id: str,
        amount_minor: int,
        currency: CurrencyCode,
        maker_actor_id: str,
        maker_reason: str,
    ) -> FinanceExceptionItem:
        exc = FinanceExceptionItem(
            exception_id=str(uuid4()),
            category=category,
            reference_id=reference_id,
            amount_minor=amount_minor,
            currency=currency,
            maker_actor_id=maker_actor_id,
            maker_reason=maker_reason,
        )
        self._exceptions[exc.exception_id] = exc
        return exc

    def resolve_finance_exception_maker_checker(
        self,
        *,
        exception_id: str,
        checker_actor_id: str,
        decision: Literal["APPROVED", "REJECTED"],
        checker_notes: str,
    ) -> FinanceExceptionItem:
        """§17.7: Enforces Maker != Checker separation of duties on financial adjustments."""
        exc = self._exceptions[exception_id]
        if exc.maker_actor_id == checker_actor_id:
            raise PermissionError(
                "MAKER_CHECKER_VIOLATION: MAKER_CANNOT_ACT_AS_CHECKER: The maker of a financial exception cannot be its checker."
            )
        exc.status = decision
        exc.checker_actor_id = checker_actor_id
        exc.checker_notes = checker_notes
        exc.resolved_at_iso = datetime.now(UTC).isoformat()
        return exc

    def build_sponsor_utilisation_report(self, agreement_id: str) -> SponsorSafeUtilisationReport:
        """
        §10.5 & AT-14:
        Produces an aggregate-only SponsorCare report.
        Suppresses cohort counts when eligible or served population is > 0 and < k (default k=5)
        so sponsors can never infer an individual beneficiary's medical status.
        """
        pool = self._pools[agreement_id]
        elig_count = len(pool.eligible_beneficiary_ids)
        served_count = len(pool.beneficiaries_served_ids)

        suppressed = (0 < elig_count < self._min_k) or (0 < served_count < self._min_k)
        return SponsorSafeUtilisationReport(
            agreement_id=pool.agreement_id,
            sponsor_name=pool.sponsor_name,
            currency=pool.currency,
            committed_unfunded_minor=pool.committed_unfunded_minor,
            funded_cash_received_minor=pool.funded_cash_minor,
            active_reserved_minor=pool.active_reserved_minor,
            redeemed_settled_minor=pool.redeemed_minor,
            available_to_reserve_minor=pool.available_to_reserve_minor,
            eligible_population_count=(
                "SUPPRESSED_SMALL_COHORT_K_LT_5" if suppressed else elig_count
            ),
            beneficiaries_served_count=(
                "SUPPRESSED_SMALL_COHORT_K_LT_5" if suppressed else served_count
            ),
            completed_encounters_count=len(pool.completed_encounter_ids),
            k_anonymity_suppressed=suppressed,
            clinical_details_included=False,
        )

    @staticmethod
    def compute_encounter_unit_economics(
        *,
        encounter_id: str,
        payer_cohort: str,
        currency: CurrencyCode = "NGN",
        recognised_revenue_minor: int = 600_000,  # 6,000 NGN
        clinician_direct_cost_minor: int = 330_000,  # 3,300 NGN
        payment_processing_fee_minor: int = 15_000,  # 150 NGN
        communications_rtc_ai_cost_minor: int = 20_000,  # 200 NGN
        variable_support_cost_minor: int = 40_000,  # 400 NGN
        refund_quality_reserve_minor: int = 20_000,  # 200 NGN
    ) -> EncounterContributionBreakdown:
        """
        §17.2 Formula:
        Encounter contribution = recognised settled encounter revenue - clinician direct cost
          - communications/model cost - payment fees - variable support - expected fulfilment losses/refunds
        Default baseline yields 175,000 kobo (1,750 NGN) = 29.17% contribution margin.
        """
        total_var = (
            clinician_direct_cost_minor
            + payment_processing_fee_minor
            + communications_rtc_ai_cost_minor
            + variable_support_cost_minor
            + refund_quality_reserve_minor
        )
        margin = recognised_revenue_minor - total_var
        pct = (
            round((margin / recognised_revenue_minor) * 100.0, 2)
            if recognised_revenue_minor > 0
            else 0.0
        )
        return EncounterContributionBreakdown(
            encounter_id=encounter_id,
            payer_cohort=payer_cohort,
            currency=currency,
            recognised_revenue_minor=recognised_revenue_minor,
            clinician_direct_cost_minor=clinician_direct_cost_minor,
            payment_processing_fee_minor=payment_processing_fee_minor,
            communications_rtc_ai_cost_minor=communications_rtc_ai_cost_minor,
            variable_support_cost_minor=variable_support_cost_minor,
            refund_quality_reserve_minor=refund_quality_reserve_minor,
            contribution_margin_minor=margin,
            contribution_margin_pct=pct,
        )

    @staticmethod
    def compute_monthly_break_even_encounters(
        *,
        monthly_fixed_operating_cost_minor: int,
        contracted_covered_lives: int,
        institutional_contribution_per_life_minor: int = 25_000,  # 250 NGN
        weighted_encounter_contribution_minor: int = 175_000,  # 1,750 NGN
    ) -> int:
        """
        §17.5 Formula:
        N_break_even = CEIL(MAX(0, monthly_fixed_operating_cost - IC) / CM)
        """
        ic = contracted_covered_lives * institutional_contribution_per_life_minor
        remaining_fixed = max(0, monthly_fixed_operating_cost_minor - ic)
        if weighted_encounter_contribution_minor <= 0:
            raise ValueError("weighted_encounter_contribution_minor must be positive")
        return ceil(remaining_fixed / weighted_encounter_contribution_minor)

    def _serialize_exception(
        self,
        exc: FinanceExceptionItem,
        agreement_id: str | None = None,
        encounter_id: str | None = None,
        exception_type: str | None = None,
    ) -> dict[str, Any]:
        ref = exc.reference_id
        agr = agreement_id or (ref if ref.startswith("AGR-") else None)
        enc = encounter_id or (ref if ref.startswith("ENC-") else None)
        ext = exception_type or exc.category
        return {
            "exception_id": exc.exception_id,
            "agreement_id": agr,
            "encounter_id": enc,
            "exception_type": ext,
            "amount_minor": exc.amount_minor,
            "currency": exc.currency,
            "reason": exc.maker_reason,
            "maker_id": exc.maker_actor_id,
            "checker_id": exc.checker_actor_id,
            "status": exc.status,
            "action_notes": exc.checker_notes,
            "created_at_iso": getattr(exc, "created_at_iso", datetime.now(UTC).isoformat()),
            "resolved_at_iso": exc.resolved_at_iso,
        }

    def record_finance_exception(
        self,
        *,
        agreement_id: str | None = None,
        encounter_id: str | None = None,
        exception_type: str,
        amount_minor: int,
        currency: CurrencyCode = "NGN",
        reason: str,
        maker_id: str,
    ) -> dict[str, Any]:
        cat_map: dict[str, Any] = {
            "DUPLICATE_CHARGE_REFUND": "DUPLICATE_CHARGE",
            "DUPLICATE_CHARGE": "DUPLICATE_CHARGE",
            "SETTLED_BUT_CANCELLED": "SETTLED_BUT_CANCELLED",
            "BOOKING_NO_ENCOUNTER": "BOOKING_NO_ENCOUNTER",
            "REFUND_AFTER_REDEMPTION": "REFUND_AFTER_REDEMPTION",
            "PROVIDER_DISPUTE": "PROVIDER_DISPUTE",
            "MANUAL_ADJUSTMENT": "MANUAL_ADJUSTMENT",
        }
        category = cat_map.get(exception_type, "MANUAL_ADJUSTMENT")
        ref_id = agreement_id or encounter_id or f"ref-{uuid4().hex[:8]}"
        now_iso = datetime.now(UTC).isoformat()
        exc_id = f"exc-{uuid4().hex[:8]}"
        exc = FinanceExceptionItem(
            exception_id=exc_id,
            category=category,
            reference_id=ref_id,
            amount_minor=amount_minor,
            currency=currency,
            maker_actor_id=maker_id,
            maker_reason=reason,
            status="PENDING_REVIEW",
            created_at_iso=now_iso,
        )
        self._exceptions[exc.exception_id] = exc
        return self._serialize_exception(
            exc, agreement_id=agreement_id, encounter_id=encounter_id, exception_type=exception_type
        )

    def action_finance_exception(
        self,
        *,
        exception_id: str,
        checker_id: str,
        action: Literal["APPROVE", "REJECT", "REMEDIATE"],
        notes: str,
    ) -> dict[str, Any]:
        if exception_id not in self._exceptions:
            raise KeyError(f"Exception {exception_id} not found")
        exc = self._exceptions[exception_id]
        if exc.maker_actor_id == checker_id:
            raise PermissionError(
                "MAKER_CHECKER_VIOLATION: MAKER_CANNOT_ACT_AS_CHECKER: The creator of a financial exception cannot approve or reject it."
            )
        status_map: dict[str, Any] = {
            "APPROVE": "APPROVED",
            "REJECT": "REJECTED",
            "REMEDIATE": "REMEDIATED",
        }
        exc.status = status_map.get(action, "APPROVED")
        exc.checker_actor_id = checker_id
        exc.checker_notes = notes
        exc.resolved_at_iso = datetime.now(UTC).isoformat()
        return self._serialize_exception(exc)

    def list_finance_exceptions(
        self, status: str | None = None, agreement_id: str | None = None
    ) -> list[dict[str, Any]]:
        items = list(self._exceptions.values())
        if status:
            items = [e for e in items if e.status == status]
        serialized = [self._serialize_exception(e) for e in items]
        if agreement_id:
            serialized = [
                s
                for s in serialized
                if s.get("agreement_id") == agreement_id or s.get("reference_id") == agreement_id
            ]
        return serialized

    def compute_reconciliation_summary(self) -> dict[str, Any]:
        """§17.1 & LWC-SCR-305: Reconciled ledger state, restricted pools, and imbalance detection."""
        total_debits = sum(l.amount_minor for l in self._journal if l.direction == "DEBIT")
        total_credits = sum(l.amount_minor for l in self._journal if l.direction == "CREDIT")
        is_balanced = total_debits == total_credits

        total_funded_cash = sum(p.funded_cash_minor for p in self._pools.values())
        total_active_reserved = sum(p.active_reserved_minor for p in self._pools.values())
        total_redeemed_settled = sum(p.redeemed_minor for p in self._pools.values())
        total_available_to_reserve = sum(p.available_to_reserve_minor for p in self._pools.values())

        total_payables_pending = sum(
            p.clinician_payable_minor
            for p in self._payables_by_encounter.values()
            if p.status == "VALIDATED"
        )
        total_payables_paid = sum(
            p.clinician_payable_minor
            for p in self._payables_by_encounter.values()
            if p.status == "PAID"
        )

        pending_exceptions_count = sum(
            1
            for e in self._exceptions.values()
            if e.status in ("PENDING_CHECKER", "PENDING_REVIEW")
        )

        now_iso = datetime.now(UTC).isoformat()
        return {
            "summary_id": f"rec-{uuid4().hex[:8]}",
            "as_of_iso": now_iso,
            "reconciliation_timestamp_iso": now_iso,
            "double_entry_balanced": is_balanced,
            "is_double_entry_balanced": is_balanced,
            "total_sponsor_cash_received_minor": total_funded_cash,
            "total_reserved_minor": total_active_reserved,
            "total_redeemed_minor": total_redeemed_settled,
            "total_available_liability_minor": total_available_to_reserve,
            "total_clinician_payables_minor": total_payables_pending,
            "total_clinician_paid_minor": total_payables_paid,
            "unresolved_exceptions_count": pending_exceptions_count,
            "pending_maker_checker_exceptions_count": pending_exceptions_count,
            "total_debits_minor": total_debits,
            "total_credits_minor": total_credits,
            "discrepancy_minor": abs(total_debits - total_credits),
            "sponsor_pools": {
                "total_funded_cash_minor": total_funded_cash,
                "total_active_reserved_minor": total_active_reserved,
                "total_redeemed_settled_minor": total_redeemed_settled,
                "total_available_to_reserve_minor": total_available_to_reserve,
            },
            "clinician_payables": {
                "pending_minor": total_payables_pending,
                "paid_minor": total_payables_paid,
            },
            "journal_lines_count": len(self._journal),
        }
