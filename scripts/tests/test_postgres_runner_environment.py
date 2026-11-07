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
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/test_postgres.py'), str(probe)],
                            cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr + result.stdout
    assert '1 passed' in result.stdout
