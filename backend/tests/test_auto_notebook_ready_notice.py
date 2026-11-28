"""Synthetic standalone notebook preparation and notices; never call AI or FCM."""

import re
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from conftest import HEADERS, register
from fastapi.testclient import TestClient
from schulpilot import notebook_auto, notifications, ready_notifications, study_path, worker
from schulpilot.db import (
    DB,
    Attempt,
    Child,
    Job,
    LearningUnit,
    Material,
    Message,
    PushDelivery,
    UnitSource,
    Usage,
    engine,
    now,
)
from schulpilot.main import app
from schulpilot.notebook_auto_models import NotebookAutoIntent
from sqlalchemy import event, func, select
from test_notebook_auto import prepare

pytest_plugins = ["test_notebook_practice"]


@pytest.fixture(autouse=True)
def no_provider(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("Notification recovery must never contact a provider")
    monkeypatch.setattr(worker, "request_provider", forbidden)
    monkeypatch.setattr(study_path, "request_provider", forbidden)
    monkeypatch.setattr(notifications, "send_fcm", forbidden)


def completed_notebook_fixture(notebook):
    """Reserve through the real coordinator; synthesize saved output locally."""
    intent_id, _ = prepare(notebook)
    assert intent_id
    notebook_auto.advance_one()
    with DB.begin() as db:
        intent = db.get(NotebookAutoIntent, intent_id)
        assert intent.status == "queued"
        job = db.get(Job, intent.job_id)
        assert job.kind == "unit" and job.payload["notebook_practice"]["version"] == 1
        assert job.payload["completion_origin"]["user_id"] == notebook.actor_id
        source = db.get(Material, intent.material_id)
        assert source.confirmed and source.school_day_id is None and source.revision == intent.revision
        unit = LearningUnit(child_id=intent.child_id, material_id=source.id, subject=source.subject,
                            topic=source.topic, explanation="Künstliche Erklärung.", provider="fixture", synthetic=False,
                            questions=[{"id": "q", "type": "short", "prompt": "Künstliche Frage?", "answer": "13",
                                        "options": [], "accepted": [], "hints": [], "explanation": "Künstlich."}])
        db.add(unit)
        db.flush()
        db.add(UnitSource(unit_id=unit.id, material_id=source.id, revision=source.revision))
        job.status, job.finished, job.result = "completed", int(now()), {"unit_id": unit.id}
        return intent_id, job.id, unit.id, source.id


def test_completed_notebook_notice_is_unique_owned_and_opens_the_saved_round(notebook, api, mailbox):
    intent_id, jid, uid, _ = completed_notebook_fixture(notebook)
    with DB() as db:
        initial = tuple(db.scalar(select(func.count()).select_from(model)) for model in (Job, Usage, Attempt))
    worker.process(jid)
    worker.process(jid)
    notebook_auto.advance_one()
    ready_notifications.advance_one()
    for _ in range(2):
        response = notebook.client.get("/api/notifications/inbox")
        assert response.status_code == 200
        events = [entry for entry in response.json()["items"] if entry["kind"] == "round_ready"]
        assert len(events) == 1 and events[0]["route"] == f"/unit/{uid}"
        assert notebook.client.get(f"/api/units/{uid}").status_code == 200
    eid = events[0]["id"]
    assert notebook.client.post("/api/notifications/inbox/read", json={"ids": [eid]}).status_code == 200
    assert notebook.client.post("/api/notifications/inbox/read", json={"ids": [eid]}).status_code == 200
    with TestClient(app, headers=HEADERS) as other:
        register(other, mailbox, "other-notebook-family@example.org")
        assert eid not in {entry["id"] for entry in other.get("/api/notifications/inbox").json()["items"]}
        assert other.get(f"/api/units/{uid}").status_code in (403, 404)
    with DB() as db:
        assert tuple(db.scalar(select(func.count()).select_from(model)) for model in (Job, Usage, Attempt)) == initial
        assert db.scalar(select(func.count()).select_from(Message).where(Message.kind == "round_ready")) == 1
        assert db.scalar(select(func.count()).select_from(PushDelivery)) == 0
        assert db.get(LearningUnit, uid).status == "not_started"
        assert db.get(NotebookAutoIntent, intent_id).status == "completed"


@pytest.mark.parametrize("when", ["before_notice", "after_notice"])
def test_source_revision_change_suppresses_the_notebook_notice(notebook, when):
    _intent, jid, uid, material_id = completed_notebook_fixture(notebook)
    if when == "after_notice":
        worker.process(jid)
        assert any(e["route"] == f"/unit/{uid}" for e in notebook.client.get("/api/notifications/inbox").json()["items"])
    with DB.begin() as db:
        db.get(Material, material_id).revision += 1
    worker.process(jid)
    ready_notifications.advance_one()
    assert not any(e["route"] == f"/unit/{uid}" for e in notebook.client.get("/api/notifications/inbox").json()["items"])
    with DB() as db:
        count = db.scalar(select(func.count()).select_from(Message).where(Message.kind == "round_ready"))
        assert count == (1 if when == "after_notice" else 0)


def test_parallel_notebook_notice_recovery_writes_one_receipt(notebook):
    _intent, jid, uid, _ = completed_notebook_fixture(notebook)
    barrier, scans = Barrier(2), []
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
        assert len(db.get(Job, jid).payload[ready_notifications.RECEIPTS]) == 1
        assert db.get(Job, jid).payload[ready_notifications.RECEIPTS][0]["unit_id"] == uid
        assert db.get(Child, notebook.child["id"])
