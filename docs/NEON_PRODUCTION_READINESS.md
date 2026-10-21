# Neon production readiness

## Actual databases

- Shared Neon: read-only metadata connection succeeded; pooled hostname confirmed. Revision is **0002** and installed extensions are **plpgsql**. It is not the Phase 4 target schema, and pgvector is not installed. There were no migrations, role changes or application-table writes. One connect-plus-metadata sample took 6823.5 ms, including possible compute wake-up; it is not a throughput benchmark.
- Local QA: `dsbca_phase4_qa`, schema 0004, 61 tables, 74 FK checks and 0 orphans. Data is fictional; the dataset contains different roles, companies, expiries and document approval states.
- Local recovery: a custom-format dump was restored into `dsbca_phase4_restore`; schema 0004, 5 users and 5 companies were verified. The dump is ignored. Private object-store recovery was not tested by this DB rehearsal.

## Connection and query review

Request engine pool is 2 connections, overflow 0, pool wait 8s, recycle 240s, pre-ping enabled, connect timeout 8s, statement timeout 15s and lock timeout 5s. Sessions commit/rollback/close through the dependency; requests never create schema. Hosted URLs require verify-full TLS. Use Neon's pooled URL for traffic and the direct URL for reviewed migrations. Do not replay arbitrary failed writes automatically. Fleet concurrency times per-instance pool size must fit the chosen Neon connection budget.

EXPLAIN ANALYZE/BUFFERS was executed only on local QA for scheduler selection, conversation history, company expiries, admin pagination and FTS. Plans and actual timings are in `phase4/performance.json`. The small corpus did not justify speculative indexes; none were added merely to force an index plan. Existing ownership/date/status/foreign-key and FTS indexes remain. Native HNSW/pgvector plans and representative production-volume query plans are not verified.

## Required migration and recovery procedure

Provision a separate Neon development branch and least-privilege runtime/migrator roles. Back up the existing schema/data and keys; verify restore and private-object versions. Install/configure pgvector through reviewed migrations, run 0003/0004 on that branch, then execute all acceptance/security/retrieval tests against it. Review additive schema and any rollback data loss before authorizing production migration. No production downgrade/reset is permitted as a casual rollback.

Prefer application rollback to a compatible deployment; forward-fix schema problems. A rollback involving dropped new tables requires an explicit backup/restore and data-loss plan. Set recovery objectives, retention and restore ownership with DSBCA; none are invented here. Back up encryption keys separately and test access before rotation. Shared Neon remains a release blocker until this procedure is executed and reviewed.
