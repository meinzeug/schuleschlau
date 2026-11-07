"""Synthetic messages must not outlive their retention after a restore."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from schulpilot.db import DB, Base, Message, now
from schulpilot.message_retention import RETENTION_SECONDS, purge_expired
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]


def test_live_message_cutoff_is_strict_and_idempotent(household):
    _, child = household
    current = 1_900_000_000
    with DB.begin() as db:
        messages = [Message(child_id=child['id'], kind='help', body='synthetic', created=stamp)
                    for stamp in (current - RETENTION_SECONDS - 1, current - RETENTION_SECONDS, current)]
        db.add_all(messages)
        db.flush()
        identifiers = [message.id for message in messages]
        assert purge_expired(db, current) == 1
        assert purge_expired(db, current) == 0
        assert db.get(Message, identifiers[0]) is None
        assert all(db.get(Message, identifier) is not None for identifier in identifiers[1:])
        with pytest.raises(ValueError):
            purge_expired(db, True)


@pytest.mark.parametrize('condition', ['valid', 'tampered', 'missing-time', 'invalid-time', 'future-time'])
def test_real_restore_cli_requires_verified_journal_and_explicit_time(tmp_path, household, condition):
    _, child = household
    current = int(now())
    with DB.begin() as db:
        old = Message(child_id=child['id'], kind='help', body='synthetic old',
                      created=current - RETENTION_SECONDS - 3600)
        retained = Message(child_id=child['id'], kind='reply', body='synthetic recent', created=current)
        db.add_all([old, retained])
        db.flush()
        old_id, retained_id = old.id, retained.id
    with DB() as db:
        snapshot = {table: list(db.execute(table.select()).mappings()) for table in Base.metadata.sorted_tables}

    target = tmp_path / 'messages_restore_test'
    engine = create_engine('sqlite:///' + str(target))
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        for table, rows in snapshot.items():
            if rows:
                connection.execute(table.insert(), [dict(row) for row in rows])
    key = tmp_path / 'synthetic-key'
    ledger = tmp_path / 'synthetic-ledger'
    uploads = tmp_path / 'restored-uploads'
    key.write_text('synthetic-key')
    ledger.write_text('{"record":{},"signature":"invalid"}\n' if condition == 'tampered' else '')
    uploads.mkdir()
    env = {**os.environ, 'ENVIRONMENT': 'test'}
    command = [
        sys.executable, str(ROOT / 'scripts/reconcile_restore.py'), '--diagnostic-only',
        '--database-url', 'sqlite:///' + str(target), '--ledger', str(ledger),
        '--master-key-file', str(key), '--uploads', str(uploads),
    ]
    if condition != 'missing-time':
        stamp = 0 if condition == 'invalid-time' else current + 86400 if condition == 'future-time' else current
        command += ['--retention-as-of', str(stamp)]
    result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30)
    assert (result.returncode == 0) is (condition == 'valid')
    with Session(engine) as db:
        assert (db.get(Message, old_id) is not None) is (condition != 'valid')
        assert db.get(Message, retained_id) is not None
    with DB() as db:
        assert db.get(Message, old_id) is not None
        assert db.get(Message, retained_id) is not None
    engine.dispose()
