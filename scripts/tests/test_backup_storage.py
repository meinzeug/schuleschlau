"""Synthetic tests; never operate on real mounts or production locks."""
import fcntl
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "deploy"))
from backup_storage import operation_lock, require_volume  # noqa: E402


def test_shared_lock_blocks_cutover(tmp_path):
    path = tmp_path / "stable.lock"
    with operation_lock(path, exclusive=False):
        with path.open("rb") as contender:
            with pytest.raises(BlockingIOError):
                fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
    with operation_lock(path, exclusive=True):
        pass


def test_lock_rejects_symlink_and_hardlink(tmp_path):
    original = tmp_path / "original"
    original.touch(mode=0o600)
    symlink = tmp_path / "symlink"
    symlink.symlink_to(original)
    with pytest.raises(OSError):
        with operation_lock(symlink, exclusive=True):
            pass
    hardlink = tmp_path / "hardlink"
    os.link(original, hardlink)
    with pytest.raises(RuntimeError):
        with operation_lock(hardlink, exclusive=True):
            pass


def test_volume_requires_exact_mountpoint_and_uuid(monkeypatch):
    def fake_run(args, **kwargs):
        assert args[-2:] == ["--mountpoint", "/test/backups"]
        return SimpleNamespace(stdout="01234567-89ab-cdef-0123-456789abcdef\n")
    monkeypatch.setattr(subprocess, "run", fake_run)
    require_volume(Path("/test/backups"), "01234567-89ab-cdef-0123-456789abcdef")
    with pytest.raises(RuntimeError):
        require_volume(Path("/test/backups"), "01234567-89ab-cdef-0123-456789abcdee")
    with pytest.raises(ValueError):
        require_volume(Path("/test/backups"), "not-a-uuid")


def test_offsite_access_checks_names_and_rejects_symlinks(tmp_path, monkeypatch):
    import backup_access

    monkeypatch.setattr(backup_access, "DIRECTORY", tmp_path)
    name = "20261031T120000Z.tar.enc"
    (tmp_path / name).write_bytes(b"synthetic")
    result = backup_access.inventory()
    assert result["backups"][0]["name"] == name
    assert result["backups"][0]["size"] == len(b"synthetic")
    with pytest.raises(ValueError):
        backup_access.open_backup("../private")
    (tmp_path / name).unlink()
    (tmp_path / name).symlink_to(tmp_path / "elsewhere")
    with pytest.raises(OSError):
        backup_access.open_backup(name)


def test_configured_volume_failure_prevents_operation(tmp_path, monkeypatch):
    import backup_storage

    config = tmp_path / 'volume.uuid'
    config.write_text('01234567-89ab-cdef-0123-456789abcdef\n')
    config.chmod(0o600)
    config_ino = config.stat().st_ino
    original_fstat = os.fstat

    def root_owned_config(fd):
        result = original_fstat(fd)
        if result.st_ino == config_ino:
            return SimpleNamespace(st_mode=result.st_mode, st_uid=0, st_nlink=result.st_nlink)
        return result

    def unavailable(*_args):
        raise RuntimeError('volume unavailable')

    monkeypatch.setattr(backup_storage, 'OPERATION_LOCK', tmp_path / 'operation.lock')
    monkeypatch.setattr(backup_storage, 'VOLUME_CONFIG', config)
    monkeypatch.setattr(os, 'fstat', root_owned_config)
    monkeypatch.setattr(backup_storage, 'require_volume', unavailable)
    ran = []
    with pytest.raises(RuntimeError, match='volume unavailable'):
        with backup_storage.guarded_operation():
            ran.append(True)
    assert not ran
