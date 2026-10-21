# Three independent Vercel projects

Create **dsbca-user**, **dsbca-admin** and **dsbca-api**. No deployment has been executed in this session. No production URLs are assumed.

## API

Set project Root Directory to `dsbca/backend` (or `backend` if this directory is the repository root), Framework Preset FastAPI. `vercel.json` selects fastapi, and `pyproject.toml` declares `app.main:app`. `index.py` also exports the ASGI app for standard root discovery. Install dependencies from requirements.txt. No legacy `@vercel/python` builds/rewrites are used.

Configure DATABASE_URL (Neon pooler, sslmode=require), DATABASE_URL_UNPOOLED (Neon direct endpoint), JWT_SECRET_KEY, JWT_ALGORITHM=HS256, ACCESS_TOKEN_EXPIRE_MINUTES=15, REFRESH_TOKEN_EXPIRE_DAYS=30, CORS_ALLOWED_ORIGINS (JSON list of the actual User/Admin origins) and APP_ENV=production. Optional RESET_DELIVERY_URL/TOKEN configure email reset delivery. Never place these values in Flutter config.

Before release, run Alembic explicitly against the intended Neon branch from a trusted operator environment. Never run migration as a request or application startup side effect. The supplied development database already has migrations through 0002 and labeled demonstration accounts/content. Use a clean production branch and explicitly provision production operators; do not silently reuse development operator accounts. Validate branch connectivity and seed only intended content.

## Web apps

The workflow installs pinned Flutter 3.38.5, runs analysis/tests, builds each app, copies its SPA config into build/web and deploys that static directory to the corresponding Vercel project. Flutter SDK is not required in Vercel builds. Configure static projects as Other; the deployed artifact directory is the entire build/web content.

`API_BASE_URL` is a GitHub repository variable containing the API origin without trailing slash. Add GitHub Actions secrets VERCEL_TOKEN, VERCEL_ORG_ID, VERCEL_USER_PROJECT_ID, VERCEL_ADMIN_PROJECT_ID and VERCEL_API_PROJECT_ID. Run `.github/workflows/deploy.yml` manually after verifying migrations. The workflow deploys three separate projects and does not run database migrations.

The web configs serve real files before SPA fallback and set security headers. Do not cache index.html or Flutter bootstrap across releases. Verify direct navigation to `/home` (hash URL routing is used by default), static assets and browser navigation. If enabling clean path URLs later, the same fallback supports them.

## Production verification

Check API `/api/v1/health` and `/api/v1/ready`, `/openapi.json`, actual allowed-origin CORS responses, registration/login/refresh/logout, content publication between applications, ownership denial across accounts and reminder persistence on the Neon branch. Confirm both web artifacts use the deployed API origin. Do not report live deployment until these checks pass. Restrict preview origins rather than allowing wildcard credential traffic.

Sources checked during implementation: [Vercel FastAPI](https://vercel.com/docs/frameworks/backend/fastapi), [FastAPI deployment guide](https://vercel.com/kb/guide/ship-a-fastapi-app-on-vercel), [static project configuration](https://vercel.com/docs/project-configuration/vercel-json).
