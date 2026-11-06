"""Synthetic offline tests for journal rotation and offsite acknowledgement."""

import fcntl
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import threading
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "deploy"))
import backup  # noqa: E402
import export_ledger  # noqa: E402
import restore_check  # noqa: E402
from ledger_snapshot import backup_lock  # noqa: E402


def test_restore_interpreter_and_backend_use_the_same_immutable_runtime(tmp_path, monkeypatch):
    runtime = tmp_path / 'recovery-release'
    monkeypatch.setattr(restore_check, 'RUNTIME_ROOT', runtime)
    calls = []

    def fake_command(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(stdout=b'clean\n')

    monkeypatch.setattr(restore_check, 'command', fake_command)
    assert restore_check.live_outbox_pending({}) is False
    assert calls[0][0][4] == str(runtime / 'venv/bin/python')
    assert calls[0][1]['cwd'] == runtime / 'backend'
    assert restore_check.runtime_command('pass')[4] == str(runtime / 'venv/bin/python')


@pytest.mark.parametrize('response', [b'no\n', b'', b'yes', b'yes\nextra\n'])
def test_restore_rejects_unconfirmed_clock_before_retention(monkeypatch, response):
    monkeypatch.setattr(restore_check, 'command', lambda *_a, **_kw: SimpleNamespace(stdout=response))
    with pytest.raises(RuntimeError, match='clock synchronization'):
        restore_check.synchronized_retention_time()


def test_restore_accepts_confirmed_clock_and_captures_one_cutoff(monkeypatch):
    monkeypatch.setattr(restore_check, 'command', lambda *_a, **_kw: SimpleNamespace(stdout=b'yes\n'))
    monkeypatch.setattr(restore_check.time, 'time', lambda: 1900000000.9)
    assert restore_check.synchronized_retention_time() == 1900000000


def test_restore_holds_publication_lock_and_missing_lock_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(restore_check, "guarded_operation", nullcontext)
    monkeypatch.setattr(restore_check.os, "geteuid", lambda: 0)
    monkeypatch.setattr(restore_check.os, "umask", lambda _mask: None)
    monkeypatch.setattr(restore_check, "Path", lambda _value: tmp_path)
    invoked = []

    def rehearsal():
        invoked.append(True)
        with (tmp_path / ".backup.lock").open("rb") as contender:
            with pytest.raises(BlockingIOError):
                fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)

    monkeypatch.setattr(restore_check, "restore", rehearsal)
    with pytest.raises(FileNotFoundError):
        restore_check.main()
    assert not invoked
    (tmp_path / ".backup.lock").touch()
    restore_check.main()
    assert invoked == [True]


def test_backup_directory_lock_cannot_coordinate_directory_replacement(tmp_path):
    """A path swap creates a different inode despite an identical lock path."""
    current = tmp_path / "backups"
    current.mkdir()
    (current / ".backup.lock").touch()
    with backup_lock(current, exclusive=True):
        current.rename(tmp_path / "previous")
        current.mkdir()
        (current / ".backup.lock").touch()
        with (current / ".backup.lock").open("rb") as other:
            # This succeeds: the old directory's lock cannot protect a mount
            # or directory replacement. A separate stable lock is required.
            fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)


def test_missing_and_empty_journal_are_distinct_and_no_lock_is_created(tmp_path):
    ledger = tmp_path / "erasure-ledger.jsonl"
    lock = tmp_path / ".erasure-ledger.lock"
    snapshot = tmp_path / "snapshot"
    key = tmp_path / "key"
    key.write_bytes(b"synthetic-backup-key")
    assert backup.capture_journal(ledger, snapshot) == "missing"
    assert not lock.exists() and not snapshot.exists()
    ledger.touch()
    assert backup.capture_journal(ledger, snapshot) == "unavailable"
    with pytest.raises(FileNotFoundError):
        export_ledger.export(ledger, key, io.BytesIO())
    assert not lock.exists()
    lock.touch()
    ledger.unlink()
    output = io.BytesIO()
    with pytest.raises(FileNotFoundError):
        export_ledger.export(ledger, key, output)
    assert output.getvalue() == b""
    ledger.touch()
    assert backup.capture_journal(ledger, snapshot) == "present"
    assert snapshot.read_bytes() == b""
    export_ledger.export(ledger, key, output)
    encrypted = output.getvalue()
    assert AESGCM(hashlib.sha256(key.read_bytes()).digest()).decrypt(encrypted[4:16], encrypted[16:], b"SPB1") == b""


def test_encrypted_backup_preserves_database_when_journal_is_missing(tmp_path, monkeypatch):
    data, destination = tmp_path / "data", tmp_path / "backups"
    data.mkdir()
    (data / "uploads").mkdir()
    (data / "uploads" / "synthetic.jpg").write_bytes(b"synthetic-image")
    key = tmp_path / "key"
    key.write_bytes(b"synthetic-backup-key")

    def fake_pg_dump(args, *, stdout, check):
        assert args[:4] == ["runuser", "-u", "schulpilot", "--"] and check
        stdout.write(b"synthetic-postgres-dump")

    monkeypatch.setattr(backup.subprocess, "run", fake_pg_dump)
    first = backup.create_backup(destination, data, key, stamp="20261031T120000Z")
    status = json.loads((destination / (first.name + ".journal.json")).read_text())
    assert status == {"backup": first.name, "journal": "missing"}
    encrypted = first.read_bytes()
    plaintext = AESGCM(hashlib.sha256(key.read_bytes()).digest()).decrypt(encrypted[4:16], encrypted[16:], b"SPB1")
    with tarfile.open(fileobj=io.BytesIO(plaintext)) as archive:
        assert archive.extractfile("database.dump").read() == b"synthetic-postgres-dump"
        assert archive.extractfile("uploads/synthetic.jpg").read() == b"synthetic-image"
        assert json.load(archive.extractfile("erasure-journal-status.json")) == {"journal": "missing"}
        assert "erasure-ledger.jsonl" not in archive.getnames()
    with pytest.raises(RuntimeError):
        export_ledger.require_backup_journal(destination, first.name, hashlib.sha256(encrypted).hexdigest())
    assert not (data / ".erasure-ledger.lock").exists()

    (data / ".erasure-ledger.lock").touch()
    (data / "erasure-ledger.jsonl").write_bytes(b"synthetic signed record\n")
    second = backup.create_backup(destination, data, key, stamp="20261031T120001Z")
    assert first.read_bytes() == encrypted
    encrypted_second = second.read_bytes()
    plaintext = AESGCM(hashlib.sha256(key.read_bytes()).digest()).decrypt(
        encrypted_second[4:16], encrypted_second[16:], b"SPB1")
    with tarfile.open(fileobj=io.BytesIO(plaintext)) as archive:
        assert archive.extractfile("erasure-ledger.jsonl").read() == b"synthetic signed record\n"
        assert json.load(archive.extractfile("erasure-journal-status.json")) == {"journal": "present"}
    export_ledger.require_backup_journal(destination, second.name, hashlib.sha256(encrypted_second).hexdigest())


@pytest.mark.parametrize("journal_state", ["missing", "unavailable"])
def test_incomplete_backup_is_retained_but_cannot_report_success(tmp_path, monkeypatch, journal_state):
    data, destination = tmp_path / "data", tmp_path / "backups"
    data.mkdir()
    (data / "uploads").mkdir()
    if journal_state == "unavailable":
        # A readable journal without its stable lock must not be treated as captured.
        (data / "erasure-ledger.jsonl").write_text("synthetic\n")
    key = tmp_path / "key"
    key.write_bytes(b"synthetic-backup-key")
    monkeypatch.setattr(backup.subprocess, "run", lambda args, *, stdout, check: stdout.write(b"synthetic dump"))
    name = "20261106T120000Z.tar.enc"
    with pytest.raises(RuntimeError, match="journal snapshot is unavailable"):
        backup.create_backup(destination, data, key, stamp="20261106T120000Z", require_journal=True)
    encrypted = (destination / name).read_bytes()
    content = AESGCM(hashlib.sha256(key.read_bytes()).digest()).decrypt(encrypted[4:16], encrypted[16:], b"SPB1")
    with tarfile.open(fileobj=io.BytesIO(content)) as archive:
        assert archive.extractfile("database.dump").read() == b"synthetic dump"
        assert json.load(archive.extractfile("erasure-journal-status.json")) == {"journal": journal_state}
    assert json.loads((destination / (name + ".journal.json")).read_text()) == {
        "backup": name, "journal": journal_state,
    }


def test_backup_service_requires_journal_snapshot(monkeypatch):
    from contextlib import nullcontext

    calls = []
    monkeypatch.setattr(backup, "guarded_operation", lambda: nullcontext())
    monkeypatch.setattr(backup, "create_backup", lambda *args, **kwargs: calls.append(kwargs))
    backup.main()
    assert calls == [{"require_journal": True}]


@pytest.mark.parametrize("reader", ["backup", "export", "restore"])
def test_rotation_and_readers_share_stable_lock(tmp_path, reader):
    ledger = tmp_path / "erasure-ledger.jsonl"
    lock = tmp_path / ".erasure-ledger.lock"
    lock.touch()
    ledger.write_bytes(b"old synthetic row\n")
    key = tmp_path / "key"
    key.write_bytes(b"synthetic-backup-key")
    started, done = threading.Event(), threading.Event()
    result = []

    def read():
        started.set()
        try:
            if reader == "backup":
                snap = tmp_path / "snapshot"
                result.append((backup.capture_journal(ledger, snap), snap.read_bytes()))
            elif reader == "export":
                output = io.BytesIO()
                export_ledger.export(ledger, key, output)
                encrypted = output.getvalue()
                result.append(AESGCM(hashlib.sha256(key.read_bytes()).digest()).decrypt(
                    encrypted[4:16], encrypted[16:], b"SPB1"))
            else:
                result.append(restore_check.current_journal(ledger))
        finally:
            done.set()

    with lock.open("rb") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        thread = threading.Thread(target=read)
        thread.start()
        assert started.wait(2)
        assert not done.wait(0.1)
        replacement = tmp_path / "new"
        replacement.write_bytes(b"new synthetic row\n")
        os.replace(replacement, ledger)
    thread.join(timeout=5)
    assert done.is_set()
    expected = ("present", b"new synthetic row\n") if reader == "backup" else (
        "new synthetic row\n" if reader == "restore" else b"new synthetic row\n")
    assert result == [expected]


def test_ack_identity_and_publication_are_serialized(tmp_path):
    (tmp_path / ".backup.lock").touch()
    old = tmp_path / "20261031T120000Z.tar.enc"
    old.write_bytes(b"synthetic-old-archive")
    backup.write_status(old, "present")
    digest = hashlib.sha256(old.read_bytes()).hexdigest()
    export_ledger.require_backup_journal(tmp_path, old.name, digest)
    new = tmp_path / "20261031T120001Z.tar.enc"
    partial = tmp_path / "new.partial"
    partial.write_bytes(b"synthetic-new-archive")
    started, done = threading.Event(), threading.Event()

    def publish():
        started.set()
        try:
            backup.publish_backup(partial, new, "present")
        finally:
            done.set()

    with backup_lock(tmp_path, exclusive=False):
        thread = threading.Thread(target=publish)
        thread.start()
        assert started.wait(2)
        assert not done.wait(0.1)
        export_ledger.require_backup_journal(tmp_path, old.name, digest)
    thread.join(timeout=5)
    assert done.is_set() and new.exists()
    with pytest.raises(RuntimeError, match="changed"):
        export_ledger.require_backup_journal(tmp_path, old.name, digest)
    assert old.read_bytes() == b"synthetic-old-archive"
    with pytest.raises(FileExistsError):
        backup.publish_backup(old, new, "present")
    assert old.read_bytes() == b"synthetic-old-archive"
    assert new.read_bytes() == b"synthetic-new-archive"


def test_ack_refuses_missing_unavailable_invalid_or_legacy_backup_status(tmp_path):
    archive = tmp_path / "20261031T120000Z.tar.enc"
    archive.write_bytes(b"synthetic-archive")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    for status in (None, "missing", "unavailable"):
        if status is not None:
            backup.write_status(archive, status)
        with pytest.raises(RuntimeError):
            export_ledger.require_backup_journal(tmp_path, archive.name, digest)
    backup.write_status(archive, "present")
    with pytest.raises(RuntimeError, match="changed"):
        export_ledger.require_backup_journal(tmp_path, archive.name, "0" * 64)
    export_ledger.require_backup_journal(tmp_path, archive.name, digest)


def test_ack_never_records_success_for_missing_journal_or_changed_backup(tmp_path, monkeypatch, capsys):
    def mapped(value):
        path = Path(value)
        return path if path.is_relative_to(tmp_path) else tmp_path / str(path).lstrip("/")

    monkeypatch.setattr(export_ledger, "Path", mapped)
    directory = mapped("/var/backups/schulpilot")
    data = mapped("/var/lib/schulpilot")
    monitor = mapped("/var/backups/schulpilot-monitor")
    etc = mapped("/etc/schulpilot")
    for path in (directory, data, monitor, etc):
        path.mkdir(parents=True)
    (directory / ".backup.lock").touch()
    archive = directory / "20261031T120000Z.tar.enc"
    archive.write_bytes(b"synthetic-archive")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    backup.write_status(archive, "present")
    lock = data / ".erasure-ledger.lock"
    lock.touch()
    marker = monitor / "offsite-last-success.json"
    with pytest.raises(FileNotFoundError):
        export_ledger.acknowledge(archive.name, digest)
    assert not marker.exists()
    (data / "erasure-ledger.jsonl").touch()
    export_ledger.acknowledge(archive.name, digest)
    previous = marker.read_bytes()

    newer = directory / "20261031T120001Z.tar.enc"
    newer.write_bytes(b"synthetic-newer-archive")
    backup.write_status(newer, "present")
    with pytest.raises(export_ledger.NewerBackupAvailable, match="changed"):
        export_ledger.acknowledge(archive.name, digest)
    assert marker.read_bytes() == previous

    # The command emits its narrowly scoped rejection only before modifying
    # the acknowledgement. Generic errors retain their ordinary failure mode.
    monkeypatch.setattr(export_ledger, "guarded_operation", nullcontext)
    monkeypatch.setattr(export_ledger.os, "geteuid", lambda: 0)
    monkeypatch.setattr(sys, "argv", ["export_ledger.py", "--ack", archive.name, digest])
    with pytest.raises(SystemExit) as rejected:
        export_ledger.main()
    assert rejected.value.code == 75
    assert capsys.readouterr().err == "offsite_ack_rejected_backup_changed_v1\n"
    assert marker.read_bytes() == previous


def test_offsite_failed_journal_export_keeps_previous_copy_and_success_marker(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1] / "offsite_backup.py"
    spec = importlib.util.spec_from_file_location("offsite_journal_test", source)
    offsite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(offsite)
    archive = b"synthetic-encrypted-backup"
    name = "20261031T120000Z.tar.enc"
    existing = tmp_path / name
    existing.write_bytes(archive)
    previous = tmp_path / "erasure-ledger.enc"
    previous.write_bytes(b"prior-encrypted-journal")
    marker = tmp_path / "last-success.json"
    marker.write_text('{"checked_at":1}\n')
    server_now = int(datetime(2026, 10, 31, 12, tzinfo=timezone.utc).timestamp())
    inventory = {"backups": [{"name": name, "size": len(archive), "sha256": hashlib.sha256(archive).hexdigest()}],
                 "server_now": server_now}
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args[-1])
        if args[-1].endswith("/backup_access.py inventory"):
            return SimpleNamespace(stdout=json.dumps(inventory))
        raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(offsite, "run", fake_run)
    with pytest.raises(subprocess.CalledProcessError):
        offsite.pull(tmp_path)
    assert previous.read_bytes() == b"prior-encrypted-journal"
    assert marker.read_text() == '{"checked_at":1}\n'
    assert existing.read_bytes() == archive
    assert not any("--ack" in call for call in calls)


def test_offsite_ack_race_restores_previous_journal_and_does_not_record_success(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1] / "offsite_backup.py"
    spec = importlib.util.spec_from_file_location("offsite_ack_test", source)
    offsite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(offsite)
    archive = b"synthetic-encrypted-backup"
    name = "20261031T120000Z.tar.enc"
    (tmp_path / name).write_bytes(archive)
    prior = tmp_path / "erasure-ledger.enc"
    prior.write_bytes(b"previous-verified-snapshot")
    marker = tmp_path / "last-success.json"
    marker.write_text('{"checked_at":1}\n')
    digest = hashlib.sha256(archive).hexdigest()
    server_now = int(datetime(2026, 10, 31, 12, tzinfo=timezone.utc).timestamp())
    inventory = {"backups": [{"name": name, "size": len(archive), "sha256": digest}], "server_now": server_now}
    new_journal = b"SPB1" + b"x" * 28

    def fake_run(args, **kwargs):
        command = args[-1]
        if command.endswith("/backup_access.py inventory"):
            return SimpleNamespace(stdout=json.dumps(inventory))
        if command.endswith("/export_ledger.py"):
            kwargs["stdout"].write(new_journal)
            return SimpleNamespace()
        assert command.endswith("--ack " + name + " " + digest)
        assert prior.read_bytes() == new_journal
        raise subprocess.CalledProcessError(1, args)  # a newer backup appeared during transfer

    monkeypatch.setattr(offsite, "run", fake_run)
    with pytest.raises(subprocess.CalledProcessError):
        offsite.pull(tmp_path)
    assert prior.read_bytes() == b"previous-verified-snapshot"
    assert marker.read_text() == '{"checked_at":1}\n'
    assert (tmp_path / name).read_bytes() == archive
    assert not (tmp_path / ".erasure-ledger.previous").exists()
    assert (tmp_path / ".erasure-ledger.pending").exists()
    with pytest.raises(offsite.InterruptedTransfer):
        offsite.pull(tmp_path)


@pytest.mark.parametrize("failure", ["ack_timeout", "local_status_write"])
def test_ambiguous_ack_keeps_reconciliation_marker_and_previous_snapshot(tmp_path, monkeypatch, failure):
    source = Path(__file__).resolve().parents[1] / "offsite_backup.py"
    spec = importlib.util.spec_from_file_location("offsite_ambiguous_ack_test", source)
    offsite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(offsite)
    ledger = tmp_path / "erasure-ledger.enc"
    ledger.write_bytes(b"previous-verified-snapshot")
    partial = tmp_path / "erasure-ledger.partial"
    partial.write_bytes(b"new-synthetic-snapshot")
    marker = tmp_path / "last-success.json"
    marker.write_text('{"checked_at":1}\n')
    remote_ack = tmp_path / "synthetic-remote-ack"
    original_replace = Path.replace

    def replace(source, target):
        if failure == "local_status_write" and Path(target) == marker:
            raise OSError("synthetic local status failure")
        return original_replace(source, target)

    monkeypatch.setattr(Path, "replace", replace)

    def acknowledged_or_timed_out():
        # Model the remote server saving its ACK before a connection timeout.
        remote_ack.touch()
        if failure == "ack_timeout":
            raise subprocess.TimeoutExpired("synthetic-ssh", 1)

    with pytest.raises((OSError, subprocess.TimeoutExpired)):
        offsite.commit_ledger(tmp_path, partial, acknowledged_or_timed_out, {"checked_at": 2})
    assert remote_ack.exists()
    assert ledger.read_bytes() == b"previous-verified-snapshot"
    assert marker.read_text() == '{"checked_at":1}\n'
    assert (tmp_path / ".erasure-ledger.pending").exists()
    with pytest.raises(offsite.InterruptedTransfer):
        offsite.pull(tmp_path)


def test_interrupted_offsite_commit_is_detected_and_preserves_previous_snapshot(tmp_path):
    source = Path(__file__).resolve().parents[1] / "offsite_backup.py"
    spec = importlib.util.spec_from_file_location("offsite_interrupt_test", source)
    offsite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(offsite)
    ledger = tmp_path / "erasure-ledger.enc"
    ledger.write_bytes(b"previous-verified-snapshot")
    partial = tmp_path / "erasure-ledger.partial"
    partial.write_bytes(b"new-synthetic-snapshot")
    marker = tmp_path / "last-success.json"
    marker.write_text('{"checked_at":1}\n')

    def interrupt():
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        offsite.commit_ledger(tmp_path, partial, interrupt, {"checked_at": 2})
    assert (tmp_path / ".erasure-ledger.pending").exists()
    assert (tmp_path / ".erasure-ledger.previous").read_bytes() == b"previous-verified-snapshot"
    assert marker.read_text() == '{"checked_at":1}\n'
    with pytest.raises(offsite.InterruptedTransfer):
        offsite.pull(tmp_path)


def test_ambiguous_first_ack_does_not_leave_an_unverified_snapshot(tmp_path):
    source = Path(__file__).resolve().parents[1] / "offsite_backup.py"
    spec = importlib.util.spec_from_file_location("offsite_first_ack_test", source)
    offsite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(offsite)
    partial = tmp_path / "erasure-ledger.partial"
    partial.write_bytes(b"new-synthetic-snapshot")

    def timeout():
        raise subprocess.TimeoutExpired("synthetic-ssh", 1)

    with pytest.raises(subprocess.TimeoutExpired):
        offsite.commit_ledger(tmp_path, partial, timeout, {"checked_at": 2})
    assert not (tmp_path / "erasure-ledger.enc").exists()
    assert not (tmp_path / "last-success.json").exists()
    assert (tmp_path / ".erasure-ledger.pending").exists()


def test_restore_journal_rejects_pending_outbox_while_holding_journal_lock(tmp_path):
    ledger = tmp_path / 'erasure-ledger.jsonl'
    ledger.write_text('synthetic\n')
    lock = tmp_path / '.erasure-ledger.lock'
    lock.touch()

    def pending():
        with lock.open('rb') as contender:
            with pytest.raises(BlockingIOError):
                fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True

    with pytest.raises(RuntimeError, match='Unpublished'):
        restore_check.current_journal(ledger, pending)
    assert restore_check.current_journal(ledger, lambda: False) == 'synthetic\n'
