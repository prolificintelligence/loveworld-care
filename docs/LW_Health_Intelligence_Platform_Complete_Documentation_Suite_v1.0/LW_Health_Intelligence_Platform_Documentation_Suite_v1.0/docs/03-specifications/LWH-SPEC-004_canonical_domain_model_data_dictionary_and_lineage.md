---
document_id: "LWH-SPEC-004"
title: "Canonical domain model, data dictionary and lineage"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Data and clinical information architects"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-ARC-001", "LWH-SPEC-006", "LWH-SPEC-017", "LWH-GOV-004"]
source_refs: ["LWH-SRC-009", "LWH-SRC-025", "LWH-SRC-026"]
directive_refs: []
---

# Canonical domain model, data dictionary and lineage

## Storage and identity conventions

Use globally collision-resistant random identifiers suitable for offline creation, with issuing-node/external-ID crosswalks. Identifiers do not authorise access. Source records carry `id: uuid`, `schema_version: string`, `authority_node_id: uuid`, `custodian_org_id: uuid`, `jurisdiction_profile_id: string`, `created_at/recorded_at: timestamp-with-offset`, `origin_actor_id: uuid`, `aggregate_version: integer >=1`, `source_system/ref: string`, `classification`, `retention_policy_ref` and immutable provenance. Patient-related records additionally require `patient_id` and applicable `encounter_id/episode_id/facility_id` links. Administrative records bind to their actual organisation/resource scope.

`observed_at` denotes when a clinical observation/event occurred; `recorded_at` when a node accepted it. Preserve original time zone, clock uncertainty and late-entry reason. Node sequence and aggregate version support replication/conflict checks; wall-clock order alone does not resolve clinical truth. Date-only facts never acquire a fabricated time. Exact quantities use decimal value plus unit; money uses signed integer minor units plus currency/scale. Missingness is typed, not encoded as zero, empty strings or invented negatives.

## Entity dictionary

| Entity | Required key/domain attributes (common fields also apply) | Custody / authority | Invariants and purpose |
|---|---|---|---|
| Organisation | org_id; type; name; operator_entity_id; country_profile_id; active_interval | Global/institutional | Typed ministry, owner, operator, partner or programme entity; no implicit patient access |
| OrgRelationship | parent_id; child_id; relationship_type; valid_from/to; decision_ref | Institutional | Acyclic Region → Zone spine; separate optional hierarchy and legal geography |
| Account | account_id; verified_contact_refs; identity_status; recovery_state | Identity cell | Actor identity; no embedded patient chart or universal ministry membership requirement |
| RoleAssignment | actor_id; role; resource_scope; actions; purpose; validity; grantor; policy_epoch | Identity/local | Grant provenance, delegation and expiry; incompatible duties evaluated |
| ProfessionalCredential | actor_id; issuer; registration_no; profession; jurisdiction; validity; verification | Jurisdiction/local | Professional authority evidence distinct from account role |
| Privilege | actor_id; facility_id; service; allowed_actions; validity; approver | Facility | Exact clinical service/action scope, known suspension and review |
| Facility | facility_id; operator_org_id; ownership; site_type; jurisdiction; registry_status | Network | Stable site identity, separate from owner and login |
| FacilityIdentifier | facility_id; system; issuer; value; verification; validity | Network | Unique issuer/system/value mapping with dispute and historical alias |
| FacilityAssignment | facility_id; zone_id; region_id_derived; primary_flag; validity | Institutional | One adopted primary reporting assignment for a period; service links independent |
| FacilityLocation | facility_id; civil_codes; address; coordinates; precision; source | Network | Civil geography independent of ministry hierarchy; protected location variants supported |
| Capability | facility_id; service_code; population; scope; evidence; activation_state | Network/facility | Declared, reviewed and activated capability; no inferred readiness |
| ReadinessAssertion | facility_service_id; observed_at; valid_until; status; capacity; constraints; reporter | Facility | Short-lived actual readiness with source; accepted referral remains separate |
| CriteriaSet | version; scope; jurisdiction; facility_type; requirements; adoption_ref | Standards | Immutable adopted criterion snapshot and evidence methods |
| Application | facility_id; type; criteria_version; submitted_version; state; accountable_contact | Standards | Original applicant evidence preserved; no approval from fee payment |
| Evidence | application_id; criterion_id; object_ref; sha256; issuer; observed/expiry; verification | Private standards | Malware-checked private object with source and reviewer findings |
| Inspection | application_id; inspector_id; visit_window; conflict_declaration; status | Standards | Assigned competent inspector; observations and recommendations separate |
| Finding | inspection_id; criterion_id; observed_fact; evidence_refs; severity_policy; response | Standards | Self-report, observation and reviewer conclusion distinguished |
| AffiliationDecision | application_id; decision; scope; conditions; effective/expiry; reason; central_decider | Central standards | Append-only Directorate decision with review/appeal references |
| CorrectiveAction | finding_id; owner; target; due; evidence; review; state | Standards/workflow | Submission is not verified correction |
| AppealReview | decision_id; requester; grounds; reviewer; notices; result | Standards | Independent review route and original decision preserved |
| Publication | facility_id; approved_fields_version; eligibility; published_at; status | Directory | Public projection excludes private evidence and raw clinical data |
| ReportingTemplate | template_id; version; field/indicator_refs; stream; adopted_interval | Reporting | Versioned schema and definitions; source-template reconciliation record |
| ReportingObligation | unit_id; stream; period; expected_indicators; deadline; hierarchy_version | Reporting | Expected units fixed by effective obligation rather than only received returns |
| ReturnVersion | obligation_id; version; values; missingness; source_refs; attester; received/review_state | Reporting | Immutable submission snapshot; previous/correction reasons retained |
| ValidationRun | source_version; rule_version; findings; blocking_count; reviewer_disposition | Quality | Reproducible checks and explained warning overrides |
| HealthEvent | event_id; type; occurrence; location_precision; source_reports; review_state; owner | Reporting/quality | Notification versus confirmed occurrence; no automatic incidence claim |
| EventLink | event_id; source_report_id; relationship; reviewer; deduplication_reason | Quality | Multiple reports can describe one reviewed event |
| IndicatorDefinition | code; version; population; numerator; denominator; period; exclusions; dimensions | Analytics | Approved formula, missingness and comparability contract |
| AggregateSnapshot | definition_version; scope; period; hierarchy_version; source_versions; values; coverage | Analytics | Immutable reproducible released/provisional snapshot with disclosure status |
| Intervention | evidence_refs; intended_result; scope; owner; resources; due/review; state | Programme | Accepted responsibility and separate completion/outcome review |
| Task | task_type; subject/resource_ref; responsible_team; assignee; due; state; accepted_at | Workflow/local | Durable obligation with explicit handover; delivery cannot close a clinical task |
| ContentVersion | type; text/object; author/reviewer; sources; jurisdiction; audience; validity; status | Editorial | Approved clinical/policy/faith purpose labels and withdrawal propagation |
| Patient | patient_id; local_identifiers; demographics; provisional_flag; custodian; matching_state | Facility/cell | Patient can exist without account; source-local identity remains preserved |
| PatientIdentifierLink | patient_id; external_system; external_id; match_evidence; reviewer; status | Protected exchange | Reviewed crosswalk; no destructive automatic global merge |
| RepresentativeGrant | actor_id; patient_id; authority_type; evidence; actions; fields; validity | Protected identity | Family/next-of-kin is not a blanket permission |
| Episode | patient_id; programme/service; owner_team; start/end; state; continuity_tasks | Facility/care cell | Longitudinal responsibility across multiple encounters |
| Encounter | patient_id; episode_id; facility_id; service; arrival/start/end; responsible_team; disposition | Facility authority | Clinical encounter state independent of billing and outstanding tasks |
| ClinicalDocument | patient_id; encounter_id; type; structured/narrative_content; author; attestation; version | Facility authority | Draft/sign/addendum/error lifecycle; signed content immutable |
| Problem | patient_id; code; clinical_status; verification; onset/resolution; source | Facility | Problem versus tentative assessment; no AI diagnosis promotion |
| AllergyIntolerance | patient_id; agent; reaction; certainty; criticality; status; absence_reason; source | Facility | Unknown, none-known, absent and confirmed allergy states remain distinct |
| Observation | patient_id; encounter_id; code; typed_value; unit; effective_at; method; source; status | Facility | Observed versus recorded time; precision/missingness/provenance retained |
| CarePlan | patient_id; episode_id; version; goals; instructions; owner; review; source_order_refs | Facility/care cell | Clinical instructions differ from patient-controlled reminders |
| Appointment | patient_id; service; resources; slot/hold; timezone; state; accepted_by | Authority of schedule | Hold, request and confirmed booking are distinct; no overbooking race |
| AdmissionStay | patient_id; encounter_id; ward; bed; team; admission/discharge; state | Facility | Actual stay and exclusive bed occupancy guarded locally |
| BedOccupancy | bed_id; stay_id; valid_from/to; reservation_or_occupancy; version | Facility | Prevent overlapping exclusive active occupancy at authority node |
| NursingRecord | patient_id; encounter_id; assessment/observation/task; performed_at; actor; attestation | Facility | Actual care and planned care are separate |
| ClinicalOrder | patient_id; encounter_id; kind; requested_service/product; requester; priority; signed_version; state | Facility | One authority; changes preserve intent and prior execution |
| Specimen | patient_id; order_id; accession; type; collected/received; collector; chain; rejection | Department/local | Identity/label chain and recollection explicit |
| DiagnosticReport | patient_id; orders; results; status; verifier; released_at; amendment_of; version | Department/local | Preliminary/final/corrected; no overwrite of prior signed report |
| ImagingStudy | patient_id; accession; study_uid; modalities; series_refs; source_archive; report_ref | Imaging/local | Pixel data and metadata protected; gateway access audited |
| MedicationOrder | clinical_order_id; product; dose; route; timing; duration; indication; quantity; substitution | Facility | Exact decimal/unit fields; applicable clinical checks and signatures |
| Dispense | order_id; patient_id; product; quantity; lot_refs; dispenser; time; substitution_ref | Facility | Actual supply distinct from administration; stock movement linked |
| Administration | order_version; patient_id; dose/product; actual_time; actor; state; omission_reason | Facility | Irreversible event record; idempotent request key; late-entry attribution |
| StockLot | facility_id; product; lot; expiry; location; quantity_basis; quarantine/recall | Facility | Clinical stock authority independent of optional procurement |
| StockMovement | lot_id; type; exact_quantity; unit; source_event; actor; reason; reversal_of | Facility | Append-only movement; duplicate delivery cannot duplicate effect |
| PregnancyEpisode | patient_id; pregnancy_id; dating/evidence; relevant_history; care_plan; outcomes | Facility | Maternal episode linked to chart, not a substitute patient identity |
| BirthRecord | maternal_patient_id; pregnancy_id; actual_time; infant_ids; outcome; attesting_team | Facility | Each infant independently identified; uncertain identity stays provisional |
| Immunisation | patient_id; product; batch; dose_record; administration; performer; schedule_version | Facility | Actual administered event; recommendations use adopted current schedule |
| ProcedureRecord | patient_id; encounter_id; planned/performed; procedure/site; team; findings; specimens; devices | Facility | Attested actual intervention, phase checks and recovery handover |
| TransfusionRecord | patient_id; order_id; specimen/crossmatch_ref; component_unit; checks; start/end; reaction | Facility | Blood-bank evidence and actual recipient/unit traceability |
| Referral | patient_id; sender; need; receiving_service; permitted_summary; acceptance; transport; outcome | Sender + accepted receiver | Transfer of responsibility requires explicit acceptance and receipt |
| SharingGrant | patient_id; recipient; purpose; scope; authority; valid_until; revocation; policy_version | Protected exchange | Anonymous analytics are a separate dataset, not a reversible grant mode |
| DisclosureReceipt | grant_id; subject_link; source_versions; recipient; delivery/access; audit_ref | Protected exchange | Record exactly what was disclosed and actually received |
| Programme | operator; sponsor; eligibility; services; restrictions; currency; approved_terms | Programme finance | Contract and operating obligations versioned |
| EntitlementAllocation | beneficiary; programme; node; limit; currency_or_units; expiry; signature_ref | Programme/local | Offline allowance allocated once to a spending authority |
| EntitlementReservation | allocation_id; service_request; amount/units; state; expires; fulfilment_ref | Spending authority | Atomic reserve/settle/release; no cross-node double allocation |
| ChargeInvoiceClaim | patient/payer; service_evidence; tariff_version; amount; currency; claim/invoice_state | Care finance | Care service, invoice, claim approval and payment states independent |
| LedgerEntry | group_id; account; debit/credit_minor; currency; scale; source_key; reversal_of | Finance authority | Balanced append-only group and independent sensitive adjustment approval |
| PaymentReceipt | provider_or_cash; external_id; amount_minor; currency; actual_received; allocation; state | Finance | Confirmed receipt distinct from intent; provider callbacks deduplicate |
| PolicyPackage | type; version; applicability; approval; hash; effective/expiry; dependencies | Control/local | Signed release package, pinned at runtime; no uncontrolled clinical rule learning |
| NodeSyncEnvelope | origin_node; epoch; sequence; event_id; entity/version; dependency_refs; hash; receipt_state | Node/integration | Durable outbox/inbox with per-object outcomes and retry control |
| AuditRecord | actor; action; resource; subject_scope; purpose; before/after_refs; policy; observed/recorded; outcome | Restricted audit | Append-only signed/chained evidence where configured; never claim perfect immutability |
| IntegrationMapping | partner; profile_version; source/target_codes; identifiers; transform; validation; approval | Integration | Reversible, tested mapping with version and retired codes preserved |
| EnterpriseTransaction | optional_module; org; country_rules; approval; source; posted/paid_state | Optional ERP | Accounting/procurement/HR/payroll separated from clinical records |


## Relationships and constraints

Each clinical child references an existing local patient and its facility/encounter scope; incoming messages with unresolved parents wait in quarantine/dependency queues. A source-local patient can link to several external identifiers only through reviewed mappings. Source custodians remain visible after exchange. Clinical notes, orders, results, medicines and finance retain separate version/state semantics. A general task may reference a clinical item without copying the full note into the workflow/analytics store.

Unique constraints include external identifier issuer/system/value within applicable scope; one idempotency operation key per actor/node/resource operation; one origin node/epoch/sequence; one externally confirmed provider transaction; one finance source posting key; and one active exclusive bed occupancy interval per bed. Facility assignment intervals cannot conflict with the adopted primary-reporting rule. Referential links survive closure, withdrawal and record correction. Soft-deletion flags never erase legally retained or signed histories.

## Transaction boundaries

Clinical command commits current version, immutable history, task effects, audit and outbox in one local database transaction. Medication administration and associated stock effect use one operation identity with defined partial/compensating handling; they are never inferred from a notification. Financial postings commit a balanced group or fail as a group. A service order cannot be marked performed solely by its bill. Separate remote systems reconcile through explicit receipts rather than uncoordinated dual writes.

```sql
-- Structural reference; production migrations add scoped RLS/policy, FKs and indexes.
CREATE TABLE origin_inbox (
 origin_node_id uuid NOT NULL, epoch bigint NOT NULL,
 sequence_no bigint NOT NULL, event_id uuid NOT NULL,
 payload_hash text NOT NULL, outcome text NOT NULL,
 PRIMARY KEY (origin_node_id, epoch, sequence_no), UNIQUE(event_id)
);
CREATE TABLE entity_revision (
 entity_id uuid NOT NULL, revision bigint NOT NULL CHECK(revision>0),
 authority_node_id uuid NOT NULL, record_kind text NOT NULL,
 payload jsonb NOT NULL, previous_hash text, payload_hash text NOT NULL,
 recorded_at timestamptz NOT NULL, actor_id uuid NOT NULL,
 PRIMARY KEY(entity_id, revision)
);
CREATE TABLE domain_outbox (
 event_id uuid PRIMARY KEY, aggregate_id uuid NOT NULL,
 aggregate_version bigint NOT NULL, payload jsonb NOT NULL,
 recorded_at timestamptz NOT NULL, acknowledged_at timestamptz,
 UNIQUE(aggregate_id, aggregate_version, event_id)
);
```

These fragments demonstrate deduplication/history/outbox shape; they are not a complete production migration. The dictionary above is the canonical logical model; implementation schemas must produce a field-by-field mapping and verify all integrity, authority and retention constraints before activation.

## Lineage and analytic projections

Record raw source version, transformation/mapping/rule version, reviewer, correction and generated metric snapshot. A report revision invalidates affected aggregates, source-dependent summaries and downstream work where relevant. Anonymous projections remove identifying/linkable keys and assess combinations, small groups and repeated queries. Protected clinical exchange keeps its own controlled linkage and cannot be relabelled anonymous. Read models and caches are disposable projections, not independent sources of truth.

## Retention and portability

Retention is assigned by record class, country, age/context and legal hold under an adopted policy, never a universal invented duration. Preserve exportability of source documents, structured records, provenance, code-system versions, grants and audit. Closing an account, withdrawing affiliation or ending a supplier contract triggers custody/export responsibilities; it does not erase clinical obligations or history. Backups and replicas carry the same protected classification and controlled deletion/hold rules.
