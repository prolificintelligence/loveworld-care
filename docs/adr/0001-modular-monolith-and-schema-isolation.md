# ADR-0001: Modular Monolith with Schema-Isolated PostgreSQL, Three-Valued Protocol Engine & Multi-Currency Ledger

- **Status:** Accepted
- **Date:** 2026-10-31
- **Context:** LoveWorld Care Master Specification v1.0.0 (§7, §10, §12, §15, §16, §17, §25)

## Decisions

1. **Frontend Topology (`apps/*`):**
   - 4 isolated Next.js PWAs (`patient-web`, `clinician-web`, `command-web`, `sponsor-web`) in a Turborepo + `pnpm` monorepo sharing `packages/design-system`, `packages/api-contracts`, `packages/domain-types`, `packages/authorization`, `packages/audit`, and `packages/fhir-adapters`.
2. **Backend Topology (`services/*`):**
   - Python `uv` workspace with `services/api` (FastAPI `/v1`), `services/protocol-runtime` (deterministic three-valued AST engine), `services/model-gateway` (policy-limited AI router + AI-Off Kill Switch), and `services/worker` (durable transactional outbox consumer & daily close reconciler).
3. **Data-Plane Isolation (`PostgreSQL`):**
   - Five isolated schemas (`identity`, `care_clinical`, `finance_ledger`, `governance_audit`, `analytics`) with append-only immutability triggers on signed clinical documents, double-entry journal lines, and tamper-evident hash-chained audit logs.
4. **Payments & Currency Ecosystem:**
   - Unified `PaymentGatewayPort` supporting **Paystack** (`NGN` kobo), **Flutterwave** (`NGN`/`USD`), and **Espees Wallet (`ESP`)** in integral minor units.
5. **Storage Isolation on Development Host:**
   - All caches, package stores, virtual environments, and build artifacts are pinned to `D:\.toolchains` and `D:\Projects\LoveWorld Care` via `scripts/env-d-drive.ps1` and `.npmrc`.
