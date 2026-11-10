# Phase A service and release assurance

This increment advances tickets 003, 004 and 019. Capacity qualification (002), canonical conformance (014), operating adoption and full-suite acceptance remain separate gates. No additional hosting or operating approvals are introduced.

## Evidence-dependent operation

Authenticated `/v1/service-capabilities` and the institutional/reliability contexts expose an explicit evidence-upload capability. Without a configured scanner or private storage, new uploads are excluded and the registry/governance workspaces disable their upload controls. Required evidence still gates submission and affiliation decisions. Existing retained evidence remains subject to its permissions, expiry and history controls.

Configured prerequisites permit an attempt, not a claim of scanner qualification. Every new file must still pass the actual scanner before storage or CLEAN metadata. This release does not install a scanner, bypass scanning, accept unscanned files or qualify a scanner engine. File-dependent operation remains excluded until that engineering/operating boundary is resolved within the authorised stack.

## Schema-9 recovery

`platform_continuity.py` now shares the archive engine's supported-version set (5–9). Schema-9 reconciliation also checks missing/out-of-date reporting-source projections. Neither reconciliation nor a successful isolated restore completes care or approves resumption.

Run the existing operator commands with the existing ignored escrow file; never paste keys into arguments or output. `scripts/verify_continuity_postgres.py` creates a random isolated schema and private-object prefixes. It verifies signed clinical records, nonempty reporting-source projections, private evidence bytes, stock, balanced ledger entries and open work. It appends newer source care/ledger records after the snapshot and verifies that isolated restoration leaves those newer records intact. Wrong keys and corrupted chunks must fail. Each run removes only its own disposable schema/objects; failed evidence is retained.

This qualification does not establish automatic backup cadence, independent off-account/key custody, adopted RPO/RTO, representative maximum-volume recovery or an actual staffed service-resumption decision.

## Staging and exact-build promotion

The existing cloud release CLI now stages production builds by default. `deploy --target api|web` requires committed sources and successful Python/web/secrets-scan CI for that exact commit, and submits `autoAssignCustomDomains=false`. It tags the candidate with its source commit and CI run. This is the documented [staged production build workflow](https://vercel.com/docs/cli/deploying-from-cli), within the existing two Vercel projects.

After the candidate reaches READY, use `promote --target ... --deployment-id ... --expected-current ...` from the same clean source commit. The guard verifies project identity, production target, exact source metadata, all submitted file UIDs (including dependency/config inputs), signed-out candidate health/authentication, and the active production alias both before and after inspection. A changed expected parent aborts promotion. The provider promotes that deployment ID without rebuilding it. Record the active alias again after promotion.

The GitHub release workflow supports schema 9, explicit stage/promote actions, a single production concurrency group, and read-only access to CI results. Its existing production environment remains in place. These technical gates are not institutional operating approvals.

Production-backed candidates receive only signed-out read probes. Synthetic fixtures remain in isolated Neon/R2 qualification namespaces. This is not a separately isolated end-to-end Vercel/provider sandbox; actual function capacity under representative source/event growth remains ticket 002 work.

The guard reduces accidental or mismatched promotion; it is not a provider-side atomic compare-and-swap. Privileged external promotion can still race a final alias read. Restrict concurrent release operators and reconcile provider results. Technical inability to inspect a protected candidate is a failure, not permission to unprotect it.

## Recovery and rollback boundary

An isolated restore never replaces `health_platform`. The source's post-snapshot care/finance records must survive qualification. Promotion changes aliases, not database contents. Do not restore an older database or remove schema markers to reverse a code release.

The prior schema-9 release may be a compatibility candidate, but a complete code-pair rollback, concurrent-new-data rehearsal and clinical operating resumption still require qualification. The schema-8 runtime remains unsuitable as a schema-9 rollback artifact. Preserve all failed assurance history.

## Remaining sequence

Complete 002 capacity/latency measurements, 004 cadence/custody/targets and representative recovery, 014 field/screen/state conformance, and 019 isolated staging/dependency-licence/rollback assurance. Then demonstrate the real Director-first registry → affiliation → return → independent verification → leadership release → accepted intervention/outcome loop with nominated people and adopted inputs. The 200 requirements and 111 specified cases remain NOT_RUN until formally executed.
