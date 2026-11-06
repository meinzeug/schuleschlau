"""Synthetic real-transaction checks for session-scoped deletion."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep

import pytest
from conftest import HEADERS
from fastapi.testclient import TestClient
from schulpilot import security
from schulpilot.config import settings
from schulpilot.db import DB, Attempt, Child, LearningUnit, Material, Session, User, engine
from schulpilot.main import app
from sqlalchemy import select, text, update
from test_notebook_actions import kid, photo, preview, saved_round
from test_unconfirmed_deletion import review_day
from test_unit_deletion import unit_preview


def fixture_for(api, child, monkeypatch, kind):
    if kind == "day":
        day, ids, paths = review_day(api, child, monkeypatch, count=1)
        return f"/api/school-days/{day['id']}/pages/{ids[0]}", "DELETE", None, ids[0], paths[0], None, None
    material, path = photo(api, child, confirmed=kind == "unit")
    if kind == "unit":
        unit, attempt = saved_round(child, material)
        return f"/api/units/{unit}/delete", "POST", unit, material, path, unit, attempt
    return (f"/api/materials/{material}" if kind == "direct" else f"/api/children/{child['id']}/materials/bulk-delete",
            "DELETE" if kind == "direct" else "POST", None, material, path, None, None)


def token_for(client, child, kind, unit, material):
    if kind == "bulk":
        return {"selection_token": preview(client, child, ids=[material])["selection_token"], "delete_linked_units": True}
    if kind == "unit":
        return {"selection_token": unit_preview(client, unit)["selection_token"]}
    return None


def own_session_id():
    with DB() as db:
        user = db.scalar(select(User).where(User.username == "test-child"))
        return db.scalar(select(Session.id).where(Session.user_id == user.id, Session.revoked.is_(False)))


def send(client, method, path, data):
    return client.request(method, path, json=data)


@pytest.mark.parametrize("kind", ["direct", "day", "bulk", "unit"])
def test_session_lock_busy_fails_closed_then_revoked_session_is_unauthorized(api, household, monkeypatch, kind):
    if engine.dialect.name != "postgresql":
        pytest.skip("NOWAIT row contention requires PostgreSQL")
    _, child = household
    path, method, pre_unit, material, image, unit, attempt = fixture_for(api, child, monkeypatch, kind)
    with kid() as client:
        data = token_for(client, child, kind, pre_unit, material)
        journal = settings.data_dir / "erasure-ledger.jsonl"
        before_journal = journal.read_bytes() if journal.exists() else None
        sid = own_session_id()
        headers = {**HEADERS, "Authorization": client.headers["Authorization"]}
        def remove():
            with TestClient(app, headers=headers) as concurrent:
                return send(concurrent, method, path, data)
        # The uncommitted revocation is invisible to authentication but holds
        # the actual row. No delete may wait on it while retaining Unit/Child.
        with ThreadPoolExecutor(max_workers=1) as pool:
            with DB.begin() as revoker:
                revoker.execute(update(Session).where(Session.id == sid).values(revoked=True))
                response = pool.submit(remove).result(timeout=8)
                assert response.status_code == 409, response.text
            assert send(client, method, path, data).status_code == 401
    with DB() as db:
        assert db.get(Material, material) is not None
        if unit:
            assert db.get(LearningUnit, unit) and db.get(Attempt, attempt)
    assert image.exists()
    assert (journal.read_bytes() if journal.exists() else None) == before_journal


@pytest.mark.parametrize("action", ["child_device", "own_device", "logout"])
def test_delete_session_lock_serializes_real_revocation_and_logout(api, household, monkeypatch, action):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires real PostgreSQL row locks")
    _, child = household
    path, method, _, material, image, _, _ = fixture_for(api, child, monkeypatch, "direct")
    locked, proceed, revoker_started = Event(), Event(), Event()
    original = security.lock_session_after_child
    def pause_after_lock(db, user_id, session_id):
        value = original(db, user_id, session_id)
        locked.set()
        assert proceed.wait(10)
        return value
    monkeypatch.setattr(security, "lock_session_after_child", pause_after_lock)
    with kid() as client:
        sid = own_session_id()
        child_headers = {**HEADERS, "Authorization": client.headers["Authorization"]}
        parent_headers = {**HEADERS, "Authorization": api.headers["Authorization"]}
        def remove():
            with TestClient(app, headers=child_headers) as concurrent:
                return send(concurrent, method, path, None)
        def revoke():
            headers = parent_headers if action == "child_device" else child_headers
            with TestClient(app, headers=headers) as concurrent:
                revoker_started.set()
                if action == "child_device":
                    return concurrent.delete(f"/api/children/{child['id']}/sessions/{sid}")
                if action == "own_device":
                    return concurrent.delete(f"/api/auth/sessions/{sid}")
                return concurrent.post("/api/auth/logout")
        with ThreadPoolExecutor(max_workers=2) as pool:
            deleting = pool.submit(remove)
            assert locked.wait(8)
            revoking = pool.submit(revoke)
            assert revoker_started.wait(8)
            # Observe a real blocked database statement, not just a started
            # Python thread. Logout waits on Child; device revocation on Session.
            expected_table = "children" if action == "logout" else "sessions"
            deadline = monotonic() + 8
            blocked = False
            while monotonic() < deadline and not blocked:
                with DB() as db:
                    blocked = bool(db.scalar(text(
                        "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
                        "AND wait_event_type = 'Lock' AND lower(query) LIKE :statement"
                    ), {"statement": f"%update {expected_table}%"}))
                if not blocked:
                    sleep(0.05)
            assert blocked, "Revocation never reached a blocked database write"
            assert not revoking.done(), "Revocation must wait until deletion commits"
            proceed.set()
            assert deleting.result(12).status_code == 200
            assert revoking.result(12).status_code == 200
    with DB() as db:
        assert db.get(Material, material) is None
        assert db.get(Session, sid).revoked
    assert not image.exists()


def test_sqlite_child_writer_serializes_session_revocation(api, household):
    if engine.dialect.name != "sqlite":
        pytest.skip("SQLite writer serialization only")
    import sqlite3

    from sqlalchemy.engine import make_url

    _, child = household
    with kid():
        sid = own_session_id()
        # A separate connection with zero busy timeout proves the actual writer
        # conflict without waiting for a scheduling-dependent thread signal.
        other = sqlite3.connect(make_url(settings.database_url).database, timeout=0)
        try:
            with DB.begin() as writer:
                writer.execute(update(Child).where(Child.id == child["id"]).values(grade=Child.grade))
                with pytest.raises(sqlite3.OperationalError, match="locked"):
                    other.execute("UPDATE sessions SET revoked=1 WHERE id=?", (sid,))
                other.rollback()
                assert writer.get(Session, sid).revoked is False
            other.execute("UPDATE sessions SET revoked=1 WHERE id=?", (sid,))
            other.commit()
        finally:
            other.close()
        with DB() as db:
            assert db.get(Session, sid).revoked


def test_family_call_session_first_does_not_deadlock_with_child_first_deletion(api, household, monkeypatch):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires real PostgreSQL NOWAIT row locking")
    from schulpilot import family_calls, notifications
    from schulpilot.config import settings
    from test_family_calls import start

    object.__setattr__(settings, "family_calls_enabled", True)
    object.__setattr__(settings, "turn_urls", '["turn:school.invalid:3478?transport=udp"]')
    object.__setattr__(settings, "turn_secret", "synthetic-operator-secret-" + "x" * 32)
    monkeypatch.setattr(notifications, "dispatch_call", lambda _: None)
    _, child = household
    mid, image = photo(api, child, confirmed=False)
    deletion_has_child, accept_has_session = Event(), Event()
    original_guard, original_call_lock = security.lock_session_after_child, family_calls.lock
    def before_session(db, user_id, session_id):
        deletion_has_child.set()
        assert accept_has_session.wait(8)
        return original_guard(db, user_id, session_id)
    def before_call_child(db, call, *, unit=False):
        accept_has_session.set()  # accept() has already locked the same parent Session.
        assert deletion_has_child.wait(8)
        return original_call_lock(db, call, unit=unit)
    monkeypatch.setattr(security, "lock_session_after_child", before_session)
    monkeypatch.setattr(family_calls, "lock", before_call_child)
    headers = {**HEADERS, "Authorization": api.headers["Authorization"]}
    with kid() as child_client:
        call = start(child_client)
        def delete_page():
            with TestClient(app, headers=headers) as client:
                return client.delete(f"/api/materials/{mid}")
        def accept():
            with TestClient(app, headers=headers) as client:
                return client.post(f"/api/family-calls/{call['id']}/accept")
        with ThreadPoolExecutor(max_workers=2) as pool:
            deleting = pool.submit(delete_page)
            assert deletion_has_child.wait(8)
            accepting = pool.submit(accept)
            assert deleting.result(12).status_code == 409
            response = accepting.result(12)
            assert response.status_code == 200, response.text
    with DB() as db:
        assert db.get(Material, mid) is not None
    assert image.exists()


@pytest.mark.parametrize("first", ["deletion", "family_revocation"])
def test_real_family_revocation_and_parent_deletion_are_serialized(api, household, mailbox, monkeypatch, first):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires real PostgreSQL row locks")
    from contextlib import contextmanager
    from threading import Lock

    from conftest import register
    from schulpilot import erasure
    from schulpilot.db import Membership
    from sqlalchemy import event

    owner, child = household
    mid, image = photo(api, child, confirmed=False)
    family = owner["families"][0]["id"]
    with TestClient(app, headers=HEADERS) as member_client:
        member = register(member_client, mailbox, "synthetic-second-parent@example.org")
        with DB.begin() as db:
            membership = Membership(user_id=member["id"], family_id=family, permission="manage")
            db.add(membership)
            db.flush()
            membership_id = membership.id
        member_headers = {**HEADERS, "Authorization": member_client.headers["Authorization"]}
        owner_headers = {**HEADERS, "Authorization": api.headers["Authorization"]}
        held, proceed = Event(), Event()
        second_journal_attempt = Event()
        count_lock, count = Lock(), [0]
        original_journal_lock = erasure.journal_write_lock

        @contextmanager
        def observed_journal_lock():
            with count_lock:
                count[0] += 1
                if count[0] == 2:
                    second_journal_attempt.set()
            with original_journal_lock():
                yield

        monkeypatch.setattr(erasure, "journal_write_lock", observed_journal_lock)
        def delete_page():
            with TestClient(app, headers=member_headers) as client:
                return client.delete(f"/api/materials/{mid}")
        def revoke():
            with TestClient(app, headers=owner_headers) as client:
                return client.delete(f"/api/families/{family}/members/{membership_id}")
        if first == "deletion":
            original = security.lock_session_after_child
            def hold_session(db, user_id, session_id):
                value = original(db, user_id, session_id)
                held.set()
                assert proceed.wait(10)
                return value
            monkeypatch.setattr(security, "lock_session_after_child", hold_session)
        else:
            def after_statement(conn, cursor, statement, parameters, context, executemany):
                if not held.is_set() and statement.lower().startswith("update children set"):
                    held.set()
                    assert proceed.wait(10)
            event.listen(engine, "after_cursor_execute", after_statement)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                first_future = pool.submit(delete_page if first == "deletion" else revoke)
                assert held.wait(8)
                second_future = pool.submit(revoke if first == "deletion" else delete_page)
                # Both mutations now serialize earlier on the journal lock;
                # assert the second has reached that lock rather than waiting
                # for an impossible child-row lock acquisition.
                assert second_journal_attempt.wait(8)
                assert not second_future.done()
                proceed.set()
                first_response, second_response = first_future.result(12), second_future.result(12)
                assert first_response.status_code == 200, first_response.text
                if first == "deletion":
                    assert second_response.status_code == 200, second_response.text
                else:
                    # The revoked member may be rejected by the fresh family
                    # check (404) before the session check (401).
                    assert second_response.status_code in (401, 404), second_response.text
        finally:
            proceed.set()
            if first == "family_revocation":
                event.remove(engine, "after_cursor_execute", after_statement)
        with DB() as db:
            assert (db.get(Material, mid) is None) == (first == "deletion")
            assert db.get(Membership, membership_id) is None
        assert image.exists() is (first == "family_revocation")


@pytest.mark.parametrize("action", ["child_device", "own_device"])
def test_actual_device_revocation_holding_session_forces_delete_to_abort(api, household, monkeypatch, action):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires real PostgreSQL NOWAIT row locking")
    from sqlalchemy import event

    _, child = household
    path, method, _, material, image, _, _ = fixture_for(api, child, monkeypatch, "direct")
    held, proceed = Event(), Event()
    with kid() as client:
        sid = own_session_id()
        child_headers = {**HEADERS, "Authorization": client.headers["Authorization"]}
        parent_headers = {**HEADERS, "Authorization": api.headers["Authorization"]}
        def after_statement(conn, cursor, statement, parameters, context, executemany):
            if not held.is_set() and statement.lower().startswith("update sessions set revoked"):
                held.set()  # This real API transaction owns the Session row.
                assert proceed.wait(10)
        event.listen(engine, "after_cursor_execute", after_statement)
        def revoke():
            with TestClient(app, headers=parent_headers if action == "child_device" else child_headers) as other:
                if action == "child_device":
                    return other.delete(f"/api/children/{child['id']}/sessions/{sid}")
                return other.delete(f"/api/auth/sessions/{sid}")
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                revoking = pool.submit(revoke)
                assert held.wait(8)
                with TestClient(app, headers=child_headers) as deletion:
                    response = pool.submit(send, deletion, method, path, None).result(8)
                    assert response.status_code == 409, response.text
                proceed.set()
                assert revoking.result(12).status_code == 200
            assert send(client, method, path, None).status_code == 401
        finally:
            proceed.set()
            event.remove(engine, "after_cursor_execute", after_statement)
    with DB() as db:
        assert db.get(Material, material) is not None and db.get(Session, sid).revoked
    assert image.exists()


def test_real_logout_winning_child_lock_prevents_later_delete(api, household, monkeypatch):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires real PostgreSQL row locks")
    from schulpilot import materials
    from sqlalchemy import event

    _, child = household
    path, method, _, material, image, _, _ = fixture_for(api, child, monkeypatch, "direct")
    held, proceed, delete_ready = Event(), Event(), Event()
    original = materials.lock_material_units
    def before_child(db, child_id, material_id):
        result = original(db, child_id, material_id)
        delete_ready.set()
        return result
    monkeypatch.setattr(materials, "lock_material_units", before_child)
    def after_statement(conn, cursor, statement, parameters, context, executemany):
        if not held.is_set() and statement.lower().startswith("update children set"):
            held.set()  # Logout holds Child before revoking the session.
            assert proceed.wait(10)
    event.listen(engine, "after_cursor_execute", after_statement)
    try:
        with kid() as client:
            headers = {**HEADERS, "Authorization": client.headers["Authorization"]}
            def logout():
                with TestClient(app, headers=headers) as other:
                    return other.post("/api/auth/logout")
            def remove():
                with TestClient(app, headers=headers) as other:
                    return send(other, method, path, None)
            with ThreadPoolExecutor(max_workers=2) as pool:
                ending = pool.submit(logout)
                assert held.wait(8)
                deleting = pool.submit(remove)
                assert delete_ready.wait(8)
                proceed.set()
                assert ending.result(12).status_code == 200
                assert deleting.result(12).status_code == 401
    finally:
        proceed.set()
        event.remove(engine, "after_cursor_execute", after_statement)
    with DB() as db:
        assert db.get(Material, material) is not None
    assert image.exists()


def test_session_guard_fails_closed_on_unsupported_dialect():
    from types import SimpleNamespace

    db = SimpleNamespace(bind=SimpleNamespace(dialect=SimpleNamespace(name="unsupported")))
    with pytest.raises(RuntimeError, match="only on PostgreSQL and SQLite"):
        security.lock_session_after_child(db, "synthetic-user", "synthetic-session")
