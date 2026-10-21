# Live Vercel deployment — 21 October 2026

Three GitHub-connected projects in the AIMERS Vercel account now deploy from indianservers/DSBCA, main:

| Service | URL | Project / root |
|---|---|---|
| Backend | https://dsbca.vercel.app/docs | dsbca / backend |
| User | https://dsbca-user.vercel.app | dsbca-user / apps/dsbca_user |
| Admin | https://dsbca-admin.vercel.app | dsbca-admin / apps/dsbca_admin |

Backend health and readiness returned 200 and schema 0004. Exact User/Admin CORS preflights passed, an untrusted origin was rejected, unauthenticated Admin access returned 401, and API security headers were checked. The User browser loaded the catalogue and returned NPV 41.32 for rate 0.1 and cash flows [-1000,600,600]. The Admin browser displayed its guarded login form. No authenticated hosted administrator CRUD or real provider acceptance is claimed. Evidence: phase4/vercel-http-checks.json, vercel-user-npv.png and vercel-admin-login.png.

The owner approved saving the Neon connection and newly generated JWT/encryption secrets in encrypted Vercel project variables. Runtime APP_ENV remains staging during acceptance, even though main uses Vercel's Production deployment target. Secrets are not committed. Local recovery settings are in ignored backend/.env.vercel.local. Those keys must be retained securely; changing the data encryption key without a migration can make encrypted records unreadable. Preview branches need their own explicitly configured isolated backend environment; production secrets were not copied to arbitrary preview branches.

The owner approved backing up and upgrading the existing Neon database. A PostgreSQL 18 custom archive was created in ignored .qa-backups/neon-before-vercel-0002.dump and its catalogue checked. Restore was not exercised for this remote snapshot. Additive Alembic migrations 0002 → 0004 completed, pgvector 0.8.6 is installed, and existing user/company counts were preserved. No demo data was inserted. See phase4/neon-deployment-migration.json.

Deployment repairs: Git imports now build Flutter 3.38.5 using scripts/vercel-flutter-build.sh and the public HTTPS API origin. Static CLI workflows retain their prebuilt configuration. Vercel Python packaging now has all 58 pinned runtime dependencies explicitly declared in pyproject.toml. Verified PostgreSQL TLS uses the pinned certifi CA bundle. Query timeouts use SET LOCAL on each transaction because Neon's transaction pooler rejects startup options. Local backend regression: 100 passed. Hosted GitHub verification passed after fixing Python test invocation, a corrupt PNG fixture and an invalid workflow context; final source run: https://github.com/indianservers/DSBCA/actions/runs/39639600532 .

The earlier final release reports are the pre-deployment audit snapshot. This record supersedes their hosting/Neon activation status. OpenAI, private object storage, external email/push, durable hosted execution, signed mobile releases and full staged/professional/privacy acceptance remain open. The deployment is available for acceptance; it does not establish full production readiness. Existing administrator credentials are required; no new privileged account was created.
