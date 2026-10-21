# Final implementation audit — discovery baseline

21 October 2026. Source inspection, not previous completion statements, establishes the following baseline. This audit precedes Phase 4 repairs. Re-run results and final dispositions are in FINAL_RELEASE_REPORT.md and FINAL_TEST_MATRIX.md.

| Feature / route | Backend and permission | Discovery status / actionable controls |
|---|---|---|
| Sign in /sign-in | /auth/register,login,refresh,logout; public/session | Implemented and previously tested; Phase 4 rerun required. OAuth/reset delivery blocked by configuration; buttons report unavailability. Web tokens intentionally memory-only. |
| Home /home | /dashboard; owner | Partially implemented: dashboard omits Phase 3 obligations/documents and can claim no company despite an existing company. Shortcuts navigate. |
| Discuss /discuss | /ai/conversations,chat/stream,messages,cancel,feedback,sources; owner | Implemented provider adapters, streaming, history, cancel, copy, feedback and source cards. Live OpenAI blocked. Citation quote existence/number validation does NOT establish semantic entailment: high release concern. |
| Videos /learn | /videos,categories,video-categories; published/user | Implemented search/filter/player/speed/fullscreen/bookmark/progress. Configured demonstration clip only; professional library absent. |
| Publications /learn?tab=publications | /publications,chapters,professional/media; published/owner | Implemented chapters, downloads and progress; download/share uses platform handler, not an embedded full publication PDF reader. AI page previews are separate. |
| Toolkit /toolkit and /toolkit/:code | professional/calculators,calculations; public maths/owner saves | 14 Decimal services implemented with explicit limitations and version applicability; need independent regression/boundary re-execution. |
| Updates /updates | /updates and subscriptions; published/owner | Review/independent approval/subscriptions implemented. |
| Webinars /content/webinars/:id | register,registration,join,calendar; owner registration | Capacity/idempotency/cancel/ICS implemented; real event provider is unconfigured. |
| Compliance /reminders | companies/people/documents/obligations/preferences; owner | Persisted profiles/renewal/status/history/private uploads/deletion implemented. First-page company/person listing limits discoverability after 20 records. |
| Notifications /notifications,/delivery-settings | recipients/settings/jobs/devices; owner | In-app worker implemented; external delivery blocked; client push activation missing. |
| Profile /profile,/settings | /users/me PATCH exists | Partially implemented: profile display/logout/preferences work; profile editor absent. Account deletion/export workflow missing (must document operational handling). |
| Learning paths /learning-library | paths,enroll,library,state; owner | Implemented paths/saved/recent, completion and deep links. |
| Admin dashboard/users | /admin/dashboard,users; administrator/superadmin role edits | Existing reads/edit/search/page/audit. User creation uses registration then privileged role grant, not admin create. No hard-delete UI. |
| Admin learning workspace | /admin/content/*,learning-paths,video-categories; editor | CRUD/archive/reorder/private attachment/forms; advanced metadata uses JSON and IDs. Search/filter/page contracts inconsistent for special lists. |
| Admin rules | /admin/professional/rules; administrator + independent reviewer | Immutable versions, source links, validation/publish/supersede and history implemented. Production legal approval not established by local seed. |
| Admin regulatory/webinars | /admin/updates/workflow,content/webinars,attendees.csv | Persisted review/workflow, scheduling and attendee export implemented; no real broadcast/events. |
| Admin knowledge/settings/approvals/analytics | /admin/ai/*; editor/admin, document ACL | Ingestion/job lifecycle/approval/versioning/settings/analytics implemented. Live model/vector/S3 acceptance blocked. |
| Admin notifications/audit/general settings | /admin/professional/notifications,admin/audit-logs,settings | Implemented jobs/campaign/retry/templates/aggregate metrics and audit records. Operational request telemetry absent. |
| Database | Alembic 0001–0004; local isolated PostgreSQL | Additive migrations previously exercised locally. Shared Neon stays unchanged; no separate development branch. Pool bounded 2/0, connect/SQL timeouts present. Need query evidence before new indexes. |
| CI/deployment | .github/workflows/deploy.yml + three Vercel configs | High defect: manual workflow immediately deploys --prod without protected environment or branch gate. PR verification missing. Dependency lock stale after Phase 3 additions. |
| Mobile | Android/iOS projects | High defect: release variant silently signs with debug key. No production keystore; do not create one. Default launcher artwork, unconfigured app/universal links and push; iOS compile blocked by Windows. |

## Prioritized findings

- High: citation validator accepts reversed qualitative meaning if quote exists; enforce safe evidence presentation before release.
- High: debug signing for release and unguarded production CI deployment; fail closed and introduce gated release policy.
- High: missing production storage/AI/provider/Neon branch/Vercel activation and real delivery acceptance; release remains blocked.
- Medium: no request IDs/redacted operational telemetry or no-store policy across authenticated API responses.
- Medium: dashboard ignores new deadlines; profile update UI absent; special admin pagination inconsistent.
- Medium: media declared MIME is not checked against decoded image format/extension.
- Medium: account deletion/retention/production recovery not operationally verified.
- Low: unreachable LegacyToolkit/LegacyReminders duplicate User classes remain. No routes reference them; remove obsolete UI while preserving compatibility API tests.

Source inventory contains hashes/sizes for inspected code/config/test files, excluding secrets, dependencies and build outputs. The route inventory generated alongside this audit records every registered endpoint and its dependency functions. Local fixture datasets are labeled; production content is not fabricated. No production write/deployment is authorized here.

## Final disposition — 21 October 2026

Local repairs and final verification are recorded in FINAL_RELEASE_REPORT.md and FINAL_TEST_MATRIX.md: 404 automated tests passed. AI output is restricted to complete exact excerpts, without claiming semantic entailment validation. PDF action/geometry bounds, hosted environment/TLS guards, request telemetry, profile/deadline fixes, immutable reviewed rule transitions and signing guards are implemented. Saved renewal templates apply to new/replanned in-app jobs; external delivery retains generic private messages. General identity settings remain stored metadata and do not dynamically rebrand the User app.

Manual cross-app article create/edit/archive visibility and selected Admin navigation were verified; see phase4/manual-browser.md. Production/provider/privacy/mobile/acceptance gaps remain in RELEASE_BLOCKERS.md. Recommendation: NO GO. No shared Neon schema or production data was changed.
