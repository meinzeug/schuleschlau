"""Real PostgreSQL row-lock regression with synthetic family data only."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep

import pytest
from conftest import HEADERS
from fastapi.testclient import TestClient
from schulpilot import admin_users
from schulpilot.db import DB, Child, ErasureRequest, Family, Usage, User, engine
from schulpilot.main import app
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from test_family_calls import child_api, turn
from test_admin_users import confirm, preview
from test_admin_users import operator as operator_fixture


@pytest.fixture
def operator():
    yield from operator_fixture.__wrapped__()


@pytest.mark.parametrize("entry", ["admin"])
def test_family_deletion_aborts_when_child_action_would_need_family_fk(api, household, operator, entry):
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row locks required")
    parent, child = household
    family_id = parent["families"][0]["id"]
    value = preview(operator, parent["id"], "account_and_sole_families") if entry == "admin" else None
    headers = dict(operator.headers) if entry == "admin" else {**HEADERS, "Authorization": api.headers["Authorization"]}

    def delete():
        with TestClient(app, headers=headers) as client:
            if entry == "admin":
                return confirm(client, parent["id"], value)
            return client.request("DELETE", "/api/account", json={"password": "secure-parent-pass-123"})

    with ThreadPoolExecutor(max_workers=1) as pool:
        with DB.begin() as child_transaction:
            child_transaction.execute(update(Child).where(Child.id == child["id"]).values(grade=Child.grade))
            # The deletion cannot wait on the held Child while it holds Family:
            # a real tutoring reservation may next need Family's FK KEY SHARE.
            response = pool.submit(delete).result(timeout=15)
            assert response.status_code == 409, response.text
            child_transaction.add(Usage(
                family_id=family_id, child_id=child["id"], job_id="f" * 32,
                provider="sample", model="sample", config_revision=1, function="tutor",
                reserved_micros=1, bucket_ids=[],
            ))
            child_transaction.flush()
    with DB() as db:
        assert db.get(Family, family_id) is not None
        assert db.get(Child, child["id"]) is not None
        assert db.get(User, parent["id"]) is not None
        assert db.scalar(select(Usage.id).where(Usage.job_id == "f" * 32)) is not None


@pytest.mark.parametrize("entry", ["admin"])
def test_parent_delete_aborts_on_parent_session_held_before_child(api, household, operator, entry):
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row locks required")
    from schulpilot.db import Session

    parent, child = household
    value = preview(operator, parent["id"], "account_and_sole_families") if entry == "admin" else None
    headers = dict(operator.headers) if entry == "admin" else {**HEADERS, "Authorization": api.headers["Authorization"]}

    def delete():
        with TestClient(app, headers=headers) as client:
            if entry == "admin":
                return confirm(client, parent["id"], value)
            return client.request("DELETE", "/api/account", json={"password": "secure-parent-pass-123"})

    with ThreadPoolExecutor(max_workers=1) as pool:
        with DB.begin() as call:
            session = call.scalar(select(Session).where(Session.user_id == parent["id"]).with_for_update())
            assert session is not None
            # A family-call acceptance owns Session before reaching Child.
            response = pool.submit(delete).result(timeout=15)
            assert response.status_code == 409, response.text
            call.execute(update(Child).where(Child.id == child["id"]).values(grade=Child.grade))
    with DB() as db:
        assert db.get(Child, child["id"]) is not None
        assert db.get(User, parent["id"]) is not None




@pytest.mark.parametrize('which', ['parent', 'child'])
def test_late_session_insert_blocked_after_account_delete_user_locks(operator, household, monkeypatch, which):
    if engine.dialect.name != 'postgresql': pytest.skip('requires PG')
    from schulpilot.db import Session, now
    from schulpilot.security import digest
    parent, child = household
    cid = child['id']; target = parent['id']
    with DB() as db: child_user_id = db.get(Child, cid).user_id
    uid = target if which == 'parent' else child_user_id
    value = preview(operator, target, 'account_and_sole_families')
    locked = Event(); release = Event(); started = Event()
    original = admin_users.lock_target
    def pause(db, user_id, *, family_delete=False):
        result = original(db, user_id, family_delete=family_delete)
        if family_delete:
            locked.set(); assert release.wait(15)
        return result
    monkeypatch.setattr(admin_users, 'lock_target', pause)
    headers = dict(operator.headers)
    def remove():
        with TestClient(app, headers=headers) as client: return confirm(client, target, value)
    def insert():
        try:
            with DB.begin() as db:
                db.add(Session(user_id=uid, token_hash=digest('synthetic-late-session-' + which), device='Synthetic', expires=int(now())+3600))
                started.set(); db.flush()
        except IntegrityError: return 'missing_user'
        return 'inserted'
    with ThreadPoolExecutor(max_workers=2) as pool:
        deletion = pool.submit(remove)
        assert locked.wait(15)
        actor = pool.submit(insert); assert started.wait(15)
        deadline = monotonic() + 8; blocked = False
        while monotonic() < deadline:
            with DB() as db:
                blocked = bool(db.scalar(text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock' AND lower(query) LIKE '%insert into sessions%'")))
            if blocked: break
            sleep(.05)
        try: assert blocked and not actor.done()
        finally: release.set()
        response = deletion.result(15)
        assert response.status_code == 200, response.text
        assert actor.result(15) == 'missing_user'






@pytest.mark.parametrize('actor', ['admin'])
def test_real_family_call_accept_vs_account_delete_avoids_deadlock(api, household, operator, child_api, turn, monkeypatch, actor):
    if engine.dialect.name != 'postgresql': pytest.skip('requires PG')
    from schulpilot import family_calls
    from test_family_calls import start
    parent, child = household
    target = parent['id']; value = preview(operator, target, 'account_and_sole_families')
    call = start(child_api)
    accepting = Event(); release = Event(); original = family_calls.lock
    def pause(db, call, *, unit=False):
        accepting.set(); assert release.wait(15)
        return original(db, call, unit=unit)
    monkeypatch.setattr(family_calls, 'lock', pause)
    parent_headers = dict(api.headers); admin_headers = dict(operator.headers)
    def accept():
        with TestClient(app, headers=parent_headers) as client: return client.post(f"/api/family-calls/{call['id']}/accept")
    def remove():
        if actor == 'admin':
            with TestClient(app, headers=admin_headers) as client: return confirm(client, target, value)
        with TestClient(app, headers=parent_headers) as client:
            return client.request('DELETE', '/api/account', json={'password': 'secure-parent-pass-123'})
    with ThreadPoolExecutor(max_workers=2) as pool:
        acceptance = pool.submit(accept); assert accepting.wait(15)
        deletion = pool.submit(remove)
        try:
            response = deletion.result(8)
            assert response.status_code == 409, response.text
        finally: release.set()
        assert acceptance.result(15).status_code == 200
    with DB() as db:
        assert db.get(Child, child['id']) is not None
        assert db.scalar(select(ErasureRequest.id).where(ErasureRequest.target == child['id'])) is None
