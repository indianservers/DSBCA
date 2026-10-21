# PDF ingestion pipeline

## Intake and private objects

Admin multipart intake is capped at 3 MB to stay below a serverless request ceiling. Larger documents use backend-authorized S3 presigned POST with exact size, type and staging key. The configured upper bound is 30 MB and 200 pages. Intake checks MIME/PDF header, encryption and root active actions. A SHA-256 hash and duplicate checks precede indexing; all content is untrusted.

Direct uploads land under `intake/`; the worker verifies bytes/hash and writes a separate immutable `originals/{version}/{hash}.pdf` using conditional creation. Replaying a still-valid staging upload cannot overwrite an approved original. S3 AES256 and private bucket permissions are required. No original PDF bytes are stored in PostgreSQL.

## Durable processing

`python -m app.ai.worker --max-steps 1000` drives bounded persisted checkpoints. Alternatively an authenticated `GET /api/v1/internal/ai/jobs/tick` executes one checkpoint per invocation. No FastAPI BackgroundTasks or in-memory queue is used.

PostgreSQL advisory locking enforces the worker concurrency limit; `FOR UPDATE SKIP LOCKED`, random lease fencing and expiry protect claims. Each successful step commits progress. Failure records a sanitized code and preserves resumable progress; explicit retry is subject to the attempt limit. Stable page/chunk uniqueness avoids duplicate work. A stale lease cannot publish an index.

Stages: validate/hash -> one page per tick -> structural chunks -> bounded embedding batch -> completeness validation. Text comes from pdfplumber, printed labels from pypdf and page previews from PDFium. Tables are retained as structured cells alongside page text. The worker renders a single page, not an entire mobile PDF. Chunks follow article/section/heading boundaries with page ranges. Oversized sections fail for review instead of arbitrary splitting.

Missing/very short page text produces `OCR_REQUIRED_PAGE_n`. No OCR provider is configured; such versions remain failed and unapprovable. Extraction heuristics do not replace expert review, particularly for complex tables, columns, Arabic text or numerical quality. PDFs are not an execution environment or a malware scanning service.

Per-user daily upload/token quotas, small batches, bounded provider timeouts and retry limits control consumption. Embedding tokens are reserved atomically under the user lock before network calls; failed calls keep conservative reservations for that daily window. Ready status requires all pages, chunks and embeddings. Approval remains separate and explicit.

## Retention

Originals and citation-bearing versions are retained, including after archive/supersession. Configure bucket lifecycle to remove abandoned `intake/` objects after at least one day; do not apply expiry to referenced `originals/` or `previews/`. No automatic original deletion is performed. Conversation deletion hides history immediately; `python -m app.ai.retention` previews expired soft deletions and `--execute` purges their messages/evidence/feedback after configured retention. Review backup/legal hold requirements before operational purge.
