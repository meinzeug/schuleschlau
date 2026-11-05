#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
unset SCHULPILOT_RELEASE_ATTESTATION_DIR
build_commit="$(python3 scripts/release_attestation.py check-source)"
# Fail before the expensive Flutter builds if release metadata disagrees.
python3 - <<'PY'
import re
from pathlib import Path
app = re.search(r'^version:\s*([^+\s]+)\+', Path('app/pubspec.yaml').read_text(), re.M)
backend = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', Path('backend/schulpilot/__init__.py').read_text(), re.M)
if not app or not backend or app.group(1) != backend.group(1):
    raise SystemExit('App and backend version must match')
PY
flutter_bin="${SCHULPILOT_FLUTTER:-$HOME/.local/share/schulpilot-flutter/bin/flutter}"
export SCHULPILOT_SIGNING_PROPERTIES="${SCHULPILOT_SIGNING_PROPERTIES:-$HOME/.local/share/schulpilot-signing/signing.properties}"
export SCHULPILOT_STORE_BUILD=true
test -f "$SCHULPILOT_SIGNING_PROPERTIES"
"$flutter_bin" --version --machine | python3 -c 'import json,sys; expected=json.load(open("toolchain.json")); actual=json.load(sys.stdin); assert actual["frameworkRevision"]==expected["flutter_revision"] and actual["dartSdkVersion"].split()[0]==expected["dart"], "Use the pinned Flutter SDK"'
cd app
app_version="$(python3 -c 'import re; print(re.search(r"^version:\s*(\S+)", open("pubspec.yaml").read(), re.M)[1])')"
"$flutter_bin" pub get --enforce-lockfile
"$flutter_bin" build web --release --no-pub --no-web-resources-cdn --csp --dart-define=APP_VERSION="$app_version"
"$flutter_bin" build appbundle --flavor play --release --dart-define=API_URL=https://schulpilot.dorfspy.de/api --dart-define=APP_VERSION="$app_version" --no-pub
cp build/app/outputs/bundle/playRelease/app-play-release.aab ../artifacts/schulpilot-play.aab
cd ..
python3 scripts/prepare_repair_source.py --commit "$build_commit" --output artifacts/repair-source.tar.gz
python3 scripts/prepare_repair_source.py --commit "$build_commit" --output artifacts/repair-source.tar.gz --verify
python3 scripts/release_attestation.py prepare "$build_commit"
cd app
SCHULPILOT_RELEASE_ATTESTATION_DIR="$PWD/build/release-attestation" "$flutter_bin" build apk --flavor direct --release --dart-define=API_URL=https://schulpilot.dorfspy.de/api --dart-define=APP_VERSION="$app_version" --no-pub
cp build/app/outputs/flutter-apk/app-direct-release.apk ../artifacts/schulpilot-android.apk
chmod 600 ../artifacts/schulpilot-android.apk ../artifacts/schulpilot-play.aab
cd ..
python3 scripts/android_manifest.py
python3 scripts/release_attestation.py finish "$build_commit"
