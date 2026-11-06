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


@pytest.mark.parametrize("entry", ["parent"])
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


@pytest.mark.parametrize("entry", ["parent"])
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


@pytest.mark.parametrize("own_permission,other_permission,expected", [
    ("owner", "manage", 409),
    ("owner", "view", 409),
    ("owner", "owner", 200),
    ("view", "owner", 200),
])
def test_parent_account_deletion_preserves_shared_family(api, household, own_permission, other_permission, expected):
    from schulpilot.db import ErasureRequest, Membership

    parent, child = household
    family_id = parent["families"][0]["id"]
    with DB.begin() as db:
        own = db.scalar(select(Membership).where(Membership.family_id == family_id, Membership.user_id == parent["id"]))
        own.permission = own_permission
        own_id = own.id
        other = User(username="shared-family-test@example.invalid", email="shared-family-test@example.invalid",
                     display_name="Synthetic parent", password_hash="unused", role="parent", verified=True)
        db.add(other)
        db.flush()
        other_id = other.id
        db.add(Membership(family_id=family_id, user_id=other_id, permission=other_permission))
    response = api.request("DELETE", "/api/account", json={"password": "secure-parent-pass-123"})
    assert response.status_code == expected, response.text
    with DB() as db:
        assert db.get(Family, family_id) is not None
        assert db.get(Child, child["id"]) is not None
        assert db.get(User, other_id) is not None
        assert db.scalar(select(Membership.id).where(Membership.family_id == family_id, Membership.user_id == other_id))
        assert (db.get(User, parent["id"]) is None) is (expected == 200)
        event = db.scalar(select(ErasureRequest).where(ErasureRequest.target == own_id))
        assert (event is not None) is (expected == 200)
        if event:
            assert event.published is True


@pytest.mark.parametrize('actor', ['parent'])
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
