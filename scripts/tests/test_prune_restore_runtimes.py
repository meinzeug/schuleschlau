import json
import os
import time
from contextlib import contextmanager

import pytest

from deploy import prune_restore_runtimes as retention
from deploy.prune_restore_runtimes import RetentionError, _reference_names, plan, process_references
from deploy.stage_release import acquire_lock, release_lock


def make(root, name, when):
    path = root / name
    path.mkdir(mode=0o700)
    os.utime(path, (when, when))
    return path


def test_keeps_current_previous_and_newest_and_only_removes_old_preparations(tmp_path):
    now = time.time() + 7200
    current, previous, newest, older = ('a' * 40, 'b' * 40, 'c' * 40, 'd' * 40)
    for i, name in enumerate((older, current, previous, newest), 1):
        make(tmp_path, name, i)
    stale = make(tmp_path, '.prepare-' + 'e' * 40, 1)
    fresh = make(tmp_path, '.prepare-' + 'f' * 40, now - 10)
    operator = tmp_path / 'operator-note'
    operator.write_text('kept')
    result = plan(tmp_path, {current, previous}, now=now)
    assert set(result) == {tmp_path / older, stale}
    assert fresh not in result and operator.exists()


def test_extra_slot_keeps_only_two_protected_versions(tmp_path):
    for i, name in enumerate(('a' * 40, 'b' * 40, 'c' * 40), 1):
        make(tmp_path, name, i)
    assert plan(tmp_path, {'a' * 40, 'b' * 40}, limit=2, now=time.time() + 7200) == [tmp_path / ('c' * 40)]


def test_never_deletes_a_runtime_in_use_even_when_over_limit(tmp_path):
    for name in ('a' * 40, 'b' * 40, 'c' * 40, 'd' * 40):
        make(tmp_path, name, 1)
    with pytest.raises(RetentionError, match='in use'):
        plan(tmp_path, {'a' * 40, 'b' * 40, 'c' * 40, 'd' * 40}, now=time.time() + 7200)


def test_never_removes_newly_prepared_runtime(tmp_path):
    for name in ('a' * 40, 'b' * 40, 'c' * 40, 'd' * 40):
        make(tmp_path, name, 1)
    with pytest.raises(RetentionError, match='in use'):
        plan(tmp_path, {'a' * 40, 'b' * 40})


def test_rejects_symlink_or_untrusted_directory(tmp_path):
    target = tmp_path / 'other'
    target.mkdir()
    (tmp_path / ('a' * 40)).symlink_to(target)
    with pytest.raises(RetentionError, match='Untrusted'):
        plan(tmp_path, set())
    assert target.is_dir()


def test_process_and_service_path_extraction_does_not_log_contents():
    commit = 'a' * 40
    assert _reference_names(f'path=/opt/schulpilot/restore-runtimes/{commit}/venv/bin/python ;') == {commit}
    assert _reference_names(f'/opt/schulpilot/restore-runtimes/{commit}\x00other') == {commit}


def test_process_scan_protects_command_mappings_and_file_descriptors(tmp_path):
    process = tmp_path / '123'
    process.mkdir()
    (process / 'fd').mkdir()
    (process / 'cmdline').write_bytes(b'python\x00/opt/schulpilot/restore-runtimes/' + b'a' * 40 + b'/run.py\x00')
    (process / 'maps').write_text('0-1 r-xp 0 0 0 /opt/schulpilot/restore-runtimes/' + 'b' * 40 + '/lib.so\n')
    (process / 'fd' / '4').symlink_to('/opt/schulpilot/restore-runtimes/' + 'c' * 40 + '/file')
    assert process_references(tmp_path) == {'a' * 40, 'b' * 40, 'c' * 40}


def fake_installation(tmp_path, monkeypatch):
    base = tmp_path / 'app'
    base.mkdir(mode=0o700)
    releases = base / 'releases'
    releases.mkdir()
    for name, commit in (('20261123T000001Z-aaaaaaa', 'a' * 40), ('20261123T000000Z-bbbbbbb', 'b' * 40)):
        path = releases / name
        path.mkdir()
        (path / 'release.json').write_text(json.dumps({'source_commit': commit}))
    (base / 'current').symlink_to(releases / '20261123T000001Z-aaaaaaa')
    (base / 'previous').symlink_to(releases / '20261123T000000Z-bbbbbbb')
    root = base / 'restore-runtimes'
    root.mkdir(mode=0o700)
    make(root, 'a' * 40, 1)
    make(root, 'b' * 40, 1)
    monkeypatch.setattr(retention, 'BASE', base)
    monkeypatch.setattr(retention, 'RUNTIMES', root)
    monkeypatch.setattr(retention, 'verify_restore', lambda _: None)
    monkeypatch.setattr(retention, 'systemd_references', lambda: set())
    monkeypatch.setattr(retention, 'process_references', lambda: set())
    monkeypatch.setattr(retention, 'require_root', lambda: None)
    return base


def test_unavailable_backup_volume_does_not_leave_a_maintenance_lease(tmp_path, monkeypatch):
    base = fake_installation(tmp_path, monkeypatch)
    @contextmanager
    def unavailable(**kwargs):
        raise RuntimeError('volume unavailable')
        yield
    monkeypatch.setattr(retention, 'guarded_operation', unavailable)
    monkeypatch.setattr('sys.argv', ['prune', '--apply'])
    assert retention.main() == 2
    assert not (base / '.deploy.lock').exists()


def test_running_deployment_blocks_runtime_cleanup(tmp_path, monkeypatch):
    base = fake_installation(tmp_path, monkeypatch)
    lock = acquire_lock(base, 'deploy', '20261123T000002Z-ccccccc')
    try:
        monkeypatch.setattr('sys.argv', ['prune', '--apply'])
        assert retention.main() == 2
        assert len(list((base / 'restore-runtimes').iterdir())) == 2
    finally:
        release_lock(base, lock['token'])
