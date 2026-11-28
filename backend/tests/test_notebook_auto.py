"""Artificial standalone material: finite auto-reservation, never provider calls."""
import test_material_auto_review as review_tests
import test_notebook_practice as notebook_tests
from schulpilot import notebook_auto
from schulpilot.db import DB, Child, Job, Material, Session
from schulpilot.notebook_auto_models import NotebookAutoIntent
from sqlalchemy import func, select

pytest_plugins = ["test_notebook_practice", "test_material_auto_review"]


def prepare(book):
    with DB.begin() as db:
        page = db.get(Material, book.refs[0]["id"])
        page.school_day_id = None
        session = db.scalar(select(Session).where(Session.user_id == book.actor_id).order_by(Session.created.desc()))
        child = db.get(Child, book.child["id"])
        authority = {"version": 1, "user_id": book.actor_id, "session_id": session.id, "family_id": child.family_id}
        notebook_auto.arm(db, child, page, authority)
        notebook_auto.arm(db, child, page, authority)
        db.flush()
        return db.scalar(select(NotebookAutoIntent.id).where(NotebookAutoIntent.material_id == page.id)), session.id


def test_duplicate_arm_and_reservation_then_provider_failure_has_no_retry(notebook):
    intent_id, _ = prepare(notebook)
    assert intent_id
    notebook_auto.advance_one()
    notebook_auto.advance_one()
    with DB.begin() as db:
        intent = db.get(NotebookAutoIntent, intent_id)
        assert intent.status == "queued"
        assert db.scalar(select(func.count()).select_from(NotebookAutoIntent).where(
            NotebookAutoIntent.material_id == intent.material_id)) == 1
        job = db.get(Job, intent.job_id)
        assert job.kind == "unit"
        job.status = "failed"
    notebook_auto.advance_one()
    notebook_auto.advance_one()
    with DB() as db:
        intent = db.get(NotebookAutoIntent, intent_id)
        assert intent.status == "blocked"
        assert db.scalar(select(func.count()).select_from(Job).where(Job.child_id == intent.child_id)) == 1


def test_source_change_before_reservation_blocks(notebook):
    intent_id, _ = prepare(notebook)
    with DB.begin() as db:
        intent = db.get(NotebookAutoIntent, intent_id)
        db.get(Material, intent.material_id).revision += 1
    notebook_auto.advance_one()
    with DB() as db:
        assert db.get(NotebookAutoIntent, intent_id).status == "blocked"
        assert db.scalar(select(func.count()).select_from(Job).where(Job.child_id == notebook.child["id"])) == 0


def test_revoked_session_blocks(notebook):
    intent_id, session_id = prepare(notebook)
    with DB.begin() as db:
        db.get(Session, session_id).revoked = True
    notebook_auto.advance_one()
    with DB() as db:
        assert db.get(NotebookAutoIntent, intent_id).status == "blocked"
        assert db.scalar(select(func.count()).select_from(Job).where(Job.child_id == notebook.child["id"])) == 0


def test_foreign_family_cannot_schedule(notebook):
    intent_id, _ = prepare(notebook)
    with DB.begin() as db:
        intent = db.get(NotebookAutoIntent, intent_id)
        intent.family_id = "a" * 32
    notebook_auto.advance_one()
    with DB() as db:
        assert db.get(NotebookAutoIntent, intent_id).status == "blocked"
        assert db.scalar(select(func.count()).select_from(Job).where(Job.child_id == notebook.child["id"])) == 0


def test_round_uses_one_reserved_job_and_publishes_once(notebook, monkeypatch):
    intent_id, _ = prepare(notebook)
    notebook_auto.advance_one()
    with DB() as db:
        job_id = db.get(NotebookAutoIntent, intent_id).job_id
    result, calls = notebook_tests.process(notebook, monkeypatch, job_id, 3)
    assert result["status"] == "completed", result
    assert len(calls) == 1
    notebook_auto.advance_one()
    notebook_auto.advance_one()
    with DB() as db:
        assert db.get(NotebookAutoIntent, intent_id).status == "completed"
        assert db.scalar(select(func.count()).select_from(Job).where(Job.child_id == notebook.child["id"])) == 1


def test_pending_intent_is_exported_and_cascades_with_page(notebook):
    from schulpilot.families import export_child

    intent_id, _ = prepare(notebook)
    with DB.begin() as db:
        row = db.get(NotebookAutoIntent, intent_id)
        data = export_child(db, db.get(Child, row.child_id))["notebook_auto_intents"]
        assert len(data) == 1 and data[0]["id"] == intent_id
        assert "authority" not in data[0]
        db.delete(db.get(Material, row.material_id))
    with DB() as db:
        assert db.get(NotebookAutoIntent, intent_id) is None


def test_old_terminal_intent_expires_while_pending_is_kept(notebook):
    from schulpilot.notebook_auto import purge_expired

    intent_id, _ = prepare(notebook)
    with DB.begin() as db:
        row = db.get(NotebookAutoIntent, intent_id)
        row.created = 1
        purge_expired(db, 2)
        assert db.get(NotebookAutoIntent, intent_id) is not None
        row.status = "blocked"
        db.flush()
        purge_expired(db, 2)
        assert db.get(NotebookAutoIntent, intent_id) is None


def test_day_exam_and_vocabulary_are_not_armed(notebook):
    with DB.begin() as db:
        page = db.get(Material, notebook.refs[0]["id"])
        child = db.get(Child, notebook.child["id"])
        session = db.scalar(select(Session).where(Session.user_id == notebook.actor_id).order_by(Session.created.desc()))
        authority = {"version": 1, "user_id": notebook.actor_id, "session_id": session.id, "family_id": child.family_id}
        notebook_auto.arm(db, child, page, authority)  # belongs to a school day
        page.school_day_id = None
        page.purpose = "exam"
        notebook_auto.arm(db, child, page, authority)
        page.purpose = "notebook"
        page.subject = "Englisch"
        page.topic = "Vokabeln"
        page.content = "English | Deutsch\ncat | Katze\ndog | Hund"
        notebook_auto.arm(db, child, page, authority)
        db.flush()
        assert db.scalar(select(func.count()).select_from(NotebookAutoIntent)) == 0


def test_competing_workers_reserve_only_once(notebook):
    from concurrent.futures import ThreadPoolExecutor

    intent_id, _ = prepare(notebook)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: notebook_auto.advance_one(), range(2)))
    with DB() as db:
        intent = db.get(NotebookAutoIntent, intent_id)
        assert intent.status == "queued"
        assert db.scalar(select(func.count()).select_from(Job).where(Job.child_id == intent.child_id)) == 1


def test_deleted_session_loses_binding_and_blocks(notebook):
    intent_id, session_id = prepare(notebook)
    with DB.begin() as db:
        db.delete(db.get(Session, session_id))
    notebook_auto.advance_one()
    with DB() as db:
        row = db.get(NotebookAutoIntent, intent_id)
        assert row.session_id is None and row.status == "blocked"
        assert db.scalar(select(func.count()).select_from(Job).where(Job.child_id == notebook.child["id"])) == 0


def test_deleted_child_cascades_to_intent(notebook):
    intent_id, _ = prepare(notebook)
    with DB.begin() as db:
        db.delete(db.get(Child, notebook.child["id"]))
    with DB() as db:
        assert db.get(NotebookAutoIntent, intent_id) is None


def test_parent_confirmation_creates_one_intent_and_get_does_not(notebook):
    with DB.begin() as db:
        page = db.get(Material, notebook.refs[0]["id"])
        page.school_day_id = None
        page.confirmed = False
        page.status = "review"
        revision = page.revision
        material_id = page.id
        body = {"subject": page.subject, "topic": page.topic, "content": page.content,
                "homework": [], "revision": revision, "uncertainties_resolved": True}
    assert notebook.parent_api.get(f"/api/materials/{material_id}").status_code == 200
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(NotebookAutoIntent)) == 0
    response = notebook.parent_api.put(f"/api/materials/{material_id}/confirm", json=body)
    assert response.status_code == 200, response.text
    assert notebook.parent_api.put(f"/api/materials/{material_id}/confirm", json=body).status_code == 200
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(NotebookAutoIntent)) == 1
        assert db.scalar(select(func.count()).select_from(Job).where(Job.child_id == notebook.child["id"])) == 0


def test_auto_image_countercheck_arms_standalone_round(pipeline):
    page = review_tests.upload(pipeline)
    review_tests.first(pipeline, page)
    review_tests.check(pipeline)
    with DB() as db:
        intent = db.scalar(select(NotebookAutoIntent).where(NotebookAutoIntent.material_id == page["id"]))
        assert intent and intent.status == "pending"
        revision = db.get(Material, page["id"]).revision
        assert intent.revision == revision
    notebook_auto.advance_one()
    with DB() as db:
        intent = db.scalar(select(NotebookAutoIntent).where(NotebookAutoIntent.material_id == page["id"]))
        assert intent.status == "queued"
        assert db.get(Job, intent.job_id).payload["material_revision"] == revision


def test_round_robin_reaches_intents_after_first_hundred(notebook, monkeypatch):
    intent_id, _ = prepare(notebook)
    with DB.begin() as db:
        seed = db.get(NotebookAutoIntent, intent_id)
        for index in range(101):
            db.add(NotebookAutoIntent(
                id=f"{index:032x}", child_id=seed.child_id, material_id=seed.material_id,
                revision=1000 + index, user_id=seed.user_id, session_id=seed.session_id,
                family_id=seed.family_id, selection=seed.selection, status="pending", created=1,
            ))
    seen = []
    monkeypatch.setattr(notebook_auto, "_cursor", None)
    monkeypatch.setattr(notebook_auto, "_advance", lambda db, identifier: seen.append(identifier))
    notebook_auto.advance_one()
    assert f"{100:032x}" not in seen
    notebook_auto.advance_one()
    assert f"{100:032x}" in seen


def test_exhausted_job_rate_waits_until_next_window(notebook, monkeypatch):
    from schulpilot.db import RateBucket

    intent_id, _ = prepare(notebook)
    timestamp = int(notebook_auto.time.time())
    tick = timestamp // 60
    clock = [timestamp]
    monkeypatch.setattr(notebook_auto.time, "time", lambda: clock[0])
    with DB.begin() as db:
        row = db.get(NotebookAutoIntent, intent_id)
        db.add(RateBucket(id=f"job:{row.user_id}:{tick}", count=30, expires=(tick + 1) * 60))
    for _ in range(3):
        notebook_auto.advance_one()
    with DB() as db:
        assert db.get(NotebookAutoIntent, intent_id).status == "pending"
        assert db.scalar(select(func.count()).select_from(Job).where(Job.child_id == notebook.child["id"])) == 0
    clock[0] = (tick + 1) * 60
    notebook_auto.advance_one()
    with DB() as db:
        assert db.get(NotebookAutoIntent, intent_id).status == "queued"


def test_actual_job_rate_race_stays_pending_without_reservation(notebook, monkeypatch):
    from fastapi import HTTPException
    from schulpilot import materials
    from schulpilot.db import Usage

    intent_id, _ = prepare(notebook)

    def limited(*args, **kwargs):
        raise HTTPException(429, "Zu viele Anfragen. Bitte später erneut versuchen.")

    monkeypatch.setattr(materials, "rate_limit", limited)
    notebook_auto.advance_one()
    with DB() as db:
        assert db.get(NotebookAutoIntent, intent_id).status == "pending"
        assert db.scalar(select(func.count()).select_from(Job).where(Job.child_id == notebook.child["id"])) == 0
        assert db.scalar(select(func.count()).select_from(Usage).where(Usage.child_id == notebook.child["id"])) == 0


def test_cost_429_even_with_same_text_blocks_without_retry(notebook, monkeypatch):
    from fastapi import HTTPException
    from schulpilot import materials
    from schulpilot.db import Usage

    intent_id, _ = prepare(notebook)
    calls = []

    def rejected(*args, **kwargs):
        calls.append(True)
        raise HTTPException(429, "Zu viele Anfragen. Bitte später erneut versuchen.")

    monkeypatch.setattr(materials, "reserve", rejected)
    notebook_auto.advance_one()
    notebook_auto.advance_one()
    with DB() as db:
        assert db.get(NotebookAutoIntent, intent_id).status == "blocked"
        assert db.scalar(select(func.count()).select_from(Job).where(Job.child_id == notebook.child["id"])) == 0
        assert db.scalar(select(func.count()).select_from(Usage).where(Usage.child_id == notebook.child["id"])) == 0
    assert len(calls) == 1


def test_two_children_share_atomic_job_limit_and_wait_independently(notebook, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    from conftest import create_child
    from schulpilot.db import RateBucket

    second_child = create_child(notebook.parent_api, notebook.parent, username="test-child-two")
    first_id, _ = prepare(notebook)
    stamp = int(notebook_auto.time.time())
    tick = stamp // 60
    clock = [stamp]
    monkeypatch.setattr(notebook_auto.time, "time", lambda: clock[0])
    with DB.begin() as db:
        first = db.get(NotebookAutoIntent, first_id)
        parent_id = notebook.parent["id"]
        session = db.scalar(select(Session).where(Session.user_id == parent_id).order_by(Session.created.desc()))
        first.user_id, first.session_id = parent_id, session.id
        source = db.get(Material, first.material_id)
        child = db.get(Child, second_child["id"])
        page = Material(child_id=child.id, title="Künstliche zweite Seite", subject=source.subject,
                        topic=source.topic, content=source.content, confirmed=True, status="confirmed")
        db.add(page)
        db.flush()
        notebook_auto.arm(db, child, page, {"version": 1, "user_id": parent_id,
                                            "session_id": session.id, "family_id": child.family_id})
        db.add(RateBucket(id=f"job:{parent_id}:{tick}", count=29, expires=(tick + 1) * 60))
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: notebook_auto.advance_one(), range(2)))
    with DB() as db:
        intents = list(db.scalars(select(NotebookAutoIntent)))
        assert sorted(row.status for row in intents) == ["pending", "queued"]
        assert db.get(RateBucket, f"job:{parent_id}:{tick}").count == 30
        assert db.scalar(select(func.count()).select_from(Job)) == 1
    clock[0] = (tick + 1) * 60
    notebook_auto.advance_one()
    with DB() as db:
        assert sorted(row.status for row in db.scalars(select(NotebookAutoIntent))) == ["queued", "queued"]
        assert db.scalar(select(func.count()).select_from(Job)) == 2
