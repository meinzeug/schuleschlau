"""Verify the direct updater with synthetic APKs on an isolated emulator.

Build the isolated test APK and instrumentation first; see ANDROID_UPDATES.md.
No child account, production signing key, provider request or real installation
of the candidate APKs is used. The fake Activity intercepts installer intents.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, timezone

PACKAGE = 'de.dorfspy.schulpilot.updateprobe'
TEST_PACKAGE = PACKAGE + '.test'
RUNNER = TEST_PACKAGE + '/de.dorfspy.schulpilot.qa.FamilyCallInstrumentation'
FIXTURES = ('good', 'wrong-package', 'wrong-signer', 'wrong-version', 'old-version', 'unsupported-sdk')


def command(args, *, input=None, timeout=120):
    return subprocess.run([str(part) for part in args], input=input, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=True, timeout=timeout).stdout


def badging(aapt, path):
    text = command([aapt, 'dump', 'badging', path]).decode()
    match = re.search(r"package: name='([^']+)' versionCode='(\d*)'", text)
    if not match:
        raise RuntimeError('APK metadata unavailable')
    return (*match.groups(), '\napplication-debuggable\n' in '\n' + text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', required=True, help='Explicit emulator-NNNN device')
    parser.add_argument('--app', type=Path, required=True, help='Isolated direct debug APK')
    parser.add_argument('--test', type=Path, required=True, help='Isolated instrumentation APK')
    args = parser.parse_args()
    if not re.fullmatch(r'emulator-\d+', args.serial):
        raise SystemExit('Explicit emulator serial required')
    sdk = Path.home() / 'android-sdk'
    adb, tools = sdk / 'platform-tools/adb', sdk / 'build-tools/36.0.0'
    aapt, signer = tools / 'aapt', tools / 'apksigner'
    debug_key = Path.home() / '.android/debug.keystore'
    debug_code, code_text, debug_enabled = badging(aapt, args.app)
    test_code, _, test_debug_enabled = badging(aapt, args.test)
    if (debug_code != PACKAGE or test_code != TEST_PACKAGE or not code_text
            or not debug_enabled or not test_debug_enabled):
        raise SystemExit('Refusing non-isolated test APKs')
    code = int(code_text)
    if not 1 <= code < 2_100_000_000:
        raise SystemExit('Invalid synthetic APK version')
    prefix = [adb, '-s', args.serial]
    def device(*argv, input=None, timeout=120):
        return command([*prefix, *argv], input=input, timeout=timeout)
    if device('shell', 'getprop', 'ro.kernel.qemu').strip() != b'1':
        raise SystemExit('Refusing non-emulator device')
    sdk_version = int(device('shell', 'getprop', 'ro.build.version.sdk').strip())
    if not 26 <= sdk_version < 1000:
        raise SystemExit('Unsupported emulator API level')
    def packages():
        return set(device('shell', 'pm', 'list', 'packages').decode().splitlines())
    before = packages()
    if any('package:' + name in before for name in (PACKAGE, TEST_PACKAGE)):
        raise SystemExit('Test package already exists; inspect it instead of replacing it')
    before_regular = 'package:de.dorfspy.schulpilot' in before
    created = []
    try:
        with tempfile.TemporaryDirectory(prefix='schulpilot-apk-probe-') as tmp:
            tmp = Path(tmp)
            wrong_key = tmp / 'synthetic.jks'
            keytool = shutil.which('keytool')
            if not keytool or not debug_key.is_file():
                raise RuntimeError('Synthetic signing prerequisites unavailable')
            command([keytool, '-genkeypair', '-keystore', wrong_key, '-alias', 'probe',
                     '-storepass', 'synthetic', '-keypass', 'synthetic', '-dname', 'CN=Synthetic',
                     '-keyalg', 'RSA', '-validity', '3', '-noprompt'])
            android_jar = sdk / 'platforms/android-36/android.jar'
            cases = [
                ('good', PACKAGE, code + 1, 24, debug_key, 'androiddebugkey', 'android'),
                ('wrong-package', PACKAGE + '.other', code + 1, 24, debug_key, 'androiddebugkey', 'android'),
                ('wrong-signer', PACKAGE, code + 1, 24, wrong_key, 'probe', 'synthetic'),
                ('wrong-version', PACKAGE, code + 2, 24, debug_key, 'androiddebugkey', 'android'),
                ('old-version', PACKAGE, code, 24, debug_key, 'androiddebugkey', 'android'),
                ('unsupported-sdk', PACKAGE, code + 1, sdk_version + 1, debug_key, 'androiddebugkey', 'android'),
            ]
            for name, package, version, minsdk, key, alias, password in cases:
                directory = tmp / name
                directory.mkdir()
                manifest = directory / 'AndroidManifest.xml'
                manifest.write_text(
                    '<manifest xmlns:android="http://schemas.android.com/apk/res/android" '
                    f'package="{package}" android:versionCode="{version}" android:versionName="synthetic">'
                    f'<uses-sdk android:minSdkVersion="{minsdk}" android:targetSdkVersion="36"/>'
                    '<application android:hasCode="false"/></manifest>', encoding='utf-8')
                apk = tmp / (name + '.apk')
                command([aapt, 'package', '-f', '-M', manifest, '-I', android_jar, '-F', apk])
                # The first key is Android's standard *debug* key. The second
                # key and its synthetic password exist only in this temporary directory.
                command([signer, 'sign', '--ks', key, '--ks-key-alias', alias,
                         '--ks-pass', 'pass:' + password, '--key-pass', 'pass:' + password, apk])
            device('install', args.app, timeout=180)
            created.append(PACKAGE)
            device('install', args.test, timeout=180)
            created.append(TEST_PACKAGE)
            device('shell', 'run-as', PACKAGE, 'mkdir', '-p', 'files/update-probe')
            for name in FIXTURES:
                device('shell', 'run-as', PACKAGE, 'tee', f'files/update-probe/{name}.apk',
                       input=(tmp / (name + '.apk')).read_bytes())
            device('shell', 'appops', 'set', PACKAGE, 'REQUEST_INSTALL_PACKAGES', 'allow')
            output = device('shell', 'am', 'instrument', '-w', '-e', 'mode', 'update_probe', RUNNER,
                            timeout=90).decode()
            expected = 'OK: valid, size, hash, package, signer, version, downgrade, min_sdk, installer_gate'
            if expected not in output or 'FAILED' in output:
                raise RuntimeError('Synthetic native update validation failed')
    finally:
        errors = []
        for name in reversed(created):
            try:
                device('uninstall', name, timeout=60)
            except subprocess.SubprocessError:
                errors.append(name)
        after = packages()
        if errors or any('package:' + name in after for name in (PACKAGE, TEST_PACKAGE)):
            raise RuntimeError('Synthetic emulator package cleanup incomplete')
        if ('package:de.dorfspy.schulpilot' in after) != before_regular:
            raise RuntimeError('Regular emulator package presence changed')
    source = Path(__file__).resolve().parents[1] / 'app/android/app/src/direct/kotlin/de/dorfspy/schulpilot/AppUpdater.kt'
    print(json.dumps({'checked_at_utc': datetime.now(timezone.utc).isoformat(),
          'local_source_sha256_not_build_attestation': hashlib.sha256(source.read_bytes()).hexdigest(),
          'target_version_code': code, 'emulator': args.serial, 'emulator_api': sdk_version,
          'synthetic_cases': ['valid', 'size', 'hash',
          'package', 'signer', 'version', 'downgrade', 'min_sdk', 'installer_gate'],
          'installer_was_intercepted': True, 'test_packages_removed': True,
          'regular_package_presence_unchanged': True}, sort_keys=True))


if __name__ == '__main__':
    main()
