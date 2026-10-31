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
        return SimpleNamespace(stdout="0123-abcd\n")
    monkeypatch.setattr(subprocess, "run", fake_run)
    require_volume(Path("/test/backups"), "0123-abcd")
    with pytest.raises(RuntimeError):
        require_volume(Path("/test/backups"), "0123-abce")
    with pytest.raises(ValueError):
        require_volume(Path("/test/backups"), "not-a-uuid")
