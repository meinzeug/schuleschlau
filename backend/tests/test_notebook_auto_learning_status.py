"""Read-only learning status for one current auto-notebook source."""
import pytest
from conftest import create_child
from schulpilot import notebook_auto
from schulpilot.db import DB, Attempt, Job, LearningUnit, Material, UnitSource, Usage
from schulpilot.notebook_auto_models import NotebookAutoIntent
from sqlalchemy import func, select
from test_notebook_auto import prepare as arm

pytest_plugins = ["test_notebook_practice", "test_material_auto_review"]


def prepare(book):
    from schulpilot.db import now
    result = arm(book)
    with DB.begin() as db:
        db.get(LearningUnit, book.old_id).completed = int(now())
    return result


def counts(child):
    with DB() as db:
        return tuple(db.scalar(select(func.count()).select_from(model).where(
            model.child_id == child)) for model in (Job, Usage, LearningUnit))


def item(book):
    response = book.client.get(f"/api/children/{book.child['id']}/learning?section=ready")
    assert response.status_code == 200, response.text
    return next(row for row in response.json()["items"] if row["kind"] == "material" and row["id"] == book.refs[0]["id"])


def test_pending_is_read_only_and_old_client_cannot_make_duplicate_job(notebook):
    intent_id, _ = prepare(notebook)
    assert intent_id
    before = counts(notebook.child["id"])
    for _ in range(3):
        assert item(notebook)["automatic_preparation"] == {"status": "pending"}
    response = notebook.client.post(f"/api/children/{notebook.child['id']}/units",
        json={"material_id": notebook.refs[0]["id"]}, headers={"Idempotency-Key": "stale-list-00000001"})
    assert response.status_code == 409
    assert counts(notebook.child["id"]) == before


@pytest.mark.parametrize("job_status,expected", [("queued", "queued"), ("running", "running"),
                                                ("failed", "blocked"), ("completed", "ready")])
def test_matching_auto_job_status_is_scoped_and_read_only(notebook, job_status, expected):
    intent_id, _ = prepare(notebook)
    notebook_auto.advance_one()
    with DB.begin() as db:
        intent = db.get(NotebookAutoIntent, intent_id)
        job = db.get(Job, intent.job_id)
        assert job and job.child_id == notebook.child["id"]
        job.status = job_status
        if job_status == "completed":
            job.result = {"unit_id": notebook.old_id}
            db.add(UnitSource(unit_id=notebook.old_id, material_id=intent.material_id, revision=intent.revision))
        job_id = job.id
    before = counts(notebook.child["id"])
    status = item(notebook)["automatic_preparation"]
    assert status == {"status": expected, "job_id": job_id}
    assert counts(notebook.child["id"]) == before


def test_failed_unreserved_intent_has_no_job_link_or_silent_retry(notebook):
    intent_id, _ = prepare(notebook)
    with DB.begin() as db:
        db.get(NotebookAutoIntent, intent_id).status = "blocked"
    before = counts(notebook.child["id"])
    assert item(notebook)["automatic_preparation"] == {"status": "blocked"}
    assert counts(notebook.child["id"]) == before


def test_completed_job_without_matching_saved_round_is_not_reported_ready(notebook):
    intent_id, _ = prepare(notebook)
    notebook_auto.advance_one()
    with DB.begin() as db:
        intent = db.get(NotebookAutoIntent, intent_id)
        job = db.get(Job, intent.job_id)
        job.status, job.result = "completed", {"unit_id": notebook.old_id}
    assert item(notebook)["automatic_preparation"] == {"status": "blocked"}


def test_failed_job_exposes_only_current_source_and_explicit_manual_start(notebook):
    intent_id, _ = prepare(notebook)
    notebook_auto.advance_one()
    with DB.begin() as db:
        intent = db.get(NotebookAutoIntent, intent_id)
        job = db.get(Job, intent.job_id)
        job.status = "failed"
        job_id = job.id
    notebook_auto.advance_one()
    before = counts(notebook.child["id"])
    for _ in range(2):
        status = notebook.client.get(f"/api/jobs/{job_id}")
        assert status.status_code == 200
        assert status.json()["notebook_retry_material_id"] == notebook.refs[0]["id"]
    assert counts(notebook.child["id"]) == before
    response = notebook.client.post(f"/api/children/{notebook.child['id']}/units",
        json={"material_id": notebook.refs[0]["id"]}, headers={"Idempotency-Key": "explicit-later-123456"})
    assert response.status_code == 202, response.text
    assert counts(notebook.child["id"])[0] == before[0] + 1
    with DB.begin() as db:
        db.get(Material, notebook.refs[0]["id"]).revision += 1
    assert notebook.client.get(f"/api/jobs/{job_id}").json()["notebook_retry_material_id"] is None


def test_explicit_parent_assignment_not_blocked_by_pending_auto_intent(notebook):
    from schulpilot.db import Assignment

    prepare(notebook)
    with DB.begin() as db:
        assignment = Assignment(child_id=notebook.child["id"], material_id=notebook.refs[0]["id"],
                                kind="parent", subject="Mathematik", topic="Brüche")
        db.add(assignment)
        db.flush()
        assignment_id = assignment.id
    response = notebook.client.post(f"/api/children/{notebook.child['id']}/units",
        json={"assignment_id": assignment_id}, headers={"Idempotency-Key": "explicit-parent-12345"})
    assert response.status_code == 202, response.text


def test_explicit_multi_page_practice_not_blocked_by_pending_auto_intent(notebook):
    from test_notebook_practice import post

    prepare(notebook)
    response = post(notebook, key="explicit-multiple-pages-12345")
    assert response.status_code == 202, response.text


def test_old_revision_and_foreign_job_never_become_a_status_link(api, notebook):
    intent_id, _ = prepare(notebook)
    sibling = create_child(api, notebook.parent, username="auto-status-sibling")
    with DB.begin() as db:
        intent = db.get(NotebookAutoIntent, intent_id)
        foreign = Job(child_id=sibling["id"], kind="unit", status="running", idempotency="foreign-status-job",
                      payload={"material_id": intent.material_id, "material_revision": intent.revision})
        db.add(foreign)
        db.flush()
        intent.status, intent.job_id = "queued", foreign.id
        foreign_id = foreign.id
    status = item(notebook)["automatic_preparation"]
    assert status == {"status": "blocked"}
    assert foreign_id not in str(status)
    with DB.begin() as db:
        intent = db.get(NotebookAutoIntent, intent_id)
        db.get(Material, intent.material_id).revision += 1
    assert "automatic_preparation" not in item(notebook)


def test_other_family_cannot_read_status(api, notebook, mailbox):
    intent_id, _ = prepare(notebook)
    assert intent_id
    from conftest import HEADERS, register
    from fastapi.testclient import TestClient
    from schulpilot.main import app
    with TestClient(app, headers=HEADERS) as other:
        register(other, mailbox, email="auto-status-outsider@example.org")
        result = other.get(f"/api/children/{notebook.child['id']}/learning?section=ready")
        assert result.status_code in (403, 404)


def test_preexisting_saved_round_remains_a_separate_item(notebook):
    prepare(notebook)
    with DB.begin() as db:
        unit = db.get(LearningUnit, notebook.old_id)
        unit.status = "paused"
    response = notebook.client.get(f"/api/children/{notebook.child['id']}/learning?section=ready")
    assert response.status_code == 200
    entries = response.json()["items"]
    assert any(row["kind"] == "unit" and row["id"] == notebook.old_id for row in entries)
    assert any(row["kind"] == "material" and row.get("automatic_preparation", {}).get("status") == "pending" for row in entries)
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Attempt).where(Attempt.unit_id == notebook.old_id)) == 1


def test_random_selection_never_starts_pending_material_and_keeps_saved_round(notebook):
    from schulpilot.subject_registry import identity

    prepare(notebook)
    subject = identity("mathematik")
    url = f"/api/children/{notebook.child['id']}/learning/subjects/{subject}/random"
    before = counts(notebook.child["id"])
    response = notebook.client.get(url)
    assert response.status_code == 409
    assert counts(notebook.child["id"]) == before
    with DB.begin() as db:
        db.get(LearningUnit, notebook.old_id).status = "paused"
    response = notebook.client.get(url)
    assert response.status_code == 200, response.text
    assert response.json()["item"]["kind"] == "unit"
    assert response.json()["item"]["id"] == notebook.old_id
    assert counts(notebook.child["id"]) == before


def test_pending_intent_added_during_stale_post_blocks_before_reservation(notebook):
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor

    from schulpilot.db import Child, Session, engine
    from sqlalchemy import event, text, update

    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL transaction ordering")
    material_id = notebook.refs[0]["id"]
    before = counts(notebook.child["id"])
    waiting, writer_pid = threading.Event(), []
    def gate(_conn, cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().lower().startswith("update children"):
            writer_pid.append(cursor.connection.info.backend_pid)
            waiting.set()
    with DB() as db:
        db.execute(update(Child).where(Child.id == notebook.child["id"]).values(grade=Child.grade))
        child = db.get(Child, notebook.child["id"])
        page = db.get(Material, material_id)
        page.school_day_id = None
        session = db.scalar(select(Session).where(Session.user_id == notebook.actor_id).order_by(Session.created.desc()))
        notebook_auto.arm(db, child, page, {"user_id": notebook.actor_id, "session_id": session.id,
                                          "family_id": child.family_id})
        db.flush()
        event.listen(engine, "before_cursor_execute", gate)
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                task = pool.submit(notebook.client.post, f"/api/children/{child.id}/units",
                    json={"material_id": material_id}, headers={"Idempotency-Key": "stale-wait-1234567"})
                try:
                    assert waiting.wait(15)
                    deadline = time.monotonic() + 10
                    blocked = False
                    while time.monotonic() < deadline:
                        with DB() as observer:
                            blocked = bool(observer.scalar(text("select cardinality(pg_blocking_pids(:pid)) > 0"),
                                                           {"pid": writer_pid[0]}))
                        if blocked:
                            break
                        threading.Event().wait(.02)
                    assert blocked
                finally:
                    db.commit()
                response = task.result(timeout=15)
        finally:
            event.remove(engine, "before_cursor_execute", gate)
    assert response.status_code == 409, response.text
    assert counts(notebook.child["id"]) == before


def test_many_completed_intents_use_batched_source_validation(notebook):
    from schulpilot.db import Child, engine
    from sqlalchemy import event

    material_ids = []
    with DB.begin() as db:
        child = db.get(Child, notebook.child["id"])
        for index in range(35):
            material = Material(child_id=child.id, subject="Mathematik", topic=f"Künstlich {index}",
                title="Künstliche Seite", content="Künstlicher Inhalt", confirmed=True,
                status="confirmed", purpose="notebook")
            db.add(material)
            db.flush()
            unit = LearningUnit(child_id=child.id, subject="Mathematik", topic=f"Künstlich {index}",
                explanation="Künstlich", questions=[], status="not_started", provider="fixture")
            db.add(unit)
            db.flush()
            db.add(UnitSource(unit_id=unit.id, material_id=material.id, revision=material.revision))
            job = Job(child_id=child.id, kind="unit", status="completed", idempotency=f"batch-status-{index}",
                      payload={"material_id": material.id, "material_revision": material.revision},
                      result={"unit_id": unit.id})
            db.add(job)
            db.flush()
            db.add(NotebookAutoIntent(child_id=child.id, material_id=material.id, revision=material.revision,
                family_id=child.family_id, selection={}, status="completed", job_id=job.id))
            material_ids.append(material.id)
    with DB() as db:
        child = db.get(Child, notebook.child["id"])
        rows = [{"id": ident, "kind": "material"} for ident in material_ids]
        statements = []
        def count_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)
        event.listen(engine, "before_cursor_execute", count_sql)
        try:
            notebook_auto.annotate_plan(db, child, [rows])
        finally:
            event.remove(engine, "before_cursor_execute", count_sql)
        assert len(statements) <= 2
        assert len(rows) == 35
        assert all(row["automatic_preparation"]["status"] == "ready" for row in rows)
