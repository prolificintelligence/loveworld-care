# Capacity and conformance increment — 10 November 2026

## Code delivery

Tooling commit `3e167fd112743993a3e0066ee3263faaf274291c` delivers the [canonical crosswalk](conformance/README.md), generated JSON/five CSV views, CI drift checks, negative integrity/isolation tests and the [cloud qualification harness](2026-11-10-capacity-qualification-runbook.md). A disposable instrumented Vercel preview `dpl_BVoSexBc4xd5TjzrWprLDLf1U67f` was deployed on the existing API project, tested and deleted. It was never promoted. Its entrypoint/configuration differ intentionally from production, and its qualification metadata cannot pass the production promotion guard.

Production remains runtime `3633c9572535f23522a2bb21b1d900b04105bd51`: API `dpl_FVWYJSPJgTvF59TbkVAht2vvzYSS` and web `dpl_2yBK8rEmhraHP6X6CQKo2CVjW1hc`. No application runtime or schema change was necessary in this increment. Neon remains **schema 9 /102 tables /53 protected history tables**. [Exact evidence](2026-11-10-capacity-and-conformance-evidence.json) retains CI, request measurements, source manifest, cleanup, original failed CI and before/after production observations.

## Engineering evidence

[CI 42754146252](https://github.com/prolificintelligence/loveworld-care/actions/runs/42754146252) passed on the tooling commit: **242 Python /11 client /4 PWA tests**, builds, typecheck and secret scan. The canonical-register integrity step passed on Linux. Local targeted integrity/isolation tests: **11 passed**. The first run correctly rejected platform-dependent text fingerprints; implementation hashes are now explicitly LF-normalized while original document and deployment source checks remain byte-exact.

The first qualification preview failed during function discovery (`unused_function`) before measurements. Its preview/schema were removed and production aliases stayed unchanged. A diagnostic build isolated the conditional app-export issue; the corrected module-level app export reached READY. Diagnostic previews were deleted with subsequent lookup 404. Failed build and cleanup evidence is retained separately from the final measured run.

### 002 — Bounded actual-cloud measurements

All 15 measured requests ran in the actual Vercel Python function with **NullPool** against a disposable schema in the existing Neon database. Fixture setup used a local pool and is excluded from measured request timings. The wrapper supplied a separate one-use encryption key, schema translation, route/provider exclusions and measurement headers. This uses existing database connectivity: schema translation is not separate database-role or provider-account isolation. It removed cron and never changed production aliases or project environment configuration. All 69 submitted source files were verified; the exact wrapper/config differences are in the evidence.

Verified 5,001 unrelated later-period records leave the selected-period source hash unchanged; simultaneous duplicate requests return an identical receipt. The 5,000 selected-record boundary succeeds with **4990 missing summaries explicitly UNKNOWN**, never nil or complete. Simultaneous facility requests and three further bound requests completed; the second facility had no synthetic clinical sources, so this is not simultaneous maximum-volume facilities. A **20,000 selected signed-event** history passed; **20,001 events** and **5,001 selected records** each returned `409 SOURCE_BATCH_REQUIRED`, without truncated totals. Retained extraction history remained readable after overflow. Existing isolated fixture setup also exercised correction invalidation, protected-history deletion rejection and clinical/reporting hash verification; it did not qualify sustained cloud correction traffic.

| Request | HTTP | Client seconds | Application ms | Process lifetime maximum RSS KiB |
|---|---:|---:|---:|---:|
| cold_readiness | 200 | 4.573 | 3523.426 | 115916 |
| baseline_extract | 200 | 6.742 | 6304.717 | 119780 |
| 5001_later_period_extract | 200 | 6.876 | 6131.257 | 119960 |
| duplicate_a | 200 | 6.643 | 6165.102 | 120844 |
| duplicate_b | 200 | 6.913 | 6137.396 | 120844 |
| 5000_selected_extract | 200 | 9.773 | 8973.575 | 166560 |
| simultaneous_facility_b | 200 | 6.689 | 5975.998 | 166560 |
| simultaneous_facility_a | 200 | 9.581 | 9185.193 | 166560 |
| repeated_bound_1 | 200 | 9.403 | 9067.103 | 168236 |
| repeated_bound_2 | 200 | 9.262 | 8935.157 | 168236 |
| repeated_bound_3 | 200 | 9.308 | 8963.485 | 168236 |
| 5000_records_20000_events | 200 | 13.469 | 12777.223 | 202880 |
| 20001_events_overflow | 409 | 9.086 | 8368.639 | 202880 |
| 5001_selected_overflow | 409 | 7.445 | 7134.173 | 202880 |
| retained_extract_history_after_overflow | 200 | 5.792 | 5478.573 | 202880 |

Maximum observed process-lifetime high-water RSS: **202880 KiB (198.12 MiB)**. This is not per-request allocation or provider-billed memory. Application elapsed time excludes upstream startup; client wall time includes network and may include startup, and is not provider-billed duration. The first readiness sample is labelled `cold_readiness` in the harness; no instance identity or confirmed cold/warm classification was captured. Concurrent samples may share process history. The existing **60-second maxDuration** was retained. This short synthetic sequence does not establish representative sustained capacity, a production SLO or adoption of latency targets. **002 remains open.**

Temporary provider probe access was revoked; final automation-token count is zero and SSO configuration is unchanged. Preview deletion was accepted and subsequent lookup returned **404**. The disposable schema was removed. Production business counts stayed one account and zero units/facilities/clinical sites/records/events/reporting definitions/obligations/returns/snapshots. No production synthetic records, approvals, emails or job dispatch were created.

### 014 — Full inventory, explicit unresolved conformance

The register covers **51 forms /355 fields /75 screens /30 state families /52 capture routes /15 commands /15 query families**, with **296 actual institutional API routes /58 typed models** indexed. It preserves canonical source, requiredness, type, validation rule and classification, and links actual candidate schemas/routes plus permission/validation/persistence/test source candidates. These candidate links do not assert field equivalence or test coverage. Domain page links do not prove 75 separately implemented screens.

**47 forms** have candidate typed-route associations and **four** have explicit mapping gaps. **48 fields** have name/alias candidates; **307** retain explicit field-mapping gaps. All fields still need semantic missingness/permission/persistence and failure proof. **Eight requiredness differences** are recorded for review, not declared defects: generic submitted capture and consequential actions have different guards. All **75 screen and 30 state-family** semantic proofs remain open. All **82 interface** contracts retain explicit reconciliation status. No extension adoption or parity was invented. **014 remains open.**

The Director-first next review is forms 001–018/screens 001–030: registry → affiliation → returns → independent verification → permitted leadership intelligence → accepted intervention/outcome. Representative examples needing review are tagged canonical unknown values versus split native commands; structured location/provenance and purpose-specific contacts versus simpler inputs; scanned evidence exclusion; and actual receiving-outcome state coverage. The outcome-review `limitations` input is optional in a shared action schema but required by its server transition guard; schema requiredness alone cannot classify that workflow as missing. The four unmapped form contracts are rights requests, programme funding, downtime/sync and optional ERP; unmapped does not mean every related capability is absent.

## Operating adoption

**Incomplete.** Real nominations/deputies, independent reviewers/deciders, facility registration/affiliation, adopted forms/calendar/disclosure and actual service authority remain owner inputs. Synthetic preview fixtures establish no operating decision. Director-first sequencing is retained. Native LW Care requires no second EMR; equipment follows selected-facility registration/approval. Offline care remains core while additional/local hosting remains deferred.

## Full-suite acceptance and next gates

**Incomplete: 200 requirements /111 formal cases remain NOT_RUN.** Neither inventory completeness nor engineering CI changes those statuses.

Continue 014 with field-specific proofs and explicit extension review, and 002 with representative sustained correction/replay/contention, production-configuration/provider telemetry and owner-adopted targets. Keep 003 scanner qualification, 004 automatic cadence/independent custody/RPO/RTO/staffed resumption and 019 dependency/licence/paired rollback/full provider-sandbox gates open. A disposable reporting preview advances isolation evidence; it is not the full service/provider sandbox or clinical resumption acceptance. Independent security/privacy and actual-role/device/accessibility/low-bandwidth UAT remain separate.

Fresh production checks again verified exact live source identities, both origins' readiness, signed-out boundaries, invalid login rejection and all 12 pages. All **78 controlled document hashes**, the native mapping contract and recording SHA-256 `4fd2bbb9fedb1b6ab890f6b79488ba53f4bd266acab2a980a7f7f5dfc9aac5bf` are unchanged. No Playwright, additional host, dependency or invented approval was introduced.
