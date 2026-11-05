"""Offline filesystem-order tests; no assertion about power-loss survival."""
import json
import os
import stat
import sys
from pathlib import Path
from threading import Event, Thread

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "deploy"))
import backup  # noqa: E402


def paths(tmp_path):
    return tmp_path / "synthetic.partial", tmp_path / "20261105T100000Z.tar.enc"


def test_ciphertext_status_and_directory_are_synced_in_publication_order(tmp_path, monkeypatch):
    partial, final = paths(tmp_path)
    partial.write_bytes(b"synthetic-complete-ciphertext-and-tag")
    events = []
    real_fsync, real_replace = os.fsync, Path.replace

    def sync(fd):
        mode = os.fstat(fd).st_mode
        name = Path(os.readlink(f"/proc/self/fd/{fd}")).name
        events.append("sync-dir" if stat.S_ISDIR(mode) else "sync-status" if name.startswith(".backup-status-") else "sync-ciphertext")
        return real_fsync(fd)

    def replace(source, target):
        events.append("rename-status" if Path(target).name.endswith(".journal.json") else "rename-archive")
        return real_replace(source, target)

    monkeypatch.setattr(backup.os, "fsync", sync)
    monkeypatch.setattr(Path, "replace", replace)
    backup.publish_backup(partial, final, "present")
    assert events == ["sync-ciphertext", "sync-status", "rename-status", "sync-dir", "rename-archive", "sync-dir"]
    assert final.read_bytes() == b"synthetic-complete-ciphertext-and-tag"
    assert json.loads(backup.status_path(final).read_text()) == {"backup": final.name, "journal": "present"}
    assert not partial.exists()


@pytest.mark.parametrize("failed_step", ["ciphertext", "status", "status_directory", "archive_directory"])
def test_any_sync_error_reports_failure_without_destroying_existing_data(tmp_path, monkeypatch, failed_step):
    partial, final = paths(tmp_path)
    partial.write_bytes(b"synthetic-encrypted-data")
    older = tmp_path / "20261104T100000Z.tar.enc"
    older.write_bytes(b"preserve-older-backup")
    original = os.fsync
    calls = {"directory": 0}

    def sync(fd):
        mode = os.fstat(fd).st_mode
        name = Path(os.readlink(f"/proc/self/fd/{fd}")).name
        if stat.S_ISDIR(mode):
            calls["directory"] += 1
            current = "status_directory" if calls["directory"] == 1 else "archive_directory"
        elif name.startswith(".backup-status-"):
            current = "status"
        else:
            current = "ciphertext"
        if current == failed_step:
            raise OSError("synthetic fsync error")
        return original(fd)

    monkeypatch.setattr(backup.os, "fsync", sync)
    with pytest.raises(OSError, match="synthetic fsync"):
        backup.publish_backup(partial, final, "present")
    assert older.read_bytes() == b"preserve-older-backup"
    assert not list(tmp_path.glob(".backup-status-*"))
    if failed_step == "archive_directory":
        # A rename was already visible. Its durable outcome is unknown; do
        # not delete it or assert either success or power-loss survival.
        assert final.read_bytes() == b"synthetic-encrypted-data"
        assert backup.status_path(final).exists()
    else:
        assert not final.exists()
        assert partial.read_bytes() == b"synthetic-encrypted-data"


def test_rejects_linked_temporary_or_existing_dangling_final(tmp_path):
    partial, final = paths(tmp_path)
    victim = tmp_path / "existing"
    victim.write_bytes(b"must-not-change")
    partial.symlink_to(victim)
    with pytest.raises(OSError):
        backup.publish_backup(partial, final, "present")
    partial.unlink()
    partial.write_bytes(b"new")
    final.symlink_to(tmp_path / "absent")
    with pytest.raises(FileExistsError):
        backup.publish_backup(partial, final, "present")
    assert victim.read_bytes() == b"must-not-change" and final.is_symlink()


def test_rejects_partial_from_another_directory(tmp_path):
    partial = tmp_path / "elsewhere" / "backup.partial"
    partial.parent.mkdir()
    partial.write_bytes(b"synthetic")
    with pytest.raises(ValueError, match="destination"):
        backup.publish_backup(partial, tmp_path / "backup.tar.enc", "present")
    assert partial.read_bytes() == b"synthetic"


def test_temp_inode_replacement_is_rejected_before_archive_publish(tmp_path, monkeypatch):
    partial, final = paths(tmp_path)
    partial.write_bytes(b"first")
    write_status = backup.write_status

    def replace_temporary(*args):
        write_status(*args)
        partial.unlink()
        partial.write_bytes(b"different")

    monkeypatch.setattr(backup, "write_status", replace_temporary)
    with pytest.raises(RuntimeError, match="changed"):
        backup.publish_backup(partial, final, "present")
    assert not final.exists()
    assert partial.read_bytes() == b"different"


def test_hardlinked_temporary_is_rejected(tmp_path):
    partial, final = paths(tmp_path)
    partial.write_bytes(b"synthetic")
    os.link(partial, tmp_path / "second-name")
    with pytest.raises(RuntimeError, match="changed"):
        backup.publish_backup(partial, final, "present")
    assert not final.exists()


@pytest.mark.parametrize("exclusive", [False, True])
def test_readers_and_retention_wait_for_durable_archive_status_pair(tmp_path, monkeypatch, exclusive):
    partial, final = paths(tmp_path)
    partial.write_bytes(b"synthetic")
    arrived, release, attempting, completed = Event(), Event(), Event(), Event()
    errors, observed = [], []
    original = backup.sync_directory
    count = 0

    def pause_after_status(directory):
        nonlocal count
        original(directory)
        count += 1
        if count == 1:
            arrived.set()
            if not release.wait(5):
                raise TimeoutError("synthetic publication pause")

    def writer():
        try:
            backup.publish_backup(partial, final, "present")
        except BaseException as error:
            errors.append(error)

    def reader():
        try:
            attempting.set()
            with backup.backup_lock(tmp_path, exclusive=exclusive):
                observed.append((final.read_bytes(), json.loads(backup.status_path(final).read_text())))
        except BaseException as error:
            errors.append(error)
        finally:
            completed.set()

    monkeypatch.setattr(backup, "sync_directory", pause_after_status)
    writer_thread = Thread(target=writer)
    reader_thread = Thread(target=reader)
    writer_thread.start()
    try:
        assert arrived.wait(5)
        reader_thread.start()
        assert attempting.wait(5)
        assert not completed.wait(0.1)
    finally:
        release.set()
        writer_thread.join(timeout=5)
        if reader_thread.ident is not None:
            reader_thread.join(timeout=5)
    assert not writer_thread.is_alive() and not reader_thread.is_alive() and not errors
    assert observed == [(b"synthetic", {"backup": final.name, "journal": "present"})]
