"""Assemble evidence-linked release reports from executed local checks."""
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
docs = root / 'docs'
evidence = docs / 'phase4'


def read(name):
    return (evidence / name).read_text(encoding='utf-8', errors='replace')


def result(name, flutter=False):
    value = read(name)
    matches = re.findall(r'\+(\d+): All tests passed!' if flutter else r'(\d+) passed', value)
    return int(matches[-1]) if matches and ('Some tests failed' not in value and 'FAILED ' not in value) else None


counts = {'Backend': result('backend-tests.log'), 'Flutter User': result('user-tests.log', True), 'Flutter Admin': result('admin-tests.log', True), 'Shared API client': result('client-tests.log', True)}
total = sum(counts.values()) if all(x is not None for x in counts.values()) else 'pending'
performance = json.loads(read('performance.json'))
database = json.loads(read('database-audit.json'))
neon = json.loads(read('neon-readonly.json'))
config = json.loads(read('config-validation.json'))
bandit = json.loads(read('bandit-final.json'))
advisories = json.loads(read('dependency-audit-final.json'))
known = sum(len(x['vulns']) for x in advisories['dependencies'])
medium_high = sum(x['issue_severity'] in ['MEDIUM', 'HIGH'] for x in bandit['results'])
low = sum(x['issue_severity'] == 'LOW' for x in bandit['results'])
test_table = '\n'.join(f'| {name} | {count if count is not None else "Pending final execution"} | phase4/{file} |' for (name, count), file in zip(counts.items(), ['backend-tests.log', 'user-tests.log', 'admin-tests.log', 'client-tests.log']))
latencies = '\n'.join(f"| {name} | {row['requests']} / {row['concurrency']} | {row['median_ms']} | {row['p95_ms']} | {row['errors']} |" for name, row in performance['http'].items())
assets = '\n'.join(f"| {name} | {row['main_js_bytes']:,} | {row['gzip_bytes']:,} | {row['total_build_bytes']:,} |" for name, row in performance['assets'].items())


def write(name, body):
    (docs / name).write_text(body.strip() + '\n', encoding='utf-8')


write('FINAL_TEST_MATRIX.md', f'''# Final test matrix

21 October 2026. Local execution is distinct from hosted/provider/native-device acceptance.

| Suite | Passed | Evidence log |
|---|---:|---|
{test_table}
| Total | {total} | No excluded tests |

Backend covers authentication/session rotation and revocation, role permissions, owner isolation, content CRUD, PDF ingestion/approval/versioning/retrieval/citations, deterministic calculations, deadlines, notification scheduling/delivery state, webinars and typed AI tools. Phase 4 adds reversed-meaning/incomplete-quote rejection, page-level PDF script rejection, request-body bounds, error/log redaction, CORS/cache headers, profile persistence, current owner deadlines, file-type mismatches, cross-app CRUD/archive/search/audit, verified-TLS guards, overall chat timeout and immutable rule transitions.

User tests include 14 calculator forms at six widths and academy/compliance/settings views. Eight accessibility tests exercise 150%/200% text on 360px sign-in, Home, Profile and Compliance. A contrast assertion checks muted text against four shared light surfaces. The Admin suite exercises navigation, knowledge and seven professional workspaces at six widths. Flutter analysis results are separate `user-analysis.log` and `admin-analysis.log`.

## Actual manual and HTTP workflows

- Browser: User/Admin release previews opened; local reader/operator signed in; Home showed the owner's persisted licence expiry; Profile name was edited/saved and reflected back; Admin displayed approved, rejected and superseded demonstration PDFs. Additional observations are in `phase4/manual-browser.md` and screenshots. Do not infer every CRUD action was manually clicked.
- Live HTTP: toolkit compute/save/reopen, company/licence creation and renewal, review/independent approval/publication with actual in-app worker delivery, typed chat calculation/company tools, webinar scheduling/registration/private joining/UTC ICS. See `phase4/acceptance-http.json` and `scripts/phase4_acceptance.py`.
- Automated cross-app: draft is hidden, administrator publishes, reader sees edited record, search/page works, another reader cannot edit, archive hides it and audit exists for videos/publications/articles/webinars.
- Database: fresh local QA migration to 0004, 74 FK orphan checks, DB backup restored to a separate local database. Shared Neon read-only metadata only.

## Visual and accessibility evidence

54 User captures cover nine screens at 360/390/430/768/1024/1440px under `phase4/screenshots`. `reference-contact.png` contains all nine approved references; `actual-contact.png` summarizes current 390px captures. These are controlled widget fixtures, not production content. Admin responsive tests and browser screenshots are separate. No golden baseline was blindly approved to hide differences. Browser AX labels and profile keyboard text entry were inspected; full NVDA/VoiceOver/TalkBack and physical-device keyboard testing are not claimed.

## Failures found and corrected

Initial large-text Home overflows were fixed with text-scaled grid height. A debug/main Android manifest conflict was fixed with an explicit debug-only cleartext override. A citation-page regression from an over-restrictive whole-chunk policy was fixed by allowing complete verbatim sentences while rejecting paraphrases and clipped qualifiers; the page-two mapping test passed again. The old manual-reminder-only dashboard assertion was updated to require the still-active document expiry after completing its manual reminder. An early unsupported GridView parameter was corrected and rebuilt. Final logs supersede intermediate failed runs.

## Not executed / release gates

Real OpenAI generation/embeddings and professional answer evaluation; native pgvector retrieval on the target Neon branch; S3 object permissions/restore; actual email/push delivery; production/preview Vercel deployment and cold-start/streaming tests; signed Android AAB; iOS compilation/device testing; full manual CRUD/invalid-input matrix on hosted services and final visual approval. These remain explicit gates, not passing or excluded tests.
''')

write('SECURITY_AUDIT.md', f'''# Security audit

Source review, API negative tests, ownership tests and supported scanners were executed. This is not a penetration-test certification or a claim of formal legal compliance.

## Findings repaired

| Finding | Repair and verification |
|---|---|
| Qualitative claims could contradict a real quote | Unverified paraphrases and clipped statements are rejected. Output uses complete exact source excerpts/sentences, labeled as excerpts rather than professional conclusions. Uncited model limitation prose is not emitted. Tests reverse negation/conditions and preserve page mapping. |
| Active PDF checks covered only the root | Bounded recursive object inspection rejects page/annotation scripts, launch/submit/import actions and embedded-file associations. Native parsing never executes source instructions. |
| Declared MIME/extension could disagree | Private images must match decoded format and extension; PDF endpoints require .pdf plus validated PDF bytes. Size/pixel/page/object limits remain enforced. |
| Release silently used debug signing | Release Gradle tasks fail without four owner-supplied signing variables. Expected preflight rejection recorded; no production key created. |
| Unprotected manual production deployment | Main-branch/manual/protected-environment gate, verification dependency and pre-deployment schema gate added. Protection/reviewers must still be configured in GitHub. |
| Private response caching / raw failure context | Streaming-safe middleware emits no-store/nosniff/frame/referrer protections, correlation IDs and redacted operational events; generic failure responses never expose exception messages. |
| Weak hosted transport configuration | Hosted DB requires verify-full TLS; migration connection must be direct with verified TLS. Exact query parsing rejects disabled/ambiguous modes. Hosted CORS must use explicit HTTPS origins; local storage and exact-vector production fallback are rejected. |
| Hidden legacy/UI gaps | Unreachable duplicate screens removed, profile editor wired, owner deadlines integrated, invalid Admin workflow transitions disabled/rejected. |

Auth remains Argon2 + short-lived HS256 tokens tied to revocable DB sessions. Refresh rotates/revokes the old session; roles are loaded from the DB. Login does a dummy password verification for absent accounts. Auth/calculator/upload limits and AI account quotas are durable. Model tools remain explicit read-only allowlists with no SQL or write interface. Company attachments are owner-scoped even for general administrators. Sensitive company JSON uses a separate AES-GCM key. No weakening of authentication was introduced.

## Dependency and source tooling

The first pip-audit reported vulnerable cryptography 47.0.0 and pip 25.3. They were upgraded to cryptography 50.0.2 and pip 26.2.2. The final pinned-runtime scan reports **{known} known advisories**. Scanner databases and execution environment limit what this establishes. Bandit reports **{medium_high} medium/high and {low} low findings**; low findings concern constant protocol/rule labels and assertions in explicit development checks, reviewed as such. Ruff's fatal/syntax/undefined-name selection is recorded in `python-static-final.json`. This is not exhaustive type or semantic analysis.

Runtime dependencies are pinned separately from development tools, with a Linux CPython 3.12 dependency closure including psycopg-binary. Compatible wheels were downloaded successfully; actual Linux/Vercel execution remains pending. Optional provider/PDF/S3 imports are lazy. CI repeats tests and scanning; hosted CI has not run because this checkout has no commits/remote configured.

## Secrets and residual risks

Local .env files, QA accounts, private storage, backups and keystores are ignored. The source/log scan does not print values. No commit history exists here, so historical remote exposure cannot be cleared by a local scan. Previously shared Neon credentials must be rotated before production, and the owner-like runtime account replaced by least-privilege application/migration roles. No rotation or role change was made on shared Neon.

Production monitoring, object access policy/restore, account export/deletion handling, administrator access policy, signing/links/push, legal source approval and live model quality remain unverified. Full adversarial/hosted/device testing is not complete. See RELEASE_BLOCKERS.md; production release is not approved.
''')

write('NEON_PRODUCTION_READINESS.md', f'''# Neon production readiness

## Actual databases

- Shared Neon: read-only metadata connection succeeded; pooled hostname confirmed. Revision is **{neon.get('schema_revision')}** and installed extensions are **{', '.join(neon.get('extensions', []))}**. It is not the Phase 4 target schema, and pgvector is not installed. There were no migrations, role changes or application-table writes. One connect-plus-metadata sample took {neon.get('connect_and_metadata_ms')} ms, including possible compute wake-up; it is not a throughput benchmark.
- Local QA: `dsbca_phase4_qa`, schema {database['schema']}, {database['tables']} tables, {len(database['orphan_checks'])} FK checks and {sum(database['orphan_checks'].values())} orphans. Data is fictional; the dataset contains different roles, companies, expiries and document approval states.
- Local recovery: a custom-format dump was restored into `dsbca_phase4_restore`; schema {database['recovery']['schema']}, {database['recovery']['users']} users and {database['recovery']['companies']} companies were verified. The dump is ignored. Private object-store recovery was not tested by this DB rehearsal.

## Connection and query review

Request engine pool is 2 connections, overflow 0, pool wait 8s, recycle 240s, pre-ping enabled, connect timeout 8s, statement timeout 15s and lock timeout 5s. Sessions commit/rollback/close through the dependency; requests never create schema. Hosted URLs require verify-full TLS. Use Neon's pooled URL for traffic and the direct URL for reviewed migrations. Do not replay arbitrary failed writes automatically. Fleet concurrency times per-instance pool size must fit the chosen Neon connection budget.

EXPLAIN ANALYZE/BUFFERS was executed only on local QA for scheduler selection, conversation history, company expiries, admin pagination and FTS. Plans and actual timings are in `phase4/performance.json`. The small corpus did not justify speculative indexes; none were added merely to force an index plan. Existing ownership/date/status/foreign-key and FTS indexes remain. Native HNSW/pgvector plans and representative production-volume query plans are not verified.

## Required migration and recovery procedure

Provision a separate Neon development branch and least-privilege runtime/migrator roles. Back up the existing schema/data and keys; verify restore and private-object versions. Install/configure pgvector through reviewed migrations, run 0003/0004 on that branch, then execute all acceptance/security/retrieval tests against it. Review additive schema and any rollback data loss before authorizing production migration. No production downgrade/reset is permitted as a casual rollback.

Prefer application rollback to a compatible deployment; forward-fix schema problems. A rollback involving dropped new tables requires an explicit backup/restore and data-loss plan. Set recovery objectives, retention and restore ownership with DSBCA; none are invented here. Back up encryption keys separately and test access before rotation. Shared Neon remains a release blocker until this procedure is executed and reviewed.
''')

write('VERCEL_PRODUCTION_DEPLOYMENT.md', '''# Vercel deployment readiness

The three-project architecture is preserved: User/Admin Flutter static outputs and a FastAPI Python API. No hosted preview or production deployment was performed; Vercel projects/token/domains are unavailable.

## Prepared configuration

User/Admin Vercel configs provide filesystem routing followed by SPA fallback, no-cache for index/bootstrap/unversioned JavaScript/service-worker/version metadata, and security/referrer/permission headers. Authenticated API responses are always no-store. Do not give unversioned bootstrap files immutable caching; an earlier browser cache masked updated UI during Phase 3.

Backend `index.py` exports FastAPI; pyproject entrypoint and Python 3.12 selection are explicit. `vercel.json` specifies FastAPI and a 60-second function budget. `.vercelignore` excludes local environments, private files, QA seed/check modules and tests. Runtime pins are separated from dev/scanner dependencies. Linux wheels were downloaded for compatibility; that is not a Vercel bundle/cold-start validation.

Current primary references: [Python runtime](https://vercel.com/docs/functions/runtimes/python), [function limits](https://vercel.com/docs/functions/limitations), [duration configuration](https://vercel.com/docs/functions/configuring-functions/duration). Request/response/function limits and scheduler cadence depend on current runtime/plan; check the selected account at activation. Larger PDFs use private direct upload/presigned delivery rather than ordinary function bodies. The API enforces a bounded 3.5 MB request envelope and 3 MB multipart file endpoints.

## Activation order

1. Create separate project IDs and protected GitHub production/preview environments with required reviewers. Configure an approved main branch policy; this checkout has no commits/remote, so no hosted CI run is claimed.
2. Provision isolated Neon development/staging, direct/pooled verified-TLS URLs, independent JWT/encryption keys and exact HTTPS CORS origins. Validate schema 0004 and native vector readiness before routing traffic.
3. Configure private S3-compatible storage, OpenAI models/key and durable workers. Optional Resend/FCM require real end-to-end acceptance. Secrets belong in encrypted platform environments, never Flutter defines.
4. Deploy API preview with staged environment, then check health/readiness/capabilities, owner authorization, source visibility, signed downloads and SSE. Configure exact User/Admin preview origins.
5. Build web using the public HTTPS API origin; deploy both static previews. Test deep links, refresh, file download and two browser engines. Run the full acceptance matrix again.
6. Only after approval use the manual production workflow. It requires verification, main branch, protected environment and pre-deployment readiness reporting schema 0004. First bootstrap requires a separately reviewed operator procedure; the gate does not silently migrate shared Neon.
7. Verify each deployment URL, domain/HTTPS, provider behavior and runtime logs. Record deployment IDs and rollback targets. Post-deployment readiness checks do not replace functional QA.

Verification workflow runs on pushes/PRs. Preview deployment is opt-in (`PREVIEW_DEPLOY_ENABLED`) and excludes fork PRs; separate preview environment/secrets and PREVIEW_API_BASE_URL are required. Production is manual/protected. Owner-signed Android has its own protected manual workflow. All definitions are locally syntax-reviewed; GitHub/Vercel execution and project protections remain unverified.

Schedulers must invoke authenticated bounded ticks. Never start indefinite workers in request functions. PDF indexing persists checkpoints and provider retries are delegated to durable job state; large or slow workloads require a suitable external executor. The overall chat await budget is 35s by default, below the configured 60s function limit, with SQL/connect timeouts as additional bounds. Verify real streaming/disconnect/cold-start behavior on the selected plan before launch.
''')

write('FLUTTER_ANDROID_RELEASE.md', '''# Android release readiness

Both apps retain their existing application IDs; User is `com.dsbca.dsbca_user`. Display names are DSBCA/DSBCA Admin. User minimum API is 24 for video playback. Production network traffic is HTTPS-only and application backup is disabled. Debug manifests explicitly permit local cleartext transport for emulator QA, with a merger override scoped to debug.

Deep-link intent filters are prepared for `dsbca://app/...` and `dsbca-admin://app/...`. They do not establish verified HTTPS App Links or domain ownership. No auth token belongs in a URL. Push remains unconfigured; no notification permission/delivery claim is made.

## Signing and artifacts

Release builds no longer fall back to the debug signing key. Supply owner-controlled `DSBCA_ANDROID_KEYSTORE`, `DSBCA_ANDROID_STORE_PASSWORD`, `DSBCA_ANDROID_KEY_ALIAS`, and `DSBCA_ANDROID_KEY_PASSWORD`. No production keystore was generated. Release preflight was executed and deliberately rejected missing signing material; **no release AAB is generated or approved**.

The protected manual Android workflow accepts an existing owner-supplied keystore secret and builds an AAB with an HTTPS API origin after tests. Configure its protected environment and Play App Signing policy with the owner. Do not commit signing files or copy them into build artifacts.

Internal QA debug APKs are built with `scripts/android.ps1 -App user|admin -ApiBaseUrl http://10.0.2.2:8004`. See `phase4/android-*-debug.log` and artifact manifest for actual outcomes/hashes. The project-local Flutter argument wrapper addresses the bundled SDK's encoded DartDefines forwarding without changing the cached SDK. These APKs use emulator loopback; rebuild with a reachable API for devices.

Before store release, approve launcher/adaptive icons and splash artwork (template native artwork remains), verify application-ID ownership/versioning, release signing, real devices, file/media handlers, verified links, notifications, backup/secure-storage behavior and store privacy disclosures. Debug compilation alone does not satisfy these gates.
''')

write('FLUTTER_IOS_RELEASE.md', '''# iOS release preparation

This environment is Windows; Xcode, Apple signing and native iOS compilation/device acceptance are unavailable. **No archive or IPA was generated.**

Existing bundle IDs are preserved (User `com.dsbca.dsbcaUser`), display names are DSBCA/DSBCA Admin, deployment target is iOS 13.0, and plist syntax was parsed. ATS explicitly disallows arbitrary loads. User/Admin custom URL schemes are prepared separately. No camera, microphone, location or push permission is fabricated for inactive integrations.

Video player, file picker, share and secure-storage plugins are present in Flutter dependency locks and have iOS implementations; that is source/dependency inspection, not successful native linking. The owner must verify plugin deployment targets using CocoaPods/Xcode on macOS.

On an authorized macOS machine: install the pinned Flutter toolchain, resolve plugins, run analysis/tests, select the owner's team/bundle IDs, configure signing/provisioning and approved icons/launch screens, add verified associated domains if provided, and activate Firebase/APNs only with credentials/consent. Build an archive/export using the reviewed HTTPS API origin. Test on physical devices before TestFlight/App Store submission.

Review privacy manifests and App Store privacy answers against actual enabled SDK/data flows. Account deletion/export and legal text require an approved operational policy. No privacy-law certification or successful iOS release is claimed.
''')

write('WEB_PERFORMANCE_REPORT.md', f'''# Web and API performance measurements

Environment: Windows, Flutter 3.38.5 / Dart 3.10.4, JavaScript release builds, loopback HTTP, PostgreSQL 17.6 and small fictional QA fixtures. These results do not predict hosted/mobile-network performance.

| Operation | Requests / concurrency | Median ms | p95 ms | Errors |
|---|---:|---:|---:|---:|
{latencies}

Typed chat SSE: first event {performance['typed_chat_stream']['first_event_ms']} ms, first validated answer {performance['typed_chat_stream']['first_validated_answer_ms']} ms, total {performance['typed_chat_stream']['total_ms']} ms. This is a deterministic selected application tool, not live model time-to-first-token. PostgreSQL FTS plus explicit QA synthetic exact vectors took median {performance['retrieval']['median_ms']} ms across five retrievals; no native pgvector/OpenAI latency was measured.

Browser readiness proxy (one sample each): User 3825 ms, Admin 3515 ms, navigation through attachment of Flutter's accessibility activation control. Browser/renderer caches were already warm; each application origin was new. Instrumentation/IPC is included. These are not LCP, cold-cache TTI, mobile-throttled or cross-browser results.

| Build | Main JS bytes | Main JS gzip bytes | All output bytes |
|---|---:|---:|---:|
{assets}

All-output size includes renderer alternatives/assets and is not the initial transfer. Gzip sizes are locally calculated, not a measured Vercel CDN transfer. Tree shaking is enabled. The optional WASM compatibility dry run is disabled because platform plugins are not fully WASM compatible; JavaScript builds are the verified target.

## Measured repair

A fresh Python process with warm filesystem cache imported the API in 4964.34 ms before and 2898.56 ms after lazy imports of optional AI SDK, PDF and S3 dependencies (one paired local sample). Ordinary API startup no longer imports those unused providers. This does not claim a Vercel cold-start result. Runtime/test dependencies were separated and pinned; compatible Linux wheel payload is 58,403,046 bytes compressed and 145,400,973 bytes expanded, excluding platform/runtime build overhead.

Request correlation/duration telemetry, bounded pools/timeouts, no-store private responses and bootstrap no-cache policies were added. Query plans did not justify speculative new indexes on the tiny QA corpus. There is no fabricated pre-change HTTP baseline or claimed statistical improvement from one sample.

Before release, repeat cold/warm browser and API measurements on Vercel/Neon, with representative corpus/company sizes, device/network throttling, CDN headers, real model/storage providers and approved concurrency limits. Full list virtualization, large-account company selection beyond first-page UI, renderer/font transfer, hosted monitoring and native vector plans remain measurement targets.
''')

write('AI_CITATION_QUALITY_REPORT.md', '''# AI evidence and citation quality

The local suite executes real PDF parsing, page previews, chunking, PostgreSQL FTS, controlled vector fixtures, access filters, applicability/version selection, citation storage and streamed delivery. The QA dataset contains approved, rejected and superseded demonstration documents. No live OpenAI generation/embedding run occurred; the user deferred configuration.

## Defect and bounded repair

Finding: a valid substring quote and matching numbers could accompany a reversed or overbroad qualitative claim. Quote existence does not prove entailment. A scanner or second unvalidated model would not establish it either.

The server now permits complete verbatim source excerpts/sentences only: claim text equals its supporting quote, the quote exists in the supplied passage, and clipped sentence prefixes or paraphrases fail closed. Output labels excerpts as source material, not a professional conclusion. Uncited generated limitation prose is not emitted. Citations are server-built with known version/page/passage metadata; model-supplied URLs/foreign IDs and unsupported numbers are rejected. The complete sentence on page two of a cross-page chunk still maps to page two.

This is a deliberate capability restriction, not a semantic verifier. A sentence can still need adjacent exceptions/context, and an approved source can itself be wrong or outdated. The system must not be marketed as independently validating all legal reasoning. A professional synthesis mode requires a separately evaluated entailment/context policy and human source/rule review before activation.

## Executed negatives and controls

Tests cover no sources, inaccessible/foreign sources, historical/current applicability and supersession, invalid pages/quotes, invented citations, reversed negation/conditions, truncated qualifiers, conflicting/unavailable evidence, prompt-injection strings, model/provider outage, cancellation and timeout while preserving questions. Source/history text is labeled untrusted in the provider contract. The generative provider has no network/database tools. Application tool selection is separately constrained to authenticated read-only allowlists; numeric results come from Decimal engines and owner data queries are server-authorized. Write requests have no enabled execution path.

An overall 35s chat await budget bounds provider chains below the prepared function duration. Hidden SDK retries were removed; durable indexing jobs control explicit retry/checkpoint state and user retries retain request-id behavior. Actual configured-provider token billing/timeout/disconnect behavior must still be measured.

Live natural-language selection, professional answer quality, real embedding recall, native pgvector ranking, adversarial PDF/model evaluation and hosted source downloads remain release gates. Typed tools and controlled providers are never presented as proof of live GPT acceptance.
''')

write('CALCULATOR_ACCURACY_REPORT.md', '''# Calculator accuracy and coverage

Fourteen Decimal engines and stored rule-case validation were inspected and re-executed through the backend suite. Formula/rate changes were not made to disguise a failed expected result. Monetary rounding is explicit half-up; schedules and supported input bounds remain documented in CALCULATOR_RULE_ENGINE.md and CALCULATOR_VALIDATION.md.

| Engine | Checked scope / important limit |
|---|---|
| Corporate Tax | Standard taxable-income adjustments, exempt/non-deductible amounts, 75% loss cap, bands and explicit SBR facts/period; special regimes restricted. |
| VAT | Inclusive/exclusive, standard/zero/exempt/out-of-scope, per-line rounding, recoverable input/output/net; classification supplied by user. |
| QFZP | Adjusted denominator/exclusions, lower-of de minimis threshold, separate conditions/missing facts; screening only. |
| Gratuity | Eligible federal foreign full-time framework, actual anniversary fractions, unpaid convention, 21/30-day bands and wage cap; other employment regimes unsupported. |
| TP range | Selected comparable data and inclusive/exclusive percentile interpolation; no automatic comparable selection or arm's-length opinion. |
| TP interest | User-supplied currency/date/benchmark/spread/range and repayment convention; no invented market rate. |
| TP documentation | Revenue/group thresholds as a preliminary obligation screen; not full disclosure/legal classification. |
| Pillar Two | Group scope/two-of-four screen, simplified ETR/loss/top-up and qualified-data safe-harbour screens; not a complete GloBE return. |
| Lease | Fixed-payment PV/amortization, advance/arrears and supplied discount rate; not full variable-payment/modification accounting. |
| Effective interest | Supplied yield/cash flows and reconciliation; not an unsupervised fair-value/yield judgment. |
| NPV | Equal-period discounted cash flows including time zero and zero-rate case. |
| Depreciation | Supported straight-line/reducing methods, residual/useful-life bounds; no automatic policy judgment. |
| Impairment | Simplified VIU/FVLCD and sensitivity with user assumptions; not a full allocation/disclosure opinion. |
| Loan | Annuity/bullet/fixed principal, zero rate, final reconciliation and early-repayment validation. |

The suite contains 29 pure calculator tests plus API/rule/template/tool cases. Eight draft source-backed templates have stored expected cases and date windows. Local QA simulates independent review for testing only. Approved versions are immutable through lifecycle transitions; superseded rules cannot be republished. New professional approval requires a new version and explicit applicability review. Saved inputs/results and rule snapshots reproduce historical runs; foreign histories are inaccessible. Typed chat results match the same engine exactly.

The demonstrated CT case is AED 47,250 for AED 900,000 supplied accounting profit in the supported 2026 standard scenario. This is a test fixture, not advice for a real entity. Production activation requires qualified review of source versions, legal facts, edge conditions and any unsupported scenarios. The existing coverage warnings must remain visible.
''')

write('NOTIFICATION_DELIVERY_REPORT.md', '''# Notification delivery verification

In-app scheduling and delivery were executed using fictional local accounts. The live HTTP acceptance path published an independently reviewed update to a subscriber, ran the durable worker and verified a notification/recipient record. This proves in-app availability, not an email inbox or device receipt.

Database jobs include dedupe/source/user/channel/due state, bounded leases/attempts and delivery logs. Renewal/preferences cancel or replan future jobs; document/obligation ownership and state are rechecked. Regulatory subscription/publication and webinar registration/publication are rechecked before delivery. Source cancellation, retry limits, preference opt-in, device removal, ambiguous delivery and duplicate prevention are covered by API/integration tests. Scheduling uses documented Dubai conventions; uncertain legal calendar cases await confirmation rather than inventing a deadline.

| Channel | Actual status |
|---|---|
| In-app | Executed with real database delivery transaction; read/unread and preferences tested. |
| Resend email | Adapter/state/idempotency tests with controlled responses only. API key and verified sender absent; no real inbox delivery. Provider acceptance is labeled submitted, not delivered. |
| Android push | Server adapter and device-token lifecycle tests only. Firebase client/service credentials and device acceptance absent. |
| iOS push | Unconfigured APNs/Firebase/signing and no physical-device test. |

An ambiguous push result is not blindly replayed. Email retry windows and provider idempotency semantics must be checked against configured service behavior. External channels are off without consent/configuration. A hosted scheduler/worker is not provisioned; CLI QA worker execution is not evidence that production scheduling exists.

Before launch: configure sender/storage/device projects and secret mounts, test lead times/timezones/renewal races with real providers, verify receipts and failure-token removal, and configure operator alerts for blocked/failed/uncertain jobs. Never relabel planned/submitted records as successful device/email delivery.
''')

write('PRODUCTION_OPERATIONS.md', '''# Production operations and privacy runbook

## Deployment and health

Liveness is `/api/v1/health` (phase 4); readiness checks database connectivity and schema 0004. Deployment must not route traffic until readiness and the acceptance matrix succeed. Production/preview environments, required reviewers, secrets, domains and alerts are not provisioned. Record deployment/source identifiers before any release; this checkout has no commits/remote yet.

API telemetry emits correlation ID, route template, method, status, duration and exception type. It deliberately omits prompts, query strings, files, credential headers and exception messages. Flutter handlers emit error type only in release; detailed default diagnostics remain debug-only. Forward this metadata to an approved monitoring service and configure failure/latency/DB/AI/indexing/notification alerts before launch; no remote telemetry/alerting service was silently connected.

AI usage events and durable job/delivery records capture outcomes, latency and retries. Chat has an overall await budget and providers do not perform hidden retries. SQL/connect/lock/pool timeouts are bounded. Do not replay uncertain external sends or non-idempotent writes. Bounded job ticks/leases/checkpoints run via an approved scheduler/executor, not indefinite request workers.

## Recovery and maintenance

Local DB dump/restore was rehearsed; production restore and private-object recovery were not. Set owner-approved RPO/RTO, backup retention, recovery credentials and object versioning. Preserve independent encryption keys separately; losing a key makes protected data unreadable. Practice whole-system restore before activation. Prefer application rollback plus compatible/forward schema fixes over destructive downgrades. Production migration/destructive maintenance needs a reviewed plan and explicit authorization.

Clean expired/revoked sessions, reset tokens and obsolete rate-limit buckets under a reviewed retention job. Existing AI retention CLI is dry-run by default and purges only eligible deleted conversations when explicitly executed. Do not run it against shared data without policy/backup review. Deletion of database references does not establish erasure from object versions/backups.

## QA workflow

`scripts/phase4.ps1 -Task migrate|seed|api|worker|test` uses ignored `.env.phase4.local`; API 8004, previews 5303/5304. Seed is idempotent and loopback/exact-database guarded. Five fictional accounts/roles, companies, people, expiries, learning, source dispositions and rule cases are supplied. Synthetic vector fixtures are explicitly QA-only and excluded from deployment.

From backend, `python -m app.release_qa_reset` is a dry run. Only `--confirm dsbca_phase4_qa` enables deletion, after the exact local database/environment guard. Stop local QA API/worker first, back up if needed, then reseed. The reset preserves migration metadata and does not purge private files. No destructive reset was executed during this release pass.

## Privacy and account handling

Owner-scoped APIs and encrypted sensitive company fields are implemented. Web sessions are intentionally memory-only and require sign-in after a reload; mobile refresh tokens use secure storage. Notification consent/configuration and conversation deletion are implemented. A full account deletion/export API/UI and verified production object lifecycle are not complete.

DSBCA must approve/publish privacy notice, terms, AI limitations, support/contact, retention periods, administrative access policy, rights/export/deletion process and incident response responsibilities. Until automated account handling exists, a reviewed operator process must verify the requester, enumerate ownership/dependencies, revoke sessions, handle legal holds, export/delete authorized records and coordinate object/backups without promising impossible immediate backup erasure. These are policy requirements, not legal certifications. Launch is blocked until an acceptable process and user-facing information are established.
''')

write('RELEASE_BLOCKERS.md', '''# Release blockers — NO GO

The application has substantially improved local verification, but production release is not approved.

| Gate | Evidence / required action |
|---|---|
| Target database | Supplied Neon is schema 0002, no installed pgvector. Provision an isolated branch, reviewed migration to 0004, vector/index tests and restore rehearsal before any authorized production migration. |
| Live research promise | OpenAI/models absent. Typed tools and controlled providers are tested; natural-language selection, real retrieval recall and professional answer quality are not. Output is deliberately restricted to source excerpts pending evaluated reasoning/entailment policy. |
| Private storage and recovery | Hosted private S3 access, signed delivery, backup/version lifecycle and restore not configured/verified. Local private storage is forbidden in production. |
| Hosting and operations | Vercel projects/token/domains, schedulers/executors, protected environments/reviewers and production alerts unavailable. No hosted deployment or CI run is claimed. |
| Credentials and roles | Rotate previously shared credentials, provision least-privilege runtime/migrator access and approve operator access policies. No remote rotation/role changes performed. |
| Mobile release | No owner signing keystore, no AAB; no macOS/Xcode/Apple signing/device tests. Native launcher/splash artwork, verified HTTPS links, push and store disclosures need approval/testing. |
| Privacy and account lifecycle | Publish approved policy/terms/AI limitations and support information; establish usable export/deletion and object/backups handling. No formal legal compliance is claimed. |
| Final acceptance | Repeat complete manual/invalid-input/authorization workflows on staged services, cross-browser/native accessibility/media/download flows, real provider delivery and final visual approval. Manual browser coverage here is a documented subset. |

Email/push are honestly inactive and may remain disabled if the owner explicitly releases without them. Full special legal/IFRS regimes remain visibly unsupported/preliminary. Those bounded optional limitations do not convert the missing core research/hosting/privacy/mobile validation into a release pass.
''')

write('FINAL_RELEASE_REPORT.md', f'''# DSBCA final release-readiness report

21 October 2026. **Recommendation: NO GO for production.** Local hardening/build evidence is substantial; external activation, professional AI quality and release acceptance gates remain open. No production deployment or data modification was performed.

## Delivered repairs

Restricted unsupported AI prose to complete exact source excerpts with server-built citations; added qualitative contradiction/condition/timeout tests; rejected page-level active PDFs and mismatched media types; bounded/logged/redacted API requests with private-response security headers; enforced hosted verified TLS/HTTPS CORS/storage/vector guards; removed hidden provider retries and added a total chat await budget; made reviewed rule lifecycle transitions immutable; eliminated debug-key release signing and added protected CI/schema gates.

User repairs include current owner document/obligation deadlines, profile editing, correct nested navigation selection, empty-topic suppression, compact document filters, removal of unreachable duplicate screens, large-text grid layout and improved muted-text contrast. Admin controls reflect legal workflow states and distinguish structural deletion. Flutter release errors emit redacted type metadata.

## Executed verification

| Suite | Passed | Evidence |
|---|---:|---|
{test_table}
| Total | {total} | Final execution logs |

Both analyzers, web/Android outcomes and artifact hashes are recorded in the manifest/logs. Fifty-four User responsive captures and browser proof are linked in FINAL_TEST_MATRIX.md. Scanners report {known} known runtime dependency advisories and {medium_high} Bandit medium/high findings; {low} reviewed low findings remain. This does not establish absence of vulnerabilities.

The separate QA database migrated to 0004, passed {len(database['orphan_checks'])} FK checks with {sum(database['orphan_checks'].values())} orphans and was restored to a separate database. The actual shared Neon read-only audit found schema {neon.get('schema_revision')} and only {', '.join(neon.get('extensions', []))}; it remains unchanged. Query plans, bounded concurrency measurements and compatible Linux dependency-wheel checks are saved as JSON evidence. Local import time improved from 4964.34 to 2898.56 ms in one paired sample; no hosted cold-start improvement is claimed.

## Build and deployment disposition

- User/Admin JavaScript web release outputs and internal QA debug APKs: see artifact manifest for actual existence, sizes and hashes. Local origins/API defines are QA-only.
- Android release AAB: not generated; missing signing material triggered the intentional preflight guard. No production key was created.
- iOS archive/IPA: not generated; Windows has no Xcode/signing/device environment.
- FastAPI: source/configuration, health/readiness and local HTTP workflows verified. Vercel deployment/bundle/streaming acceptance not executed. Python 3.12/Linux wheels downloaded, but local tests use Windows Python 3.14; hosted CI is still needed.
- CI definitions: verification, opt-in non-fork previews, protected manual production deployment with schema gate, protected owner-signed Android workflow. Configurations parsed locally; no hosted execution or reviewer policy setup is claimed.

## Remaining work and limitations

RELEASE_BLOCKERS.md lists target Neon migration/vector setup, live OpenAI professional evaluation, private storage/recovery, hosting/scheduling/monitoring, credential rotation/least privilege, signed/native releases, privacy/account lifecycle and complete staged manual/cross-browser/device approval. Those are concrete missing acceptance gates; this report does not claim all 180 endpoints or 231 controls were manually exercised.

Evidence index: FINAL_IMPLEMENTATION_AUDIT.md, FINAL_TEST_MATRIX.md, SECURITY_AUDIT.md, NEON_PRODUCTION_READINESS.md, VERCEL_PRODUCTION_DEPLOYMENT.md, FLUTTER_ANDROID_RELEASE.md, FLUTTER_IOS_RELEASE.md, WEB_PERFORMANCE_REPORT.md, AI_CITATION_QUALITY_REPORT.md, CALCULATOR_ACCURACY_REPORT.md, NOTIFICATION_DELIVERY_REPORT.md and PRODUCTION_OPERATIONS.md.
''')
print('Release evidence reports assembled. Current executed total:', total)
