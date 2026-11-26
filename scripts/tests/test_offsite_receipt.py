"""Synthetic server/client protocol checks; no live host or private journal."""

import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "deploy"))
import backup  # noqa: E402
import export_ledger  # noqa: E402

spec = importlib.util.spec_from_file_location("offsite_receipt_test", Path(__file__).resolve().parents[1] / "offsite_backup.py")
offsite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(offsite)


def test_real_protocol_rejects_changed_journal_and_preserves_previous(tmp_path, monkeypatch):
    server, client = tmp_path / "server", tmp_path / "client"
    client.mkdir()

    def mapped(value):
        path = Path(value)
        return path if path.is_relative_to(tmp_path) else server / str(path).lstrip("/")

    monkeypatch.setattr(export_ledger, "Path", mapped)
    monkeypatch.setattr(export_ledger, "outbox_pending", lambda: False)
    backup_dir, data, monitor, etc = [mapped(value) for value in (
        "/var/backups/schulpilot", "/var/lib/schulpilot", "/var/backups/schulpilot-monitor", "/etc/schulpilot")]
    for path in (backup_dir, data, monitor, etc):
        path.mkdir(parents=True)
    (backup_dir / ".backup.lock").touch()
    (data / ".erasure-ledger.lock").touch()
    ledger, key = data / "erasure-ledger.jsonl", etc / "backup.key"
    ledger.write_bytes(b"synthetic-before\n")
    key.write_bytes(b"synthetic-backup-key")
    archive = backup_dir / "20261126T120000Z.tar.enc"
    archive.write_bytes(b"synthetic-archive")
    backup.write_status(archive, "present")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    now = int(datetime(2026, 11, 26, 12, tzinfo=timezone.utc).timestamp())
    inventory = {"server_now": now, "backups": [{"name": archive.name, "size": archive.stat().st_size, "sha256": digest}]}
    prior = client / "erasure-ledger.enc"
    prior.write_bytes(b"previous-synthetic-snapshot")
    marker = client / "last-success.json"
    marker.write_bytes(b"previous-success\n")
    (client / archive.name).write_bytes(archive.read_bytes())
    change_before_ack = True

    def transport(args, **kwargs):
        nonlocal change_before_ack
        command = args[-1]
        if command.endswith(" inventory"):
            return SimpleNamespace(stdout=json.dumps(inventory))
        if command.endswith("/export_ledger.py"):
            receipt = export_ledger.export(ledger, key, kwargs["stdout"])
            return SimpleNamespace(stderr=("offsite_ledger_receipt_v1:" + receipt + "\n").encode())
        if " --ack " in command:
            if change_before_ack:
                ledger.write_bytes(b"synthetic-before\nsynthetic-new-deletion\n")
                change_before_ack = False
            try:
                export_ledger.acknowledge(*command.split(" --ack ", 1)[1].split())
            except export_ledger.JournalChanged:
                raise subprocess.CalledProcessError(76, args, output=b"", stderr=b"offsite_ack_rejected_ledger_changed_v1\n") from None
            return SimpleNamespace()
        raise AssertionError("Unexpected synthetic request")

    monkeypatch.setattr(offsite, "run", transport)
    with pytest.raises(offsite.AcknowledgementRejected):
        offsite.pull(client)
    assert prior.read_bytes() == b"previous-synthetic-snapshot"
    assert marker.read_bytes() == b"previous-success\n"
    assert not (monitor / "offsite-last-success.json").exists()
    assert not (client / ".erasure-ledger.pending").exists()

    offsite.pull(client)
    encrypted = prior.read_bytes()
    decrypted = AESGCM(hashlib.sha256(key.read_bytes()).digest()).decrypt(encrypted[4:16], encrypted[16:], b"SPB1")
    assert decrypted == ledger.read_bytes()
    assert (monitor / "offsite-last-success.json").exists()
    assert not (client / ".erasure-ledger.pending").exists()


@pytest.mark.parametrize("response", [b"", b"old server warning\n", b"offsite_ledger_receipt_v1:" + b"z" * 64 + b"\n"])
def test_old_or_invalid_export_receipt_never_replaces_previous(tmp_path, monkeypatch, response):
    archive = b"synthetic-archive"
    name = "20261126T120000Z.tar.enc"
    (tmp_path / name).write_bytes(archive)
    ledger = tmp_path / "erasure-ledger.enc"
    ledger.write_bytes(b"previous")
    now = int(datetime(2026, 11, 26, 12, tzinfo=timezone.utc).timestamp())
    inventory = {"server_now": now, "backups": [{"name": name, "size": len(archive), "sha256": hashlib.sha256(archive).hexdigest()}]}

    def transport(args, **kwargs):
        if args[-1].endswith(" inventory"):
            return SimpleNamespace(stdout=json.dumps(inventory))
        if args[-1].endswith("/export_ledger.py"):
            kwargs["stdout"].write(b"SPB1" + b"x" * 28)
            return SimpleNamespace(stderr=response)
        raise AssertionError("No acknowledgement should be sent")

    monkeypatch.setattr(offsite, "run", transport)
    with pytest.raises(RuntimeError, match="receipt"):
        offsite.pull(tmp_path)
    assert ledger.read_bytes() == b"previous"
    assert not (tmp_path / ".erasure-ledger.pending").exists()
