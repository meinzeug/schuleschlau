"""Actual disposable cluster must ignore inherited libpq/loader settings."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_hostile_parent_environment_cannot_redirect_disposable_cluster(tmp_path):
    probe = tmp_path / 'test_disposable_connection.py'
    probe.write_text('''\
import os
from pathlib import Path
import psycopg
from sqlalchemy.engine import make_url

def test_clean_environment_uses_unix_socket():
    for key in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS", "PGSSLMODE", "LD_PRELOAD", "LD_LIBRARY_PATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTEST_ADDOPTS"):
        assert key not in os.environ, key
    url = make_url(os.environ["TEST_DATABASE_URL"])
    assert os.environ["PGHOST"] == url.query["host"]
    assert os.environ["PGPORT"] == url.query["port"]
    assert os.environ["PGDATABASE"] == "schulpilot_isolated_test"
    assert Path(os.environ["PGPASSFILE"]).parent == Path(os.environ["HOME"])
    with psycopg.connect() as connection:
        name, remote, data = connection.execute("SELECT current_database(), inet_server_addr(), current_setting('data_directory')").fetchone()
        assert name == "schulpilot_isolated_test" and remote is None
        assert Path(data).parent == Path(os.environ["HOME"])
''')
    env = {**os.environ, 'TMPDIR': '/dev/shm', 'PGHOSTADDR': '127.0.0.1', 'PGSERVICE': 'synthetic-invalid',
           'PGSERVICEFILE': '/synthetic-invalid', 'PGOPTIONS': '-c default_transaction_read_only=on',
           'PGSSLMODE': 'disable', 'LD_LIBRARY_PATH': '/synthetic-invalid',
           'PYTHONSTARTUP': '/synthetic-invalid', 'PYTEST_ADDOPTS': '--invalid-synthetic-flag'}
    # Set loader/Python variables only after the runner interpreter has
    # started: this tests what it passes to children without loading an
    # untrusted library into the parent test process itself.
    bootstrap = ("import os,runpy,sys; "
                 "os.environ['LD_PRELOAD']='/synthetic-invalid'; "
                 "os.environ['PYTHONHOME']='/synthetic-invalid'; "
                 "os.environ['PYTHONPATH']='/synthetic-invalid'; "
                 "sys.argv=sys.argv[1:]; runpy.run_path(sys.argv[0],run_name='__main__')")
    result = subprocess.run([sys.executable, '-c', bootstrap, str(ROOT / 'scripts/test_postgres.py'), str(probe)],
                            cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr + result.stdout
    assert '1 passed' in result.stdout


def test_browser_optins_are_rejected_before_cluster_creation(tmp_path):
    import importlib.util


    spec = importlib.util.spec_from_file_location('runner', ROOT / 'scripts/test_postgres.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    for option in runner.BROWSER_ONLY_OPTIONS:
        env = {**os.environ, option: '1', 'TMPDIR': str(tmp_path)}
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/test_postgres.py')], cwd=ROOT, env=env,
                                capture_output=True, text=True, timeout=10)
        assert result.returncode != 0 and option in result.stderr
        assert list(tmp_path.iterdir()) == []


def test_cluster_directory_is_preserved_when_stop_is_uncertain(tmp_path, monkeypatch):
    import importlib.util
    from types import SimpleNamespace

    import pytest

    spec = importlib.util.spec_from_file_location('runner', ROOT / 'scripts/test_postgres.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    for case in ('stop_failed', 'stop_timeout', 'status_running', 'status_error', 'startup_uncertain'):
        root = tmp_path / case
        root.mkdir()
        data = root / 'database'
        data.mkdir()
        (data / 'synthetic').write_text('preserve')
        def run(args, **_kwargs):
            if args[-1] == 'stop':
                if case == 'stop_timeout':
                    raise subprocess.TimeoutExpired(args, 60)
                return SimpleNamespace(returncode=1 if case == 'stop_failed' else 0)
            return SimpleNamespace(returncode=0 if case == 'status_running' else 1)
        monkeypatch.setattr(runner.subprocess, 'run', run)
        with pytest.raises(RuntimeError, match='uncertain'):
            runner.cleanup_cluster(root, data, Path('/synthetic/bin'), {}, start_attempted=True,
                                   started=case != 'startup_uncertain')
        assert (data / 'synthetic').read_text() == 'preserve'


def test_cluster_directory_is_removed_only_after_confirmed_stop(tmp_path, monkeypatch):
    import importlib.util
    from types import SimpleNamespace

    spec = importlib.util.spec_from_file_location('runner', ROOT / 'scripts/test_postgres.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    root = tmp_path / 'cluster'
    root.mkdir()
    data = root / 'database'
    data.mkdir()
    calls = []
    def run(args, **_kwargs):
        calls.append(args[-1])
        return SimpleNamespace(returncode=0 if args[-1] == 'stop' else 3)
    monkeypatch.setattr(runner.subprocess, 'run', run)
    runner.cleanup_cluster(root, data, Path('/synthetic/bin'), {}, start_attempted=True, started=True)
    assert calls == ['stop', 'status']
    assert not root.exists()
