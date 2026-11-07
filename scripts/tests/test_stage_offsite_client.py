"""Tests stage only disposable Git repositories and never call systemd."""
import fcntl
import os
import signal
import subprocess
import sys

import pytest

from scripts import stage_offsite_client as stager


def git(repo, *args):
    return subprocess.run(['/usr/bin/git', '-C', str(repo), *args], check=True, capture_output=True).stdout.decode().strip()


@pytest.fixture
def repository(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir(mode=0o700)
    git(repo, 'init', '-q')
    git(repo, 'config', 'user.name', 'Synthetic Test')
    git(repo, 'config', 'user.email', 'test@example.invalid')
    for index, path in enumerate(stager.FILES):
        file = repo / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(f'synthetic tracked content {index}\n')
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', 'synthetic fixture')
    revision = git(repo, 'rev-parse', 'HEAD')
    dest = tmp_path / 'private-stage'
    dest.mkdir(mode=0o700)
    return repo, dest, revision


def test_stage_and_verify_use_git_revision_and_never_start_a_service(repository, monkeypatch):
    repo, dest, rev = repository
    original = subprocess.run
    calls = []

    def only_git(args, **kwargs):
        calls.append(args)
        assert args[0] == '/usr/bin/git'
        return original(args, **kwargs)

    monkeypatch.setattr(stager.subprocess, 'run', only_git)
    # A dirty checkout cannot alter the staged committed bytes.
    (repo / 'scripts/offsite_backup.py').write_text('uncommitted fixture\n')
    stager.stage(repo, dest, rev)
    stager.verify(repo, dest, rev)
    assert (dest / rev / 'offsite_backup.py').read_text() == 'synthetic tracked content 0\n'
    assert all(c[0] == '/usr/bin/git' for c in calls)
    assert (dest / rev / 'manifest.json').stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        stager.stage(repo, dest, rev)


@pytest.mark.parametrize('change', ['content', 'extra', 'missing', 'symlink', 'mode'])
def test_verify_rejects_changed_candidate(repository, change):
    repo, dest, rev = repository
    stager.stage(repo, dest, rev)
    candidate = dest / rev
    item = candidate / 'offsite_backup.py'
    if change == 'content':
        item.write_text('different fixture')
    elif change == 'extra':
        (candidate / 'unexpected').write_text('extra')
    elif change == 'missing':
        item.unlink()
    elif change == 'symlink':
        item.unlink()
        item.symlink_to(candidate / 'schulpilot-offsite.timer')
    else:
        item.chmod(0o644)
    with pytest.raises((ValueError, OSError)):
        stager.verify(repo, dest, rev)


def test_wrong_or_incomplete_revision_and_untrusted_directory_fail(repository):
    repo, dest, rev = repository
    for value in ('HEAD', rev[:12], 'f' * 40):
        with pytest.raises((ValueError, subprocess.CalledProcessError)):
            stager.stage(repo, dest, value)
    dest.chmod(0o755)
    with pytest.raises(ValueError, match='owner-private'):
        stager.stage(repo, dest, rev)
    dest.chmod(0o700)
    symlink = dest.parent / 'stage-link'
    symlink.symlink_to(dest, target_is_directory=True)
    with pytest.raises(OSError):
        stager.stage(repo, symlink, rev)


def test_git_symlink_blob_rejected(repository):
    repo, dest, _ = repository
    file = repo / 'scripts/offsite_backup.py'
    file.unlink()
    file.symlink_to('../deploy/schulpilot-offsite.timer')
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', 'synthetic symlink')
    with pytest.raises(ValueError, match='regular Git blobs'):
        stager.stage(repo, dest, git(repo, 'rev-parse', 'HEAD'))
    assert set(os.listdir(dest)) == set()


def test_failed_write_leaves_partial_directory_and_never_reuses_it(repository, monkeypatch):
    repo, dest, rev = repository
    original = stager._write

    def fail(directory, name, data):
        if name == 'schulpilot-offsite.service':
            raise OSError('synthetic failure')
        original(directory, name, data)

    monkeypatch.setattr(stager, '_write', fail)
    with pytest.raises(OSError, match='synthetic failure'):
        stager.stage(repo, dest, rev)
    with pytest.raises(ValueError, match='incomplete'):
        stager.verify(repo, dest, rev)
    with pytest.raises(FileExistsError):
        stager.stage(repo, dest, rev)


def test_hardlinked_candidate_is_refused(repository):
    repo, dest, rev = repository
    stager.stage(repo, dest, rev)
    target = dest / rev / 'offsite_backup.py'
    os.link(target, dest / 'extra-link')
    with pytest.raises(ValueError, match='untrusted staged file'):
        stager.verify(repo, dest, rev)


def test_lock_contention_refuses_verification_and_staging(repository):
    repo, dest, rev = repository
    stager.stage(repo, dest, rev)
    lock = os.open(dest / '.stage.lock', os.O_RDWR)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with pytest.raises(TimeoutError, match='stage lock busy'):
            stager.verify(repo, dest, rev, timeout=0)
        with pytest.raises(TimeoutError, match='stage lock busy'):
            stager.stage(repo, dest, rev, timeout=0)
    finally:
        os.close(lock)


def test_sigkill_leaves_incomplete_candidate_unusable(repository):
    repo, dest, rev = repository
    child = os.fork()
    if child == 0:
        original = stager._write

        def kill_after_first(directory, name, data):
            original(directory, name, data)
            os.kill(os.getpid(), signal.SIGKILL)

        stager._write = kill_after_first
        try:
            stager.stage(repo, dest, rev)
        finally:
            os._exit(99)
    _, status = os.waitpid(child, 0)
    assert os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGKILL
    with pytest.raises(ValueError, match='incomplete'):
        stager.verify(repo, dest, rev)
    with pytest.raises(FileExistsError):
        stager.stage(repo, dest, rev)


def test_cli_stages_and_verifies_without_activation(repository):
    repo, dest, rev = repository
    script = os.path.abspath(stager.__file__)
    for action in ('stage', 'verify'):
        result = subprocess.run([sys.executable, script, action, '--repo', str(repo), '--destination', str(dest),
                                 '--revision', rev], check=True, capture_output=True, text=True, timeout=10)
        assert 'No installation, process fence or cutover is authorized.' in result.stdout


def test_sigkill_after_manifest_can_only_recover_by_resyncing_every_file_and_directory(repository, monkeypatch):
    repo, dest, rev = repository
    child = os.fork()
    if child == 0:
        original = stager._write

        def kill_after_manifest(directory, name, data):
            original(directory, name, data)
            if name == 'manifest.json':
                os.kill(os.getpid(), signal.SIGKILL)

        stager._write = kill_after_manifest
        try:
            stager.stage(repo, dest, rev)
        finally:
            os._exit(99)
    _, status = os.waitpid(child, 0)
    assert os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGKILL
    original = os.fsync
    synced = set()

    def record(fd):
        synced.add(os.readlink(f'/proc/self/fd/{fd}'))
        return original(fd)

    monkeypatch.setattr(stager.os, 'fsync', record)
    stager.verify(repo, dest, rev)
    assert {str(dest), str(dest / rev), *(str(dest / rev / name) for name in stager.FILES.values()),
            str(dest / rev / 'manifest.json')} <= synced


@pytest.mark.parametrize('target', ['file', 'manifest', 'candidate-directory', 'base-directory'])
def test_verification_fsync_failure_never_claims_success(repository, monkeypatch, target):
    repo, dest, rev = repository
    stager.stage(repo, dest, rev)
    paths = {'file': dest / rev / 'offsite_backup.py', 'manifest': dest / rev / 'manifest.json',
             'candidate-directory': dest / rev, 'base-directory': dest}
    original = os.fsync

    def fail(fd):
        if os.readlink(f'/proc/self/fd/{fd}') == str(paths[target]):
            raise OSError('synthetic fsync failure')
        return original(fd)

    monkeypatch.setattr(stager.os, 'fsync', fail)
    with pytest.raises(OSError, match='synthetic fsync failure'):
        stager.verify(repo, dest, rev)
