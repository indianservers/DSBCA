# Final test matrix

21 October 2026. Local execution is distinct from hosted/provider/native-device acceptance.

| Suite | Passed | Evidence log |
|---|---:|---|
| Backend | 100 | phase4/backend-tests.log |
| Flutter User | 193 | phase4/user-tests.log |
| Flutter Admin | 109 | phase4/admin-tests.log |
| Shared API client | 2 | phase4/client-tests.log |
| Total | 404 | No excluded tests |

Backend covers authentication/session rotation and revocation, role permissions, owner isolation, content CRUD, PDF ingestion/approval/versioning/retrieval/citations, deterministic calculations, deadlines, notification scheduling/delivery state, webinars and typed AI tools. Phase 4 adds reversed-meaning/incomplete-quote rejection, page-level PDF script rejection, request-body bounds, error/log redaction, CORS/cache headers, profile persistence, current owner deadlines, file-type mismatches, cross-app CRUD/archive/search/audit, verified-TLS guards, overall chat timeout and immutable rule transitions.

User tests include 14 calculator forms at six widths and academy/compliance/settings views. Eight accessibility tests exercise 150%/200% text on 360px sign-in, Home, Profile and Compliance. A contrast assertion checks muted text against four shared light surfaces. The Admin suite exercises navigation, knowledge and seven professional workspaces at six widths. Flutter analysis results are separate `user-analysis.log` and `admin-analysis.log`.

## Actual manual and HTTP workflows

- Browser: User/Admin release previews opened; local reader/operator signed in; Home showed the owner's persisted licence expiry; Profile name was edited/saved and reflected back; Admin displayed approved, rejected and superseded demonstration PDFs. Additional observations are in `phase4/manual-browser.md` and screenshots. Do not infer every CRUD action was manually clicked.
- Live HTTP: toolkit compute/save/reopen, company/licence creation and renewal, review/independent approval/publication with actual in-app worker delivery, typed chat calculation/company tools, webinar scheduling/registration/private joining/UTC ICS. See `phase4/acceptance-http.json` and `scripts/phase4_acceptance.py`.
- Automated cross-app: draft is hidden, administrator publishes, reader sees edited record, search/page works, another reader cannot edit, archive hides it and audit exists for videos/publications/articles/webinars.
- Database: fresh local QA migration to 0004, 74 FK orphan checks, DB backup restored to a separate local database. Shared Neon read-only metadata only.

## Visual and accessibility evidence

54 User captures cover nine screens at 360/390/430/768/1024/1440px under `phase4/screenshots`. `reference-contact.png` contains all nine approved references; `actual-contact.png` summarizes current 390px captures. These are controlled widget fixtures, not production content. Admin responsive tests and browser screenshots are separate. No golden baseline was blindly approved to hide differences. Browser AX labels and profile keyboard text entry were inspected; full NVDA/VoiceOver/TalkBack and physical-device keyboard testing are not claimed.

## Failures found and corrected

Initial large-text Home overflows were fixed with text-scaled grid height. A debug/main Android manifest conflict was fixed with an explicit debug-only cleartext override. A citation-page regression from an over-restrictive whole-chunk policy was fixed by allowing complete verbatim sentences while rejecting paraphrases and clipped qualifiers; the page-two mapping test passed again. The old manual-reminder-only dashboard assertion was updated to require the still-active document expiry after completing its manual reminder. An early unsupported GridView parameter was corrected and rebuilt. Final logs supersede intermediate failed runs.

## Not executed / release gates

Real OpenAI generation/embeddings and professional answer evaluation; native pgvector retrieval on the target Neon branch; S3 object permissions/restore; actual email/push delivery; production/preview Vercel deployment and cold-start/streaming tests; signed Android AAB; iOS compilation/device testing; full manual CRUD/invalid-input matrix on hosted services and final visual approval. These remain explicit gates, not passing or excluded tests.
