"""Synthetic child deletion races with late learning-round insertion."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep

import pytest
from conftest import HEADERS
from fastapi.testclient import TestClient
from schulpilot import security
from schulpilot.db import DB, Child, ErasureRequest, LearningUnit, engine
from schulpilot.main import app
from sqlalchemy import event, select, text, update
from sqlalchemy.exc import IntegrityError


def test_late_unit_after_snapshot_rejects_child_erasure(api, household):
    if engine.dialect.name != 'postgresql':
        pytest.skip('Requires PostgreSQL row and foreign-key locks')
    _, child = household
    cid = child['id']
    selected = Event()
    def after_sql(conn, cursor, statement, parameters, context, executemany):
        if 'SELECT learning_units.id' in statement and 'FOR UPDATE' in statement:
            selected.set()
    event.listen(engine, 'after_cursor_execute', after_sql)
    headers = {**HEADERS, 'Authorization': api.headers['Authorization']}
    def remove():
        with TestClient(app, headers=headers) as client:
            return client.request('DELETE', f'/api/children/{cid}', json={'password':'secure-parent-pass-123'})
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            with DB.begin() as holder:
                holder.execute(update(Child).where(Child.id == cid).values(grade=Child.grade))
                deletion = pool.submit(remove)
                assert selected.wait(15)
                obj = LearningUnit(child_id=cid, subject='Mathematik', topic='synthetisch', explanation='Test', questions=[], provider='sample')
                holder.add(obj)
                holder.flush()
                unit_id=obj.id
            response = deletion.result(15)
        assert response.status_code == 409, response.text
        with DB() as db:
            assert db.get(Child, cid) is not None
            assert db.get(LearningUnit, unit_id) is not None
            assert db.scalar(select(ErasureRequest.id).where(ErasureRequest.target == cid)) is None
    finally:
        event.remove(engine, 'after_cursor_execute', after_sql)


def test_child_full_lock_blocks_new_unit_insert_until_erasure_commits(api, household, monkeypatch):
    if engine.dialect.name != 'postgresql':
        pytest.skip('Requires PostgreSQL row and foreign-key locks')
    _, child = household
    cid = child['id']
    child_locked = Event()
    release = Event()
    started = Event()
    original = security.lock_session_after_child
    def pause(db, user_id, session_id):
        child_locked.set()
        assert release.wait(15)
        return original(db, user_id, session_id)
    monkeypatch.setattr(security, 'lock_session_after_child', pause)
    headers = {**HEADERS, 'Authorization': api.headers['Authorization']}
    def remove():
        with TestClient(app, headers=headers) as client:
            return client.request('DELETE', f'/api/children/{cid}', json={'password':'secure-parent-pass-123'})
    def insert():
        try:
            with DB.begin() as db:
                db.add(LearningUnit(child_id=cid, subject='Mathematik', topic='synthetisch', explanation='Test', questions=[], provider='sample'))
                started.set()
                db.flush()
        except IntegrityError:
            return 'missing_child'
        return 'inserted'
    with ThreadPoolExecutor(max_workers=2) as pool:
        deletion = pool.submit(remove)
        assert child_locked.wait(15)
        actor = pool.submit(insert)
        assert started.wait(15)
        deadline = monotonic()+8
        blocked=False
        while monotonic() < deadline:
            with DB() as db:
                blocked = bool(db.scalar(text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock' AND lower(query) LIKE '%insert into learning_units%'")))
            if blocked:
                break
            sleep(.05)
        try:
            assert blocked, 'INSERT must wait on the real PostgreSQL child row lock'
            assert not actor.done()
        finally:
            release.set()
        response = deletion.result(15)
        assert response.status_code == 200, response.text
        assert actor.result(15) == 'missing_child'
