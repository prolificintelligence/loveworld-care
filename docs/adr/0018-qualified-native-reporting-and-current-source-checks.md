# ADR-0018: Qualified native reporting and current-source checks

Date: 9 November 2026. Implement within Vercel/Neon; no migration or additional host.

The next Director-first priority is source automation for reviewed reporting definitions. Deliver four exact native profiles for service contacts, inpatient deaths, institutional inpatient mortality proportion and actual referral acceptance. The original manual working forms remain immutable. Their separate native edition, `LWH-NATIVE-2026.1`, is proposed for independent review and adoption through the existing template lifecycle.

A governor cannot attach these selectors to changed measurement semantics. Preparing the native form configures immutable exact definitions and a DRAFT mapping in the existing transaction/idempotency framework. It does not adopt the template, declare coverage or create clinical records. Native and manual totals are not automatically added.

Verify relevant-kind clinical event/envelope hashes, Ed25519 attestations, ordered version chains and projection agreement before extracting. Use actual occurrence times and signed same-subject/encounter summaries. Distinguish completed contacts from unique people, final inpatient dispositions from ward/bed events, receiving acceptance from a sent request, and late acceptance from acceptance within the fixed reporting cut-off. Invalid source evidence fails closed or produces explicit UNKNOWN, rather than an inferred clinical zero.

The aggregate response contains values/components, counts, qualification scope and limitations. Retain record/version/event-head references in a separately encrypted append-only reporting-history manifest. No patient IDs, chart narrative or receiving-person identity are returned to source reporting roles. Leadership access remains through existing disclosure-controlled independent release.

Bind each native extract to a fingerprint of period-relevant records, referenced summaries/error markers and facility activation. Recompute current-use eligibility at reporting decisions and snapshot reads. New late in-period sources and corrections invalidate current use; unrelated later-period care does not. Retain historical values and released cells, explicitly label stale clinical evidence, and require a new extract plus retained return correction and independent review before renewed release. The same percentage with changed numerator/denominator remains a discrepancy.

Use synchronous bounded source work with explicit SOURCE_BATCH_REQUIRED errors instead of silent truncation. The current bounds are configuration limits, not evidence of representative maximum-volume performance. Broader batch qualification remains open. This increment adds no external continuous worker or urgent escalation claim.

In the officer workspace, preparation produces a preview. Explicit application replaces only the mapped draft fields and retains ratio components, UNKNOWN and native-subset PARTIAL status. Independent reviewers can inspect the retained aggregate extract and its current-use status. A complete/NIL declaration requires actual source-coverage examination; extraction alone does not establish whole-facility completeness or clinical truth.

See the [source guide](../implementation/native-reporting-source-guide.md) for definitions, exclusions and operating steps. Full institutional/clinical acceptance, wider native mappings and approved equipment connections remain separately qualified work. Offline care remains core; facility-local installation and extra persistent hosting remain deferred.
