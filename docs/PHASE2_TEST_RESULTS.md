# Phase 2 verification — 21 October 2026

**Status: local implementation verified; live provider/hosted acceptance pending.** OpenAI setup was explicitly deferred by the user. No live AI response, live private S3 operation, native pgvector execution or Vercel deployment is represented as passing.

## Recorded checks

| Check | Result / scope |
|---|---|
| Backend PostgreSQL | 34 tests passed on disposable local PostgreSQL 17 `dsbca_test`, explicit exact vectors and real PostgreSQL FTS |
| Backend SQLite portability | 33 tests passed before the final exact-page test was added; PostgreSQL remains the authoritative final run |
| User Flutter | 63 tests passed, including all Phase 1 tests and seven new research/source/stream/cancel tests |
| Admin Flutter | 61 tests passed, including all Phase 1 tests and six new four-tab/upload responsive tests |
| Shared API client | 2 authentication/refresh/logout tests passed |
| Flutter analysis | User and Admin: no issues found |
| Release Web | Both applications built with public API origin `http://localhost:8002` |
| Android debug | User and Admin built; platform build only, no physical-device acceptance claimed |
| iOS | Not built: macOS/signing unavailable |
| Migration | Additive 0003 applied locally; disposable test downgrade to 0002 and upgrade to 0003 passed |
| Production vector DDL | Compiled offline and checked vector extension, HNSW cosine and GIN FTS statements; not executed on Neon |
| Shared Neon | Connectivity/TLS and available vector extension inspected; no Phase 2 migration applied |
| Live local API | Health 200 (phase 2); ready 200 (revision 0003); both local accounts authenticated; history and existing companies available |
| Local demonstration indexing | Three private labeled PDFs extracted/chunked; jobs safely stopped at embeddings with PROVIDER_NOT_CONFIGURED, pending approval |
| PDF visual QA | All six pages rendered and visually inspected; every page contains exact demonstration disclaimer |
| Secret handling | Existing environment and local access files ignored; configured-secret scan passed across exportable source |

Final automated suites total **160 passing tests** across PostgreSQL backend, User, Admin and shared API client. SQLite runs are supplementary, not added to this total. Logs are ignored local verification artifacts in `docs/phase2-*.log`.

## What the backend integration tests actually verify

Real PDF bytes are uploaded to the API and persisted in private local storage. Actual extraction, page labels, page PNG generation, meaningful chunks, PostgreSQL persistence, FTS, job checkpoints, approvals, REST/SSE, evidence snapshots and source/download access are exercised. Embedding vectors and generated answers are **controlled test fixtures**. The official SDK call test mocks the transport and asserts strict structured Responses parameters, store=False and absence of model tools. This is integration coverage of our application, not evidence of live model quality.

Covered cases include immutable replacement, content hash corruption, malformed/empty inputs, OCR-required failure, incomplete approval denial, provider failure and retry, organization/private isolation before generation, cross-user history/feedback/source denial, malicious PDF instructions/forged citation IDs, historical period/supersession, daily quota, explicit retention, request idempotency, persistent cancellation and expired lease fencing. S3 signing policies and conditional immutable puts are checked with the real signing SDK and a stubbed object request, with no cloud account contact. Embedding model identity is pinned across batches.

The exact-page test constructs an article spanning physical pages 1–2, returns a supporting quote found only on page 2, and asserts the saved citation resolves physical page 2, printed label 2 and matched_pages=[2]. This catches the error of always linking the first page of a multi-page chunk.

## Acceptance matrix

| Requested outcome | Verified state |
|---|---|
| Independent PDF repository and source administration | Real local API/storage/DB verified; private hosted storage activation pending |
| Extraction/index/approval/answer/exact citation workflow | Full controlled-provider integration test passes; actual OpenAI end-to-end run pending |
| Hybrid search and metadata/applicability filtering | PostgreSQL FTS plus exact controlled vectors tested; native pgvector and live semantic quality pending |
| Citation identifiers, quotes and source pages | Validated server-side; forged IDs rejected; cross-page exact-page test passes |
| Pending/unapproved/private isolation | Covered by integration tests |
| Prompt injection | Adversarial fixtures and forbidden citation/scope checks pass; live model adversarial evaluation pending |
| Durable processing and recovery | Persisted checkpoints, lease expiry, retry and model pinning tested locally; hosted runner not scheduled |
| Responsive User research experience | 360, 390, 430, 768, 1024 and 1440 px tested; Markdown tables/source viewer/cancel included |
| Responsive Admin knowledge experience | Same six widths; all four tabs plus upload dialog tested |
| Existing foundation | All original backend/User/Admin/shared-client tests remain passing |
| Production deployment | Prepared and documented; not performed |

## Visual comparison and artifacts

The existing Discuss reference remains the design basis: serif title, green evidence status, horizontal subject chips, violet user bubble, white source-backed response, lavender background and rounded composer. The wider workspace adds history and sources at adaptive breakpoints. No legal answer from the mockup was copied into production responses. The header accurately states Approved PDFs and mandatory citations instead of claiming independently verified law.

- [Mobile research fixture](phase2/research-390.png) and [desktop research fixture](phase2/research-1440.png): controlled UI demonstration, explicitly labeled as not AI output.
- [Browser research preview](phase2/research-browser.png): actual built web app, signed-out state.
- [Six-page demo contact sheet](phase2/pdf-previews/contact-sheet.png).
- [Offline production migration SQL](phase2/pgvector-migration.sql).

The local Admin browser authenticated and displayed all three real seeded documents with failed embedding/pending approval states. Browser screenshot capture for that tab was unavailable; Admin layout verification uses responsive widget tests and the visible accessibility state. Final human visual approval and device keyboard/browser PDF viewer behavior remain release checks.

## Known limits and next activation

Configure an OpenAI key and supported chat/512-dimensional embedding models, a private S3-compatible bucket, a separate Neon development branch and an authenticated scheduler/worker. Configure the three Vercel projects, run the production migration only on the reviewed development branch, then verify the real upload-to-answer-to-page workflow and retrieval quality on approved professional material. Optional OCR, reranking and official-web verification remain disabled. Local exact-vector retrieval has a 1,000-candidate bound. Estimated provider cost stays unavailable until explicit prices are configured. Citation validation verifies identity/quotation provenance, not complete legal entailment.

Phase 2 is **not declared complete** under the prompt's live acceptance criterion. Phase 3 feature work has not started.
