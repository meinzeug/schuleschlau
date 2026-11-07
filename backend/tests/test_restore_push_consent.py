"""Restores cannot resurrect withdrawn child push consent (synthetic only)."""

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest
from schulpilot.db import DB, Base, Child, PushDelivery, PushDevice, now
from schulpilot.db import Session as UserSession
from schulpilot.restore_push import clear_restored_push
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]


def seed(household):
    parent, child = household
    with DB.begin() as db:
        row = db.get(Child, child['id'])
        row.preferences = {'push_consent': True, 'daily_minutes': 35}
        row.preferences_revision = 7
        session = db.scalar(select(UserSession).where(UserSession.user_id == parent['id']))
        device = PushDevice(user_id=parent['id'], session_id=session.id, token_hash='e' * 64,
                            encrypted_token='synthetic-only', platform='web', timezone='Europe/Berlin',
                            quiet_start=0, quiet_end=0)
        db.add(device)
        db.flush()
        db.add(PushDelivery(device_id=device.id, dedup_key='synthetic-event', kind='test'))
    return child['id']


def test_restore_cleanup_is_idempotent_and_preserves_other_preferences(household):
    child_id = seed(household)
    with DB.begin() as db:
        clear_restored_push(db)
        db.flush()
        clear_restored_push(db)
    with DB() as db:
        child = db.get(Child, child_id)
        assert child.preferences == {'push_consent': False, 'daily_minutes': 35}
        assert child.preferences_revision == 8
        assert list(db.scalars(select(PushDevice))) == []
        assert list(db.scalars(select(PushDelivery))) == []


def test_exhausted_revision_fails_restore_transaction_closed(household):
    child_id = seed(household)
    with DB.begin() as db:
        db.get(Child, child_id).preferences_revision = 2147483647
    with pytest.raises(ValueError, match='revision exhausted'), DB.begin() as db:
        clear_restored_push(db)
    with DB() as db:
        assert db.get(Child, child_id).preferences['push_consent'] is True
        assert len(list(db.scalars(select(PushDevice)))) == 1


@pytest.mark.parametrize('route', ['cli', 'rehearsal'])
@pytest.mark.parametrize('condition', ['valid', 'tampered', 'missing-table', 'old-schema'])
def test_both_real_restore_paths_clear_only_after_verified_journal(tmp_path, household, route, condition):
    child_id = seed(household)
    with DB() as db:
        snapshot = {table: list(db.execute(table.select()).mappings()) for table in Base.metadata.sorted_tables}
    target = tmp_path / 'push_restore_test'
    engine = create_engine('sqlite:///' + str(target))
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        for table, rows in snapshot.items():
            if rows:
                connection.execute(table.insert(), [dict(row) for row in rows])
        if condition == 'missing-table':
            connection.exec_driver_sql('DROP TABLE push_devices')
        if condition == 'old-schema':
            connection.exec_driver_sql('ALTER TABLE children DROP COLUMN preferences_revision')
        connection.exec_driver_sql('CREATE TABLE alembic_version (version_num varchar(32) NOT NULL)')
        connection.exec_driver_sql("INSERT INTO alembic_version VALUES ('synthetic')")
    current = str(int(now()))
    ledger_data = '{"record":{},"signature":"invalid"}\n' if condition == 'tampered' else ''
    env = {**os.environ, 'ENVIRONMENT': 'test', 'PYTHONPATH': str(ROOT / 'backend')}
    if route == 'cli':
        key, ledger, uploads = tmp_path / 'key', tmp_path / 'ledger', tmp_path / 'uploads'
        key.write_text('synthetic-key')
        ledger.write_text(ledger_data)
        uploads.mkdir()
        cmd = [sys.executable, str(ROOT / 'scripts/reconcile_restore.py'), '--diagnostic-only', '--database-url', 'sqlite:///' + str(target),
               '--ledger', str(ledger), '--master-key-file', str(key), '--uploads', str(uploads),
               '--retention-as-of', current]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=30)
    else:
        tree = ast.parse((ROOT / 'deploy/restore_check.py').read_text())
        code = next(ast.literal_eval(node.value) for node in ast.walk(tree)
                    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'code' for t in node.targets)
                    and isinstance(node.value, ast.Constant) and 'retained_image_names' in str(node.value.value))
        env.update(DATABASE_URL='sqlite:///' + str(target), SCHULPILOT_RESTORE_RETENTION_AS_OF=current)
        prelude = 'import schulpilot.migrate as migration\nmigration.upgrade = lambda: None\n'
        result = subprocess.run([sys.executable, '-c', prelude + code], input=ledger_data,
                                env=env, capture_output=True, text=True, timeout=30)
    assert (result.returncode == 0) is (condition == 'valid'), result.stderr
    assert 'synthetic-only' not in result.stdout + result.stderr
    with Session(engine) as db:
        preferences = db.scalar(select(Child.preferences).where(Child.id == child_id))
        assert preferences['push_consent'] is (condition != 'valid')
        assert preferences['daily_minutes'] == 35
        if condition != 'old-schema':
            assert db.get(Child, child_id).preferences_revision == (8 if condition == 'valid' else 7)
        if condition != 'missing-table':
            assert len(list(db.scalars(select(PushDevice)))) == (0 if condition == 'valid' else 1)
            assert len(list(db.scalars(select(PushDelivery)))) == (0 if condition == 'valid' else 1)
    with DB() as db:
        original = db.get(Child, child_id)
        assert original.preferences['push_consent'] is True
        assert original.preferences_revision == 7
        assert len(list(db.scalars(select(PushDevice)))) == 1
        assert len(list(db.scalars(select(PushDelivery)))) == 1
    engine.dispose()


@pytest.mark.parametrize('route', ['cli', 'rehearsal'])
@pytest.mark.parametrize('tampered', [False, True])
def test_restore_paths_on_separate_isolated_postgresql(tmp_path, household, route, tampered):
    """Use only the throwaway cluster created by scripts/test_postgres.py."""
    from uuid import uuid4

    from sqlalchemy.engine import make_url

    test_url = os.environ.get('TEST_DATABASE_URL', '')
    if not test_url:
        pytest.skip('PostgreSQL-only restore test')
    url = make_url(test_url)
    socket = url.query.get('host', '')
    if (url.database != 'schulpilot_isolated_test' or url.query.get('port') != '55440'
            or not Path(socket).parent.name.startswith('schulpilot-isolated-pg-')
            or Path(socket).name != 'socket'):
        pytest.skip('Requires the disposable scripts/test_postgres.py cluster')
    child_id = seed(household)
    with DB() as db:
        snapshot = {table: list(db.execute(table.select()).mappings()) for table in Base.metadata.sorted_tables}
    name = 'consent_' + uuid4().hex + '_restore_test'
    admin = create_engine(url, isolation_level='AUTOCOMMIT')
    target = None
    created = False
    try:
        with admin.connect() as connection:
            connection.exec_driver_sql(f'CREATE DATABASE "{name}"')
        created = True
        target = create_engine(url.set(database=name))
        Base.metadata.create_all(target)
        with target.begin() as connection:
            for table, rows in snapshot.items():
                if rows:
                    connection.execute(table.insert(), [dict(row) for row in rows])
            connection.exec_driver_sql('CREATE TABLE alembic_version (version_num varchar(32) NOT NULL)')
            connection.exec_driver_sql("INSERT INTO alembic_version VALUES ('synthetic')")
        ledger_data = '{"record":{},"signature":"invalid"}\n' if tampered else ''
        env = {**os.environ, 'ENVIRONMENT': 'test', 'PYTHONPATH': str(ROOT / 'backend'),
               'PGHOST': socket, 'PGPORT': '55440'}
        if route == 'cli':
            key, ledger, uploads = tmp_path / 'key', tmp_path / 'ledger', tmp_path / 'uploads'
            key.write_text('synthetic-key')
            ledger.write_text(ledger_data)
            uploads.mkdir()
            clean_url = url.set(database=name, query={})
            cmd = [sys.executable, str(ROOT / 'scripts/reconcile_restore.py'), '--diagnostic-only', '--database-url', str(clean_url),
                   '--ledger', str(ledger), '--master-key-file', str(key), '--uploads', str(uploads),
                   '--retention-as-of', str(int(now()))]
            # A real isolated PostgreSQL copy must not change without an explicit
            # diagnostic action, even if the supplied ledger happens to be signed.
            blocked = subprocess.run([item for item in cmd if item != '--diagnostic-only'],
                                     env=env, capture_output=True, text=True, timeout=30)
            assert blocked.returncode != 0
            assert 'only --diagnostic-only' in blocked.stderr
            with Session(target) as before:
                assert before.get(Child, child_id).preferences['push_consent'] is True
                assert len(list(before.scalars(select(PushDevice)))) == 1
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=30)
        else:
            tree = ast.parse((ROOT / 'deploy/restore_check.py').read_text())
            code = next(ast.literal_eval(node.value) for node in ast.walk(tree)
                        if isinstance(node, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == 'code' for t in node.targets)
                        and isinstance(node.value, ast.Constant) and 'retained_image_names' in str(node.value.value))
            env.update(DATABASE_URL=str(url.set(database=name)), SCHULPILOT_RESTORE_RETENTION_AS_OF=str(int(now())))
            prelude = 'import schulpilot.migrate as migration\nmigration.upgrade = lambda: None\n'
            result = subprocess.run([sys.executable, '-c', prelude + code], input=ledger_data,
                                    env=env, capture_output=True, text=True, timeout=30)
        assert (result.returncode == 0) is (not tampered), result.stderr
        with Session(target) as db:
            restored = db.get(Child, child_id)
            assert restored.preferences['push_consent'] is tampered
            assert restored.preferences['daily_minutes'] == 35
            assert restored.preferences_revision == (7 if tampered else 8)
            assert len(list(db.scalars(select(PushDevice)))) == (1 if tampered else 0)
            assert len(list(db.scalars(select(PushDelivery)))) == (1 if tampered else 0)
        with DB() as db:
            assert db.get(Child, child_id).preferences['push_consent'] is True
            assert len(list(db.scalars(select(PushDevice)))) == 1
    finally:
        if target is not None:
            target.dispose()
        if created:
            with admin.connect() as connection:
                connection.exec_driver_sql(f'DROP DATABASE "{name}"')
        admin.dispose()


def test_postgresql_backup_0046_real_migration_and_restore(tmp_path, household):
    """Restore a synthetic 0046 dump, run real Alembic and reconcile push state."""
    from uuid import uuid4

    from sqlalchemy.engine import make_url

    raw_url = os.environ.get('TEST_DATABASE_URL', '')
    if not raw_url:
        pytest.skip('PostgreSQL-only migration and dump test')
    url = make_url(raw_url)
    socket = url.query.get('host', '')
    if (url.database != 'schulpilot_isolated_test' or url.query.get('port') != '55440'
            or not Path(socket).parent.name.startswith('schulpilot-isolated-pg-')
            or Path(socket).name != 'socket'):
        pytest.skip('Requires the disposable scripts/test_postgres.py cluster')
    child_id = seed(household)
    with DB() as db:
        snapshot = {table: list(db.execute(table.select()).mappings()) for table in Base.metadata.sorted_tables}
    names = ['old_' + uuid4().hex + '_restore_test', 'new_' + uuid4().hex + '_restore_test']
    admin = create_engine(url, isolation_level='AUTOCOMMIT')
    engines = []
    created = []
    try:
        with admin.connect() as connection:
            for name in names:
                connection.exec_driver_sql(f'CREATE DATABASE "{name}"')
                created.append(name)
        old = create_engine(url.set(database=names[0]))
        engines.append(old)
        Base.metadata.create_all(old)
        with old.begin() as connection:
            for table, rows in snapshot.items():
                if rows:
                    connection.execute(table.insert(), [dict(row) for row in rows])
            connection.exec_driver_sql('ALTER TABLE children DROP COLUMN preferences_revision')
            connection.exec_driver_sql('CREATE TABLE alembic_version (version_num varchar(32) NOT NULL)')
            connection.exec_driver_sql("INSERT INTO alembic_version VALUES ('0046')")
        old.dispose()
        backup = tmp_path / 'synthetic-0046.dump'
        binaries = Path('/usr/lib/postgresql/16/bin')
        db_args = ['-h', socket, '-p', '55440', '-U', url.username]
        subprocess.run([str(binaries / 'pg_dump'), *db_args, '--format=custom', '--file', str(backup), names[0]],
                       check=True, capture_output=True, timeout=30)
        subprocess.run([str(binaries / 'pg_restore'), *db_args, '--exit-on-error', '--no-owner', '--no-acl',
                        '-d', names[1], str(backup)], check=True, capture_output=True, timeout=30)
        restored = create_engine(url.set(database=names[1]))
        engines.append(restored)
        key, ledger, uploads = tmp_path / 'key', tmp_path / 'ledger', tmp_path / 'uploads'
        key.write_text('synthetic-key')
        ledger.write_text('')
        uploads.mkdir()
        env = {**os.environ, 'ENVIRONMENT': 'test', 'PYTHONPATH': str(ROOT / 'backend'),
               'PGHOST': socket, 'PGPORT': '55440'}
        clean_url = url.set(database=names[1], query={})
        cmd = [sys.executable, str(ROOT / 'scripts/reconcile_restore.py'), '--diagnostic-only', '--database-url', str(clean_url),
               '--ledger', str(ledger), '--master-key-file', str(key), '--uploads', str(uploads),
               '--retention-as-of', str(int(now()))]
        offline = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=30)
        assert offline.returncode != 0
        with restored.connect() as connection:
            assert connection.exec_driver_sql('SELECT version_num FROM alembic_version').scalar_one() == '0046'
            assert connection.exec_driver_sql('SELECT preferences FROM children').scalar_one()['push_consent'] is True
            assert connection.exec_driver_sql('SELECT count(*) FROM push_devices').scalar_one() == 1
        tree = ast.parse((ROOT / 'deploy/restore_check.py').read_text())
        code = next(ast.literal_eval(node.value) for node in ast.walk(tree)
                    if isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'code' for t in node.targets)
                    and isinstance(node.value, ast.Constant) and 'retained_image_names' in str(node.value.value))
        env.update(DATABASE_URL=str(url.set(database=names[1])), SCHULPILOT_RESTORE_RETENTION_AS_OF=str(int(now())))
        result = subprocess.run([sys.executable, '-c', code], input='', env=env,
                                capture_output=True, text=True, timeout=45)
        assert result.returncode == 0, result.stderr
        with Session(restored) as db:
            restored_child = db.get(Child, child_id)
            assert restored_child.preferences == {'push_consent': False, 'daily_minutes': 35}
            assert restored_child.preferences_revision == 2
            assert list(db.scalars(select(PushDevice))) == []
            assert list(db.scalars(select(PushDelivery))) == []
            assert all(session.revoked for session in db.scalars(select(UserSession)))
            assert db.connection().exec_driver_sql('SELECT version_num FROM alembic_version').scalar_one() == '0047'
        with old.connect() as connection:
            assert connection.exec_driver_sql('SELECT version_num FROM alembic_version').scalar_one() == '0046'
            assert connection.exec_driver_sql('SELECT preferences FROM children').scalar_one()['push_consent'] is True
            assert connection.exec_driver_sql('SELECT count(*) FROM push_devices').scalar_one() == 1
    finally:
        for engine in engines:
            engine.dispose()
        with admin.connect() as connection:
            for name in reversed(created):
                connection.exec_driver_sql(f'DROP DATABASE "{name}"')
        admin.dispose()
