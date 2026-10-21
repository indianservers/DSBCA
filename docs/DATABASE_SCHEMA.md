# Database schema

All business records use UUID strings, created_at and updated_at. Foreign keys enforce relationships; ownership queries enforce tenancy. Tables are created only by versioned migrations. PostgreSQL is required at runtime; SQLite is available solely for isolated unit tests.

| Area | Tables and relationships |
|---|---|
| Identity | users → user_profiles (one-to-one); users ↔ roles through user_roles; users → auth_sessions and password_reset_tokens |
| Companies | users → companies → company_people, company_documents, company_reminders; documents may reference company people, reminders may reference documents; reminder_preferences belongs to user |
| Learning | subject_categories → videos, publications, articles, regulatory_updates, webinars; video_categories → videos; publications → publication_chapters; users ↔ articles through article_bookmarks |
| Alerts | notifications ↔ users through notification_recipients (per-user read_at); notification_preferences belongs to user |
| Regulatory reading | regulatory_update_reads links user/update with unique per-user read state |
| Admin | app_settings (unique key and JSON value), audit_logs (actor/action/resource), rate_limits (hashed bucket key/window/count) |

Unique constraints cover email, role/category names, user/role assignments, publication chapter position, bookmarks, recipients and per-user preferences. Indexes cover email, ownership, parent IDs, content status/category and expiry/due dates. Content deletion archives rows; company deletion cascades its child records. Personal documents are metadata only. Files are not persisted in PostgreSQL or local serverless storage.

Neon pooled URL is `DATABASE_URL`; direct URL is `DATABASE_URL_UNPOOLED`. Both must enforce SSL. Migrations use a NullPool and must be run deliberately against the intended branch. Never migrate/test a production database from test scripts. Offline migration SQL can be reviewed with `python -m alembic upgrade head --sql`.

Chat conversations/messages and knowledge source/document/version concepts remain interfaces; no final Phase 2 tables exist.
