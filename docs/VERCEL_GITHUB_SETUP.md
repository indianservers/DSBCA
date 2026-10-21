# Vercel GitHub import

Import indianservers/DSBCA three times, using main. Project names below are proposed; actual domains must be taken from Vercel.

| Project | Root directory | Framework | Build / output |
|---|---|---|---|
| dsbca-api | backend | FastAPI | Automatic Python build |
| dsbca-user | apps/dsbca_user | Other | Repository vercel.json / build/web |
| dsbca-admin | apps/dsbca_admin | Other | Repository vercel.json / build/web |

For both Flutter projects, enable **Include source files outside of the Root Directory in the Build Step**, because shared packages and the pinned Flutter build script live outside each app directory. Set API_BASE_URL to the actual HTTPS API origin, without /api/v1; the client appends that prefix. Do not upload localhost QA archives.

Backend variables: APP_ENV=staging for initial acceptance, DATABASE_URL with sslmode=verify-full, JWT_SECRET_KEY (independent random secret, >=32 characters), DATA_ENCRYPTION_KEY (independent URL-safe base64 encoding of 32 random bytes), CORS_ALLOWED_ORIGINS (JSON array of exact User/Admin HTTPS origins), AI_VECTOR_BACKEND=pgvector, PDF_STORAGE_BACKEND=disabled until private S3 is configured. Store secrets only in encrypted Vercel environment settings. Leave OpenAI settings absent until activation; unsupported features remain unavailable.

The existing Neon database is at 0002. Back up and explicitly review migration to 0004 with pgvector using a direct verified-TLS connection before serving traffic. Do not run Alembic or seed demo accounts automatically during builds. No hosted administrator account exists unless explicitly provisioned.

Deploy API, verify /api/v1/health and /api/v1/ready (0004), then deploy both Flutter projects against its HTTPS origin. Confirm CORS, login, refresh, owner isolation and deep links on hosted URLs. A successful build alone is not production approval; prior RELEASE_BLOCKERS.md still applies. Vercel account permissions and GitHub application access may require the owner to approve them.
