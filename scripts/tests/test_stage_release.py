import errno
import importlib.util
import os
import stat
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


stage = module('stage_release', ROOT / 'deploy/stage_release.py')
prune = module('prune_releases', ROOT / 'deploy/prune_releases.py')
RELEASE = '20261031T200000Z-abcdef0'
CURRENT = '20261030T200000Z-abcdef1'
PREVIOUS = '20261029T200000Z-abcdef2'


@pytest.fixture
def root(tmp_path):
    base = tmp_path / 'schulpilot'
    base.mkdir(mode=0o700)
    releases = base / 'releases'
    releases.mkdir(mode=0o755)
    for name in (CURRENT, PREVIOUS):
        (releases / name).mkdir()
    (base / 'current').symlink_to(releases / CURRENT)
    (base / 'previous').symlink_to(releases / PREVIOUS)
    return base


def test_unfinished_upload_is_invisible_to_old_prune_then_published_atomically(root):
    owner = os.geteuid()
    stage.prepare(root, RELEASE, owner)
    partial = root / 'staging' / RELEASE
    (partial / 'upload-in-progress').write_text('incomplete')
    assert stat.S_IMODE((root / 'staging').stat().st_mode) == 0o700
    assert prune.plan_prune(root / 'releases', root / 'current', root / 'previous') == []
    assert not (root / 'releases' / RELEASE).exists()
    (partial / 'upload-in-progress').write_text('verified')
    stage.publish(root, RELEASE, owner)
    assert not partial.exists()
    published = root / 'releases' / RELEASE
    assert (published / 'upload-in-progress').read_text() == 'verified'
    assert stat.S_IMODE(published.stat().st_mode) == 0o755
    # An old prune can still remove a published but not yet activated release.
    assert prune.plan_prune(root / 'releases', root / 'current', root / 'previous') == [published]


def test_prune_during_paused_upload_cannot_delete_staging(root, monkeypatch):
    owner = os.geteuid()
    stage.prepare(root, RELEASE, owner)
    partial = root / 'staging' / RELEASE
    stale = root / 'releases' / '20261028T200000Z-abcdef3'
    stale.mkdir()
    started, proceed = threading.Event(), threading.Event()

    def upload():
        (partial / 'part').write_text('first')
        started.set()
        assert proceed.wait(5)
        (partial / 'part').write_text('complete')

    thread = threading.Thread(target=upload)
    thread.start()
    try:
        assert started.wait(5)
        monkeypatch.setattr(prune, 'BASE', root)
        monkeypatch.setattr(prune, 'RELEASES', root / 'releases')
        monkeypatch.setattr(prune, '_assert_services_use_kept_releases', lambda *_: None)
        monkeypatch.setattr(prune.sys, 'argv', ['prune', '--apply'])
        assert prune.main() == 0
        assert not stale.exists()
        assert (partial / 'part').read_text() == 'first'
    finally:
        proceed.set()
        thread.join(timeout=5)
    assert not thread.is_alive()
    assert (partial / 'part').read_text() == 'complete'


def test_collision_preserves_existing_release_and_staging(root):
    owner = os.geteuid()
    stage.prepare(root, RELEASE, owner)
    destination = root / 'releases' / RELEASE
    destination.mkdir()
    (destination / 'keep').write_text('original')
    with pytest.raises(FileExistsError):
        stage.publish(root, RELEASE, owner)
    assert (destination / 'keep').read_text() == 'original'
    assert stat.S_IMODE((root / 'staging' / RELEASE).stat().st_mode) == 0o700


def test_same_release_is_not_prepared_twice(root):
    stage.prepare(root, RELEASE, os.geteuid())
    with pytest.raises(FileExistsError):
        stage.prepare(root, RELEASE, os.geteuid())


@pytest.mark.parametrize('invalid', ['../escape', 'a', '20261031T200000Z-ABCD123', '20261031T200000Z-abcdef0/other'])
def test_invalid_release_id_is_rejected(root, invalid):
    with pytest.raises(ValueError):
        stage.prepare(root, invalid, os.geteuid())


def test_refuses_symlink_or_public_staging(root, tmp_path):
    (root / 'staging').symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(OSError):
        stage.prepare(root, RELEASE, os.geteuid())
    (root / 'staging').unlink()
    (root / 'staging').mkdir(mode=0o755)
    with pytest.raises(ValueError, match='permissions'):
        stage.prepare(root, RELEASE, os.geteuid())


def test_refuses_changed_staging_or_release_parent(root):
    owner = os.geteuid()
    stage.prepare(root, RELEASE, owner)
    (root / 'releases').chmod(0o777)
    with pytest.raises(ValueError, match='permissions'):
        stage.publish(root, RELEASE, owner)
    assert (root / 'staging' / RELEASE).is_dir()


def test_rename_failure_is_closed_and_leaves_private_stage(root, monkeypatch):
    owner = os.geteuid()
    stage.prepare(root, RELEASE, owner)
    def fail(*_args):
        raise OSError(errno.EXDEV, 'different devices')
    monkeypatch.setattr(stage, '_rename_noreplace', fail)
    with pytest.raises(OSError) as failure:
        stage.publish(root, RELEASE, owner)
    assert failure.value.errno == errno.EXDEV
    assert not (root / 'releases' / RELEASE).exists()
    assert stat.S_IMODE((root / 'staging' / RELEASE).stat().st_mode) == 0o700
