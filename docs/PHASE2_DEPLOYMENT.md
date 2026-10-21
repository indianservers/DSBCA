# Phase 2 deployment preparation

Deployment was not performed: Vercel projects/login, a separate Neon development branch, OpenAI and private object-storage credentials are absent. The user deferred OpenAI configuration. Existing shared Neon Phase 1 data/schema remains unchanged by Phase 2 migrations.

## Activation sequence

1. Provision an explicit Neon development branch, configure pooled/direct TLS URLs, retain Phase 1 backups and review additive migration 0003. Use `AI_VECTOR_BACKEND=pgvector` before migration. Run Alembic upgrade/check and verify vector/HNSW/GIN in that branch. Do not switch a local exact JSON schema to pgvector by changing an environment flag.
2. Configure a private S3-compatible bucket and restricted credentials. Verify AES256, conditional put, exact-size presigned POST, GET, CORS and short-lived downloads against the chosen vendor. Apply cleanup only to abandoned staging objects; retain referenced originals/previews.
3. Configure backend-only OpenAI key and account-approved chat/embedding model IDs. Test a small 512-dimensional embedding batch and structured Responses request. Review privacy/retention and pricing with the account owner. Do not silently create a paid service.
4. Deploy the existing FastAPI Vercel project (`backend/vercel.json`, framework fastapi). Check installed Python/PDF native wheel support, cold-start/package size, streaming proxy behavior, function memory and duration in the actual project. The default code uses local dependencies but hosted execution has not been verified.
5. Schedule a runner calling `GET /api/v1/internal/ai/jobs/tick` with `Authorization: Bearer <INDEXING_WORKER_SECRET or CRON_SECRET>`. Each call processes one bounded checkpoint. Choose frequency/concurrency for the library and plan; a one-page or batch step must fit function duration. An explicit external long-running worker can use `python -m app.ai.worker --max-steps 1000` in repeated bounded runs. PostgreSQL persists the queue, not the process. No scheduler is activated by this repository.
6. Build/deploy User and Admin projects with public API_BASE_URL, then set exact CORS origins on API and storage. All provider/storage/worker/database secrets belong only to the API/worker projects.
7. Upload a demonstration PDF, complete extraction/embeddings, inspect pages, approve, opt into demonstrations in Discuss, ask a covered question and confirm the exact physical page and source version. Repeat with a real approved source, history, failure/retry, cancellation and cross-tenant tests. Only then accept Phase 2 and proceed to Phase 3.

## Queue/workflow choice and cost

A PostgreSQL leased queue plus authenticated scheduler was chosen to reuse the existing database and avoid an unconfigured workflow-service dependency. It supplies durable checkpoints and explicit recovery; scheduling and liveness monitoring are deployment responsibilities. Vercel Cron or an external worker are possible runners, but neither has been activated. Additional costs can include function/cron execution, storage requests/egress, database vector storage/compute and OpenAI tokens. Paid plan or workflow provisioning requires the owner's deployment choice; no subscription was created.

Vercel documentation consulted for production validation: [function limits](https://vercel.com/docs/functions/limitations), [cron jobs](https://vercel.com/docs/cron-jobs). Multipart is intentionally capped at 3 MB; large PDFs bypass the API body through authorized direct uploads. Confirm current project limits when deploying. One checkpoint still reads a bounded original PDF; batching does not guarantee that every 30 MB/200-page document fits a specific function plan. Use an external worker if it does not.

## Local operation

From repository root: `scripts/phase2.ps1 -Task migrate`, `-Task seed`, `-Task worker`, `-Task api`, `-Task build`. API uses port 8002; isolated preview ports are 5193 User and 5194 Admin. Original Phase 1 ports/configurations are preserved. Test using a disposable database explicitly named dsbca_test; never point tests at shared Neon. iOS builds require macOS and signing and are not verified here.

Rollback: disable the tick scheduler and AI entry points first. Keep originals/history for review. Migration downgrade removes Phase 2 data and is destructive; use it only in an approved disposable branch. No automatic production rollback or purge is performed.
