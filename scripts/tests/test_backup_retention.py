"""Retention checks operate only on synthetic files and temporary locks."""

import fcntl
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "deploy"))
spec = importlib.util.spec_from_file_location("backup_retention", ROOT / "deploy/backup_retention.py")
retention = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retention)
sys.path.remove(str(ROOT / "deploy"))
NOW = int(datetime(2026, 11, 1, 12, tzinfo=timezone.utc).timestamp())
FRESH = "20261101T110000Z.tar.enc"
OLD = "20261018T115000Z.tar.enc"


def archive(directory, name, stamp):
    path = directory / name
    path.write_bytes(b"SPB1" + b"x" * 32)
    os.utime(path, (stamp, stamp))
    path.with_name(name + ".journal.json").write_text(json.dumps({"backup": name, "journal": "present"}))
    return path


@pytest.fixture
def snapshot(tmp_path):
    (tmp_path / ".backup.lock").touch()
    latest = archive(tmp_path, FRESH, NOW - 3600)
    older = archive(tmp_path, OLD, NOW - 14 * 86400 - 600)
    report = {"backup": FRESH, "checked_at": NOW - 600, "authenticated_restore": True,
        "erasure_journal_present": True, "sessions_revoked": True, "ai_emergency_stop": True,
        "production_overwritten": False, "schema": "test",
        "verified_erasure_records": 0, "orphan_images_removed": 0, "erasure_images_removed": 0,
        "before": dict.fromkeys(("families", "children", "materials", "learning_units", "attempts", "unit_coaching"), 0),
        "after": dict.fromkeys(("families", "children", "materials", "learning_units", "attempts", "unit_coaching"), 0)}
    return tmp_path, latest, older, report


def test_expired_copies_are_identified_without_writing_and_removed_under_lock(snapshot):
    directory, latest, older, report = snapshot
    with retention.backup_lock(directory, exclusive=True):
        with (directory / ".backup.lock").open("rb") as contender:
            with pytest.raises(BlockingIOError):
                fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert retention.prune(directory, NOW, report, dry_run=True) == 1
        assert older.exists() and latest.exists()
        assert retention.prune(directory, NOW, report, dry_run=False) == 1
    assert not older.exists() and not older.with_name(OLD + ".journal.json").exists()
    assert latest.exists() and latest.with_name(FRESH + ".journal.json").exists()


@pytest.mark.parametrize("change", [
    lambda d, latest, old, report: latest.unlink(),
    lambda d, latest, old, report: report.update(authenticated_restore=False),
    lambda d, latest, old, report: report.update(checked_at=NOW + 1),
    lambda d, latest, old, report: report.update(checked_at=NOW - 31 * 86400),
    lambda d, latest, old, report: report.update(backup=OLD),
    lambda d, latest, old, report: latest.with_name(FRESH + ".journal.json").unlink(),
    lambda d, latest, old, report: latest.write_bytes(b"bad"),
])
def test_invalid_fresh_backup_or_restore_report_preserves_all_expired_copies(snapshot, change):
    directory, latest, older, report = snapshot
    change(directory, latest, older, report)
    with retention.backup_lock(directory, exclusive=True), pytest.raises(RuntimeError):
        retention.prune(directory, NOW, report, dry_run=False)
    assert older.exists()


def test_new_file_time_or_newer_backup_name_fails_closed(snapshot):
    directory, latest, older, report = snapshot
    os.utime(older, (NOW, NOW))
    with retention.backup_lock(directory, exclusive=True), pytest.raises(RuntimeError):
        retention.prune(directory, NOW, report, dry_run=False)
    assert older.exists() and latest.exists()


def test_symlinked_or_unknown_archive_is_never_removed(snapshot):
    directory, latest, older, report = snapshot
    target = directory / "target"
    target.write_bytes(b"safe")
    old_link = directory / "20261017T120000Z.tar.enc"
    old_link.symlink_to(target)
    with retention.backup_lock(directory, exclusive=True), pytest.raises(RuntimeError):
        retention.prune(directory, NOW, report, dry_run=False)
    assert target.read_bytes() == b"safe" and old_link.is_symlink() and older.exists() and latest.exists()


def test_future_archive_or_timestamp_is_not_silently_pruned(snapshot):
    directory, _, older, report = snapshot
    archive(directory, "20261101T120001Z.tar.enc", NOW)
    with retention.backup_lock(directory, exclusive=True), pytest.raises(RuntimeError):
        retention.prune(directory, NOW, report, dry_run=False)
    assert older.exists()


def test_offsite_marker_is_required_when_offsite_is_enabled(tmp_path):
    enabled = tmp_path / "enabled"
    marker = tmp_path / "marker.json"
    assert retention.offsite_fresh(enabled, marker, NOW)
    enabled.touch()
    assert not retention.offsite_fresh(enabled, marker, NOW)
    for checked, expected in ((NOW - 3600, True), (NOW - 3601, False), (NOW + 1, False), (True, False)):
        marker.write_text(json.dumps({"checked_at": checked}))
        assert retention.offsite_fresh(enabled, marker, NOW) is expected


def test_legacy_expired_backup_without_sidecar_is_supported(snapshot):
    directory, latest, older, report = snapshot
    older.with_name(OLD + ".journal.json").unlink()
    with retention.backup_lock(directory, exclusive=True):
        assert retention.prune(directory, NOW, report, dry_run=False) == 1
    assert latest.exists() and not older.exists()


def test_symlinked_expired_sidecar_fails_before_any_deletion(snapshot):
    directory, latest, older, report = snapshot
    sidecar = older.with_name(OLD + ".journal.json")
    sidecar.unlink()
    sidecar.symlink_to(latest)
    with retention.backup_lock(directory, exclusive=True), pytest.raises(RuntimeError):
        retention.prune(directory, NOW, report, dry_run=False)
    assert older.exists() and latest.exists()


@pytest.mark.parametrize("field, value", [("before", {}), ("schema", ""),
    ("verified_erasure_records", True), ("production_overwritten", 0)])
def test_incomplete_restore_report_fails_closed(snapshot, field, value):
    directory, latest, older, report = snapshot
    report[field] = value
    with retention.backup_lock(directory, exclusive=True), pytest.raises(RuntimeError):
        retention.prune(directory, NOW, report, dry_run=False)
    assert older.exists() and latest.exists()


def test_missing_and_symlinked_offsite_marker_fail_closed(tmp_path):
    enabled = tmp_path / "enabled"
    marker = tmp_path / "marker"
    enabled.touch()
    target = tmp_path / "target"
    target.write_text(json.dumps({"checked_at": NOW}))
    marker.symlink_to(target)
    assert not retention.offsite_fresh(enabled, marker, NOW)
    enabled.unlink()
    enabled.symlink_to(target)
    assert not retention.offsite_fresh(enabled, marker, NOW)


def test_retention_safety_window_does_not_remove_the_only_recovery_copy(snapshot):
    directory, latest, older, report = snapshot
    older.unlink()
    boundary = archive(directory, "20261018T120500Z.tar.enc", NOW - 14 * 86400 + 300)
    with retention.backup_lock(directory, exclusive=True):
        assert retention.prune(directory, NOW, report, dry_run=False) == 1
    assert latest.exists() and not boundary.exists()


def test_main_rejects_offsite_failure_and_preserves_backups(snapshot, monkeypatch):
    from contextlib import nullcontext
    directory, latest, older, report = snapshot
    monitor = directory / 'monitor'
    monitor.mkdir()
    (monitor / 'restore-check.json').write_text(json.dumps(report))
    enabled = directory / 'enabled'
    enabled.touch()
    monkeypatch.setattr(retention, 'BACKUP_DIR', directory)
    monkeypatch.setattr(retention, 'MONITOR_DIR', monitor)
    monkeypatch.setattr(retention, 'OFFSITE_ENABLED', enabled)
    monkeypatch.setattr(retention, 'guarded_operation', nullcontext)
    monkeypatch.setattr(retention.os, 'umask', lambda _: None)
    monkeypatch.setattr(retention.time, 'time', lambda: NOW)
    with pytest.raises(RuntimeError, match='Offsite acknowledgement unavailable'):
        retention.main()
    assert older.exists() and latest.exists()


def test_main_applies_after_valid_rehearsal_and_offsite_ack(snapshot, monkeypatch):
    from contextlib import nullcontext
    directory, latest, older, report = snapshot
    monitor = directory / 'monitor'
    monitor.mkdir()
    (monitor / 'restore-check.json').write_text(json.dumps(report))
    (monitor / 'offsite-last-success.json').write_text(json.dumps({'checked_at': NOW}))
    enabled = directory / 'enabled'
    enabled.touch()
    monkeypatch.setattr(retention, 'BACKUP_DIR', directory)
    monkeypatch.setattr(retention, 'MONITOR_DIR', monitor)
    monkeypatch.setattr(retention, 'OFFSITE_ENABLED', enabled)
    monkeypatch.setattr(retention, 'guarded_operation', nullcontext)
    monkeypatch.setattr(retention.os, 'umask', lambda _: None)
    monkeypatch.setattr(retention.time, 'time', lambda: NOW)
    retention.main()
    assert latest.exists() and not older.exists()


def test_current_fractional_file_time_is_not_mistaken_for_future(tmp_path):
    current = archive(tmp_path, "20261101T120000Z.tar.enc", NOW + 0.5)
    assert retention._inspect(current, NOW + 0.8) == (NOW, NOW + 0.5)
    with pytest.raises(RuntimeError):
        retention._inspect(current, NOW + 0.2)
