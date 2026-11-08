# Cloud recovery and reconciliation release

Date: 8 November 2026, Africa/Lagos. The release is deployed and externally verified. Actual evidence and deployment identifiers follow. Scope is the next cloud-compatible Phase 4A increment, not full-platform acceptance.

## Delivered implementation

- Operator-held independent recovery key; encrypted, streamed logical archives to the existing private object store; verified file/row inventory and a completion manifest.
- Non-destructive restoration into a fresh isolated Neon schema, recovering application keys from the encrypted manifest; row/hash/reference, encrypted-field, signed clinical lineage, open task, stock/ledger and file checks; restored protections and explicit cleanup.
- Immutable recovery/reconciliation evidence and current-authority, paginated operating-history routes. The operations workspace adds **Recovery & integrity**, including actual empty/error states, latest measurements, unresolved limitations and an intentional integrity-observation form.
- Migration 5 adds the protected assurance table; the API remains compatible with schema 4 for staged deployment. There is no public archive download or live database overwrite route.

Components: `control/assurance.py`, `control/continuity.py`, current control routes/tables, shared history-protection installer, `operations/reliability-panel.tsx`, `scripts/platform_continuity.py` and `scripts/verify_continuity_postgres.py`. Authority/containment choices are in [ADR-0011](../adr/0011-cloud-recovery-evidence-and-isolated-restoration.md).

## Executed evidence

The first focused control/reliability run passed **32 tests** in 171.49 seconds. It covers scoped authority, revocation before receipt replay, one observation per idempotency key, actual injected stock/ledger/index exceptions, preservation of care state, independent-key requirements, authenticated archive identity/path binding, tamper/wrong-key rejection and scale-preserving numeric round trips. Disk-backed transport is a disposable engineering harness; the production implementation uses the configured private object store without a success fallback. The affected streamed-archive check also passed after its final chunking change (1 passed, 14.65 seconds). The frontend type check and production build passed. The first synthetic cloud attempt exposed an overlong fixture label; it was corrected. Final verification also exercised the actual operating-evidence write with a sufficiently sized status column and explicit deferred foreign-key validation.

Exact runtime source: `2014a0ed913bce41126dda0ab7a9694f8af4cab0`. [CI run 42444515399](https://github.com/prolificintelligence/loveworld-care/actions/runs/42444515399) passed Python, frontend and secrets scanning; Python job `128620517531` reports **148 passed, 1 warning in 50.39 seconds**. Engineering results do not change the archived suite's 111 NOT_RUN acceptance specifications.

The final-source real Neon/private-object drill passed with **72 tables, one private file, 26 verified encrypted fields and five valid clinical signatures**. The original application key was deliberately replaced in the supplied runtime settings; recovery still succeeded from the independently encrypted manifest. Wrong recovery keys and actually corrupted stored ciphertext were rejected. Open care, precise stock/movements and balanced ledger entries reconciled; all 38 history protections were installed. The drill wrote its synthetic fixtures only into a disposable namespace and owned private prefixes, then removed them. No email, payment or running replacement service was invoked.

Vercel deployment identifiers:

- Backend: `dpl_4vVVMWTx3MKkGuSzQz5oQKtdiBPy`
- Frontend: `dpl_2kUh7vPtszVPn1vFudjXCdPXHAmS`

Both are READY. The live verifier matched **40 uploaded backend source hashes** and **16 frontend source hashes**, confirmed schema 5 and reporting readiness through both origins, denied unauthenticated clinical/reporting/reliability/history access with no-store responses, and verified the public workspace pages. The staged API remained ready on schema 4 and gated the new evidence routes with HTTP 503 before migration. Migration 5 completed with zero seeded domain records. Post-migration institutional concurrency/idempotency and immutable-history checks passed, with **38 protected history tables / 76 trigger event entries**, plus the separate signed clinical record protection.

The actual production archive contains **72 tables / 54 rows / 0 evidence files**, captured at **2026-11-08T04:03:16.682338+00:00**, in 48.139 seconds. The archive was restored in a new temporary Neon schema, reconciled and removed in 118.2 seconds. It verified 1 encrypted fields and retained all 38 history protections. Actual current production has no clinical records or evidence files; the nonempty clinical/file/stock/ledger proof above is separate and synthetic. These measured small-population times are not adopted RPO/RTO or representative-load performance.

Archive reference: `6543789e-67d3-4b21-bf51-6345cff0e37b`.

Production reconciliation recorded **NO_EXCEPTIONS_IN_EXECUTED_CHECKS**, with explicit population counts and no clinical fulfilment/service approval inferred. Metadata-only inspection at **2026-11-08T04:15:39.326849+00:00** confirmed the actual backup, restore and reconciliation records, zero residual recovery-test schemas and zero seeded synthetic clinical/facility/policy domain records. The encrypted production archive is retained in the configured private store; temporary restored copies were removed. The independent recovery key is only in the ignored, operator-restricted `.toolchain/continuity/recovery.env`; it was neither printed nor deployed to Vercel. Independent custody remains an owner action.

All 78 controlled document hashes remain unchanged; the 200-requirement phase/evidence registers and all baseline acceptance statuses are preserved. No Playwright, new host or browser package was installed.

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
