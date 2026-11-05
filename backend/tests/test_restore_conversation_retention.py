"""Private conversation expiry also applies to an isolated older snapshot."""

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from schulpilot.conversation_retention import RETENTION_SECONDS, purge_expired
from schulpilot.db import DB, Base, ParentLearningReview, SchulbuddyTurn, TutorTurn, now
from schulpilot.db import Session as UserSession
from schulpilot.erasure import signed
from schulpilot.schulbuddy import history_for
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
MODELS = (TutorTurn, SchulbuddyTurn, ParentLearningReview)


def synthetic_journal(key, tampered=False):
    record = {'id': 'a' * 32, 'scope': 'material', 'target': 'b' * 32, 'created': 1}
    line = json.loads(signed(record, key))
    if tampered:
        line['signature'] = '0' * 64
    return json.dumps(line) + '\n'


def create_rows(db, household, current):
    parent, child = household
    session = db.scalar(select(UserSession).where(UserSession.user_id == parent['id']))
    identifiers = {}
    for index, created in enumerate((current - RETENTION_SECONDS - 1, current - RETENTION_SECONDS, current)):
        tutor = TutorTurn(child_id=child['id'], user_id=parent['id'], question='SYNTHETISCH', created=created)
        buddy = SchulbuddyTurn(child_id=child['id'], user_id=parent['id'], session_id=session.id,
            job_id=f'{index:032x}', request_key=f'request-{index}', request_hash='a' * 64,
            context_key='b' * 64, scope={}, source_revisions=[], question='SYNTHETISCH', created=created)
        review = ParentLearningReview(child_id=child['id'], family_id=parent['families'][0]['id'],
            requested_by=parent['id'], signature='c' * 64, observations={}, created=created)
        db.add_all((tutor, buddy, review))
        db.flush()
        for row in (tutor, buddy, review):
            identifiers.setdefault(type(row), []).append(row.id)
    return identifiers


def test_live_conversation_cutoff_is_strict_and_idempotent(household):
    current = 1_900_000_000
    with DB.begin() as db:
        identifiers = create_rows(db, household, current)
        with pytest.raises(ValueError):
            purge_expired(db, True)
        assert purge_expired(db, current) == {model.__tablename__: 1 for model in MODELS}
        assert purge_expired(db, current) == {model.__tablename__: 0 for model in MODELS}
        for model in MODELS:
            assert db.get(model, identifiers[model][0]) is None
            assert all(db.get(model, identifier) is not None for identifier in identifiers[model][1:])


def test_existing_tutor_reply_cascade_is_identical_on_live_expiry(household):
    current = 1_900_000_000
    parent, child = household
    with DB.begin() as db:
        old = TutorTurn(child_id=child['id'], user_id=parent['id'], question='SYNTHETISCH ALT',
                        created=current - RETENTION_SECONDS - 1)
        db.add(old)
        db.flush()
        recent = TutorTurn(child_id=child['id'], user_id=parent['id'], question='SYNTHETISCH NEU',
                           reply_to=old.id, created=current)
        db.add(recent)
        db.flush()
        recent_id = recent.id
        purge_expired(db, current)
        db.expire_all()
        assert db.get(TutorTurn, recent_id) is None


def test_buddy_reply_to_expired_turn_remains_but_cannot_resume_missing_history(household):
    current = 1_900_000_000
    with DB.begin() as db:
        identifiers = create_rows(db, household, current)
        old_id, _, recent_id = identifiers[SchulbuddyTurn]
        db.get(SchulbuddyTurn, recent_id).reply_to = old_id
        db.flush()
        purge_expired(db, current)
        db.expire_all()
        assert db.get(SchulbuddyTurn, old_id) is None
        recent = db.get(SchulbuddyTurn, recent_id)
        assert recent is not None and recent.reply_to == old_id
        with pytest.raises(HTTPException) as error:
            history_for(db, recent)
        assert error.value.status_code == 409


def test_live_maintenance_uses_the_same_conversation_cutoff(household):
    from schulpilot.worker import maintenance

    current = int(now())
    with DB.begin() as db:
        identifiers = create_rows(db, household, current)
        # Maintenance reads a fresh clock; avoid a one-second boundary race.
        for model in MODELS:
            db.get(model, identifiers[model][1]).created += 60
    maintenance()
    with DB() as db:
        for model in MODELS:
            assert db.get(model, identifiers[model][0]) is None
            assert all(db.get(model, identifier) is not None for identifier in identifiers[model][1:])


@pytest.mark.parametrize('condition', ['valid', 'tampered', 'missing-table'])
def test_restore_reapplies_conversation_retention_only_after_verified_journal(tmp_path, household, condition):
    current = int(now())
    with DB.begin() as db:
        identifiers = create_rows(db, household, current)
    with DB() as db:
        snapshot = {table: list(db.execute(table.select()).mappings()) for table in Base.metadata.sorted_tables}
    target = tmp_path / 'conversations_restore_test'
    engine = create_engine('sqlite:///' + str(target))
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        for table, rows in snapshot.items():
            if rows:
                connection.execute(table.insert(), [dict(row) for row in rows])
        if condition == 'missing-table':
            connection.exec_driver_sql('DROP TABLE parent_learning_reviews')
    key, ledger, uploads = tmp_path / 'synthetic-key', tmp_path / 'synthetic-ledger', tmp_path / 'uploads'
    key.write_text('synthetic-key')
    ledger.write_text(synthetic_journal('synthetic-key', condition == 'tampered'))
    uploads.mkdir()
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/reconcile_restore.py'),
        '--database-url', 'sqlite:///' + str(target), '--ledger', str(ledger), '--master-key-file', str(key),
        '--uploads', str(uploads), '--retention-as-of', str(current)],
        env={**os.environ, 'ENVIRONMENT': 'test'}, capture_output=True, text=True, timeout=30)
    assert (result.returncode == 0) is (condition == 'valid')
    assert 'SYNTHETISCH' not in result.stdout + result.stderr
    with Session(engine) as db:
        for model in MODELS:
            if model is ParentLearningReview and condition == 'missing-table':
                continue
            assert (db.get(model, identifiers[model][0]) is not None) is (condition != 'valid')
            assert all(db.get(model, identifier) is not None for identifier in identifiers[model][1:])
    with DB() as db:
        for model in MODELS:
            assert all(db.get(model, identifier) is not None for identifier in identifiers[model])
    engine.dispose()


@pytest.mark.parametrize('tampered', [False, True])
def test_actual_rehearsal_inline_code_applies_cutoff_after_journal_check(tmp_path, household, tampered):
    current = int(now())
    with DB.begin() as db:
        identifiers = create_rows(db, household, current)
    with DB() as db:
        snapshot = {table: list(db.execute(table.select()).mappings()) for table in Base.metadata.sorted_tables}
    target = tmp_path / 'inline_restore_test'
    engine = create_engine('sqlite:///' + str(target))
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        for table, rows in snapshot.items():
            if rows:
                connection.execute(table.insert(), [dict(row) for row in rows])
        connection.exec_driver_sql('CREATE TABLE alembic_version (version_num varchar(32) NOT NULL)')
        connection.exec_driver_sql("INSERT INTO alembic_version VALUES ('synthetic')")
    tree = ast.parse((ROOT / 'deploy/restore_check.py').read_text())
    code = next(ast.literal_eval(node.value) for node in ast.walk(tree)
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'code' for t in node.targets)
                and isinstance(node.value, ast.Constant) and 'retained_image_names' in str(node.value.value))
    # The isolated snapshot already has the current schema. We exercise the
    # actual embedded transaction, not a separate reimplementation; migration
    # and PostgreSQL restore mechanics are intentionally outside this test.
    prelude = 'import schulpilot.migrate as migration\nmigration.upgrade = lambda: None\n'
    result = subprocess.run([sys.executable, '-c', prelude + code],
        input=synthetic_journal(os.environ['MASTER_KEY'], tampered),
        env={**os.environ, 'ENVIRONMENT': 'test', 'DATABASE_URL': 'sqlite:///' + str(target),
             'PYTHONPATH': str(ROOT / 'backend'), 'SCHULPILOT_RESTORE_RETENTION_AS_OF': str(current)},
        capture_output=True, text=True, timeout=30)
    assert (result.returncode == 0) is (not tampered), result.stderr
    assert 'SYNTHETISCH' not in result.stdout + result.stderr
    with Session(engine) as db:
        for model in MODELS:
            assert (db.get(model, identifiers[model][0]) is not None) is tampered
            assert all(db.get(model, identifier) is not None for identifier in identifiers[model][1:])
    with DB() as db:
        for model in MODELS:
            assert all(db.get(model, identifier) is not None for identifier in identifiers[model])
    engine.dispose()
