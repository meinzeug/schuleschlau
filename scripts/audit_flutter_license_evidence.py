#!/usr/bin/env python3
"""Record pinned Flutter engine license/notice evidence without legal conclusions."""
import argparse
import gzip
import hashlib
import io
import json
import re
import subprocess
from pathlib import Path
from zipfile import ZipFile

ARTIFACTS = ('flutter_embedding_release', 'arm64_v8a_release', 'armeabi_v7a_release', 'x86_64_release')
LICENSE_PATH = 'engine/src/flutter/sky/packages/sky_engine/LICENSE'
MAX_NOTICE = 8_000_000


def sha_file(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def engine_files(sdk, expected_revision):
    revision = subprocess.check_output(['git', '-C', str(sdk), 'rev-parse', 'HEAD'], text=True, timeout=30).strip()
    if revision != expected_revision:
        raise ValueError('Flutter SDK revision differs from toolchain')

    def committed(path):
        return subprocess.check_output(['git', '-C', str(sdk), 'show', f'HEAD:{path}'], timeout=30)
    version = (sdk / 'bin/internal/engine.version').read_bytes()
    license_bytes = (sdk / LICENSE_PATH).read_bytes()
    if version != committed('bin/internal/engine.version') or license_bytes != committed(LICENSE_PATH):
        raise ValueError('Flutter engine metadata or license differs from committed SDK')
    engine = version.decode('ascii').strip()
    if not re.fullmatch(r'[0-9a-f]{40}', engine):
        raise ValueError('Invalid Flutter engine revision')
    return engine, hashlib.sha256(license_bytes).hexdigest()


def inspect_jar(path):
    with ZipFile(path) as jar:
        notices = sorted(name for name in jar.namelist() if re.search('license|notice', name, re.I))
    return {'sha256': sha_file(path), 'bytes': path.stat().st_size, 'embedded_notice_paths': notices}


def inspect_apk(path):
    with ZipFile(path) as apk:
        matches = [x for x in apk.infolist() if x.filename == 'assets/flutter_assets/NOTICES.Z']
        if len(matches) != 1 or matches[0].file_size > MAX_NOTICE:
            raise ValueError('Missing, duplicate, or oversized Flutter notices')
        compressed = apk.read(matches[0])
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as notice:
        decoded = notice.read(MAX_NOTICE + 1)
    if not decoded or len(decoded) > MAX_NOTICE:
        raise ValueError('Invalid or oversized decoded Flutter notices')
    return {'sha256': sha_file(path), 'bytes': path.stat().st_size,
            'notice_gzip_sha256': hashlib.sha256(compressed).hexdigest(),
            'notice_uncompressed_sha256': hashlib.sha256(decoded).hexdigest(),
            'notice_uncompressed_bytes': len(decoded)}


def audit(sdk, gradle_cache, apk, expected_revision):
    engine, license_hash = engine_files(sdk, expected_revision)
    jars = {}
    for name in ARTIFACTS:
        found = list((gradle_cache / 'io.flutter' / name / f'1.0.0-{engine}').glob('*/*.jar'))
        if len(found) != 1:
            raise ValueError(f'Expected exactly one cached JAR for {name}')
        jars[name] = inspect_jar(found[0])
    return {'flutter_revision': expected_revision, 'engine_revision': engine,
            'engine_source_license_sha256': license_hash, 'cached_jars': jars, 'local_apk': inspect_apk(apk)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--gradle-cache', type=Path, required=True)
    parser.add_argument('--apk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    revision = json.loads((Path(__file__).resolve().parents[1] / 'toolchain.json').read_text())['flutter_revision']
    args.output.write_text(json.dumps(audit(args.sdk, args.gradle_cache, args.apk, revision), indent=2) + '\n')
    print('Recorded pinned Flutter license and local artifact evidence; legal review remains open.')


if __name__ == '__main__':
    main()
