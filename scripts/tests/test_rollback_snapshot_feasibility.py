"""Adversarial, isolated evidence for a possible future rollback snapshot.

This is not production rollback code and does not authenticate an APK or
approve a release. It exercises the already deployed legacy pruning function.
"""
import hashlib
import runpy
import shutil
from pathlib import Path

import pytest

from deploy import stage_release
from scripts.release_attestation import tree

LEGACY = Path(__file__).parent / 'fixtures/prune_releases_534009f.py'
LEGACY_SHA256 = '22d6e9210c6c9966e678d0945246927a24396cf697923c0338c6631b0bddae47'
CURRENT = '20261105T030000Z-1111111'
PREVIOUS = '20261105T020000Z-2222222'
TARGET = '20261105T010000Z-3333333'
SNAPSHOT = '20261105T040000Z-4444444'


def release(path):
    path.mkdir(mode=0o700)
    for name in ('backend', 'deploy', 'workers', 'web'):
        (path / name).mkdir()
    (path / 'backend' / 'important.py').write_text('synthetic code\n')
    (path / 'backend' / 'requirements.lock').write_text('synthetic requirements\n')
    (path / 'deploy' / 'activate.py').write_text('synthetic activation\n')
    (path / 'workers' / 'worker.py').write_text('synthetic worker\n')
    (path / 'web' / 'index.html').write_text('synthetic page\n')


def fixture(tmp_path):
    releases = tmp_path / 'releases'
    releases.mkdir(mode=0o700)
    for name in (CURRENT, PREVIOUS, TARGET):
        release(releases / name)
    (tmp_path / 'current').symlink_to(releases / CURRENT)
    (tmp_path / 'previous').symlink_to(releases / PREVIOUS)
    assert hashlib.sha256(LEGACY.read_bytes()).hexdigest() == LEGACY_SHA256
    old = runpy.run_path(str(LEGACY))
    plan = old['plan_prune'](releases, tmp_path / 'current', tmp_path / 'previous')
    assert plan == [releases / TARGET]
    lease = stage_release.acquire_lock(tmp_path, 'rollback', TARGET, stage='activating')
    stage_release.guard_legacy_prune(tmp_path, TARGET, lease['token'])
    return releases, plan, old


def evidence(root):
    return (tree(root, ['backend', 'deploy', 'workers'], exclude_cache=True), tree(root, ['web']))


def test_new_snapshot_is_not_in_previously_computed_legacy_delete_list(tmp_path):
    releases, plan, old = fixture(tmp_path)
    expected = evidence(releases / TARGET)
    # The new path is published only after the guard. It did not exist when
    # old prune selected candidates. This alone does not verify the copied code.
    shutil.copytree(releases / TARGET, releases / SNAPSHOT)
    with pytest.raises(old['PruneError'], match='unexpected entry'):
        old['plan_prune'](releases, tmp_path / 'current', tmp_path / 'previous')
    for candidate in plan:
        shutil.rmtree(candidate)
    assert not (releases / TARGET).exists()
    assert evidence(releases / SNAPSHOT) == expected


def test_successful_copy_can_silently_omit_a_file_deleted_before_scandir(tmp_path):
    releases, _, _ = fixture(tmp_path)
    source = releases / TARGET
    expected = evidence(source)
    # A pre-existing rmtree can remove just one not-yet-enumerated file while
    # leaving both files the activation precheck happens to inspect.
    (source / 'backend' / 'important.py').unlink()
    snapshot = releases / SNAPSHOT
    shutil.copytree(source, snapshot)
    assert (snapshot / 'web' / 'index.html').is_file()
    assert (snapshot / 'backend' / 'requirements.lock').is_file()
    assert evidence(snapshot) != expected


def test_snapshot_tree_rejects_a_symlink_before_it_can_be_published(tmp_path):
    releases, _, _ = fixture(tmp_path)
    source = releases / TARGET
    outside = tmp_path / 'synthetic-outside.txt'
    outside.write_text('not part of the release')
    (source / 'backend' / 'unexpected').symlink_to(outside)
    snapshot = releases / SNAPSHOT
    # Preserve the link here only to demonstrate that the existing digest
    # walker refuses it. A production copier must additionally avoid following
    # links while reading and never expose private staging before validation.
    shutil.copytree(source, snapshot, symlinks=True)
    with pytest.raises(ValueError, match='Non-regular release file'):
        evidence(snapshot)
