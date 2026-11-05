"""Artificial preferences requests racing real session revocation paths."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep

import pytest
from conftest import HEADERS
from fastapi.testclient import TestClient
from schulpilot import schemas, security
from schulpilot.db import DB, Assignment, Child, Session, User, engine
from schulpilot.main import app
from sqlalchemy import event, select, text
from test_notebook_actions import kid


def data_for(child_id):
    with DB() as db:
        original = dict(db.get(Child, child_id).preferences)
        user = db.scalar(select(User).where(User.username == "parent@example.org"))
        sid = db.scalar(select(Session.id).where(Session.user_id == user.id, Session.revoked.is_(False)))
    data = schemas.Preferences(**original).model_dump(mode="json")
    data.update(daily_minutes=37, repeat_topics=["Mathematik: Künstliches Ziel"])
    return original, sid, data


@pytest.mark.parametrize("action", ["device", "logout"])
def test_revocation_first_aborts_preferences_without_writes(api, household, action):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires real PostgreSQL NOWAIT row locking")
    _, child = household
    before, sid, data = data_for(child["id"])
    headers = {**HEADERS, "Authorization": api.headers["Authorization"], "If-Match": "1"}
    held, proceed = Event(), Event()
    def after_statement(conn, cursor, statement, parameters, context, executemany):
        if not held.is_set() and statement.lower().startswith("update sessions set revoked"):
            held.set()
            assert proceed.wait(10)
    event.listen(engine, "after_cursor_execute", after_statement)
    def revoke():
        with TestClient(app, headers=headers) as client:
            return client.delete(f"/api/auth/sessions/{sid}") if action == "device" else client.post("/api/auth/logout")
    def save():
        with TestClient(app, headers=headers) as client:
            return client.put(f"/api/children/{child['id']}/preferences", json=data)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            revoking = pool.submit(revoke)
            assert held.wait(8)
            result = pool.submit(save).result(8)
            assert result.status_code == 409, result.text
            proceed.set()
            assert revoking.result(12).status_code == 200
        assert save().status_code == 401
    finally:
        proceed.set()
        event.remove(engine, "after_cursor_execute", after_statement)
    with DB() as db:
        assert db.get(Child, child["id"]).preferences == before
        assert not db.scalar(select(Assignment.id).where(Assignment.child_id == child["id"]))
        assert db.get(Session, sid).revoked


@pytest.mark.parametrize("action", ["device", "logout"])
def test_preferences_first_hold_session_until_commit_before_revocation(api, household, monkeypatch, action):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires real PostgreSQL row locks")
    _, child = household
    _, sid, data = data_for(child["id"])
    held, proceed, started = Event(), Event(), Event()
    original = security.lock_session_after_child
    def hold(db, user_id, session_id):
        value = original(db, user_id, session_id)
        held.set()
        assert proceed.wait(10)
        return value
    monkeypatch.setattr(security, "lock_session_after_child", hold)
    headers = {**HEADERS, "Authorization": api.headers["Authorization"], "If-Match": "1"}
    def save():
        with TestClient(app, headers=headers) as client:
            return client.put(f"/api/children/{child['id']}/preferences", json=data)
    def revoke():
        with TestClient(app, headers=headers) as client:
            started.set()
            return client.delete(f"/api/auth/sessions/{sid}") if action == "device" else client.post("/api/auth/logout")
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            saving = pool.submit(save)
            assert held.wait(8)
            revoking = pool.submit(revoke)
            assert started.wait(8)
            deadline, blocked = monotonic() + 8, False
            while monotonic() < deadline and not blocked:
                with DB() as db:
                    blocked = bool(db.scalar(text(
                        "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
                        "AND wait_event_type = 'Lock' AND lower(query) LIKE '%update sessions%'"
                    )))
                if not blocked:
                    sleep(0.05)
            assert blocked and not revoking.done()
            proceed.set()
            assert saving.result(12).status_code == 200
            assert revoking.result(12).status_code == 200
    finally:
        proceed.set()
    with DB() as db:
        assert db.get(Child, child["id"]).preferences["daily_minutes"] == 37
        assert db.scalar(select(Assignment.id).where(Assignment.child_id == child["id"]))
        assert db.get(Session, sid).revoked


def test_family_call_session_first_aborts_preferences_without_deadlock(api, household, monkeypatch):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires real PostgreSQL row locks")
    from schulpilot import family_calls, notifications
    from schulpilot.config import settings
    from test_family_calls import start

    object.__setattr__(settings, "family_calls_enabled", True)
    object.__setattr__(settings, "turn_urls", '["turn:school.invalid:3478?transport=udp"]')
    object.__setattr__(settings, "turn_secret", "synthetic-operator-secret-" + "x" * 32)
    monkeypatch.setattr(notifications, "dispatch_call", lambda _: None)
    _, child = household
    before, _, data = data_for(child["id"])
    preference_has_child, accept_has_session = Event(), Event()
    original_guard, original_call_lock = security.lock_session_after_child, family_calls.lock
    def before_session(db, user_id, session_id):
        preference_has_child.set()
        assert accept_has_session.wait(8)
        return original_guard(db, user_id, session_id)
    def before_call_child(db, call, *, unit=False):
        accept_has_session.set()
        assert preference_has_child.wait(8)
        return original_call_lock(db, call, unit=unit)
    monkeypatch.setattr(security, "lock_session_after_child", before_session)
    monkeypatch.setattr(family_calls, "lock", before_call_child)
    headers = {**HEADERS, "Authorization": api.headers["Authorization"], "If-Match": "1"}
    with kid() as child_client:
        call = start(child_client)
        def save():
            with TestClient(app, headers=headers) as client:
                return client.put(f"/api/children/{child['id']}/preferences", json=data)
        def accept():
            with TestClient(app, headers=headers) as client:
                return client.post(f"/api/family-calls/{call['id']}/accept")
        with ThreadPoolExecutor(max_workers=2) as pool:
            saving = pool.submit(save)
            assert preference_has_child.wait(8)
            accepting = pool.submit(accept)
            assert saving.result(12).status_code == 409
            response = accepting.result(12)
            assert response.status_code == 200, response.text
    with DB() as db:
        assert db.get(Child, child["id"]).preferences == before
        assert not db.scalar(select(Assignment.id).where(Assignment.child_id == child["id"]))
