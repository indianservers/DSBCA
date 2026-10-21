# API reference

Run FastAPI and inspect `/docs` or `/openapi.json` for the exact schema. All routes begin `/api/v1`. Bearer access authorization is required for private routes; no company identifier by itself grants access.

| Routes | Methods / access |
|---|---|
| health, ready | GET; ready checks database connectivity |
| auth/register, login, refresh | POST; rate-limited, return token pair |
| auth/logout | POST with current bearer and refresh token; revokes session |
| auth/me, users/me | GET current profile; users/me PATCH changes name |
| auth/request-password-reset, reset-password | POST; delivery adapter required; one-use expiring token |
| auth/oauth/google or microsoft | GET integration boundary; 503 until configured |
| users/me/preferences, notifications/preferences | GET / PUT authenticated preferences |
| dashboard | GET owned deadline and updates |
| categories | GET public paginated categories |
| videos, publications, articles, updates, webinars | GET public published lists and `/{id}` details; q/category_id/page/page_size filters; authenticated update lists include per-account read_at |
| updates/{id}/read | PATCH marks a published regulatory update as read for the current account |
| publications/{id}/chapters | GET ordered publication chapters |
| articles/{id}/bookmark | GET / PUT / DELETE current user's bookmark |
| companies | GET / POST current owner's companies |
| companies/{id} | GET / PUT / DELETE with ownership enforcement |
| companies/{id}/people, documents, reminders | GET / POST; `/{child_id}` PUT / DELETE with ownership and related-parent validation |
| notifications | GET recipient-filtered list; `/{id}/read` PATCH |
| toolkit/gratuity | GET monthly_basic/years validated decimal calculation |
| discuss/capabilities | GET explicit Phase 1 demonstration contract |
| admin/dashboard | GET editor/admin aggregate metrics |
| admin/users | GET administrator paginated search; `/{id}` PUT status/roles; role changes require super_admin |
| admin/content | GET resource inventory |
| admin/content/categories, videos, publications, chapters, articles, webinars | GET / POST; `/{id}` PUT / DELETE; editor role required |
| admin/updates, admin/notifications | GET / POST; `/{id}` PUT / DELETE; editor role required |
| admin/settings | GET / PUT administrator settings |
| admin/audit-logs | GET administrator paginated audit |

Paginated responses: `{items: [...], total: n, page: n, page_size: n}`. Page starts at 1; page_size is 1–100. Validation rejects unknown body fields. Content statuses: draft/published/archived. Notification publication creates per-user recipients respecting existing preferences. Current fan-out is synchronous; replace it with an external durable job adapter before large recipient campaigns.

Error conventions: 401 invalid session, 403 missing role, 404 inaccessible or missing record, 409 relational conflict, 422 validation, 429 quota, 503 unavailable dependency. Database errors never expose connection credentials.
