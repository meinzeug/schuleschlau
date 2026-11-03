"""Offsite expiry checks use only synthetic inventory and ciphertext."""

import hashlib
import importlib.util
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location("offsite_retention", Path(__file__).resolve().parents[1] / "offsite_backup.py")
offsite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(offsite)

NOW = int(datetime(2026, 11, 1, 12, tzinfo=timezone.utc).timestamp())
EXPIRED = "20261018T115959Z.tar.enc"
EARLY_EXPIRED = "20261018T135959Z.tar.enc"
BOUNDARY = "20261018T140000Z.tar.enc"
LATEST = "20261101T120000Z.tar.enc"
ARCHIVE = b"synthetic-ciphertext"
HASH = hashlib.sha256(ARCHIVE).hexdigest()


def inventory(names):
    return {"server_now": NOW, "backups": [{"name": name, "size": len(ARCHIVE), "sha256": HASH} for name in names]}


def transport(monkeypatch, data, *, fail_ack=False, ack_error=None):
    calls = []

    def fake(args, **kwargs):
        command = args[-1]
        calls.append(command)
        if command.endswith("backup_access.py inventory"):
            return SimpleNamespace(stdout=json.dumps(data))
        if "backup_access.py read " in command:
            kwargs["stdout"].write(ARCHIVE)
        elif command.endswith("export_ledger.py"):
            kwargs["stdout"].write(b"SPB1" + b"x" * 28)
        elif "export_ledger.py --ack " in command:
            if ack_error is not None:
                raise ack_error
            if fail_ack:
                raise subprocess.CalledProcessError(1, args)
        else:
            raise AssertionError("unexpected synthetic command")
        return SimpleNamespace()

    monkeypatch.setattr(offsite, "run", fake)
    return calls


def test_explicit_stale_backup_rejection_preserves_old_state_and_allows_next_pull(tmp_path, monkeypatch):
    ledger = tmp_path / "erasure-ledger.enc"
    marker = tmp_path / "last-success.json"
    ledger.write_bytes(b"prior-journal")
    marker.write_text('{"checked_at":1}\n')
    error = subprocess.CalledProcessError(75, "ssh", output=b"", stderr=b"offsite_ack_rejected_backup_changed_v1\n")
    transport(monkeypatch, inventory([LATEST]), ack_error=error)
    with pytest.raises(offsite.AcknowledgementRejected):
        offsite.pull(tmp_path)
    assert ledger.read_bytes() == b"prior-journal"
    assert marker.read_text() == '{"checked_at":1}\n'
    assert not (tmp_path / ".erasure-ledger.pending").exists()
    assert not (tmp_path / ".erasure-ledger.previous").exists()
    transport(monkeypatch, inventory([LATEST]))
    offsite.pull(tmp_path)
    assert ledger.read_bytes() == b"SPB1" + b"x" * 28


@pytest.mark.parametrize("error", [
    subprocess.TimeoutExpired("ssh", 120),
    subprocess.CalledProcessError(1, "ssh", output=b"", stderr=b"offsite_ack_rejected_backup_changed_v1\n"),
    subprocess.CalledProcessError(75, "ssh", output=b"", stderr=b"offsite_ack_rejected_backup_changed_v1\nextra"),
    subprocess.CalledProcessError(75, "ssh", output=b"untrusted", stderr=b"offsite_ack_rejected_backup_changed_v1\n"),
    subprocess.CalledProcessError(75, "ssh", output=None, stderr=b"offsite_ack_rejected_backup_changed_v1\n"),
    subprocess.CalledProcessError(255, "ssh", output=b"", stderr=b""),
])
def test_ambiguous_ssh_results_always_keep_reconciliation_marker(tmp_path, monkeypatch, error):
    ledger = tmp_path / "erasure-ledger.enc"
    ledger.write_bytes(b"prior-journal")
    transport(monkeypatch, inventory([LATEST]), ack_error=error)
    with pytest.raises((subprocess.CalledProcessError, subprocess.TimeoutExpired)):
        offsite.pull(tmp_path)
    assert ledger.read_bytes() == b"prior-journal"
    assert (tmp_path / ".erasure-ledger.pending").exists()
    with pytest.raises(offsite.InterruptedTransfer):
        offsite.pull(tmp_path)


def test_expired_remote_backup_is_never_retransferred_and_only_removed_after_success(tmp_path, monkeypatch):
    expired = tmp_path / EXPIRED
    calls = transport(monkeypatch, inventory([EXPIRED, EARLY_EXPIRED, BOUNDARY, LATEST]))
    offsite.pull(tmp_path)
    assert not any(" read " + EXPIRED in call or " read " + EARLY_EXPIRED in call for call in calls)
    assert all(any(" read " + name in call for call in calls) for name in (BOUNDARY, LATEST))
    assert not expired.exists()
    assert (tmp_path / BOUNDARY).read_bytes() == (tmp_path / LATEST).read_bytes() == ARCHIVE
    assert any("--ack " + LATEST + " " + HASH in call for call in calls)
    assert json.loads((tmp_path / "last-success.json").read_text())["backups"] == 2


def test_expired_local_backup_is_removed_after_successful_ack(tmp_path, monkeypatch):
    (tmp_path / EXPIRED).write_bytes(ARCHIVE)
    calls = transport(monkeypatch, inventory([EXPIRED, LATEST]))
    offsite.pull(tmp_path)
    assert not any(" read " + EXPIRED in call for call in calls)
    assert not (tmp_path / EXPIRED).exists()
    assert (tmp_path / LATEST).read_bytes() == ARCHIVE


def test_expired_local_backup_is_preserved_if_journal_ack_fails(tmp_path, monkeypatch):
    (tmp_path / EXPIRED).write_bytes(ARCHIVE)
    (tmp_path / "erasure-ledger.enc").write_bytes(b"previous-journal")
    transport(monkeypatch, inventory([EXPIRED, LATEST]), fail_ack=True)
    with pytest.raises(subprocess.CalledProcessError):
        offsite.pull(tmp_path)
    assert (tmp_path / EXPIRED).read_bytes() == ARCHIVE
    assert (tmp_path / "erasure-ledger.enc").read_bytes() == b"previous-journal"
    assert (tmp_path / ".erasure-ledger.pending").exists()


@pytest.mark.parametrize("names", [[], [EXPIRED], ["20261030T000000Z.tar.enc"],
    ["20261101T120001Z.tar.enc"], ["20261040T120000Z.tar.enc"], [LATEST, LATEST]])
def test_missing_recent_future_or_duplicate_inventory_never_acknowledges(tmp_path, monkeypatch, names):
    (tmp_path / EXPIRED).write_bytes(ARCHIVE)
    calls = transport(monkeypatch, inventory(names))
    with pytest.raises(RuntimeError):
        offsite.pull(tmp_path)
    assert not any("export_ledger.py" in call for call in calls)
    assert (tmp_path / EXPIRED).read_bytes() == ARCHIVE


@pytest.mark.parametrize("change", [
    lambda data: data.update(server_now=True),
    lambda data: data["backups"][0].update(sha256="invalid"),
    lambda data: data["backups"][0].update(size=True),
])
def test_invalid_inventory_never_starts_transfers(tmp_path, monkeypatch, change):
    data = inventory([LATEST])
    change(data)
    calls = transport(monkeypatch, data)
    with pytest.raises(RuntimeError):
        offsite.pull(tmp_path)
    assert len(calls) == 1 and calls[0].endswith("backup_access.py inventory")


def test_future_local_copy_does_not_get_deleted_or_acknowledged(tmp_path, monkeypatch):
    future = tmp_path / "20261101T120001Z.tar.enc"
    future.write_bytes(ARCHIVE)
    (tmp_path / EXPIRED).write_bytes(ARCHIVE)
    calls = transport(monkeypatch, inventory([LATEST]))
    with pytest.raises(RuntimeError, match="future"):
        offsite.pull(tmp_path)
    assert future.read_bytes() == (tmp_path / EXPIRED).read_bytes() == ARCHIVE
    assert not any("--ack " in call for call in calls)


def test_buffered_copy_is_removed_only_after_success_and_preserved_on_failure(tmp_path, monkeypatch):
    old = tmp_path / EARLY_EXPIRED
    old.write_bytes(ARCHIVE)
    transport(monkeypatch, inventory([EARLY_EXPIRED, LATEST]), fail_ack=True)
    with pytest.raises(subprocess.CalledProcessError):
        offsite.pull(tmp_path)
    assert old.read_bytes() == ARCHIVE
    assert (tmp_path / '.erasure-ledger.pending').exists()


def test_buffered_copy_is_removed_on_success_before_full_fourteen_days(tmp_path, monkeypatch):
    old = tmp_path / EARLY_EXPIRED
    old.write_bytes(ARCHIVE)
    calls = transport(monkeypatch, inventory([EARLY_EXPIRED, BOUNDARY, LATEST]))
    offsite.pull(tmp_path)
    assert not old.exists()
    assert not any(' read ' + EARLY_EXPIRED in call for call in calls)
    assert (tmp_path / BOUNDARY).exists()
