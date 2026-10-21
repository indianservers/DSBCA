#!/usr/bin/env bash
set -euo pipefail
# Run from apps/dsbca_user or apps/dsbca_admin. Shared packages must be included.
: "${API_BASE_URL:?Set API_BASE_URL to the deployed backend HTTPS origin}"
[[ "$API_BASE_URL" == https://* ]] || { echo 'API_BASE_URL must use HTTPS' >&2; exit 1; }
FLUTTER_VERSION=3.38.5
FLUTTER_HOME="${TMPDIR:-/tmp}/dsbca-flutter-${FLUTTER_VERSION}"
if [[ ! -x "$FLUTTER_HOME/bin/flutter" ]]; then
  git clone --depth 1 --branch "$FLUTTER_VERSION" https://github.com/flutter/flutter.git "$FLUTTER_HOME"
fi
export PATH="$FLUTTER_HOME/bin:$PATH"
flutter config --no-analytics
flutter pub get --enforce-lockfile
flutter build web --release --no-wasm-dry-run --dart-define="API_BASE_URL=$API_BASE_URL"
