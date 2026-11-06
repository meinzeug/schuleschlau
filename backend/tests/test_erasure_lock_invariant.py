"""Synthetic transactions must not publish deletion outbox rows unlocked."""

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context

import pytest
from schulpilot.db import DB, ErasureRequest, engine
from schulpilot.erasure import _clear_erasure_pool_connection, journal_write_lock, request
from sqlalchemy import create_engine, insert, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session


def test_request_without_lock_is_rejected():
    with DB() as db:
        with pytest.raises(RuntimeError, match="requires the journal write lock"):
            request(db, "user", "a" * 32)
        assert not db.new


def test_guards_are_installed_when_only_db_is_imported():
    program = """\
from sqlalchemy import insert
from schulpilot.db import engine, ErasureRequest
try:
    with engine.begin() as connection:
        connection.execute(insert(ErasureRequest).values(scope='user', target='0' * 32))
except RuntimeError as exc:
    assert 'requires the journal write lock' in str(exc)
else:
    raise AssertionError('database import did not install erasure guard')
"""
    subprocess.run([sys.executable, "-c", program], check=True, timeout=15)


def test_separate_restore_engine_can_import_existing_outbox_without_live_lock():
    restore_engine = create_engine("sqlite://")
    try:
        ErasureRequest.__table__.create(restore_engine)
        with Session(restore_engine) as db:
            db.add(ErasureRequest(scope="user", target="a" * 32))
            db.commit()
            assert db.scalar(select(ErasureRequest.target)) == "a" * 32
    finally:
        restore_engine.dispose()


def test_direct_outbox_insertion_without_lock_is_rejected():
    with DB() as db:
        db.add(ErasureRequest(scope="user", target="b" * 32))
        with pytest.raises(RuntimeError, match="requires the journal write lock"):
            db.commit()
        db.rollback()
        assert db.scalar(select(ErasureRequest.id)) is None


def test_session_execute_insert_cannot_bypass_journal_guard():
    with DB() as db:
        with pytest.raises(RuntimeError, match="requires the journal write lock"):
            db.execute(insert(ErasureRequest).values(scope="user", target="5" * 32))
        db.rollback()
        with journal_write_lock():
            db.execute(insert(ErasureRequest).values(scope="user", target="5" * 32))
        with pytest.raises(RuntimeError, match="requires the journal write lock"):
            db.commit()
        db.rollback()
        assert db.scalar(select(ErasureRequest.id)) is None


def test_bulk_insert_must_hold_lock_through_commit():
    with DB() as db:
        with pytest.raises(RuntimeError, match="requires the journal write lock"):
            db.bulk_insert_mappings(ErasureRequest, [{"scope": "user", "target": "6" * 32}])
        db.rollback()
        with journal_write_lock():
            db.bulk_insert_mappings(ErasureRequest, [{"scope": "user", "target": "6" * 32}])
        with pytest.raises(RuntimeError, match="requires the journal write lock"):
            db.commit()
        db.rollback()


def test_connection_commit_after_lock_is_rejected():
    with engine.connect() as connection:
        with journal_write_lock():
            connection.execute(insert(ErasureRequest).values(scope="user", target="7" * 32))
        with pytest.raises(RuntimeError, match="requires the journal write lock"):
            connection.commit()
        connection.rollback()


def test_failed_dbapi_commit_cannot_be_retried_after_lock_release(monkeypatch):
    original = engine.dialect.do_commit
    first = True

    def fail_once(dbapi_connection):
        nonlocal first
        if first:
            first = False
            raise engine.dialect.loaded_dbapi.OperationalError("synthetic commit failure")
        return original(dbapi_connection)

    monkeypatch.setattr(engine.dialect, "do_commit", fail_once)
    with engine.connect() as connection:
        with journal_write_lock():
            connection.execute(insert(ErasureRequest).values(scope="user", target="b" * 32))
            with pytest.raises(OperationalError):
                connection.commit()
        connection.rollback()
        connection.execute(text("SELECT 1"))
        with pytest.raises(RuntimeError, match="requires the journal write lock"):
            connection.commit()
    with DB() as db:
        assert db.scalar(select(ErasureRequest.id)) is None


def test_pool_reset_keeps_marker_if_physical_rollback_fails():
    class BrokenConnection:
        def rollback(self):
            raise RuntimeError("synthetic rollback failure")

    class Record:
        info = {"schulpilot_erasure_connection_lock": object()}

    record = Record()
    with pytest.raises(RuntimeError, match="synthetic rollback failure"):
        _clear_erasure_pool_connection(BrokenConnection(), record, None)
    assert "schulpilot_erasure_connection_lock" in record.info


def test_option_engine_cannot_bypass_application_pool_guard():
    with engine.execution_options(isolation_level="SERIALIZABLE").connect() as connection:
        with pytest.raises(RuntimeError, match="requires the journal write lock"):
            connection.execute(insert(ErasureRequest).values(scope="user", target="8" * 32))
        connection.rollback()
        with journal_write_lock():
            connection.execute(insert(ErasureRequest).values(scope="user", target="8" * 32))
        with pytest.raises(RuntimeError, match="requires the journal write lock"):
            connection.commit()
        connection.rollback()


def test_autocommit_cannot_create_an_erasure_record():
    with journal_write_lock(), engine.execution_options(isolation_level="AUTOCOMMIT").connect() as connection:
        with pytest.raises(RuntimeError, match="transactional connection"):
            connection.execute(insert(ErasureRequest).values(scope="user", target="9" * 32))


def test_rolled_back_savepoint_keeps_conservative_commit_guard():
    with engine.connect() as connection:
        outer = connection.begin()
        nested = connection.begin_nested()
        with journal_write_lock():
            connection.execute(insert(ErasureRequest).values(scope="user", target="a" * 32))
            nested.rollback()
        with pytest.raises(RuntimeError, match="requires the journal write lock"):
            outer.commit()
        connection.rollback()


def test_lock_must_survive_flush_until_commit():
    with DB() as db:
        with journal_write_lock():
            request(db, "user", "c" * 32)
            db.flush()
        with pytest.raises(RuntimeError, match="requires the journal write lock"):
            db.commit()
        db.rollback()
        assert db.scalar(select(ErasureRequest.id)) is None


def test_new_lock_does_not_authorize_previous_transaction():
    with DB() as db:
        with journal_write_lock():
            request(db, "user", "d" * 32)
            db.flush()
        with journal_write_lock():
            with pytest.raises(RuntimeError, match="outlived"):
                db.commit()
        db.rollback()
        assert db.scalar(select(ErasureRequest.id)) is None


def test_commit_and_later_transaction_under_separate_locks():
    with DB() as db:
        for target in ("e" * 32, "f" * 32):
            with journal_write_lock():
                request(db, "user", target)
                db.commit()
        assert len(list(db.scalars(select(ErasureRequest.id)))) == 2


def test_rollback_clears_transaction_owner():
    with DB() as db:
        with journal_write_lock():
            request(db, "user", "1" * 32)
            db.rollback()
        with journal_write_lock():
            request(db, "user", "2" * 32)
            db.commit()
        assert list(db.scalars(select(ErasureRequest.target))) == ["2" * 32]


def test_copied_context_expires_when_its_lock_is_released():
    with journal_write_lock():
        stale_context = copy_context()
    with DB() as db:
        with pytest.raises(RuntimeError, match="requires the journal write lock"):
            stale_context.run(request, db, "user", "3" * 32)


def test_copied_context_cannot_authorize_another_thread():
    with journal_write_lock():
        foreign_context = copy_context()

        def insert():
            with DB() as db:
                foreign_context.run(request, db, "user", "4" * 32)

        with ThreadPoolExecutor(max_workers=1) as executor:
            with pytest.raises(RuntimeError, match="requires the journal write lock"):
                executor.submit(insert).result(timeout=5)
