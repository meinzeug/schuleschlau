"""Synthetic, offline restore watchdog and neutral alarm checks."""

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("restore_monitor", ROOT / "deploy/monitor.py")
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)
NOW = 1_800_000_000


def valid_report():
    return {
        "backup": "20270101T030000Z.tar.enc",
        "production_overwritten": False,
        "schema": "123456",
        "before": dict.fromkeys(monitor.RESTORE_TABLES, 3),
        "after": dict.fromkeys(monitor.RESTORE_TABLES, 2),
        "verified_erasure_records": 1,
        "orphan_images_removed": 0,
        "erasure_images_removed": 1,
        "authenticated_restore": True,
        "erasure_journal_present": True,
        "sessions_revoked": True,
        "ai_emergency_stop": True,
        "checked_at": NOW,
    }


class RestoreMonitorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.report = self.root / "restore-check.json"
        self.setup = self.root / "restore-setup-started"

    def status(self):
        return monitor.restore_status(self.report, self.setup, NOW)

    def test_disk_threshold_accounts_for_reserved_blocks(self):
        unit = 1024**3
        # df reports 876 / (876 + 80) = 91.6%, although used / total is 87.6%.
        disk = SimpleNamespace(total=1000 * unit, used=876 * unit, free=80 * unit)
        self.assertTrue(monitor.disk_space_low(disk))
        self.assertFalse(monitor.disk_space_low(SimpleNamespace(total=100 * unit, used=90 * unit, free=10 * unit)))
        self.assertTrue(monitor.disk_space_low(SimpleNamespace(total=10 * unit, used=8 * unit, free=unit - 1)))
        self.assertTrue(monitor.disk_space_low(SimpleNamespace(total=0, used=0, free=0)))
        self.assertTrue(monitor.disk_space_low(SimpleNamespace(total=100 * unit, used=70 * unit, free=30 * unit),
                                               minimum_free=31 * unit))

    def test_configured_backup_volume_requires_exact_uuid(self):
        config = self.root / 'backup-volume.uuid'
        self.assertIsNone(monitor.backup_volume_failure(config, '/backup'))
        expected = '12345678-1234-5678-1234-567812345678'
        config.write_text(expected)
        metadata = SimpleNamespace(st_uid=0, st_nlink=1, st_mode=0o100600)
        with patch.object(monitor.os, 'fstat', return_value=metadata), \
             patch.object(monitor.subprocess, 'run', return_value=SimpleNamespace(stdout=expected + '\n')):
            self.assertIsNone(monitor.backup_volume_failure(config, '/backup'))
        with patch.object(monitor.os, 'fstat', return_value=metadata), \
             patch.object(monitor.subprocess, 'run', return_value=SimpleNamespace(stdout='different')):
            self.assertEqual(monitor.backup_volume_failure(config, '/backup'), 'backup_volume_unavailable')
        config.write_text('not-a-uuid')
        with patch.object(monitor.os, 'fstat', return_value=metadata):
            self.assertEqual(monitor.backup_volume_failure(config, '/backup'), 'backup_volume_unavailable')
        config.unlink()
        config.symlink_to(self.report)
        self.assertEqual(monitor.backup_volume_failure(config, '/backup'), 'backup_volume_unavailable')

    def test_backup_volume_low_is_a_distinct_neutral_alarm(self):
        monitor_dir = self.root / "var/backups/schulpilot-monitor"
        monitor_dir.mkdir(parents=True)
        (monitor_dir / "restore-check.json").write_text(json.dumps(valid_report()))
        backup_dir = self.root / "var/backups/schulpilot"
        backup_dir.mkdir(parents=True)
        backup = backup_dir / "20270101T030000Z.tar.enc"
        backup.write_bytes(b'x' * 100)
        backup.with_name(backup.name + '.journal.json').write_text(json.dumps({'backup': backup.name, 'journal': 'present'}))
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.status = 200

        def fake_run(args, **kwargs):
            if args[0] == 'runuser':
                return SimpleNamespace(stdout=json.dumps({'worker_age_seconds': 0, 'stalled_queued': 0,
                    'stalled_running': 0, 'pending_erasure_journal': 0}), returncode=0)
            return SimpleNamespace(returncode=1 if args[1] == 'is-failed' else 0)

        def disk(path):
            if str(path) == '/var/backups/schulpilot':
                return SimpleNamespace(total=1000, used=1, free=1024**3)
            return SimpleNamespace(total=200 * 1024**3, used=50 * 1024**3, free=150 * 1024**3)

        output = io.StringIO()
        with patch.object(monitor, 'Path', side_effect=lambda p: self.root / str(p).lstrip('/')), \
             patch.object(monitor, 'environment', return_value={}), \
             patch.object(monitor.subprocess, 'run', side_effect=fake_run), \
             patch.object(monitor.urllib.request, 'urlopen', return_value=response), \
             patch.object(monitor.shutil, 'disk_usage', side_effect=disk), \
             patch.object(monitor.time, 'time', return_value=NOW), \
             patch('sys.argv', ['monitor.py', '--dry-run']), contextlib.redirect_stdout(output):
            self.assertTrue(monitor.main())
        self.assertIn('backup_disk_space', json.loads(output.getvalue())['failures'])

    def test_fresh_report_and_staleness_boundary(self):
        report = valid_report()
        for age, expected in ((0, None), (monitor.RESTORE_MAX_AGE, None),
                              (monitor.RESTORE_MAX_AGE + 1, "restore_rehearsal_stale")):
            report["checked_at"] = NOW - age
            self.report.write_text(json.dumps(report))
            self.assertEqual(self.status(), (expected, False))

    def test_missing_only_gets_grace_with_valid_recent_setup_marker(self):
        self.assertEqual(self.status(), ("restore_rehearsal_missing", False))
        for marker, expected in ((str(NOW), True), (str(NOW - monitor.RESTORE_MAX_AGE), True),
                                 (str(NOW - monitor.RESTORE_MAX_AGE - 1), False),
                                 (str(NOW + 1), False), ("bad", False), ("0", False)):
            with self.subTest(marker=marker):
                self.setup.write_text(marker)
                self.assertEqual(self.status(), (None, True) if expected else ("restore_rehearsal_missing", False))

    def test_invalid_and_incomplete_reports_are_never_exempt(self):
        self.setup.write_text(str(NOW))
        old_report = valid_report()
        del old_report["erasure_journal_present"]
        self.report.write_text(json.dumps(old_report))
        self.assertEqual(self.status(), ("restore_rehearsal_invalid", False))
        malformed = ["", "{", "[]", "null", '"private sentinel"', "\udcff"]
        for value in malformed:
            with self.subTest(value=repr(value)):
                self.report.write_bytes(value.encode("utf-8", errors="surrogateescape"))
                self.assertEqual(self.status(), ("restore_rehearsal_invalid", False))
        for key, value in (("checked_at", True), ("checked_at", NOW + 1), ("checked_at", None),
                           ("production_overwritten", 0), ("authenticated_restore", False),
                           ("erasure_journal_present", False), ("erasure_journal_present", None),
                           ("sessions_revoked", None), ("ai_emergency_stop", 1),
                           ("backup", "private sentinel"), ("schema", " "),
                           ("verified_erasure_records", -1), ("orphan_images_removed", True),
                           ("erasure_images_removed", "1"), ("before", {}), ("after", None)):
            report = valid_report()
            report[key] = value
            self.report.write_text(json.dumps(report))
            with self.subTest(key=key, value=value):
                self.assertEqual(self.status(), ("restore_rehearsal_invalid", False))

    def test_failed_service_and_corrupt_report_reach_neutral_alarm(self):
        monitor_dir = self.root / "var/backups/schulpilot-monitor"
        monitor_dir.mkdir(parents=True)
        (monitor_dir / "restore-check.json").write_text('{"private sentinel":')
        (monitor_dir / "offsite-last-success.json").write_text("{broken")
        (monitor_dir / "state.json").write_text("{broken")
        offsite_dir = self.root / "etc/schulpilot"
        offsite_dir.mkdir(parents=True)
        (offsite_dir / "offsite-enabled").touch()
        backup_dir = self.root / "var/backups/schulpilot"
        backup_dir.mkdir(parents=True)
        backup = backup_dir / "test.tar.enc"
        backup.touch()
        backup.with_name(backup.name + ".journal.json").write_text(json.dumps({"backup": backup.name, "journal": "present"}))
        smtp = unittest.mock.MagicMock()
        smtp.__enter__.return_value = smtp
        config = {"OPERATIONS_ALERT_EMAIL": "operator@example.test", "SMTP_FROM": "system@example.test",
                  "SMTP_HOST": "mail.example.test", "SMTP_MODE": "tls"}

        def fake_run(args, **kwargs):
            if args[0] == "runuser":
                return SimpleNamespace(stdout=json.dumps({"worker_age_seconds": 0, "stalled_queued": 0,
                    "stalled_running": 0, "pending_erasure_journal": 0}), returncode=0)
            return SimpleNamespace(returncode=0)

        def local_path(path):
            return self.root / str(path).lstrip("/")

        response = unittest.mock.MagicMock()
        response.__enter__.return_value.status = 200
        output = io.StringIO()
        with patch.object(monitor, "Path", side_effect=local_path), patch.object(monitor, "environment", return_value=config), \
             patch.object(monitor.subprocess, "run", side_effect=fake_run), \
             patch.object(monitor.urllib.request, "urlopen", return_value=response), \
             patch.object(monitor.shutil, "disk_usage", return_value=SimpleNamespace(free=2**31, used=1, total=2**32)), \
             patch.object(monitor.smtplib, "SMTP_SSL", return_value=smtp), \
             patch.object(monitor.time, "time", return_value=backup.stat().st_mtime), \
             patch("sys.argv", ["monitor.py"]), contextlib.redirect_stdout(output):
            self.assertTrue(monitor.main())
        result = json.loads(output.getvalue())
        self.assertEqual(result["failures"], ["offsite_copy_stale", "restore_rehearsal_failed", "restore_rehearsal_invalid"])
        self.assertFalse(result["restore_rehearsal_initializing"])
        message = smtp.send_message.call_args.args[0]
        self.assertIn("restore_rehearsal_failed,restore_rehearsal_invalid", message.get_content())
        self.assertNotIn("private sentinel", message.as_string())
        self.assertEqual(json.loads((monitor_dir / "state.json").read_text())["failures"], result["failures"])

    def test_backup_without_valid_journal_status_is_not_reported_healthy(self):
        backup = self.root / "20261031T120000Z.tar.enc"
        backup.touch()
        status = backup.with_name(backup.name + ".journal.json")
        self.assertFalse(monitor.backup_journal_available(backup))
        for value in ("{broken", "{}", json.dumps({"backup": backup.name, "journal": "missing"}),
                      json.dumps({"backup": "different", "journal": "present"})):
            status.write_text(value)
            self.assertFalse(monitor.backup_journal_available(backup))
        status.write_text(json.dumps({"backup": backup.name, "journal": "present"}))
        self.assertTrue(monitor.backup_journal_available(backup))


if __name__ == "__main__":
    unittest.main()
