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
