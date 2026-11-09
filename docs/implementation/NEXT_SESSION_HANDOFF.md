# Next implementation session handoff

Prepared 9 November 2026 after the comprehensive audit. Read this file, the [audit report](2026-11-09-comprehensive-audit-and-production-readiness.md), [20-ticket backlog](2026-11-09-production-readiness-backlog.csv) and [current release](current-release.json) before changes. The audit supersedes older prospective sequences; preserve historical release evidence.

## Start here

Scope remains aligned, but **full-suite production/clinical acceptance is incomplete**. Start Phase A with **LWH-AUD-20261109-001 and 002**. Released historical snapshot/CSV access fails with `409 SOURCE_BATCH_REQUIRED` when current native source inventory exceeds its cap. The local probe reduces that cap to 1 to exercise the guard; this is not maximum-volume production qualification. Retained cells recover unchanged after resetting the cap. Preserve permitted historical access and active disclosure controls, expose truthful stale/unavailable current-use status, and fix bounded source accounting/lock scoping with meaningful regression and PostgreSQL/cloud qualification.

Reproduce using existing dependencies:

```powershell
. .\scripts\env-d-drive.ps1
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe scripts/audit_reporting_readiness.py
```

This is an audit probe, not a passing regression test. It uses isolated synthetic local SQLite fixtures and writes ignored `.toolchain` output. Convert the confirmed behaviour into an appropriate regression expectation while fixing it. Its lowered-cap reproduction does not prove throughput.

Then close scanner/recovery/conformance/release qualification gaps. Demonstrate the Director's actual operating loop with independent officers: registered facility → affiliation → return → independent verification → permitted leadership release → accepted intervention/outcome review. Additional module count is not acceptance.

## Baseline to recheck

- Workspace `D:\Projects\LoveWorld Care`; repository `prolificintelligence/loveworld-care`, branch `main`.
- Audited repository HEAD before this documentation commit: `f8ef5ba392a12401382740025f066c045d731efe`. Read `git log` for the later audit commit; do not reset to the earlier HEAD.
- Runtime: `2aac16a5b72e2dc1388d5a36e014a24c859e3eb5`.
- API `https://lw-health-intelligence-api.vercel.app`, deployment `dpl_3kMLz4bn2nfnXS1JLviU8U9c9E41`.
- Web `https://lw-health-intelligence.vercel.app`, deployment `dpl_AnQ8XM7eds5ZNxZmkuteEQuR1yow`.
- Fresh audit verification matched **64 API /31 web-public files**, both origins' health/readiness and signed-out denials, invalid sign-in rejection and 12 frontend pages. These were not authenticated human acceptance tests.
- [Runtime CI 42681186207](https://github.com/prolificintelligence/loveworld-care/actions/runs/42681186207): all three jobs successful; 221 Python, 11 client, four PWA tests, builds/type checking/secret scan. Recheck subsequent work before relying on it.
- Neon `health_platform`: schema **8**, **101 tables /53 protected history tables**. Audit required/issued no migration.
- Production snapshot: one account with current `PLATFORM_ADMIN`/`REGISTRY_STEWARD` grants; zero hierarchy/facilities/clinical data/reporting definitions/returns/activation packages. Aggregate inspection only; no clinical payload copied.
- Daily API cron `0 0 * * *`; continuous worker and automatic backup cadence not established. Missing `LWH_CLAMAV_HOST` makes scanning fail closed. Provider environment entry presence does not prove an integration; encrypted secret values were not compared.
- Successful isolated restores and a retained failure exist. Automatic cadence, independent copy/key custody, adopted targets and representative service resumption remain open. Never erase failed evidence.
- Original 78 documents match their manifest. Formal **200 PRD requirements /111 specified cases** remain `NOT_RUN`. Engineering tests do not replace operating acceptance.

## Binding scope and constraints

- The Director's registry/reporting/standards/intelligence/intervention outcome is first. Native EMR and personal/family care were explicitly authorised and support it.
- Native LW Care is the platform EMR; do not request a second EMR as a prerequisite. Equipment/imaging/LIS/PACS connections require registration/approval and a selected facility's documented counterpart.
- Offline **care remains core**. Facility-local installation and deployments beyond Vercel/Neon/R2/Upstash/Resend/free OpenRouter are deferred. Do not add persistent worker/scanner hosts without changed instructions. Scripts/contracts can be prepared; PWA installation is not full offline clinical runtime.
- My LW Health Care is an installable patient PWA on the **current deployment/origin**, sharing the API with independently verified personal/family permissions. Do not cache charts or clinical drafts in its service worker. Current remote care is human asynchronous requests/reviewed releases; full remote consultation and referral tracking remain partial.
- **No Playwright installation.** Use existing tests, HTTP/source checks and properly recorded manual device/accessibility UAT.
- Activate `scripts/env-d-drive.ps1` before pnpm/uv/pytest/turbo; caches stay on D:. Use existing dependencies/tools. Do not recreate providers/reset the repository to restart work.
- Initial real administrator: Emmanuel Patrick, `epatrick@prolificintelligence.co`. Do not resend invitations unnecessarily or invent other role holders. Actual reviewers, deciders and operators need real nominations and separation of duties.
- Source data was confirmed test/demo only; production is currently business-empty. Keep synthetic engineering fixtures isolated and labelled. Never create fake production facilities, staff, accepted policies/criteria, returns, clinical events, payment successes or approvals.
- Original Directorate forms are unavailable. User-authorised researched proposals can be reviewed/replaced: `LWH-WORKING-2026.1` (3 forms, 22 configurations/21 distinct metrics), separate `LWH-NATIVE-2026.1` (4 profiles). None automatically adopted. Actual roster, criteria/calendar/disclosure/content/service decisions are still operating inputs.
- AI remains free-model only, currently infrastructure; no autonomous consequential action. Optional ERP is separate; billing, stock and sponsorship remain core.
- Preserve the controlled suite and **untracked `docs/New Recording 20.m4a`**. Stage explicit intended paths only. Never print/commit decrypted credentials. Rollback must preserve newly committed care/finance events.
- Do not casually invoke authenticated `/v1/internal/jobs`: it can send email. Read-only audits should not trigger operations.
- Implementation, GitHub pushes, necessary migrations, tests and deployment within the existing cloud stack were authorised. Complete reviewable work/checks before asking for genuinely missing inputs. This audit issued no runtime fix, migration or deployment command.

## Credential locations and tooling

Use existing helpers/ignored configuration; these are file references, never content to paste:

```text
D:\Projects\secrets\Prolific-Intelligence-GitHub.md
D:\Projects\secrets\Prolific-Intelligence-Vercel.md
D:\Projects\secrets\lw-health-neondb-connection-string.md
D:\Projects\secrets\lw-health-upstash.md
D:\Projects\secrets\lw-health-resend.md
D:\Projects\secrets\prolific-engines- openrouter-kk.md
```

`scripts/cloud_credentials.py`, ignored `.env.platform.local`, existing `.toolchain` helpers and `scripts/verify_reporting_cloud.py` support established releases. The older `prolific-mailsending-resend.md` key was rejected; the replacement is `lw-health-resend.md`. Preserve current private-object/encryption settings. Vercel environment listing returned encrypted values during the audit; never compare ciphertexts as secret values or print them as configuration.

Production frontend: `apps/platform-web`. Backend: `services/api/src/lw_care_api/platform`, entrypoint `api/platform.py`. Legacy directories are not current capability evidence. Packaging/source verification must select the intended runtime explicitly.

## Starter prompt for the new session

> Continue LoveWorld Care from `docs/implementation/NEXT_SESSION_HANDOFF.md`. Read the comprehensive audit and readiness backlog first. Start Phase A with tickets LWH-AUD-20261109-001 and 002, preserving the Director-first sequence and deployment constraints. Implement and meaningfully test fixes, then deploy and verify within the existing cloud stack. Do not install Playwright, add deferred hosts or invent operating approvals. Report exact release evidence and remaining acceptance gates.

Start with `git status`, `git log` and `current-release.json` to detect intervening changes. Preserve the recording and unrelated work. State code delivery, engineering evidence, operating adoption and full-suite acceptance separately.
