# Phase 5 cloud clinical implementation release

Date: 8 November 2026, Africa/Lagos. Implementation and final release qualification are in progress. This record tracks the cloud clinical release against the suite; it does not assert full clinical/operating acceptance or offline delivery.

## Implemented capabilities

The care workspace adds Team & capacity, Nursing, Maternal & child, Medicine stewardship, Procedural monitoring and Continuity plan, with 30 typed workflow forms and repeatable actual measurements/items/infants. Its commands use real encrypted clinical persistence, signed event lineage, current authority, expected versions and idempotency. Existing encounter, diagnostics, dispensing/MAR, ward, procedure, referral and billing workflows remain integrated.

- Actual service-capacity windows, personally accepted professional shifts and bounded workload checks; accepted clinical/nursing handover of current work with preserved result responsibility.
- Separate admission orders, expiring bed holds and actual occupancy; personally accepted initial/receiving nursing responsibility; leave/return, self-discharge/death, declined transfer and separate physical bed release. Existing care and unresolved tasks survive disposition.
- Structured nursing assessments and fluid observations; maternal/labour documentation; separate infant identities and birth links; child measurements; actual administration plus specifically selected batch traceability for immunisation.
- Medicine reconciliation and unresolved review ownership; independently approved exact signed product replacement; stock reservations and separately witnessed physical adjustments/returns with actual movement reconciliation.
- Actual anaesthesia observations, device/component source traceability, owned recall review, manually recorded infusion events with separate personal witness attestation, and individual instructions with actual communication state.
- Reservation-aware bed/stock boards, due-time task ordering, scoped/bounded source lists and full-source navigation, an independent paginated-chart allergy safety context, and asynchronous response isolation by facility/subject.
- Additive schema 7, rebuilding the current work/resource index from existing encrypted source records. The index is not clinical authority; incomplete/stale projections block new resource/work decisions. Original actual records remain immutable and recoverable.

Source and authority/rollback choices: [ADR-0013](../adr/0013-cloud-clinical-teamwork-specialties-and-resources.md), `clinical/advanced_contracts.py`, `advanced.py`, `specialties.py`, `flow_index.py`, shared store/router/control integration and `care/phase5-forms.ts`.

## Engineering execution evidence

The existing clinical regression suite passed 22 tests. Iterative specialty and recovery checks exposed and corrected date parsing and test fixture/contract mismatches; those failed attempts are not claimed as acceptance. Final focused results, exact CI/runtime commit, live source hashes/deployment IDs and actual production archive results are recorded after execution.

An actual disposable Neon run already verified one effect for concurrent fact retries, one non-over-reserving stock hold, one personally accepted handover with identical receipts, denial of an unaccepted successor's task access, rejection of an actual-fact overwrite, indexed current source records and ownership after restart. A separate real Neon/private-object recovery run verified 91 tables, two evidence file families, 30 encrypted fields and six clinical signatures with wrong-key/ciphertext-tamper rejection, recovered-key operation and open care/stock/ledger reconciliation. No production domain rows or messages were seeded. Final-source repeat checks precede release.

The authored suite remains unchanged. Formal requirement/UAT baselines remain NOT_RUN; engineering tests do not certify clinical truth, operating authority, continuous coverage or all facility/user task variants. No Playwright was installed or used.

## Adoption and remaining project sequence

The production software does not fabricate facilities, protocols, staffing, prices, medicines, vaccine schedules or clinical readiness. Real country/operator/facility activation, current professional privileges and actual clinical policy/source/licence adoption are still required. Administrative access is not clinical authority. The patient/family account and consented delivery preference journeys remain Phase 6 work; external partner and existing-EMR/device interfaces remain Phase 7 qualification.

This release supplies structured manual documentation and accountable transactions. Licensed calculations/checking engines, jurisdiction-specific schedules/thresholds, fully adopted specialist templates, external image/device/blood-bank conformance, complete exception variants, representative capacity/recovery and observed accessibility/clinical-safety UAT remain outstanding. The scanner remains unconfigured and scan-dependent attachments fail closed. Daily/manual jobs are not continuous urgent escalation. Offline care remains core, while facility-local and additional worker/scanner deployments remain deferred beyond the current cloud stack.

After this release, the next recommended capability sequence is Phase 6: My LW Health Care and family authority, while remaining Phase 4A/4B/5 adoption and operating qualification continue. The [overall progress matrix](2026-11-05-platform-progress.md) retains every core PRD and shared specification without a percentage-complete claim.
