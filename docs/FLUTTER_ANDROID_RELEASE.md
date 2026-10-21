# Android release readiness

Both apps retain their existing application IDs; User is `com.dsbca.dsbca_user`. Display names are DSBCA/DSBCA Admin. User minimum API is 24 for video playback. Production network traffic is HTTPS-only and application backup is disabled. Debug manifests explicitly permit local cleartext transport for emulator QA, with a merger override scoped to debug.

Deep-link intent filters are prepared for `dsbca://app/...` and `dsbca-admin://app/...`. They do not establish verified HTTPS App Links or domain ownership. No auth token belongs in a URL. Push remains unconfigured; no notification permission/delivery claim is made.

## Signing and artifacts

Release builds no longer fall back to the debug signing key. Supply owner-controlled `DSBCA_ANDROID_KEYSTORE`, `DSBCA_ANDROID_STORE_PASSWORD`, `DSBCA_ANDROID_KEY_ALIAS`, and `DSBCA_ANDROID_KEY_PASSWORD`. No production keystore was generated. Release preflight was executed and deliberately rejected missing signing material; **no release AAB is generated or approved**.

The protected manual Android workflow accepts an existing owner-supplied keystore secret and builds an AAB with an HTTPS API origin after tests. Configure its protected environment and Play App Signing policy with the owner. Do not commit signing files or copy them into build artifacts.

Internal QA debug APKs are built with `scripts/android.ps1 -App user|admin -ApiBaseUrl http://10.0.2.2:8004`. See `phase4/android-*-debug.log` and artifact manifest for actual outcomes/hashes. The project-local Flutter argument wrapper addresses the bundled SDK's encoded DartDefines forwarding without changing the cached SDK. These APKs use emulator loopback; rebuild with a reachable API for devices.

Before store release, approve launcher/adaptive icons and splash artwork (template native artwork remains), verify application-ID ownership/versioning, release signing, real devices, file/media handlers, verified links, notifications, backup/secure-storage behavior and store privacy disclosures. Debug compilation alone does not satisfy these gates.
