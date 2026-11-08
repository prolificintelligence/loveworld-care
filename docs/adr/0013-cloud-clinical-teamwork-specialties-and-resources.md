# ADR-0013: Clinical teamwork, structured specialties and actual resources

Date: 8 November 2026. Status: implemented; deployment and exact execution evidence are recorded in the Phase 5 release.

## Scope and authority

This cloud-compatible Phase 5 release extends LWH-PRD-015 through 021 and 024, SPEC-003/018/019/021 and the four confirmed facility types. It preserves the canonical suite and its IDs. Native form/command extensions under `/v1/clinical/{facility_id}/workflows` use event extension IDs `LWH-EXT-CLINICAL-030` through `039`; they do not redefine the archived API or form contracts.

Clinical activation, professional/service privileges, patient/encounter, current treating assignment, purpose, authority node/epoch, expected versions and intentional actions remain authoritative backend checks. A Directorate administrator or clinical governor does not gain chart access by seniority. No jurisdiction, triage threshold, medicine dose, growth interpretation, vaccine schedule, compatibility rule, clinical score or policy adoption is invented. AI and optional ERP are not dependencies for these workflows.

## Record and resource model

Keep clinical records, encrypted signed event chains, original author/time, addenda and error markers. Extend PostgreSQL clinical-record protection to the new recorded actual nursing, maternal/child, reconciliation, anaesthesia, device, instructions and infusion/witness facts. Corrections append an attributable record; actual records are not rewritten. Signed diagnostic/prescribing requests retain their existing state-specific execution transitions and immutable event history.

Migration 7 adds one rebuildable `clinical_flow_index` table and its scope/owner/recipient/resource/trace indexes. It holds protected identifiers, source version, service, state, actual dates and exact stock quantity, with a keyed trace token for device/component lookup. It stores no clinical narrative. Every clinical event updates the projection in the same transaction, including changes through offboarding controls. The operator migration rebuilds existing records using their encrypted source, with source locks and version-aware upserts. Readiness, new work/resource decisions and worklists fail closed on an incomplete/stale index. Original chart/record history remains accessible under its normal authority during reconciliation.

Worklists apply current role/service, owner/recipient and treating predicates before pagination. Tasks sort by actual due time without inventing an urgency ranking. Lists are bounded to 25 source rows, with metadata/detail navigation for large bodies; physical resource boards have stable pagination. A separate attributed allergy query remains visible across chart pages; no missing page becomes a negative allergy finding.

## Accepted staffing and handover

Clinical governors configure actual service capacity windows with resource evidence and policy references, and nominate qualified duty shifts. The named professional accepts or declines their shift. Where the adopted window requires a roster, new assignment needs current personally accepted coverage and declared capacity. No configured window is explicitly `NOT_CONFIGURED`, not verified readiness. Existing manual clinical operation remains available within its activation and privilege boundaries. This is clinical staffing, not HR/payroll.

Shift end does not close work or erase ownership. A clinical/nursing handover freezes the offered open-task versions, names a qualified recipient and leaves the sender responsible. Decline/cancel retains that responsibility. Acceptance revalidates current eligibility/capacity and exact current open work, then atomically updates the corresponding encounter/ward/task responsibilities and diagnostic result-owner references. Historical prescribing, observations, performed events and authorship remain intact. Changed work or an overdue offer requires a renewed review rather than silent acceptance.

Nursing tasks carry explicit nursing responsibility. Current-authority checks, overdue notices and supervised departure handovers respect that capability. Actual notification, acknowledgement, acceptance and clinical completion remain distinct; daily/manual cloud jobs are not continuous urgent escalation.

## Inpatient and physical resource decisions

Separate the admission order, expiring bed hold and actual admission. Active holds block competing bed use, including legacy admission/transfer routes. Actual occupancy remains versioned and exclusive. A service can adopt a requirement for separate admission orders. Legacy direct actual admissions remain interpretable where that requirement has not been adopted; no older event is relabelled as a previously accepted order.

New admissions/internal transfers nominate the receiving bedside nurse without automatically granting treating access. The named currently qualified nurse personally records ward receipt before that assignment grants access. The limited pending handover is discoverable by its named recipient; restricted notes remain protected after acceptance. Legacy assignments retain their original history rather than acquire a fabricated earlier receipt.

Leave retains occupancy and creates an owned return-review obligation. Return records the actual event. Leave, self-discharge/refusal, death and declined transfer preserve care obligations and their signed evidence. Special clinical disposition, physical bed release, encounter completion, statutory certification and finance settlement remain separate steps. Death documentation is not a government certificate or automated cause of death.

Bed boards distinguish occupied, held and unoccupied resources. Stock boards separately show physical, reserved and unreserved quantities and current supply restrictions. Capacity is not inferred from an empty bed or a quantity alone. Reservations expire by their recorded times; expiry changes availability without rewriting the original offer/event.

## Structured specialty care and medication chain

- Nursing assessments and fluid intake/output retain actual observation time, method, original units, source and correction lineage; no balance, conversion or normal finding is guessed.
- Maternal/labour records preserve dating uncertainty and actual sourced measurements. Birth binds a signed maternal source and separately identified infant charts; the author must independently have appropriate treating authority for each infant. Mother/infant relationship evidence creates no caregiver/access grant. Each outcome and review remains attributable and owned.
- Child measurements retain units/age uncertainty and manual interpretation. Immunisation binds an actual given MAR event to its specifically selected matching supply/batch, and records the actual adopted schedule reference and responsible review. No schedule or growth algorithm is enabled.
- Medicine reconciliation attests sourced continue/stop/change/unknown decisions without silently changing prescriptions. Unresolved decisions create owned review tasks. A substitution needs permission on the original prescription, a distinct qualified named prescriber and their exact intentionally signed replacement; only that explicit approval stops the original order. Past dispense/MAR events remain unchanged.
- Stock holds protect actual unreserved quantities. Supply consumes the matching reservation atomically. Physical adjustments/returns require a different qualified pharmacist's review of the current lot; movements use unique effect sources. Returns cannot exceed actual supply and enter quarantine; an adjustment cannot silently release recalled/quarantined stock. These are clinical stock effects, not settlement or procurement.
- Anaesthesia/monitoring references actual procedural state, team, consent and manually recorded evidence. Devices/components retain actual identifiers and scoped recipient traceability. A recall creates a responsible review task, not an inferred adverse outcome. Infusion observations retain manual review and original quantities/units; a named witness personally attests or disputes in a separate immutable record. No rate, dose, score or compatibility calculation is generated.
- Patient instructions distinguish prepared versus actually communicated material, preserve language/source/plan and retain responsible follow-up. Patient/family self-service is a later phase; no message-delivery inference closes care.

## Deployment, continuity and rollback

Deploy the compatible API while production is schema 6; new command routes return 503 before migration. Keep existing keys/provider settings. Apply additive migration 7, complete the source-index rebuild and check readiness; then deploy the care UI. No synthetic domain data, professional appointments or clinical packages are seeded.

Logical archive/restore accepts the exact schema-5, schema-6 or schema-7 inventory (72/90/91 tables). Recovery of schema 7 additionally compares the work/resource projection with recovered signed source data and trace tokens. Existing retained archives and the independent operator recovery key remain unchanged. Rehearsals use fresh isolated schemas/private paths and never overwrite production.

`LWH_ADVANCED_CLINICAL_ENABLED=false` pauses new advanced command routes while retaining source access and previously committed capacity/reservation enforcement. Rollback uses a reviewed compatible API/fix and an attributable reversal where needed; do not drop the table, erase events, replace keys or overwrite live clinical state to simulate rollback. A failed/expired operating authority still constrains the affected service.

## Remaining acceptance and operating inputs

Actual country/service activation, named clinical operators, staffed capacity, licensed terminology/calculation/schedule packages, specialist template review, safety/privacy assessment, representative load, device/interface conformance and observed accessibility/task UAT remain operating qualification. Automated clinical algorithms are unavailable; this release supplies manual sourced workflow controls. Scanner and additional continuously running hosts remain deferred beyond the current cloud stack. Offline care remains core; facility-local deployment and WAN-loss/reconnect qualification are still outstanding, and this deployed cloud authority requires connectivity.
