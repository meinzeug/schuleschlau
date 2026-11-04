import gzip
from pathlib import Path
from zipfile import ZipFile

import pytest

from scripts.audit_flutter_license_evidence import inspect_apk, inspect_jar


def test_records_jar_notice_paths(tmp_path: Path):
    jar = tmp_path / 'sample.jar'
    with ZipFile(jar, 'w') as archive:
        archive.writestr('META-INF/LICENSE.txt', 'license')
        archive.writestr('code.class', 'example')
    result = inspect_jar(jar)
    assert result['embedded_notice_paths'] == ['META-INF/LICENSE.txt']
    assert len(result['sha256']) == 64


def test_records_compressed_and_uncompressed_notice_hashes(tmp_path: Path):
    apk = tmp_path / 'sample.apk'
    with ZipFile(apk, 'w') as archive:
        archive.writestr('assets/flutter_assets/NOTICES.Z', gzip.compress(b'example notice'))
    result = inspect_apk(apk)
    assert result['notice_uncompressed_bytes'] == len(b'example notice')
    assert len(result['notice_uncompressed_sha256']) == 64


def test_rejects_missing_and_duplicate_notices(tmp_path: Path):
    apk = tmp_path / 'sample.apk'
    with ZipFile(apk, 'w') as archive:
        archive.writestr('other.txt', 'example')
    with pytest.raises(ValueError, match='Missing'):
        inspect_apk(apk)
    with pytest.warns(UserWarning, match='Duplicate'):
        with ZipFile(apk, 'w') as archive:
            archive.writestr('assets/flutter_assets/NOTICES.Z', gzip.compress(b'first'))
            archive.writestr('assets/flutter_assets/NOTICES.Z', gzip.compress(b'second'))
    with pytest.raises(ValueError, match='duplicate'):
        inspect_apk(apk)


def test_rejects_decompression_bomb(tmp_path: Path, monkeypatch):
    monkeypatch.setattr('scripts.audit_flutter_license_evidence.MAX_NOTICE', 100)
    apk = tmp_path / 'sample.apk'
    with ZipFile(apk, 'w') as archive:
        archive.writestr('assets/flutter_assets/NOTICES.Z', gzip.compress(b'a' * 101))
    with pytest.raises(ValueError, match='oversized'):
        inspect_apk(apk)
