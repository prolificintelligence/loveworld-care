---
document_id: "LWH-SPEC-020"
title: "Laboratory, imaging, device and document interfaces"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Departmental integration lead"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-PRD-019", "LWH-SPEC-012", "LWH-SPEC-017", "LWH-ENG-007"]
source_refs: ["LWH-SRC-017", "LWH-SRC-018", "LWH-SRC-020", "LWH-SRC-042", "LWH-SRC-043"]
directive_refs: []
---

# Laboratory, imaging, device and document interfaces

## Adapter contract

Each adapter registers partner/device, operator, service scope, protocol/version, actual endpoint, authentication, identifier/code/unit mapping, authority, supported statuses, error/retry behaviour, time/clock handling, licence, support and qualification evidence. Local departmental interfaces must be reachable and usable during WAN outage if required for the facility's enabled clinical workflow. A vendor name or available port is not evidence of interoperability.

## Laboratory path

Transmit the signed accepted order with patient/order/accession and minimum clinical context. Preserve specimen collection/receipt/rejection and actual performing department. Receive structured result or source document with status, units, method/reference context, verifier and amendment relationship. Interface messages are idempotent, preserve original payload/version and reconcile every order/result. Unmatched patient/accession, invalid units/codes and unsupported statuses quarantine the item with an owner. Where a partner uses HL7 v2, CSV, document or proprietary API, pin the exact profile and map to the same canonical contract; no blind generic parser.

## Imaging path

Use qualified DICOM/DICOMweb capabilities where supported; PS3.18 is the web-services reference. Keep acquisition/worklist, study/series identifiers, patient/accession, report and image archive distinct. Authorised local PACS/viewing/reporting must remain available during qualified WAN loss. Validate patient metadata and study links before chart attachment. Image access is private, purpose checked and audited; metadata and burned-in identifiers require disclosure review for non-care use. A report can be reviewed while a large-image transfer remains separately pending.

## Device/measurement path

Record device identity, measured parameter, value/unit, source patient association, actual time/clock uncertainty, method and quality/status. Validate association and unit/code mapping before clinical use. Data from an unqualified device, consumer upload or uncertain OCR is attributed and reviewed, not automatically verified. Medical-device software/intended use and local service requirements are assessed during country/facility activation. No new diagnosis or treatment follows solely because a device message arrived.

## Document upload and extraction

Use private staged upload, content/MIME checks, malware scanning, checksum, source/author/date, patient association and permitted access. OCR/AI extraction produces draft facts with confidence and source spans; a qualified user confirms clinically meaningful values, units and matching. Preserve the original document and correction history. Do not invent a missing decimal, unit or examination. Digital signatures are verified where supported and their actual meaning shown.

## Qualification and support

Test correct/wrong patient, duplicate/replayed message, out-of-order amendment, missing order, unavailable department, invalid code/unit, large/resumable object, clock skew, local runtime restart and WAN loss. Record sender/receiver receipts and semantic outcomes. Departments own result quality and actual work; integration stewards own mapping/delivery; treating teams own clinical response. Failed adapters create an owned visible backlog and manual contingency rather than successful empty results.
