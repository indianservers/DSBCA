# Architecture

`apps/dsbca_user` and `apps/dsbca_admin` are independent Android/iOS/web applications. Riverpod provides the API/session state, GoRouter owns browser-aware routing, and Dio handles HTTP with serialized refresh rotation. The User app uses an indexed stateful shell for five persistent destinations. Secondary resource routes include profile, notifications, reminders and content details. Admin uses independent authentication and role guards.

Shared packages: `design_system` (tokens, bundled OFL fonts and reusable widgets), `api_client` (HTTP, secure mobile refresh storage, in-memory web session), `shared_models` (API page/content models) and `shared_utils` (calculator and formatting).

FastAPI exposes one common `/api/v1` contract and OpenAPI. The application is ASGI-compatible and does not create tables or migrate during startup. Vercel uses its FastAPI framework with `app.main:app` entrypoint. SQLAlchemy sessions commit successful requests and roll back failures. Pool size 2, no overflow, bounded timeout, pre-ping and recycling keep warm serverless instances bounded. Pool capacity still scales with instances; configure Neon/serverless concurrency accordingly. Writes are not automatically retried to avoid duplicate side effects; transient failures return 503 with Retry-After.

JWT access tokens carry a session ID, subject, type and expiry. Every authenticated request checks account and session validity. Refresh tokens are random, stored as SHA-256 digests server-side, rotated under row lock, and revoke the previous access session. Argon2id hashes passwords. Rate limits use atomic PostgreSQL buckets rather than process memory. Cookies are not used for authentication, so no cookie CSRF surface is introduced. Production must use HTTPS and a restrictive CORS allowlist. The in-memory web design reduces persistent browser token exposure, but does not eliminate XSS risk.

Each company has one explicit account owner in Phase 1. Every child query and mutation verifies owner access. People are descriptive records, not sharing grants. Administrative compliance views expose aggregate counts; editors receive no private document data. Role changes require super_admin; no default privileged account exists. Administrative writes generate audit rows in their transaction.

Password-reset delivery uses a configured trusted HTTPS adapter. OAuth integration routes return 503 when unconfigured. File storage, push and conversation providers are Protocol interfaces only. No vector database, embeddings, persistent chat schema or inference is introduced.
