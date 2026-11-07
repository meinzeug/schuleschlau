"""Synthetic unit, path and database identity cases only."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('first_install_guard', ROOT / 'deploy/first_install_guard.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def run_factory(*, bad_unit=None, database='schulpilot|0|0|0'):
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        if args[0] == 'systemctl':
            unit = args[2]
            state = 'loaded' if unit == bad_unit else 'not-found'
            text = f'LoadState={state}\nActiveState=inactive\nSubState=dead\nJob=\n'
            if unit.endswith('.service'):
                text += 'MainPID=0\nControlGroup=\n'
        else:
            text = database + '\n'
        return SimpleNamespace(stdout=text, returncode=0)
    return calls, run


def test_clean_bootstrap_can_proceed(tmp_path):
    (tmp_path / 'uploads').mkdir()
    calls, run = run_factory()
    assert guard.previous_release(tmp_path / 'current') is None
    guard.verify_first_install(data_dir=tmp_path, run=run)
    assert len(calls) == len(guard.UNITS) + 1
    assert calls[-1][:6] == ['runuser', '-u', 'postgres', '--', '/usr/bin/env', '-i']


@pytest.mark.parametrize('unit', guard.UNITS)
def test_existing_unit_is_not_first_install(tmp_path, unit):
    (tmp_path / 'uploads').mkdir()
    _, run = run_factory(bad_unit=unit)
    with pytest.raises(guard.FirstInstallError, match='existing service'):
        guard.verify_first_install(data_dir=tmp_path, run=run)


@pytest.mark.parametrize('database', ['schulpilot|1|0|0', 'schulpilot|0|1|0', 'schulpilot|0|0|1', 'other|0|0|0'])
def test_existing_db_or_sessions_are_not_first_install(tmp_path, database):
    (tmp_path / 'uploads').mkdir()
    _, run = run_factory(database=database)
    with pytest.raises(guard.FirstInstallError, match='database state'):
        guard.verify_first_install(data_dir=tmp_path, run=run)


def test_existing_data_or_symlink_denies_first_install(tmp_path):
    uploads = tmp_path / 'uploads'
    uploads.mkdir()
    (uploads / 'synthetic.jpg').write_text('synthetic')
    _, run = run_factory()
    with pytest.raises(guard.FirstInstallError, match='private data'):
        guard.verify_first_install(data_dir=tmp_path, run=run)
    bad = tmp_path / 'current'
    bad.symlink_to(tmp_path / 'missing')
    with pytest.raises(guard.FirstInstallError, match='inaccessible'):
        guard.previous_release(bad)


def test_valid_and_invalid_current_path(tmp_path):
    target = tmp_path / 'release'
    target.mkdir()
    current = tmp_path / 'current'
    current.symlink_to(target)
    assert guard.previous_release(current) == target
    current.unlink()
    current.write_text('unexpected')
    with pytest.raises(guard.FirstInstallError, match='not a symlink'):
        guard.previous_release(current)


def test_fresh_database_and_systemd_states_on_disposable_cluster(tmp_path, monkeypatch):
    """Actual synthetic PostgreSQL query and read-only systemd unit lookup."""
    import os
    import subprocess
    import uuid

    import psycopg
    from sqlalchemy.engine import make_url

    url = make_url(os.environ.get('TEST_DATABASE_URL', 'sqlite:///missing'))
    host = Path(url.query.get('host', ''))
    if (url.database != 'schulpilot_isolated_test' or not host.is_absolute()
            or not host.is_relative_to('/dev/shm') or not host.parent.name.startswith('schulpilot-isolated-pg-')):
        pytest.skip('requires disposable PostgreSQL cluster')
    opts = {'dbname': url.database, 'user': url.username, 'host': str(host), 'port': url.query['port']}
    synthetic_units = tuple('schulpilot-fixture-' + uuid.uuid4().hex + suffix for suffix in ('.service', '.timer'))
    monkeypatch.setattr(guard, 'UNITS', synthetic_units)
    (tmp_path / 'uploads').mkdir()
    with psycopg.connect(**opts, autocommit=True) as admin:
        admin.execute('CREATE DATABASE schulpilot')
        try:
            def run(args, **kwargs):
                if args[0] == 'systemctl':
                    return subprocess.run(args, **kwargs)
                # Override the production socket *only in this test adapter*.
                replacement = ['/usr/bin/psql', '-X', '-A', '-t', '-F', '|', '-v', 'ON_ERROR_STOP=1',
                               '-h', str(host), '-p', url.query['port'], '-U', url.username,
                               '-d', 'schulpilot', '-c', args[-1]]
                return subprocess.run(replacement, **kwargs)
            guard.verify_first_install(data_dir=tmp_path, run=run)
            with psycopg.connect(**{**opts, 'dbname': 'schulpilot'}, autocommit=True) as target:
                target.execute('CREATE TABLE synthetic_existing (value integer)')
            with pytest.raises(guard.FirstInstallError, match='database state'):
                guard.verify_first_install(data_dir=tmp_path, run=run)
        finally:
            admin.execute('DROP DATABASE schulpilot')


@pytest.mark.parametrize('suffix', [
    'DATABASE_URL=postgresql+psycopg://other@/other?host=/var/run/postgresql\n',
    'DATA_DIR=/tmp/existing-data\n',
    'PGHOSTADDR=192.0.2.1\n',
    'PGOPTIONS=-c search_path=private\n',
    'PYTHONPATH=/tmp/foreign-code\n',
    'LD_PRELOAD=/tmp/foreign-code.so\n',
    'PATH=/tmp/foreign-bin\n',
    'HOME=/tmp/foreign-home\n',
])
def test_first_install_rejects_configured_other_target_or_ambient_override(tmp_path, suffix):
    path = tmp_path / 'environment'
    lines = {'DATABASE_URL': 'postgresql+psycopg://schulpilot@/schulpilot?host=/var/run/postgresql',
             'DATA_DIR': '/var/lib/schulpilot'}
    key = suffix.split('=', 1)[0]
    if key in lines:
        del lines[key]
    path.write_text(''.join(f'{key}={value}\n' for key, value in lines.items()) + suffix)
    path.chmod(0o600)
    with pytest.raises(guard.FirstInstallError):
        guard.read_first_environment(path)


def test_first_install_config_is_bound_and_duplicate_or_symlink_rejected(tmp_path):
    path = tmp_path / 'environment'
    path.write_text('DATABASE_URL=postgresql+psycopg://schulpilot@/schulpilot?host=/var/run/postgresql\n'
                    'DATA_DIR=/var/lib/schulpilot\nENVIRONMENT=production\n')
    path.chmod(0o600)
    values, original_hash = guard.read_first_environment(path)
    assert values['DATA_DIR'] == '/var/lib/schulpilot'
    path.write_text(path.read_text() + 'SYNTHETIC_DEMO=true\n')
    assert guard.read_first_environment(path)[1] != original_hash
    path.write_text(path.read_text() + 'DATA_DIR=/var/lib/schulpilot\n')
    with pytest.raises(guard.FirstInstallError, match='Unsafe'):
        guard.read_first_environment(path)
    link = tmp_path / 'link'
    link.symlink_to(path)
    with pytest.raises(OSError):
        guard.read_first_environment(link)
