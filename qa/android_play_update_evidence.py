"""Read-only, source-bound Play AAB and update-path evidence.

Checks a completed release in the specified checkout. It does not upload an
AAB or claim that Google Play has delivered or installed any update.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile


def run(args, *, cwd=None):
    return subprocess.run([str(p) for p in args], cwd=cwd, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180).stdout


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--release-root', type=Path, required=True)
    args = parser.parse_args()
    root = args.release_root.resolve()
    bundle = root / 'artifacts/schulpilot-play.aab'
    mapping = root / 'app/build/app/outputs/mapping/playRelease/mapping.txt'
    tool = Path.home() / '.local/share/schulpilot-tools/bundletool/1.18.3/bundletool-all-1.18.3.jar'
    dexdump = Path.home() / 'android-sdk/build-tools/36.0.0/dexdump'
    proof_parts = run(['python3', 'scripts/release_attestation.py', 'verify'], cwd=root).decode().split()
    if len(proof_parts) != 3:
        raise RuntimeError('Release attestation response invalid')
    proof = json.loads(base64.b64decode(proof_parts[1], validate=True))
    current_commit = run(['git', 'rev-parse', 'HEAD'], cwd=root).decode().strip()
    if proof.get('source_commit') != current_commit or proof.get('play_aab_sha256') != digest(bundle):
        raise RuntimeError('Play bundle differs from the signed source-bound release')
    run(['java', '-jar', tool, 'validate', '--bundle=' + str(bundle)])
    xml = run(['java', '-jar', tool, 'dump', 'manifest', '--bundle=' + str(bundle)])
    doc = ET.fromstring(xml)
    namespace = '{http://schemas.android.com/apk/res/android}'
    permissions = {node.get(namespace + 'name') for node in doc.iter()
                   if node.tag in ('uses-permission', 'uses-permission-sdk-23')}
    if 'android.permission.REQUEST_INSTALL_PACKAGES' in permissions:
        raise RuntimeError('Play bundle requests APK installation permission')
    version = doc.get(namespace + 'versionCode')
    if not version or not version.isdecimal() or not proof.get('version', '').endswith('+' + version):
        raise RuntimeError('Play bundle version differs from release')
    signature = run(['jarsigner', '-verify', bundle]).decode()
    if 'jar verified.' not in signature:
        raise RuntimeError('Play bundle signature verification incomplete')
    mapping_text = mapping.read_text(encoding='utf-8')
    marker = re.search(r'^# pg_map_id: ([a-f0-9]{64})$', mapping_text, re.M)
    found = re.search(r'^de\.dorfspy\.schulpilot\.AppUpdater -> ([^:]+):\n(.*?)(?=^[^\s#].* -> [^:]+:$|\Z)',
                      mapping_text, re.M | re.S)
    if not marker or not found:
        raise RuntimeError('No corresponding R8 updater mapping')
    updater, section = found.groups()
    if ('AppUpdateManagerFactory.create' not in section or 'getAppUpdateInfo' not in section
            or 'canRequestPackageInstalls' in section or 'FileProvider' in section):
        raise RuntimeError('Unexpected updater mapping')
    with tempfile.TemporaryDirectory(prefix='schulpilot-play-dex-') as temporary:
        with ZipFile(bundle) as archive:
            dex_names = [name for name in archive.namelist() if re.fullmatch(r'base/dex/classes\d*\.dex', name)]
            if not dex_names:
                raise RuntimeError('Play bundle contains no base DEX')
            matching = 0
            for index, name in enumerate(dex_names):
                raw = archive.read(name)
                if b'canRequestPackageInstalls' in raw or b'/downloads/schulpilot-android.apk' in raw:
                    raise RuntimeError('Direct updater markers present in Play DEX')
                dex = Path(temporary) / f'{index}.dex'
                dex.write_bytes(raw)
                disassembly = run([dexdump, '-d', dex]).decode(errors='replace')
                escaped = re.escape('L' + updater.replace('.', '/') + ';')
                klass = re.search(r"Class descriptor\s*: '" + escaped + r"'\n(.*?)(?=^Class #|\Z)",
                                  disassembly, re.M | re.S)
                if klass:
                    matching += 1
                    if 'r8-map-id-' + marker.group(1) not in klass.group(1):
                        raise RuntimeError('Updater DEX does not match R8 mapping identifier')
            if matching != 1:
                raise RuntimeError('Play updater class missing or ambiguous')
    print(json.dumps({'checked_at_utc': datetime.now(timezone.utc).isoformat(),
                      'source_commit': current_commit, 'release_version': proof['version'],
                      'play_aab_sha256': proof['play_aab_sha256'], 'r8_mapping_sha256': digest(mapping),
                      'r8_mapping_identifier': marker.group(1), 'updater_obfuscated_class': updater,
                      'release_attestation_verified': True, 'bundletool_validated': True,
                      'apk_installer_permission_absent': True, 'direct_updater_markers_absent': True,
                      'mapping_indicates_play_update_manager': True,
                      'jarsigner_verified_with_warnings': 'Warning:' in signature,
                      'actual_play_delivery_tested': False}, sort_keys=True))


if __name__ == '__main__':
    main()
