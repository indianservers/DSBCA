# Windows local setup

Use Python 3.12–3.14, pinned Flutter 3.38.5 / Dart 3.10.4, Git, and PostgreSQL 17+ or a Neon development branch. Flutter was installed for this workspace at `C:\Users\saisa\.cache\dsbca-flutter`; scripts locate this fallback if Flutter is absent from PATH.

1. If `backend/.env` is not already configured, copy `backend/.env.example` to it. Preserve the existing configured file in this workspace. Set pooled/direct PostgreSQL URLs with `sslmode=require`, an independent random JWT key (32+ characters), CORS origins and APP_ENV. Never commit this file.
2. Run `./scripts/dev.ps1 -Task install`.
3. Run `./scripts/dev.ps1 -Task migrate`; review the target branch first.
4. Run `./scripts/dev.ps1 -Task seed` for clearly labeled sample learning data.
5. Start API/User/Admin in separate terminals using the README commands.
6. Register an account through the User app. Run `backend/.venv/Scripts/python -m app.grant_role email@example.com super_admin` from the backend directory to authorize the operator. No default password is supplied.
7. Optionally run `python -m app.seed --user-email email@example.com` from backend to add owned demonstration companies, documents, reminders and alerts. It is repeatable.

Password reset requires RESET_DELIVERY_URL and RESET_DELIVERY_TOKEN for an HTTPS trusted mail adapter accepting `{email, reset_token}`. Configure a link to the User app reset form. Google/Microsoft OAuth credentials and flows are not wired; their entries explicitly report unavailable.

`./scripts/dev.ps1 -Task test` runs both Flutter suites and backend isolated tests. PostgreSQL integration tests require TEST_DATABASE_URL naming an expendable `dsbca_test` database, migrated first; each test clears its tables. Production tests are prohibited.

`./scripts/dev.ps1 -Task build -ApiBaseUrl https://your-api-host` builds both web apps. Android builds require compatible JDK (17–24), Android command-line tools, licenses and SDK. iOS requires macOS/Xcode and signing; it cannot be built on this Windows host.

This execution created a local-only PostgreSQL 17.6 cluster under `C:\Users\saisa\.cache\dsbca-postgres-data`, listening on 127.0.0.1:55432, with SSL enabled. The local trust-auth role has no remote listener; do not reuse this configuration on a network server. Tests use the separate local `dsbca_test` database. The development `.env` now points to the supplied Neon pooled/direct endpoints; migrations and demonstration persistence have been verified there.

Random development operator and reader credentials are saved only in ignored `../.local-access.json` relative to backend. These are labeled demonstration accounts, not static production defaults. Use a clean production branch and explicitly provision production access.

For Android, `./scripts/android.ps1 -App user` or `-App admin` uses the local Gradle 8.14 distribution and JDK 23 without changing global Flutter settings. Set -JdkHome if needed. To access the local API from an Android emulator built with the default localhost URL, use Android platform-tools `adb reverse tcp:8000 tcp:8000`; only debug manifests permit local cleartext HTTP. Production builds must compile a real HTTPS API origin.
