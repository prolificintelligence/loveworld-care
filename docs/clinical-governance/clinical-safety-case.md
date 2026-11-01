# LoveWorld Care — Clinical Safety Case & Governance Register (§16.6 & §20.4)

> **Top-Level Safety Claim (§16.6):**
> *"Within its explicitly approved use scope, LoveWorld Care safely coordinates remote care without independently making clinical decisions."*

## Subclaims & Technical Evidence

| Subclaim | Enforcing Component | Automated Verification |
|---|---|---|
| **SC-01: Deterministic Protocol Governance** | `services/protocol-runtime` (`engine.py`) | Three-valued logic (`TRUE \| FALSE \| UNKNOWN`), SHA-256 bundle hash verification, dual clinical sign-off (`clinical_owner != reviewer`), hard-stop priority execution (`AT-05`) |
| **SC-02: Verified Provider Identity & Staffing** | `services/api/security/auth.py` & `clinical_service.py` | Active MDCN licence & expiry runtime guard (`AT-07`), stale/unstaffed slot blocker (`AT-10`), atomic case claiming (`AT-02`) |
| **SC-03: Zero-Barrier Emergency Pathway** | `GET /v1/emergency/guidance` & `EmergencySafetyBanner` | Operates with zero login, zero payment, and zero AI dependency (`AT-11`, `AT-16`) |
| **SC-04: Signed Encounter Integrity** | `services/api/crypto/signing.py` & `ClinicalDocumentModel` | Ed25519 digital signature + canonical SHA-256 hash + step-up TOTP MFA + append-only linked addenda (`AT-08`) |
| **SC-05: Confidential Clinical Records & Sponsor Boundary** | `packages/authorization` & `ledger_engine.py` | Sponsors/Support/Ops/Finance strictly blocked from `T3_SENSITIVE_CLINICAL` (`AT-06`), $k \ge 5$ small-cohort suppression (`AT-14`), shared-device lock (`AT-13`) |
| **SC-06: Bounded AI with Instant Kill Switch** | `services/model-gateway` (`router.py`) | `UNSIGNED / FOR CLINICIAN REVIEW ONLY` watermark, prompt-injection isolation (`AT-12`), false-reassurance blocker (`AT-05`), live AI-Off Kill Switch (`AT-16`) |
