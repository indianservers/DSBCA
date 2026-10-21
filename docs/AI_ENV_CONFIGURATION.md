# Phase 2 environment configuration

Copy the server-only `backend/.env.example` into an ignored local environment or configure deployment secrets. Do not paste secrets into source, logs, documentation or Flutter builds. The existing Neon `.env` was preserved. Isolated Phase 2 development uses ignored `backend/.env.phase2.local` through `scripts/phase2.ps1`.

| Setting | Meaning |
|---|---|
| DATABASE_URL / DATABASE_URL_UNPOOLED | TLS pooled API / direct migration URLs on a separate Neon development branch |
| OPENAI_API_KEY | Backend-only provider credential; currently absent |
| AI_CHAT_MODEL / AI_FAST_MODEL | Account-supported chat IDs; optional fast model has no automatic routing |
| AI_EMBEDDING_MODEL | Compatible embedding model accepting 512 dimensions |
| AI_REQUEST_TIMEOUT / AI_MAX_OUTPUT_TOKENS | Timeout and bounded output defaults |
| AI_RETRIEVAL_TOP_K / AI_MIN_EVIDENCE_SCORE / AI_HISTORY_WINDOW | Retrieval/history defaults; audited settings override |
| AI_DAILY_REQUESTS / AI_DAILY_TOKENS | Per-user consumption limits, UTC window |
| AI_EMBEDDING_BATCH_SIZE / AI_MAX_CONTEXT_CHARS | Bounded indexing/context work |
| AI_RETENTION_DAYS | Soft-deleted conversation retention, default 365 |
| AI_VECTOR_BACKEND | pgvector production; exact explicitly for isolated local JSON vectors |
| PDF_MAX_BYTES / PDF_MAX_PAGES / PDF_DAILY_UPLOADS | Intake/processing limits |
| PDF_STORAGE_BACKEND | disabled, local development only, or s3 |
| PDF_LOCAL_ROOT | Private local directory outside web roots; forbidden in production |
| S3_BUCKET / S3_ENDPOINT_URL / S3_REGION | Private S3-compatible destination |
| AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY | Restricted server-only storage identity |
| INDEXING_WORKER_SECRET / CRON_SECRET | Independent high-entropy bearer secret for worker tick |
| INDEXING_LEASE_SECONDS / INDEXING_MAX_ATTEMPTS / INDEXING_MAX_CONCURRENCY | Lease/retry/concurrency bounds |

Assistant configuration versions additionally store temperature/support flag, allowed subjects, mandatory citations, feedback, optional model IDs and optional per-million token prices. No price is invented. A configured model name alone does not enable OpenAI. Reranking and official verification are unavailable and rejected/disabled. No OCR provider is implemented; scanned/low-text documents are flagged for remediation.

Use a private bucket with public access blocked, AES256 encryption, conditional immutable puts, presigned POST/GET support, and restricted CORS allowing only the deployed frontends' direct upload origins. Some S3-compatible vendors differ in feature support; verify those operations against the selected vendor before activation.

The API connection pool is capped at 2 with zero overflow, 8-second connection/pool timeout, 15-second statement timeout and 5-second lock timeout. Migrations use the direct endpoint and NullPool. Set frontend `API_BASE_URL` to the public backend origin only; it contains no secret.
