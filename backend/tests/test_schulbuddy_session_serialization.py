"""Actual transaction race: synthetic child, mock provider, no production data."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from schulpilot.db import DB, Child, Job, LearningUnit, SchulbuddyTurn, Session, Usage, User, engine, now
from sqlalchemy import select, update
from test_schulbuddy import ask, counts, finish
from test_schulbuddy import book as book_fixture
from test_schulbuddy import transport as transport_fixture


@pytest.fixture
def book(api, household, monkeypatch):
    yield from book_fixture.__wrapped__(api, household, monkeypatch)


@pytest.fixture
def transport(monkeypatch):
    return transport_fixture.__wrapped__(monkeypatch)


def test_held_revocation_cannot_enqueue_a_tutor_request(api, book, transport):
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row locking required")
    with DB() as db:
        user_id = db.get(Child, book["child"]["id"]).user_id
        sid = db.scalar(select(Session.id).where(Session.user_id == user_id, Session.revoked.is_(False)))
    before = counts()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with DB.begin() as revoker:
            revoker.execute(update(Session).where(Session.id == sid).values(revoked=True))
            response = pool.submit(ask, book).result(timeout=10)
            assert response.status_code == 409, response.text
    assert ask(book).status_code == 401
    assert counts() == before and transport["calls"] == []


@pytest.mark.parametrize("cost", [None, 42])
def test_held_revocation_cannot_publish_a_late_tutor_reply(api, book, transport, monkeypatch, cost):
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row locking required")
    from schulpilot import schulbuddy

    original_provider = schulbuddy.request_provider

    def priced(*args):
        result = original_provider(*args)
        result.cost_micros = cost
        result.cost_source = "reported" if cost is not None else "unknown"
        return result

    monkeypatch.setattr(schulbuddy, "request_provider", priced)
    with DB.begin() as db:
        unit = db.get(LearningUnit, book["unit_id"])
        unit.status = "active"
        unit.questions = [{"id": "q1", "type": "short", "prompt": "Was ist die Sonne?",
                           "answer": "Stern", "options": [], "hints": [], "explanation": "Künstlich"}]
    turn_id = ask(book).json()["id"]
    with DB() as db:
        turn = db.get(SchulbuddyTurn, turn_id)
        sid, job_id = turn.session_id, turn.job_id
    with ThreadPoolExecutor(max_workers=1) as pool:
        with DB.begin() as revoker:
            revoker.execute(update(Session).where(Session.id == sid).values(revoked=True))
            pool.submit(finish).result(timeout=10)
    with DB() as db:
        turn = db.get(SchulbuddyTurn, turn_id)
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        assert turn.status == "failed" and turn.reply is None
        assert db.get(Job, job_id).status == "failed"
        assert usage.status == ("failed_billed" if cost is not None else "failed_unknown")
        assert usage.cost_micros == cost and usage.reserved_micros > 0
    assert len(transport["calls"]) == 1 and counts() == (1, 1, 0, 0)


@pytest.mark.parametrize("stage", ["enqueue", "publish"])
def test_tutor_commit_wins_before_real_session_revocation(api, book, transport, monkeypatch, stage):
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row locking required")
    from threading import Event
    from time import monotonic, sleep

    from conftest import HEADERS
    from fastapi.testclient import TestClient
    from schulpilot import security
    from schulpilot.main import app
    from sqlalchemy import text

    if stage == "publish":
        turn_id = ask(book).json()["id"]
    else:
        turn_id = None
    with DB() as db:
        user_id = db.get(Child, book["child"]["id"]).user_id
        sid = db.scalar(select(Session.id).where(Session.user_id == user_id, Session.revoked.is_(False)))
    held, proceed = Event(), Event()
    original = security.lock_session_after_child

    def pause_guard(db, uid, session_id):
        session = original(db, uid, session_id)
        held.set()
        assert proceed.wait(10)
        return session

    monkeypatch.setattr(security, "lock_session_after_child", pause_guard)
    headers = {**HEADERS, "Authorization": book["client"].headers["Authorization"]}

    def start_or_finish():
        if stage == "publish":
            return finish()
        with TestClient(app, headers=headers) as client:
            return ask(book, client=client)

    def revoke():
        with TestClient(app, headers=headers) as client:
            return client.delete(f"/api/auth/sessions/{sid}")

    with ThreadPoolExecutor(max_workers=2) as pool:
        active = pool.submit(start_or_finish)
        assert held.wait(8)
        revoking = pool.submit(revoke)
        deadline = monotonic() + 8
        blocked = False
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
        result = active.result(12)
        if stage == "enqueue":
            assert result.status_code == 202, result.text
            turn_id = result.json()["id"]
        assert revoking.result(12).status_code == 200
    with DB() as db:
        turn = db.get(SchulbuddyTurn, turn_id)
        assert db.get(Session, sid).revoked
        assert turn.status == ("ready" if stage == "publish" else "queued")
        assert db.scalar(select(Usage).where(Usage.job_id == turn.job_id)) is not None
    if stage == "enqueue":
        # A revoked session cannot dispatch an already reserved job.
        finish()
        with DB() as db:
            turn = db.get(SchulbuddyTurn, turn_id)
            assert turn.status == "failed" and turn.reply is None
            usage = db.scalar(select(Usage).where(Usage.job_id == turn.job_id))
            assert usage.status == "failed_not_sent" and usage.cost_micros == 0
        assert transport["calls"] == []
    assert counts() == (1, 1, 0, 0)


def test_family_call_session_first_conflicts_without_deadlock(api, book, transport, monkeypatch):
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row locking required")
    from threading import Event

    from conftest import HEADERS
    from fastapi.testclient import TestClient
    from schulpilot import family_calls, notifications, security
    from schulpilot.config import settings
    from schulpilot.main import app
    from test_family_calls import start

    object.__setattr__(settings, "family_calls_enabled", True)
    object.__setattr__(settings, "turn_urls", '["turn:school.invalid:3478?transport=udp"]')
    object.__setattr__(settings, "turn_secret", "synthetic-operator-secret-" + "x" * 32)
    monkeypatch.setattr(notifications, "dispatch_call", lambda _: None)
    has_child, has_session = Event(), Event()
    original_guard, original_call_lock = security.lock_session_after_child, family_calls.lock

    def before_session(db, uid, sid):
        has_child.set()
        assert has_session.wait(8)
        return original_guard(db, uid, sid)

    def before_call_child(db, call, *, unit=False):
        has_session.set()
        assert has_child.wait(8)
        return original_call_lock(db, call, unit=unit)

    monkeypatch.setattr(security, "lock_session_after_child", before_session)
    monkeypatch.setattr(family_calls, "lock", before_call_child)
    headers = {**HEADERS, "Authorization": api.headers["Authorization"]}
    call = start(book["client"])

    def send():
        with TestClient(app, headers=headers) as client:
            return ask(book, client=client)

    def accept():
        with TestClient(app, headers=headers) as client:
            return client.post(f"/api/family-calls/{call['id']}/accept")

    with ThreadPoolExecutor(max_workers=2) as pool:
        sending = pool.submit(send)
        assert has_child.wait(8)
        accepting = pool.submit(accept)
        assert sending.result(12).status_code == 409
        response = accepting.result(12)
        assert response.status_code == 200, response.text
    assert counts() == (0, 0, 0, 0) and transport["calls"] == []


def test_user_lock_busy_fails_closed_before_enqueuing_parent_request(api, book, transport):
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row locking required")
    before = counts()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with DB.begin() as blocker:
            blocker.execute(select(User).where(User.id == book["parent"]["id"]).with_for_update())
            response = pool.submit(ask, book, client=api).result(timeout=10)
            assert response.status_code == 409, response.text
    assert counts() == before and transport["calls"] == []


def test_admin_disabling_parent_does_not_deadlock_with_parent_tutor(api, book, transport, monkeypatch):
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row locking required")
    from threading import Event
    from time import monotonic, sleep
    from uuid import uuid4

    from conftest import HEADERS
    from fastapi.testclient import TestClient
    from schulpilot import security
    from schulpilot.main import app
    from schulpilot.security import digest
    from sqlalchemy import text

    with DB.begin() as db:
        admin = User(username="synthetic-admin-tutor", display_name="Admin", role="admin",
                     verified=True, password_hash="no-real-password")
        db.add(admin)
        db.flush()
        admin_id = admin.id
        db.add(Session(user_id=admin.id, token_hash=digest("synthetic-admin-tutor-token"),
                       device="Synthetic admin", expires=int(now()) + 3600))
    admin_headers = {**HEADERS, "Authorization": "Bearer synthetic-admin-tutor-token", "X-Schulpilot-Account": admin_id}
    with TestClient(app, headers=admin_headers) as admin_client:
        revision_response = admin_client.get(f"/api/admin/users/{book['parent']['id']}")
        assert revision_response.status_code == 200
        revision = revision_response.json()["revision"]
    parent_headers = {**HEADERS, "Authorization": api.headers["Authorization"]}
    held, proceed = Event(), Event()
    original_guard = security.lock_session_after_child

    def pause_guard(db, uid, sid):
        session = original_guard(db, uid, sid)
        held.set()
        assert proceed.wait(10)
        return session

    monkeypatch.setattr(security, "lock_session_after_child", pause_guard)

    def send():
        with TestClient(app, headers=parent_headers) as client:
            return ask(book, client=client)

    def disable():
        with TestClient(app, headers=admin_headers) as client:
            return client.post(f"/api/admin/users/{book['parent']['id']}/status",
                               json={"revision": revision, "disabled": True},
                               headers={"Idempotency-Key": uuid4().hex})

    with ThreadPoolExecutor(max_workers=2) as pool:
        sending = pool.submit(send)
        assert held.wait(8)
        disabling = pool.submit(disable)
        deadline = monotonic() + 8
        blocked = False
        while monotonic() < deadline and not blocked:
            with DB() as db:
                blocked = bool(db.scalar(text(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
                    "AND wait_event_type = 'Lock' AND lower(query) LIKE '%from users%' "
                    "AND lower(query) LIKE '%for update%'"
                )))
            if not blocked:
                sleep(0.05)
        assert blocked and not disabling.done()
        proceed.set()
        response = sending.result(12)
        assert response.status_code == 202, response.text
        response = disabling.result(12)
        assert response.status_code == 200, response.text
    assert counts() == (1, 1, 0, 0)
    finish()
    with DB() as db:
        assert db.get(User, book["parent"]["id"]).disabled
        turn = db.scalar(select(SchulbuddyTurn))
        assert turn.status == "failed" and turn.reply is None
        usage = db.scalar(select(Usage).where(Usage.job_id == turn.job_id))
        assert usage.status == "failed_not_sent" and usage.cost_micros == 0
    assert transport["calls"] == []
