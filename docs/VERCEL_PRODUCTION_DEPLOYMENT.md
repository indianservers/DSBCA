# Vercel deployment readiness

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
