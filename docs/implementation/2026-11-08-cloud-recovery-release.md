# Cloud recovery and reconciliation release

Date: 8 November 2026, Africa/Lagos. Verification/deployment is in progress. This record will be updated with executed evidence and actual deployment identifiers. Scope is the next cloud-compatible Phase 4A increment, not full-platform acceptance.

## Delivered implementation

- Operator-held independent recovery key; encrypted, streamed logical archives to the existing private object store; verified file/row inventory and a completion manifest.
- Non-destructive restoration into a fresh isolated Neon schema, recovering application keys from the encrypted manifest; row/hash/reference, encrypted-field, signed clinical lineage, open task, stock/ledger and file checks; restored protections and explicit cleanup.
- Immutable recovery/reconciliation evidence and current-authority, paginated operating-history routes. The operations workspace adds **Recovery & integrity**, including actual empty/error states, latest measurements, unresolved limitations and an intentional integrity-observation form.
- Migration 5 adds the protected assurance table; the API remains compatible with schema 4 for staged deployment. There is no public archive download or live database overwrite route.

Components: `control/assurance.py`, `control/continuity.py`, current control routes/tables, shared history-protection installer, `operations/reliability-panel.tsx`, `scripts/platform_continuity.py` and `scripts/verify_continuity_postgres.py`. Authority/containment choices are in [ADR-0011](../adr/0011-cloud-recovery-evidence-and-isolated-restoration.md).

## Executed evidence

The first focused control/reliability run passed **32 tests** in 171.49 seconds. It covers scoped authority, revocation before receipt replay, one observation per idempotency key, actual injected stock/ledger/index exceptions, preservation of care state, independent-key requirements, authenticated archive identity/path binding, tamper/wrong-key rejection and scale-preserving numeric round trips. Disk-backed transport is a disposable engineering harness; the production implementation uses the configured private object store without a success fallback. Final-source affected tests, CI, actual Neon/object-store drill, migration, source hashes and live checks remain to be recorded after execution.

## Operator execution

Use the existing D-drive environment bootstrap. Generate the recovery key once; never print or commit it. The file is ignored and operator-restricted. Arrange independently protected custody with the actual records/security owners.

```powershell
. ./scripts/env-d-drive.ps1
.venv/Scripts/python.exe -B scripts/platform_continuity.py keygen --escrow-file .toolchain/continuity/recovery.env
$ArchiveResult = .venv/Scripts/python.exe -B scripts/platform_continuity.py backup --escrow-file .toolchain/continuity/recovery.env | ConvertFrom-Json
.venv/Scripts/python.exe -B scripts/platform_continuity.py rehearse --escrow-file .toolchain/continuity/recovery.env --backup-id $ArchiveResult.result.id
.venv/Scripts/python.exe -B scripts/platform_continuity.py reconcile
```

These commands run against the explicit existing cloud environment; they do not provision another host. A rehearsal recovers a test copy and deletes that copy, preserving the archive. No destructive production restoration command is supplied. A genuine failover/resume requires its separate actual authority, fencing and reconciliation procedure. Inspect failed cleanup evidence before repeating a rehearsal. Incomplete archive objects remain protected for operator investigation; no retention deletion is enabled without adoption.

## Rollout and boundaries

Deploy the API compatible with schema 4; confirm current readiness and the recovery-evidence migration gate. Apply additive migration 5, deploy the frontend, run the actual archive/rehearsal/observation, and verify source hashes, history triggers and no unauthenticated access. Rollback retains the added table/history and uses a compatible binary or the controls pause switch. Preserve every encryption/recovery key and newer clinical transaction; a binary rollback is not a data restore.

An executed technical restoration does not establish independent off-account copies, independently held escrow, automatic backup cadence, adopted retention/RPO/RTO, key-rotation/retirement completion, representative load, witnessed clinical/finance recovery or service activation. Production has no adopted clinical sites/records at the preceding release; synthetic clinical/file/stock/ledger proof belongs only in an isolated namespace. Real reviewer appointments, response windows and institutional adoption remain operating inputs. No Playwright or additional host is installed. Full offline care remains core, with its facility-local deployment deferred.

Next recommended implementation: Phase 4B institutional lifecycle and approved information, while remaining Phase 4A operating adoption/qualification proceeds. Complete effective hierarchy/closure stewardship, affiliation corrections/renewal/restriction/appeal/reinstatement and approved education/policy publication, preserving historical reporting scope and clinical custody. The [suite-wide roadmap](2026-11-08-implementation-review-and-next-phases.md) and [overall progress matrix](2026-11-05-platform-progress.md) retain later clinical, patient/family, interface, finance, governed-assistant and qualification work.
