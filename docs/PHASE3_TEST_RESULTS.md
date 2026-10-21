# Phase 3 verification and acceptance report

Verified locally on 21 October 2026. This report distinguishes executed checks from integrations that remain inactive. No production deployment or shared Neon migration was performed.

## Automated results

| Suite | Passed | Coverage |
|---|---:|---|
| Backend | 76 | 34 existing Phase 1/2 regressions, 29 calculator tests, 13 professional API/integration tests |
| Flutter User | 184 | Existing flows plus 14 calculator forms, academy details, compliance, preferences and saving |
| Flutter Admin | 109 | Existing administration/knowledge plus seven professional workspaces |
| Shared API client | 2 | Authentication refresh/retry regression |
| **Total** | **371** | All passed |

Both Flutter analyzers report no issues. Both Flutter Web JavaScript release builds succeeded with `--no-wasm-dry-run`. Both Android debug builds succeeded using the repository-local DartDefines compatibility wrapper; no physical-device or iOS build acceptance is claimed. Android User minimum API is 24 for video playback. Debug API origins use Android emulator loopback; rebuild with a reachable origin for physical devices.

Responsive widget tests cover 360, 390, 430, 768, 1024 and 1440 logical pixels. They caught mobile calculator dropdown and Admin user-footer overflows, which were corrected. Final Admin desktop workspaces use tables; narrow screens use cards. These tests verify rendering and API interactions with fixtures, not real provider delivery.

Logs: `phase3-backend-final.log`, `phase3-user-final.log`, `phase3-admin-final.log`, `phase3-client-final.log`, both `phase3-*-analysis.log`, `phase3-*-web.log` and `phase3-*-android.log` in this directory.

## Numerical, authorization and workflow checks

Calculator tests cover CT zero/bands/loss/SBR eligibility, VAT classifications/inclusive extraction/line rounding, QFZP adjusted-denominator boundaries, gratuity anniversary/leap-year conventions and cap, TP quartiles, documentation thresholds, Pillar Two scope/loss/safe-harbour screening, zero-rate and reconciliation cases for financial schedules, and invalid inputs. All eight source-backed reference templates validate against their stored expected cases before independent publication. Local seed approval is a fixture simulation, not a professional sign-off for production law.

API checks verify rule validation/second-review/publication, immutable saved inputs/results, owner-only histories and companies, encrypted private fields, private-asset ownership, scheduled parent publication access, bookmarks/progress/path completion, source review/subscriptions, unsubscribe-before-delivery cancellation, calendar rules requiring confirmed facts, webinar capacity/idempotency/cancellation/private joining/UTC calendar, device-token removal, notification opt-in/retry/ambiguous delivery handling, and deterministic typed chat tools. General administrators cannot use their role to read another owner's company attachments.

The durable worker actually created in-app notification and recipient records in its delivery transaction. This establishes in-app availability only. Mock email/push adapters exercise state transitions; external email inbox/device delivery was not tested.

## Executed acceptance workflows

The reproducible local-only HTTP acceptance script is `scripts/phase3_acceptance.py`; its output is `docs/phase3/acceptance-http.json`. It guards the development database name and uses ignored local fixture accounts. It never prints credentials.

| Workflow | Executed evidence and limit |
|---|---|
| A — Learning | Browser searched/filtered Corporate Tax, played the configured official Flutter demonstration clip to 4s/4s, then resumed at 4s after signing in again. The reader opened the related chapter from the path, invoked its authorized PDF download, marked it completed and saw the path reach 100%. API logs confirm the private download returned 200; the downloaded PDF native viewer was not inspected. The clip is labeled a player demonstration, not tax teaching. |
| B — Toolkit | Browser calculated AED 47,250 from AED 900,000 accounting profit for calendar 2026 under the supported standard CT rule, expanded formula/references, saved and reopened account history. HTTP repeated calculate/save/reopen successfully. |
| C — Company compliance | Live HTTP created a fictional company/licence, scheduled owner reminders, renewed expiry and verified renewal history and future planning. API tests also execute due reminders and verify deduplication/cancellation. |
| D — Regulatory update | Live HTTP author created a source-linked draft, another local reviewer approved/published, the real worker delivered an in-app record to the subscribed reader and the published official source URL was returned. No external broadcast was sent. |
| E — Chat/calculator | Live existing chat endpoint executed an explicitly typed calculator tool and returned exactly AED 47,250 plus populated-calculator route/inputs. **Natural-language OpenAI tool selection is pending credentials.** |
| F — Chat/compliance | Live chat executed an explicitly typed owner-scoped reminder tool, returned the created licence and reminder deep link. Cross-owner access is denied by tests. **Natural-language OpenAI selection remains pending.** |
| G — Webinar | Live HTTP scheduled a fictional event, registered the reader, scheduled reminders, returned private joining metadata only after registration and exported UTC ICS without a private join URL. Capacity/duplicate/cancellation tests passed. The room is an explicit example.com fixture; no real webinar was attended. |

## Database and deployment boundaries

Migration 0004 succeeded on the isolated local Phase 3 PostgreSQL database. A `0004 → 0003 → 0004` cycle succeeded on disposable `dsbca_test`; the Phase 2 full-text index remained present. Local PostgreSQL has no pgvector extension, so Phase 2's explicit exact-vector development mode remains selected. The preserved Phase 2 database and the shared Neon database were not migrated or reset. A separate Neon development branch is still unavailable; Neon-native vector/migration acceptance must be repeated there.

Both web applications and the FastAPI API retain the prepared three-project Vercel architecture. No Vercel token/projects are configured, so deployment and hosted scheduling were not performed. The final attempt to restart the preview API and an alternative instance launch were blocked by automatic approval review, which supplied no detailed reason. The existing API on port 8003 remains running; restart it manually before assessing the latest server-side Admin rule-category filter. Final source was tested independently of that preview process.

## Pending activation and documented limits

- OpenAI credentials/models and live natural-language/PDF-citation acceptance remain deferred by the user. Typed application tools and deterministic chat rendering run locally without a model.
- Private S3-compatible storage, Resend email, Firebase client/server/APNs configuration and a hosted scheduler are unconfigured. Adapters remain inactive/blocked honestly; no real email/push delivery claim is made.
- Learning/company private uploads are bounded at 3 MB. Larger assets require the documented direct-upload extension; videos stream from configured approved HTTPS sources.
- QFZP, TP documentation and Pillar Two are explicitly bounded screenings. Full special CT regimes, legal classifications, treaty conclusions, full GloBE calculations and uncertain calendar exceptions require reviewed professional inputs and supported rule versions. No unsupported liability is invented.
- Rule templates have explicit dates/coverage and official links; production requires qualified independent review. No training library of substantive professional videos was fabricated.
- Release signing, physical devices, iOS, provider receipts, production retention/key rotation, production security/performance and final release QA remain Phase 4 work. Phase 4 implementation has not started.


Browser evidence: [calculation/formula/history check](phase3/calculator-browser.png), [completed learning path](phase3/learning-complete-browser.png), and [Admin workspace](phase3/admin-browser.png). Final preview build assets include cache-busting URLs in ignored build output so an earlier browser-cached bundle does not mask the new UI; repeat builds regenerate those artifacts. Local credentials and environment files are ignored by Git. A scan of non-ignored source/document/log candidates found no configured database/JWT secrets.
