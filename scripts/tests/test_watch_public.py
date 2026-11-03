"""Independent watchdog never hides malformed state or a full offsite disk."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('watch_public_test', ROOT / 'scripts/watch_public.py')
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)


def test_corrupt_marker_and_full_disk_reach_neutral_dry_run(tmp_path):
    base = tmp_path / '.local/share/schulpilot-offsite'
    base.mkdir(parents=True)
    (base / 'last-success.json').write_text('{broken')
    (base / 'watch-state.json').write_text('{broken')
    response = MagicMock()
    response.__enter__.return_value.status = 200
    response.__enter__.return_value.read.return_value = b'{"status":"ok"}'
    out = io.StringIO()
    with patch.object(watch.Path, 'home', return_value=tmp_path), \
         patch.object(watch.urllib.request, 'urlopen', return_value=response), \
         patch.object(watch.shutil, 'disk_usage', return_value=SimpleNamespace(used=95, free=5, total=100)), \
         patch('sys.argv', ['watch_public.py', '--dry-run']), contextlib.redirect_stdout(out):
        assert watch.main() is True
    result = json.loads(out.getvalue())
    assert result['failures'] == ['offsite_copy_stale', 'offsite_disk_space']
    assert (base / 'watch-state.json').read_text() == '{broken'


def test_fresh_future_and_missing_marker_are_distinguished(tmp_path):
    base = tmp_path / '.local/share/schulpilot-offsite'
    base.mkdir(parents=True)
    response = MagicMock()
    response.__enter__.return_value.status = 200
    response.__enter__.return_value.read.return_value = b'{"status":"ok"}'
    disk = SimpleNamespace(used=1, free=2**40, total=2**40 + 1)
    for value, expected in (({'checked_at': 2000}, []), ({'checked_at': 2001}, ['offsite_copy_stale']),
                            ({'checked_at': True}, ['offsite_copy_stale']), ({}, ['offsite_copy_stale'])):
        (base / 'last-success.json').write_text(json.dumps(value))
        out = io.StringIO()
        with patch.object(watch.Path, 'home', return_value=tmp_path), \
             patch.object(watch.time, 'time', return_value=2000), \
             patch.object(watch.urllib.request, 'urlopen', return_value=response), \
             patch.object(watch.shutil, 'disk_usage', return_value=disk), \
             patch('sys.argv', ['watch_public.py', '--dry-run']), contextlib.redirect_stdout(out):
            assert bool(watch.main()) is bool(expected)
        assert json.loads(out.getvalue())['failures'] == expected


def test_interrupted_transaction_requires_reconciliation_only_after_pull_lock(tmp_path):
    import fcntl

    lock_path = tmp_path / '.pull.lock'
    lock_path.touch()
    pending = tmp_path / '.erasure-ledger.pending'
    pending.touch()
    with lock_path.open('rb') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert watch.interrupted_offsite_transaction(tmp_path) is False
    assert watch.interrupted_offsite_transaction(tmp_path) is True
    pending.unlink()
    assert watch.interrupted_offsite_transaction(tmp_path) is False
    previous = tmp_path / '.erasure-ledger.previous'
    previous.symlink_to(tmp_path / 'missing')
    assert watch.interrupted_offsite_transaction(tmp_path) is True
    previous.unlink()
    (tmp_path / '.offsite-status.previous').symlink_to(tmp_path / 'missing')
    assert watch.interrupted_offsite_transaction(tmp_path) is True


def test_interrupted_transaction_without_trustworthy_lock_fails_closed(tmp_path):
    pending = tmp_path / '.erasure-ledger.pending'
    pending.touch()
    assert watch.interrupted_offsite_transaction(tmp_path) is True
    lock_path = tmp_path / '.pull.lock'
    lock_path.symlink_to(tmp_path / 'missing')
    assert watch.interrupted_offsite_transaction(tmp_path) is True


def test_interrupted_transaction_reaches_neutral_alarm(tmp_path):
    base = tmp_path / '.local/share/schulpilot-offsite'
    base.mkdir(parents=True)
    (base / 'last-success.json').write_text(json.dumps({'checked_at': 2000}))
    (base / '.erasure-ledger.pending').touch()
    response = MagicMock()
    response.__enter__.return_value.status = 200
    response.__enter__.return_value.read.return_value = b'{"status":"ok"}'
    disk = SimpleNamespace(used=1, free=2**40, total=2**40 + 1)
    out = io.StringIO()
    with patch.object(watch.Path, 'home', return_value=tmp_path), \
         patch.object(watch.time, 'time', return_value=2000), \
         patch.object(watch.urllib.request, 'urlopen', return_value=response), \
         patch.object(watch.shutil, 'disk_usage', return_value=disk), \
         patch('sys.argv', ['watch_public.py', '--dry-run']), contextlib.redirect_stdout(out):
        assert watch.main() is True
    assert json.loads(out.getvalue())['failures'] == ['offsite_transaction_incomplete']


def test_interrupted_transaction_lock_error_is_reported(tmp_path):
    (tmp_path / '.erasure-ledger.pending').touch()
    (tmp_path / '.pull.lock').touch()
    with patch.object(watch.fcntl, 'flock', side_effect=OSError('unavailable')):
        assert watch.interrupted_offsite_transaction(tmp_path) is True
