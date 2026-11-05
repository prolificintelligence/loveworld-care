# LW Health Intelligence Platform — overall implementation progress

Assessment date: 5 November 2026. Baseline: `LW_Health_Intelligence_Platform_Complete_Documentation_Suite_v1.0/LW_Health_Intelligence_Platform_Documentation_Suite_v1.0`, including its manifest, 25 PRDs, 21 shared specifications, 200 granular requirements and 111 specified acceptance cases.

This report separates implemented software, deployment verification and operating acceptance. It is not a percentage estimate or a claim that every requirement in a partially delivered PRD has been completed. The archived controlled suite remains unchanged. Its acceptance cases remain specification records; executed engineering tests and their results are recorded separately in the release evidence.

## Current delivered platform

The institutional release supplies real identity/MFA, scoped permissions, registration, inspection/affiliation decisions and public directory publication. The clinical release extends that live runtime with a persistent, encrypted EMR and staff workspace. The API has actual PostgreSQL transactions and provider integrations; there is no production fixture repository, simulated payment settlement or successful provider fallback.

The EMR includes patient registration and matching, provisional/local identifiers, demographic corrections, independently reviewed identity links, appointment requests and accepted commitments, arrivals and clinical ownership, triage, structured observations/problems/allergy assessments, clinical/nursing/specialty documents and intentional signing, addenda, treatment consent and separately scoped sharing grants, diagnostic orders/specimens/results and correction follow-up, formulary/prescribing/pharmacy/dispensing/MAR, clinical stock, physical beds/admissions/transfers/discharge, continuing-care programmes, procedure safety phases, transfusion witnessing/monitoring, referrals with actual receiving acceptance, and approved care tariffs/invoices/cash receipts with balanced ledger entries.

Each workflow remains bounded by actual facility activation, current professional authority and applicable policy. A clinical governor can issue another activated staff member's privileges; a Directorate administrator cannot browse clinical charts by seniority. No real facility readiness, professional registration, prescribing content, vaccine schedule or tariff has been invented to populate the application.

Live destinations and exact deployment/test evidence are maintained in [the EMR release record](2026-11-05-emr-release.md). The prior institutional release is recorded in [the original cloud release evidence](2026-11-05-cloud-release.md). The clinical implementation decisions and custody boundaries are in [ADR-0008](../adr/0008-cloud-emr-authority-and-record-custody.md).

## Progress against all 25 PRDs

“Partial” means a real deployed increment exists, with further specified work or qualification remaining. “Not delivered” refers to this production runtime; an older demo application is not counted as production delivery.

| Suite reference | Status | Implemented scope | Remaining material work |
|---|---|---|---|
| LWH-PRD-001 Organisation/identity/delegation | Partial | Persistent MFA accounts/sessions, scoped expiring grants, independent clinical privileges and revocation | Account recovery, full delegation depth, hierarchy transfer/handover, patient/caregiver contexts |
| LWH-PRD-002 Facility registry/directory | Partial | Actual registry, verification, scoped visibility and separate privacy-limited publication | Complete update/closure/duplicate stewardship, readiness assertions and adopted global unit roster |
| LWH-PRD-003 Affiliation/inspection/renewal | Partial | Adopted criteria records, evidence workflow, assigned inspection, independent recommendation and central decision | Actual scanner connectivity; complete correction, renewal, restriction, appeal and noncompliance casework |
| LWH-PRD-004 Periodic reporting | Not delivered | Clinical source records retain lineage for subsequent reporting | Return capture, period obligations, attestation, central receipts, revisions and roll-ups |
| LWH-PRD-005 Safety/events/review | Not delivered as a full module | Clinical reaction documentation and accountable follow-up tasks | Governed institutional event capture, classification, investigation and closure |
| LWH-PRD-006 Validation/stewardship | Not delivered as a full module | Clinical typing, source identity, version checks and preserved corrections | Independent return verification, quality queues, measurement reconciliation and stewardship operating controls |
| LWH-PRD-007 Leadership intelligence | Not delivered | None of the older demo dashboards are counted | Disclosure-controlled aggregate pipelines, snapshots, suppression and executive views |
| LWH-PRD-008 Interventions/actions | Not delivered as a full module | Clinical care tasks exist separately | Directorate interventions, resources, institutional acceptance/outcome review and exception boards |
| LWH-PRD-009 Community/referrals/readiness | Partial | Clinical referral requests, actual receiver acceptance and accountable handover | Community clinic planning, live readiness/capacity and broader network coordination |
| LWH-PRD-010 Education/policies/rights | Not delivered | No unapproved clinical/policy material is published | Editorial review, adopted content, applicability, publication/withdrawal and multilingual access |
| LWH-PRD-011 LW Care/service integration | Partial | Integrated authenticated cloud clinical workspace and clinical workflow API | Qualified remote care/video/service adapters and externally accepted fulfilment |
| LWH-PRD-012 Identity/continuity/exchange | Partial | Local identifiers, reviewed reversible crosswalks, separate recipient/purpose/record sharing grants, provenance and revocation | Cross-facility identity governance, qualified FHIR/existing-EMR exchange, patient sharing UI and recipient delivery receipts |
| LWH-PRD-013 Sponsor programmes/funding | Not delivered | Legacy sponsor demonstrations excluded | Contracted entitlements, reserved allocations, verified funding and privacy-controlled programme statements |
| LWH-PRD-014 Governed intelligence | Infrastructure only | Real free OpenRouter readiness and Upstash control from the institutional release | Clinically governed assistant tools, references, draft provenance, evaluation and approved clinical-data routing |
| LWH-PRD-015 Patient administration/chart | Partial | Registration, provisional identities, corrections, longitudinal sourced records, sensitive access, intentional signing and reversible identity review | Complete custody/exit and patient/representative workflows, document attachments and facility operational qualification |
| LWH-PRD-016 Ambulatory/emergency care | Partial | Arrivals, unclaimed/accepted clinical ownership, manual-policy triage, encounter documentation, tasks and signed disposition | Qualified triage content, capacity/roster controls, emergency partner interfaces and offline operation |
| LWH-PRD-017 Inpatient/nursing/ADT | Partial | Exclusive beds, admissions, nursing observations/MAR, offered/accepted internal transfer and discharge with pending obligations retained | Full leave/death/statutory variants, nursing handover qualification, facility department integration and offline care |
| LWH-PRD-018 Maternal/newborn/continuing care | Partial | Separate patient identities/relationship evidence, programme records/reviews/tasks and specialty document types | Complete structured labour/birth/immunisation workflows; adopted vaccine/growth packages and specialty qualification |
| LWH-PRD-019 Diagnostics/results | Partial | Signed/accepted orders, actual specimen chain, typed reports, release/correction, critical flags from cited policy and separate review/contact | Qualified analyser/LIS/PACS/DICOM interfaces, external ingestion/quarantine, image/document custody and clinical escalation qualification |
| LWH-PRD-020 Medicines/stock | Partial | Exact adopted products, intentional prescribing, manual safety evidence, pharmacy verification, actual supply/MAR, lot expiry/recall/quarantine and atomic stock effects | Licensed checking/calculation packages, substitutions, returns/adjustments/witnessed stock controls and complete exception reconciliation |
| LWH-PRD-021 Procedures/transfusion | Partial | Planned versus performed phases, consent links, privileged teams, actual procedure evidence, independent component witness and accepted recovery handover | Complete specialty anaesthesia charts/device feeds, blood-bank integration/recall workflow and clinical equipment qualification |
| LWH-PRD-022 Care finance | Partial | Adopted tariffs, fulfilment-linked charges, invoices, actual cash receipts, unique effects and balanced immutable ledger | Payer splits/claims/remittance, electronic settlement, controlled refund/reversal/maker-checker and accounting export qualification |
| LWH-PRD-023 Patient/family experience | Not delivered | Staff EMR registration is not represented as patient self-service | Patient accounts, dependants/caregiver authority, permitted own-record views, requests, sharing controls and correction history |
| LWH-PRD-024 Clinician workspace | Partial | Real scoped worklists, encounter ownership, documents/signing, source history, diagnostics/follow-up, accepted care tasks and appointment acceptance | Approved reference service, assistant drafting, coverage/capacity/leave rosters and full specialty/mobile qualification |
| LWH-PRD-025 Optional ERP | Deferred / optional | Core care has no dependency on these modules | Separately contracted accounting/procurement/HR/payroll; not part of this EMR deployment |

## Cross-cutting specifications and operating dependencies

- **SPEC-003/016:** authority is enforced by the backend using stored account, facility staff membership, independent professional privilege, patient/encounter, service and confidentiality. Secure sessions, MFA, encrypted clinical content, minimal department views and protected access history are implemented. Recovery, operational security review and penetration testing remain.
- **SPEC-004/006/009/010/018/019:** typed commands, explicit missingness, version checks, immutable attestations/corrections, separate actual clinical events and transactionally owned obligations are implemented. Native EMR routes are an explicit implementation extension under `/v1/clinical/{facility_id}`; they do not silently redefine the archived capture schemas. Country-specific forms, licensed terminology and complete specialty content remain adoption work.
- **SPEC-011/015:** clinical transactions retain durable event/audit/outbox/receipt data. Real database concurrency and replay checks are release evidence. Full clinical scheduling/escalation services, capacity tests, observability/on-call, backup/restore drills and operational service levels remain unqualified. Vercel Hobby's daily cron is not presented as a clinical escalation scheduler.
- **SPEC-012/020 and ENG-007:** native permission-scoped source downloads preserve versions; they do not claim a certified FHIR, LIS/PACS/device or legacy-EMR migration interface. Those integrations require actual counterpart systems and conformance/cutover work.
- **SPEC-017 and OPS-006:** the project lead explicitly deferred offline installation. This release requires WAN access to the cloud authority. There is no browser outbox pretending to commit clinical care offline. Facility runtime provisioning, bounded offline identity/reference packages, node trust, fenced failover, synchronisation conflict handling and outage/restore qualification remain outstanding.
- **SPEC-021 and GOV-002/003/004/008:** live use depends on actual country/custodian authority, facility operating scope, a nominated clinical governor and professional verification. Clinical adoption, retention rules, specialty packages and legal/privacy approvals are not inferred from a successful deployment.

## Assurance and next programme work

The 21 shared specifications have the following implementation coverage. This is software coverage, not acceptance certification.

| Specification | Current coverage | Outstanding qualification or scope |
|---|---|---|
| SPEC-001 Screens/design | Functional labelled staff forms, patient banner, error/conflict/empty/denied states | Full screen inventory, accessibility/device/UAT qualification |
| SPEC-002 Journeys | Institutional and clinical engineering journeys executed | Complete 20-journey service blueprint acceptance |
| SPEC-003 Authorisation | Persistent roles, clinical privileges, services, treatment/subject and sensitive scope | Complete caregiver/delegation/emergency-access policies and review |
| SPEC-004 Domain/lineage | Versioned encrypted records, immutable clinical events and policy/professional evidence | Remaining analytics/programme/exchange entities and adopted mappings |
| SPEC-005 Master/readiness | Facility hierarchy, registry and identity/statutory checks | Adopted global roster, readiness assertions, location/service stewardship |
| SPEC-006 Forms/fields | Typed native institutional/clinical input contracts | Complete parity/adoption of all 51 suite forms and country variants |
| SPEC-007 Indicators | Not delivered | Adopted indicator definitions, computation and evidence |
| SPEC-008 Reporting/quality | Not delivered as a reporting module | Return validation, revision reconciliation and quality stewardship |
| SPEC-009 State rules | Version/state guards across delivered institutional and EMR flows | Complete remaining state families, exception paths and operating adoption |
| SPEC-010 API contracts | Typed scoped native API; version/idempotency/error checks | Remaining commands/queries and interface conformance |
| SPEC-011 Events/jobs | Durable transactional history/outbox and real invitation delivery | Clinical scheduler/escalation, full consumers, dead-letter/recovery qualification |
| SPEC-012 Exchange | Scoped, revocable native source packages with original versions | Qualified FHIR/counterpart exchange and actual recipient receipts |
| SPEC-013 Intelligence | Fixed public free-model readiness and control | Governed clinical tools, references, memory, evaluation and data routing |
| SPEC-014 Analytics | Not delivered | Disclosure controls, aggregate snapshots and executive projections |
| SPEC-015 Reliability | Health/readiness, restart persistence and actual database concurrency proofs | Load/capacity, service levels, recovery and backup/restore drills |
| SPEC-016 Security | MFA, secure sessions, encrypted clinical data, protected audit and signed history | Independent security review, penetration test, recovery and operational controls |
| SPEC-017 Offline | Explicitly deferred by the project lead | Full facility runtime, trusted packages, sync, fencing and outage qualification |
| SPEC-018 Clinical teamwork | Protected signatures/addenda, order/execution separation and owned obligations | Complete specialist/shift coverage and facility operating acceptance |
| SPEC-019 Terminology/medicines | Original code/system/version, units/missingness and exact adopted products | Licensed mappings/checking engines, calculations and specialty schedules |
| SPEC-020 Department/device interfaces | Source/study/accession references and manual native department workflows | Actual LIS/PACS/DICOM/analyser/device integration and conformance |
| SPEC-021 Jurisdiction activation | Explicit recorded facility authority and bounded service/professional scope | Adopted country dossiers, legal/retention/tax rules and operating approvals |

The release record lists exact executed tests, actual PostgreSQL proofs, schema version, cloud deployment identifiers and external HTTP checks. The suite's 111 acceptance specifications are not silently changed to PASS by a build or a unit test. Actual facility/user UAT and clinical safety/operational acceptance remain separate work.

The next programme priorities are: qualify and complete the outstanding EMR operating/specialty controls; nominate and activate real clinical governance; deliver patient/family self-service; implement reporting/data stewardship and disclosure-controlled Directorate intelligence; complete care-finance and actual external-system integrations; then carry out the deferred facility-local offline deployment and recovery exercises. Optional ERP remains separately scoped.
