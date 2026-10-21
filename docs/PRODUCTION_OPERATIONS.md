# Production operations and privacy runbook

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
