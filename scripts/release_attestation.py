"""Bind the release inputs to an attestation inside the signed direct APK.

The APK signature is verified separately by android_manifest.py before verify.
This is build provenance, not a proof that the build environment is trustworthy.
"""
import base64
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF = 'schulpilot-release.json'
EXCLUDED_DIRS = {'__pycache__', '.pytest_cache'}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def tree(root, names, exclude_cache=False):
    entries = []
    for name in names:
        top = root / name
        if not top.is_dir() or top.is_symlink():
            raise ValueError(f'Missing or unsafe directory: {name}')
        for directory, dirs, files in os.walk(top, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not exclude_cache or d not in EXCLUDED_DIRS)
            for dirname in dirs:
                if (Path(directory) / dirname).is_symlink():
                    raise ValueError('Symlinks are not allowed in release trees')
            for filename in sorted(files):
                path = Path(directory) / filename
                if path.is_symlink() or not path.is_file():
                    raise ValueError('Non-regular release file')
                entries.append([path.relative_to(root).as_posix(), bool(path.stat().st_mode & 0o111), digest(path)])
    return hashlib.sha256(json.dumps(sorted(entries), separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def clean_commit(root):
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=root)
    if git('status', '--porcelain', '--untracked-files=all').strip():
        raise ValueError('Release requires a clean working tree, including untracked files')
    commit = git('rev-parse', 'HEAD').decode().strip()
    # rsync must never carry ignored extras such as private settings.
    tracked = set(git('ls-files', '-z', '--', 'backend', 'deploy', 'workers').decode().split('\0'))
    for name in ('backend', 'deploy', 'workers'):
        for directory, dirs, files in os.walk(root / name, followlinks=False):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            for item in dirs + files:
                path = Path(directory) / item
                if path.is_symlink():
                    raise ValueError('Symlinks are not allowed in deployed source')
                if path.is_file() and path.relative_to(root).as_posix() not in tracked:
                    raise ValueError('Untracked or ignored file in deployed source')
    return commit


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def bind_repair(repair, proof, commit):
    """Bind the canonical verified archive to the same commit as the signed APK."""
    if not isinstance(repair, dict) or not isinstance(proof, dict):
        raise ValueError('Invalid repair binding')
    sha = repair.get('sha256')
    if (repair.get('verified') is not True or repair.get('source_commit') != commit or proof.get('format') != 2
            or proof.get('source_commit') != commit or not isinstance(sha, str)
            or not re.fullmatch(r'[0-9a-f]{64}', sha) or proof.get('repair_sha256') != sha):
        raise ValueError('Repair source and signed release do not match')
    return sha


def payload(root, commit):
    version = re.search(r'^version:\s*(\S+)$', (root / 'app/pubspec.yaml').read_text(), re.M)
    if not version:
        raise ValueError('Missing app version')
    repair = root / 'artifacts/repair-source.tar.gz'
    if repair.is_symlink() or not repair.is_file():
        raise ValueError('Missing or unsafe repair source archive')
    return {'format': 2, 'source_commit': commit, 'version': version[1],
            'toolchain_sha256': digest(root / 'toolchain.json'),
            'sources_sha256': tree(root, ['backend', 'deploy', 'workers'], exclude_cache=True),
            'web_sha256': tree(root / 'app/build', ['web']),
            'play_aab_sha256': digest(root / 'artifacts/schulpilot-play.aab'),
            'repair_sha256': digest(repair)}


def apk_proof(apk):
    with zipfile.ZipFile(apk) as archive:
        matches = [entry for entry in archive.infolist() if entry.filename == 'assets/' + PROOF]
        if len(matches) != 1 or matches[0].file_size > 4096:
            raise ValueError('APK must contain exactly one release attestation')
        return archive.read(matches[0])


def verify(root, commit, verify_apk=None):
    raw = (root / 'app/build/release-attestation' / PROOF).read_bytes()
    if raw != encode(payload(root, commit)):
        raise ValueError('Release attestation does not match current sources and artifacts')
    apk = root / 'artifacts/schulpilot-android.apk'
    public_raw = (root / 'artifacts/android-release.json').read_bytes()
    public_metadata = json.loads(public_raw)
    if verify_apk is None:
        spec = importlib.util.spec_from_file_location('android_manifest', Path(__file__).with_name('android_manifest.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        verify_apk = module.verify_apk
    # Signer and embedded proof must be checked on the same private snapshot.
    with tempfile.TemporaryDirectory(prefix='schulpilot-release-') as temporary:
        snapshot = Path(temporary) / 'release.apk'
        shutil.copyfile(apk, snapshot)
        checked_metadata = verify_apk(snapshot, root)
        if checked_metadata != public_metadata:
            raise ValueError('APK differs from the independently verified Android metadata')
        if apk_proof(snapshot) != raw:
            raise ValueError('Signed APK attestation differs from release attestation')
        apk_sha = digest(snapshot)
    manifest = root / 'artifacts/release-attestation.json'
    if manifest.read_bytes() != encode({'attestation': json.loads(raw), 'apk_sha256': apk_sha}):
        raise ValueError('Release manifest does not match the signed APK and attestation')
    return apk_sha, base64.b64encode(raw).decode('ascii'), hashlib.sha256(public_raw).hexdigest()


def main():
    mode = sys.argv[1]
    if mode == 'bind-repair':
        print(bind_repair(json.load(sys.stdin), json.loads(base64.b64decode(sys.argv[2], validate=True)), sys.argv[3]))
        return
    if mode == 'staged':
        root = Path(sys.argv[2])
        apk_sha, raw, public_sha, repair_sha = sys.argv[3], base64.b64decode(sys.argv[4], validate=True), sys.argv[5], sys.argv[6]
        proof = json.loads(raw)
        repair = root / 'repair-source.tar.gz'
        if (not re.fullmatch(r'[0-9a-f]{64}', repair_sha) or proof.get('format') != 2
                or proof.get('repair_sha256') != repair_sha or repair.is_symlink()
                or not repair.is_file() or digest(repair) != repair_sha):
            raise ValueError('Uploaded repair source differs from verified archive')
        if raw != encode(proof) or digest(root / 'downloads/schulpilot-android.apk') != apk_sha:
            raise ValueError('Uploaded APK differs from verified APK')
        if apk_proof(root / 'downloads/schulpilot-android.apk') != raw:
            raise ValueError('Uploaded attestation differs')
        if digest(root / 'android-release.json') != public_sha:
            raise ValueError('Uploaded Android metadata differs')
        if tree(root, ['backend', 'deploy', 'workers'], exclude_cache=True) != proof['sources_sha256'] or tree(root, ['web']) != proof['web_sha256']:
            raise ValueError('Uploaded release tree differs from signed attestation')
        return
    commit = clean_commit(ROOT)
    if mode == 'check-source':
        print(commit)
    elif mode in ('prepare', 'finish'):
        if commit != sys.argv[2]:
            raise ValueError('Source commit changed during build')
        proof_path = ROOT / 'app/build/release-attestation' / PROOF
        if mode == 'prepare':
            proof_path.parent.mkdir(parents=True, exist_ok=True)
            proof_path.write_bytes(encode(payload(ROOT, commit)))
        else:
            raw = proof_path.read_bytes()
            if raw != encode(payload(ROOT, commit)) or apk_proof(ROOT / 'artifacts/schulpilot-android.apk') != raw:
                raise ValueError('Build inputs or embedded attestation changed')
            (ROOT / 'artifacts/release-attestation.json').write_bytes(encode({'attestation': json.loads(raw), 'apk_sha256': digest(ROOT / 'artifacts/schulpilot-android.apk')}))
    elif mode == 'verify':
        print(*verify(ROOT, commit))
    else:
        raise ValueError('Unknown command')


if __name__ == '__main__':
    main()
