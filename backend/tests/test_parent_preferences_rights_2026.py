"""Concurrent synthetic permission changes against preferences; no external calls."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from conftest import HEADERS
from fastapi.testclient import TestClient
from schulpilot import schemas
from schulpilot.db import DB, Assignment, Child, Membership, Session, User, engine
from schulpilot.main import app
from schulpilot.security import password_hash
from sqlalchemy import event, select, update


@pytest.mark.parametrize("change", ["view", "removed", "session"])
def test_preferences_rechecks_authority_after_waiting_for_child(api, household, change):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL row locks")
    owner, child = household
    with DB.begin() as db:
        parent = User(username="synthetic-manager", display_name="Synthetic parent", role="parent",
                      verified=True, password_hash=password_hash("secure-parent-pass-123"))
        db.add(parent)
        db.flush()
        parent_id = parent.id
        membership = Membership(user_id=parent_id, family_id=owner["families"][0]["id"], permission="manage")
        db.add(membership)
        db.flush()
        membership_id = membership.id
        before = dict(db.get(Child, child["id"]).preferences)

    with TestClient(app, headers=HEADERS) as client:
        login = client.post("/api/auth/login", json={"username": "synthetic-manager", "password": "secure-parent-pass-123"})
        assert login.status_code == 200
        headers = {**HEADERS, "Authorization": "Bearer " + login.json()["token"], "If-Match": "1"}
        with DB() as db:
            session_id = db.scalar(select(Session.id).where(Session.user_id == parent_id))
        payload = schemas.Preferences(**before).model_dump(mode="json")
        payload.update(daily_minutes=37, repeat_topics=["Mathematik: Künstliches Ziel"])
        reached = Event()

        def on_statement(_conn, _cursor, statement, _parameters, _context, _executemany):
            normalized = " ".join(statement.lower().split())
            if normalized.startswith("update children set grade="):
                reached.set()

        def save():
            with TestClient(app, headers=headers) as concurrent:
                return concurrent.put(f"/api/children/{child['id']}/preferences", json=payload)

        with ThreadPoolExecutor(max_workers=1) as pool:
            with DB.begin() as locker:
                locker.execute(update(Child).where(Child.id == child["id"]).values(grade=Child.grade))
                if change == "view":
                    locker.get(Membership, membership_id).permission = "view"
                elif change == "removed":
                    locker.delete(locker.get(Membership, membership_id))
                else:
                    locker.get(Session, session_id).revoked = True
                locker.flush()
                event.listen(engine, "before_cursor_execute", on_statement)
                try:
                    pending = pool.submit(save)
                    assert reached.wait(10)
                finally:
                    event.remove(engine, "before_cursor_execute", on_statement)
            response = pending.result(20)
    assert response.status_code == {"session": 401, "view": 403, "removed": 404}[change], response.text
    with DB() as db:
        assert db.get(Child, child["id"]).preferences == before
        assert not db.scalar(select(Assignment.id).where(Assignment.child_id == child["id"]))
