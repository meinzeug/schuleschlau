"""Synthetic fail-closed tests for the capacity runner's database identity guard."""
import importlib.util
import os
import pwd
import socket
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('capacity_guard', ROOT / 'backend/tests/capacity_guard.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


@pytest.fixture
def private_cluster(monkeypatch):
    temporary = tempfile.TemporaryDirectory(prefix='schulpilot-isolated-pg-', dir='/tmp')
    root = Path(temporary.name)
    sock, data = root / 'socket', root / 'database'
    sock.mkdir(mode=0o700)
    data.mkdir(mode=0o700)
    server = socket.socket(socket.AF_UNIX)
    server.bind(str(sock / '.s.PGSQL.55440'))
    user = pwd.getpwuid(os.getuid()).pw_name
    url = URL.create('postgresql+psycopg', username=user, database='schulpilot_isolated_test',
                     query={'host': str(sock), 'port': '55440'}).render_as_string(hide_password=False)
    monkeypatch.setenv('TEST_DATABASE_URL', url)
    monkeypatch.setenv('DATABASE_URL', url)
    monkeypatch.setenv('ENVIRONMENT', 'test')
    monkeypatch.setattr(guard.tempfile, 'gettempdir', lambda: str(root))
    calls = []
    def run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(stdout=f'schulpilot_isolated_test|unix|{data}\n')
    monkeypatch.setattr(guard.subprocess, 'run', run)
    try:
        yield root, sock, data, calls
    finally:
        server.close()
        temporary.cleanup()


def test_runner_tempdir_and_parent_style_both_verify_server(private_cluster, monkeypatch):
    root, _, _, calls = private_cluster
    guard.require_private_profile_database(helper=True)
    monkeypatch.setattr(guard.tempfile, 'gettempdir', lambda: str(root.parent))
    guard.require_private_profile_database()
    assert len(calls) == 2
    args, kwargs = calls[0]
    assert args[0] == '/usr/lib/postgresql/16/bin/psql' and '-X' in args and '-w' in args
    assert kwargs['timeout'] == 5 and kwargs['check'] is True
    assert set(kwargs['env']) == {'PATH', 'HOME', 'LANG', 'PGPASSFILE', 'PGCONNECT_TIMEOUT'}


def test_mismatched_actual_server_data_directory_is_rejected(private_cluster, monkeypatch):
    monkeypatch.setattr(guard.subprocess, 'run', lambda *a, **k: SimpleNamespace(
        stdout='schulpilot_isolated_test|unix|/var/lib/postgresql/16/main\n'))
    with pytest.raises(RuntimeError, match='identity'):
        guard.require_private_profile_database()


def test_unexpected_database_or_helper_environment_is_rejected(private_cluster, monkeypatch):
    monkeypatch.setenv('TEST_DATABASE_URL', 'postgresql+psycopg://x@localhost/production')
    with pytest.raises(RuntimeError):
        guard.require_private_profile_database()
    assert not private_cluster[3]


def test_insecure_directory_is_rejected_without_connecting(private_cluster):
    _, _, data, calls = private_cluster
    data.chmod(0o755)
    with pytest.raises(RuntimeError, match='Insecure'):
        guard.require_private_profile_database()
    assert not calls


def test_helper_requires_exact_application_url(private_cluster, monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///other')
    with pytest.raises(RuntimeError, match='environment'):
        guard.require_private_profile_database(helper=True)
    assert not private_cluster[3]
