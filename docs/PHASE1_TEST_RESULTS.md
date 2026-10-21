# Phase 1 verification — 21 October 2026

## Verified

| Check | Result |
|---|---|
| Flutter dependencies | Both apps and shared packages resolved successfully |
| Flutter static analysis | Whole project and both individual apps: no issues |
| User widget/calculator/navigation tests | 56 passed; nine screens at 360, 390, 430, 768, 1024 and 1440px; calculator eligibility/tier/cap/invalid inputs; guest navigation |
| Admin widget/routing tests | 55 passed; all nine sections at six requested widths and initial login guard |
| Shared API client tests | 2 passed; authentication, token rotation, logout and bounded failed retry |
| Backend PostgreSQL tests | 14 passed against isolated local `dsbca_test`; one Starlette/httpx deprecation warning |
| Backend SQLite tests | Initial 5-test suite passed; later expanded PostgreSQL suite is the primary record |
| PostgreSQL migration cycle | Upgrade/downgrade/upgrade exercised locally; no production/destructive Neon test operations |
| Neon pooled/direct SSL connections | Both verified using supplied credentials, stored only in ignored `.env` |
| Neon migrations | `0001` foundation and `0002` regulatory update read state applied |
| Neon schema consistency | `alembic check`: no new upgrade operations detected |
| Neon demonstration workflow | Random development accounts authenticate; Admin publishes video/article; User public API reads both; owned companies/reminders persist; admin is denied another account's private company; notification read state persists |
| User web release build | Successful |
| Admin web release build | Successful |
| Browser check | Actual Flutter web sign-in renders; guest navigation reaches Home/Learn; live Neon categories/video catalogue load; API readiness and allowed-origin CORS verified |
| Visual captures | All nine 390×844 Flutter widget screenshots saved in `docs/screenshots`; demonstration fixtures, not live database snapshots |
| Secret exclusion | `git check-ignore backend/.env .local-access.json` confirms both ignored |

Backend tests cover refresh rotation/replay rejection, logout/session revocation, password-reset token hashing/reuse rejection/session invalidation, failed-login rate limiting, role enforcement, suspended accounts, cross-account isolation, foreign-parent validation, company/document/reminder CRUD and renewal, publication/chapter visibility/order, transaction failure without audit side effects, preferences/notification recipient isolation, bookmarking, seeding repeatability, validation, health/readiness and calculation boundaries.

Neon demonstration checks create **labeled development records** and random operator/reader accounts. They do not drop tables, truncate data, or run the destructive test suite. Access details are in ignored `.local-access.json`; no password is included in this report. Use a separate clean production branch and explicitly provision production operators before release.

## Android and iOS

Both User and Admin Android debug APKs built successfully with Gradle 8.14 and JDK 23. The original Flutter wrapper download timed out; downloading Gradle from its official distribution endpoint and running the supported Gradle task resolved it. Installed Android SDK/NDK artifacts were used. Debug manifests allow local HTTP; release manifests do not enable cleartext traffic. These are debug builds, not signed store releases. Outputs: each app's `build/app/outputs/flutter-apk/app-debug.apk`. Gradle/plugin deprecation warnings remain; the builds succeeded.

iOS projects exist but cannot be compiled or signed on Windows. A macOS/Xcode validation and device run remain required. Android device runtime testing is distinct from a successful APK build.

## Visual review and remaining acceptance

Open `UI_COMPARISON.html` to compare original/reference and Flutter captures side by side. The originals remain unchanged. The violet/navy/lavender system, branded sign-in, serif headings, tabs, learning rows, calculator and notification/reminder cards are implemented with real widgets. Screenshots are never used as application backgrounds.

Known intentional differences: demonstration labels replace assertions of verified AI/law; actual deadline data/empty states replace fabricated dates; company records include functional CRUD controls; alerts are an in-app presentation rather than OS push; missing media/PDF URLs are explicitly unavailable. Layout tests verify absence of exceptions at the specified dimensions; they are not a claim of pixel identity or a completed human visual sign-off.

Production acceptance remains open for Vercel deployment and post-deployment checks, actual reset-email delivery adapter, OAuth provider credentials/implementation, production media/storage, native device verification and final visual approval. AI inference, advanced calculators and push delivery remain outside Phase 1 by design.

## Reproduction

Use `scripts/dev.ps1 -Task test` for Flutter and isolated backend tests. For PostgreSQL, migrate an expendable database named `dsbca_test`, then set TEST_DATABASE_URL before pytest. Never point it at Neon production: the fixture deletes test table contents. `python -m app.demo_check --allow-demo-writes` is a separate non-destructive development-only demonstration against configured Neon. `scripts/android.ps1 -App user` or `-App admin` reproduces the debug build with a compatible JDK. Test logs are local ignored artifacts; this document is the committed summary.
