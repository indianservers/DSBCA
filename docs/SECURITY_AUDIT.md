# Security audit

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

The first pip-audit reported vulnerable cryptography 47.0.0 and pip 25.3. They were upgraded to cryptography 50.0.2 and pip 26.2.2. The final pinned-runtime scan reports **0 known advisories**. Scanner databases and execution environment limit what this establishes. Bandit reports **0 medium/high and 11 low findings**; low findings concern constant protocol/rule labels and assertions in explicit development checks, reviewed as such. Ruff's fatal/syntax/undefined-name selection is recorded in `python-static-final.json`. This is not exhaustive type or semantic analysis.

Runtime dependencies are pinned separately from development tools, with a Linux CPython 3.12 dependency closure including psycopg-binary. Compatible wheels were downloaded successfully; actual Linux/Vercel execution remains pending. Optional provider/PDF/S3 imports are lazy. CI repeats tests and scanning; hosted CI has not run because this checkout has no commits/remote configured.

## Secrets and residual risks

Local .env files, QA accounts, private storage, backups and keystores are ignored. The source/log scan does not print values. No commit history exists here, so historical remote exposure cannot be cleared by a local scan. Previously shared Neon credentials must be rotated before production, and the owner-like runtime account replaced by least-privilege application/migration roles. No rotation or role change was made on shared Neon.

Production monitoring, object access policy/restore, account export/deletion handling, administrator access policy, signing/links/push, legal source approval and live model quality remain unverified. Full adversarial/hosted/device testing is not complete. See RELEASE_BLOCKERS.md; production release is not approved.
