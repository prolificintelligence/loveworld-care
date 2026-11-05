---
document_id: "LWH-SPEC-016"
title: "Security architecture and threat model"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Security architect and privacy owner"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-SPEC-003", "LWH-SPEC-013", "LWH-SPEC-017", "LWH-GOV-003", "LWH-OPS-005"]
source_refs: ["LWH-SRC-023", "LWH-SRC-024", "LWH-SRC-027", "LWH-SRC-033"]
directive_refs: []
---

# Security architecture and threat model

## Security baseline

Use OWASP ASVS 5.0.0 as a versioned verification reference, with an application risk profile covering clinical, financial and institutional functions. Produce an implementation control matrix selecting applicable requirements and evidence; listing ASVS does not certify the application. Privileged workflows require strong authentication and server-side policy, object/field scope, secure sessions, CSRF/session protections appropriate to architecture, input/output safety, rate limits, encryption, protected uploads, secret management and audit.

## Threat and control register

| Threat | Required design and verification |
|---|---|
| Cross-patient/facility access | Server-side scope/subject/field/purpose policy on UI/API/files/events/exports; negative object-ID tests |
| Privilege escalation/self-approval | Strong identity, scoped grants, incompatibility checks, maker-checker and audited delegation |
| Stolen sessions/phishing | Short-lived scoped sessions, privileged MFA, secure recovery, rotation and revocation |
| Compromised local node | Encrypted storage, managed keys, hardening, least-privilege services, patching and authenticated node/epoch |
| WAN/LAN adversary | TLS, authenticated services, replay protection and protected local DNS/cert lifecycle; no “trusted LAN” exemption |
| Upload/image malicious content | Private storage, MIME/content limits, malware checks, safe viewers and signed scoped access |
| Prompt injection/exfiltration | Untrusted retrieval boundary, bounded context/tools, no unrestricted production SQL or export |
| Sync tampering/replay | Envelope identity/hash/signature where adopted, inbox dedup, authority/version/dependency checks and quarantine |
| Ransomware/site loss | Independent encrypted backups, restore drills, credential isolation and clinical continuity |
| Insider browsing/export | Purpose-based access, minimum fields, audit/review, short-lived break-fix and disclosure controls |
| Payment/ledger fraud | Verified provider callbacks, unique event keys, balanced append-only journals and independent approvals |
| Clinical stale/conflicting work | Authority node, expected versions, current-order checks and no last-write-wins for signed/actual events |
| Logs/notifications leak | No patient narrative/secrets by default; neutral external messages; protected audit separate from telemetry |
| Supply chain/secrets | Dependency inventory, licence review, signed release packages, secret scanning and managed rotation |


## Identity and key architecture

Public patient passwordless access can use verified email/other approved channels. Facility clinical authentication must remain local during WAN loss using preprovisioned identity/credential verifiers, valid bounded grants and strong local factors. Do not require online email, cloud introspection or cloud SSO for every local action. Local delegated identity issuance is narrow, audited and cannot bypass known professional suspension/expiry. No shared clinical login or stored plaintext credential.

Use OAuth/OIDC patterns with audience/scope restriction, modern authorisation flows, protected redirect handling, token replay/rotation controls and sender constraints where appropriate. Store refresh/privileged secrets in protected services rather than broad browser-readable storage. Local TLS identity and certificate renewal are planned before disconnection; users are not trained to bypass certificate warnings.

Encryption keys are scoped to environment/custodian/node with protected backup, rotation, recovery, revocation and access logs. Private object/image access checks current authority. Signing keys can attest author/node/record version but do not prove clinical correctness. Audit chains/retention controls provide tamper evidence; avoid an unsupported claim of perfect immutability.

## Segmentation and operations

Separate development/test/live tenants, secrets and data. Production cannot fall back to synthetic fixtures. Isolate clinical, reporting, finance, identity, optional HR/payroll and anonymous analytics access. Network-level controls complement application policy. Technical support uses time-bounded justified access and approved break-fix procedures with minimum clinical exposure. Device/session locking protects shared workstations.

## Assurance and incident handling

Review threats for each new country, device, partner and assistant. Test authentication/recovery, authorisation, uploads, injection, data export, API abuse, signing, sync replay, backup recovery and offline grants. Findings have severity, owner, remediation and retest evidence. Critical patient-safety/privacy/financial flaws block release. Incident runbooks preserve clinical continuity and reconcile affected care/records after technical restoration; a healthy server alone does not close the incident.
