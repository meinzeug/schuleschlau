"""Artificial prepared block notification and recovery; never contacts a provider."""

import re
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from conftest import HEADERS, create_child
from fastapi.testclient import TestClient
from schulpilot import ready_notifications, worker
from schulpilot.db import (
    DB,
    Child,
    Job,
    LearningUnit,
    Material,
    Message,
    PushDelivery,
    Session,
    UnitSource,
    User,
    engine,
    now,
)
from schulpilot.main import app
from schulpilot.security import Principal
from schulpilot.study_authority import bind
from sqlalchemy import event, func, select
from test_automatic_evidence_guard import make_practice

pytest_plugins = ["test_study_path"]


@pytest.fixture(autouse=True)
def no_provider(monkeypatch):
    from schulpilot import study_path

    def prohibited(*_args, **_kwargs):
        pytest.fail("A notification read/recovery must never call an AI provider")
    monkeypatch.setattr(study_path, "request_provider", prohibited)


def saved_automatic_round(study):
    with DB.begin() as db:
        child = db.get(Child, study["child"]["id"])
        user = db.get(User, child.user_id)
        session = db.scalar(select(Session).where(Session.user_id == user.id, Session.revoked.is_(False)))
        origin = bind(db, Principal(user, session), child)
        unit_id = make_practice(db, child.id)
        unit = db.get(LearningUnit, unit_id)
        unit.status, unit.school_day_id, unit.round_kind = "not_started", study["day_id"], "study_block"
        material = db.get(Material, study["materials"][0])
        unit.material_id = material.id
        db.add(UnitSource(unit_id=unit.id, material_id=material.id, revision=material.revision))
        job = Job(child_id=child.id, kind="study_block", status="completed", finished=int(now()),
                  idempotency="synthetic-auto-notice", payload={"completion_origin": origin,
                  "automatic_study_stage": True}, result={"unit_id": unit.id})
        db.add(job)
        db.flush()
        return job.id, unit.id, material.id


def test_completed_automatic_round_gets_one_private_notice_and_correct_route(api, study):
    jid, unit_id, _material_id = saved_automatic_round(study)
    # Repeated recovery and repeated processing of an already completed job are
    # safe; process never dispatches the provider for this completed fixture.
    worker.process(jid)
    worker.process(jid)
    ready_notifications.advance_one()
    owner = study["client"]
    for _ in range(2):
        inbox = owner.get("/api/notifications/inbox")
        assert inbox.status_code == 200
        events = [item for item in inbox.json()["items"] if item["kind"] == "round_ready"]
        assert len(events) == 1 and events[0]["route"] == f"/unit/{unit_id}"
        assert owner.get(f"/api/units/{unit_id}").status_code == 200
    event_id = events[0]["id"]
    assert owner.post("/api/notifications/inbox/read", json={"ids": [event_id]}).status_code == 200
    assert owner.post("/api/notifications/inbox/read", json={"ids": [event_id]}).status_code == 200
    sibling = create_child(api, study["parent"], username="notice-sibling")
    with TestClient(app, headers=HEADERS) as other:
        login = other.post("/api/auth/login", json={"username": "notice-sibling", "password": "secure-child-pass-123"})
        assert login.status_code == 200
        other.headers["Authorization"] = "Bearer " + login.json()["token"]
        assert event_id not in {e["id"] for e in other.get("/api/notifications/inbox").json()["items"]}
        assert other.get(f"/api/units/{unit_id}").status_code in (403, 404)
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Message).where(Message.kind == "round_ready")) == 1
        assert db.scalar(select(func.count()).select_from(PushDelivery)) == 0
        assert db.get(LearningUnit, unit_id).status == "not_started"
        assert db.get(Child, sibling["id"])


def test_source_change_invalidates_previously_recorded_notice(study):
    jid, unit_id, material_id = saved_automatic_round(study)
    worker.process(jid)
    assert any(e["route"] == f"/unit/{unit_id}" for e in study["client"].get("/api/notifications/inbox").json()["items"])
    with DB.begin() as db:
        db.get(Material, material_id).revision += 1
    assert not any(e["route"] == f"/unit/{unit_id}" for e in study["client"].get("/api/notifications/inbox").json()["items"])
    worker.process(jid)
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Message).where(Message.kind == "round_ready")) == 1


def test_two_recovery_ticks_do_not_duplicate_receipts(study):
    jid, unit_id, _material_id = saved_automatic_round(study)
    # On PostgreSQL force both scanners to obtain the same pending job before
    # either can lock the child. SQLite retains its ordinary sequential check.
    barrier = Barrier(2)
    scans = []
    def synchronize(_conn, _cursor, statement, _parameters, _context, _executemany):
        if re.match(r"\s*select jobs\.id\s+from", statement, re.IGNORECASE):
            scans.append(True)
            barrier.wait(timeout=10)
    if engine.dialect.name == "postgresql":
        event.listen(engine, "after_cursor_execute", synchronize)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: ready_notifications.advance_one(), range(2)))
    finally:
        if engine.dialect.name == "postgresql":
            event.remove(engine, "after_cursor_execute", synchronize)
    if engine.dialect.name == "postgresql":
        assert len(scans) == 2
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Message).where(Message.kind == "round_ready")) == 1
        receipt = db.get(Job, jid).payload[ready_notifications.RECEIPTS]
        assert len(receipt) == 1 and receipt[0]["unit_id"] == unit_id
