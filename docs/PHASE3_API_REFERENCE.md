# Phase 3 API reference

All paths use `/api/v1`. Existing authentication, company/content CRUD and Phase 2 routes remain. `/docs` is the authoritative typed OpenAPI schema. Collection APIs return bounded/paginated data.

| Area | Endpoints |
|---|---|
| Toolkit | GET /professional/calculators; POST /professional/calculators/{code}/calculate; GET /professional/calculations; GET /professional/calculations/{id}; GET /professional/calculations/{id}/export |
| Rule management | GET/POST /admin/professional/rules; POST /admin/professional/rules/{id}/{validate,publish,supersede}; GET /admin/professional/rule-templates |
| Learning state | GET /professional/learning/{kind}/{id}/state; PUT .../progress; PUT .../bookmark; GET /professional/learning/library |
| Learning paths | GET /professional/learning/paths; POST /professional/learning/paths/{id}/enroll; GET/POST /admin/professional/learning-paths; PUT/DELETE .../{id} |
| Chapters | Existing /publications/{id}/chapters and /admin/content/chapters; PUT /admin/professional/publications/{id}/chapter-order |
| Compliance | GET /professional/companies/{id}/compliance; POST /professional/companies/{id}/documents; PUT .../documents/{document_id}; POST .../obligations; PATCH .../obligations/{obligation_id}; GET /professional/compliance-rules |
| Reminder preferences | GET/PUT /professional/reminder-settings |
| Private attachments | POST /professional/media; GET /professional/media/{id}/download |
| Delivery | GET/PUT /professional/notifications/settings; POST /professional/notifications/devices; DELETE .../devices/{id}; GET /professional/notifications/jobs |
| Admin delivery | GET /admin/professional/notifications; POST .../{id}/retry; POST .../campaigns; existing settings API stores templates |
| Scheduled runner | GET /internal/professional/notifications/tick, bearer worker secret required |
| Updates | GET/PUT /professional/updates/subscriptions; POST /admin/professional/updates/{id}/workflow |
| Events | POST/DELETE /professional/webinars/{id}/register; GET .../registration; GET .../join; GET .../calendar |
| Event administration | GET /admin/professional/webinars/{id}/registrations; GET .../attendees.csv |
| AI tools | GET /professional/ai/tools; POST /professional/ai/tools/execute; typed application_tool in existing chat/stream contracts |
| Metrics | GET /admin/professional/metrics |

Normal calculator calls can run anonymously with the existing database-backed request limiter; account saving/history/export require authentication. AI tools always require authentication. Owner-scoped APIs return 404 for foreign records. Learning content CRUD requires editor access; legal rule/update approval and delivery administration require administrator access. Rule publication needs a different reviewer. Missing providers produce inactive/blocked states rather than simulated success.


Additional academy routes: `GET /chapters/{id}` enforces parent publication status, visibility and scheduled publication time; `GET /video-categories?subject_id=...` supplies video-topic filtering. Editors manage these via `/admin/professional/video-categories`. In-use video topics cannot be deleted. Learning-path administration returns ordered items so editing metadata preserves the path. Scheduled chapter assets remain inaccessible until their parent publication is published and due. Queued regulatory alerts recheck publication and subscription at delivery time.
