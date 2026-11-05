# Implementation agent instructions

Work on **LW Health Intelligence Platform**. LW Care is a capability, My LW Health Care is the working patient name. Read README, LWH-DOC-000/001, LWH-DIR-001 and affected dependencies before implementation.

1. Preserve the Director-first scope and confirmed interactive decisions. Region → Zone is the reporting spine; affiliation decisions are central. Comprehensive clinical EMR and full local WAN-offline operation are core. Accounting/procurement/HR/payroll are optional.
2. Use stable document/requirement/form/field/screen/state/metric/API/event/test IDs. Resolve paths through manifest.json. Update the canonical owner before references; do not silently change meanings or renumber DHS/LWC IDs.
3. Enforce actor/subject/facility/purpose/field permissions at the authoritative service. Administrative seniority and frontend role flags do not grant clinical access.
4. Preserve local clinical write authority, expected versions, append-only signed/actual events and idempotent financial/stock effects. No last-write-wins for consequential clinical/financial records. External requests remain pending until actual acceptance/settlement.
5. Never invent doses, triage thresholds, vaccine schedules, local laws/tax rules, approvals, credentials, readiness, patient facts, prices, source citations or test results. Build disabled configuration and synthetic checks when an adoption dependency is unresolved.
6. Keep anonymised intelligence separate from protected coded/identified care data. Minimise data, preserve provenance/corrections, caregiver scope and disclosure controls. No uncontrolled patient-data training.
7. Audit current code/data before reuse/migration. Preserve real/signed/consent/ledger history; never assume all data is fake. Production cannot fall back to demo success.
8. Implement loading/empty/partial/stale/offline/error/denied/conflict/recovery states, accessibility and accepted handover. Core work must remain usable with cloud AI and optional ERP disabled.
9. Record meaningful tests actually executed against exact versions. The supplied cases are specifications marked NOT_RUN. Documentation/schema checks are not clinical, operational or production validation.
10. A handoff includes changed IDs/components, migration/rollback, evidence, known limits and operating dependencies. This suite authorises development planning; actual clinical activation, deployment and contractual decisions use the relevant session authority and release process.
