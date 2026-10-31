import base64
import importlib.util
import json
import subprocess
import zipfile
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / 'release_attestation.py'
spec = importlib.util.spec_from_file_location('release_attestation', MODULE)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


def write(root, path, data):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


def simulated_verified_apk(apk, root):
    # APK signer validation is exercised separately; synthetic fixtures are unsigned.
    return {'sha256': release.digest(apk), 'size_bytes': apk.stat().st_size}


@pytest.fixture
def built(tmp_path):
    root = tmp_path
    for path, data in {'app/pubspec.yaml': b'version: 1.0.0+1\n', 'toolchain.json': b'{}',
                       'backend/app.py': b'backend', 'deploy/unit': b'unit', 'workers/main': b'worker',
                       'app/build/web/index.html': b'web', 'artifacts/schulpilot-play.aab': b'play'}.items():
        write(root, path, data)
    commit = 'a' * 40
    raw = release.encode(release.payload(root, commit))
    write(root, 'app/build/release-attestation/' + release.PROOF, raw)
    apk = root / 'artifacts/schulpilot-android.apk'
    with zipfile.ZipFile(apk, 'w') as archive:
        archive.writestr('assets/' + release.PROOF, raw)
    write(root, 'artifacts/android-release.json', release.encode({'sha256': release.digest(apk), 'size_bytes': apk.stat().st_size}))
    write(root, 'artifacts/release-attestation.json', release.encode({'attestation': json.loads(raw), 'apk_sha256': release.digest(apk)}))
    return root, commit


def test_accepts_matching_artifacts(built):
    root, commit = built
    sha, proof, _ = release.verify(root, commit, simulated_verified_apk)
    assert sha == release.digest(root / 'artifacts/schulpilot-android.apk')
    assert json.loads(base64.b64decode(proof))['source_commit'] == commit


def test_repair_binding_requires_verified_hash_and_signed_commit(built):
    root, commit = built
    _, proof, _ = release.verify(root, commit, simulated_verified_apk)
    info = {'verified': True, 'source_commit': commit, 'sha256': 'a' * 64}
    parsed_proof = json.loads(base64.b64decode(proof))
    assert release.bind_repair(info, parsed_proof, commit) == 'a' * 64
    for changed in (
        {**info, 'verified': False},
        {**info, 'source_commit': 'b' * 40},
        {**info, 'sha256': 'x' * 64},
        {**info, 'sha256': None},
    ):
        with pytest.raises(ValueError):
            release.bind_repair(changed, parsed_proof, commit)
    with pytest.raises(ValueError):
        release.bind_repair(info, {**parsed_proof, 'source_commit': 'c' * 40}, commit)
    command = ['python3', str(MODULE), 'bind-repair', proof, commit]
    result = subprocess.run(command, input=json.dumps(info), text=True, capture_output=True, check=True)
    assert result.stdout.strip() == 'a' * 64
    result = subprocess.run(command, input=json.dumps({**info, 'verified': False}), text=True, capture_output=True)
    assert result.returncode != 0


@pytest.mark.parametrize('path', ['app/build/web/index.html', 'backend/app.py', 'deploy/unit', 'workers/main',
                                  'artifacts/schulpilot-play.aab', 'toolchain.json'])
def test_rejects_changed_inputs(built, path):
    root, commit = built
    write(root, path, b'manipulated')
    with pytest.raises(ValueError):
        release.verify(root, commit, simulated_verified_apk)


def test_rejects_other_commit_and_tampered_manifest(built):
    root, commit = built
    with pytest.raises(ValueError):
        release.verify(root, 'b' * 40, simulated_verified_apk)
    write(root, 'artifacts/release-attestation.json', b'{}\n')
    with pytest.raises(ValueError):
        release.verify(root, commit, simulated_verified_apk)


def test_old_apk_same_version_and_rewritten_manifest_is_rejected(built):
    root, commit = built
    old_proof = release.payload(root, 'b' * 40)
    apk = root / 'artifacts/schulpilot-android.apk'
    with zipfile.ZipFile(apk, 'w') as archive:
        archive.writestr('assets/' + release.PROOF, release.encode(old_proof))
    write(root, 'artifacts/android-release.json', release.encode({'sha256': release.digest(apk), 'size_bytes': apk.stat().st_size}))
    raw = (root / 'app/build/release-attestation' / release.PROOF).read_bytes()
    write(root, 'artifacts/release-attestation.json', release.encode({'attestation': json.loads(raw), 'apk_sha256': release.digest(apk)}))
    with pytest.raises(ValueError, match='APK attestation'):
        release.verify(root, commit, simulated_verified_apk)


def test_staged_checks_actual_transferred_files(built, tmp_path):
    import shutil
    root, commit = built
    sha, proof, public_sha = release.verify(root, commit, simulated_verified_apk)
    staged = tmp_path / 'staged'
    for name in ('backend', 'deploy', 'workers'):
        shutil.copytree(root / name, staged / name)
    shutil.copytree(root / 'app/build/web', staged / 'web')
    write(staged, 'downloads/schulpilot-android.apk', (root / 'artifacts/schulpilot-android.apk').read_bytes())
    write(staged, 'android-release.json', (root / 'artifacts/android-release.json').read_bytes())
    repair = write(staged, 'repair-source.tar.gz', b'verified repair source')
    repair_sha = release.digest(repair)
    command = ['python3', '-', 'staged', str(staged), sha, proof, public_sha, repair_sha]
    source = MODULE.read_text()
    subprocess.run(command, input=source, text=True, check=True)
    repair.write_bytes(b'swapped after local verification')
    failed = subprocess.run(command, input=source, text=True, capture_output=True)
    assert failed.returncode != 0 and 'repair source' in failed.stderr
    repair.unlink()
    failed = subprocess.run(command, input=source, text=True, capture_output=True)
    assert failed.returncode != 0 and 'repair source' in failed.stderr
    original_repair = write(staged, 'other-archive', b'verified repair source')
    repair.symlink_to(original_repair)
    failed = subprocess.run(command, input=source, text=True, capture_output=True)
    assert failed.returncode != 0 and 'repair source' in failed.stderr
    repair.unlink()
    repair.write_bytes(original_repair.read_bytes())
    bad_command = [*command[:-1], 'x' * 64]
    assert subprocess.run(bad_command, input=source, text=True, capture_output=True).returncode != 0
    subprocess.run(command, input=source, text=True, check=True)
    uploaded_apk = staged / 'downloads/schulpilot-android.apk'
    original = uploaded_apk.read_bytes()
    uploaded_apk.write_bytes(original + b'changed during upload')
    assert subprocess.run(command, input=source, text=True, capture_output=True).returncode != 0
    uploaded_apk.write_bytes(original)
    write(staged, 'backend/ignored-extra', b'unexpected')
    assert subprocess.run(command, input=source, text=True, capture_output=True).returncode != 0


def test_deploy_checks_verified_archive_after_upload_and_immediately_before_activation():
    script = (MODULE.parent / 'deploy.sh').read_text()
    verify = script.index('prepare_repair_source.py')
    upload = script.index('rsync -a --no-links artifacts/repair-source.tar.gz')
    permissions = script.index('chown root:schulpilot')
    first = script.index('python3 - staged')
    second = script.index('python3 - staged', first + 1)
    publish = script.index('python3 - publish')
    third = script.index('python3 - staged', second + 1)
    activate = script.index('deploy/activate.py $release')
    assert verify < upload < permissions < first < second < publish < third < activate
    assert 'remote_stage="/opt/schulpilot/staging/$release"' in script
    assert 'python3 - prepare "$release" < deploy/stage_release.py' in script
    assert script.count('"$release_android_sha" "$repair_sha" < scripts/release_attestation.py') == 3


def test_dirty_worktree_and_ignored_backend_extra_rejected(built, monkeypatch):
    root, _ = built
    def fake_git(args, cwd):
        if args[1] == 'status':
            return b'?? user-file\n'
        raise AssertionError(args)
    monkeypatch.setattr(release.subprocess, 'check_output', fake_git)
    with pytest.raises(ValueError, match='clean working tree'):
        release.clean_commit(root)
    def clean_git(args, cwd):
        if args[1] == 'status':
            return b''
        if args[1] == 'rev-parse':
            return b'a' * 40 + b'\n'
        return b'backend/app.py\0deploy/unit\0workers/main\0'
    monkeypatch.setattr(release.subprocess, 'check_output', clean_git)
    write(root, 'backend/private.env', b'extra')
    with pytest.raises(ValueError, match='ignored file'):
        release.clean_commit(root)
