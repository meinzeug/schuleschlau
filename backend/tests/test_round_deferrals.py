"""Child decisions defer a round, never certify knowledge or parent duties."""
import pytest
from sqlalchemy import select

from schulpilot.db import Assignment, Attempt, Child, DB, LearningEvent, LearningMemory, LearningUnit, Material
from schulpilot.learning import plan
from test_adaptive_plan import fraction_profile as original_profile, session
from test_study_path import study as original_study


@pytest.fixture
def profile(api, household):
    yield from original_profile.__wrapped__(api, household)


@pytest.fixture
def study(api, household):
    yield from original_study.__wrapped__(api, household)


def test_defer_and_restore_preserves_draft_answers_and_parent_assignment(profile):
    client, uid, mid, _, _, child = profile
    with DB.begin() as db:
        assignment = Assignment(child_id=child["id"], kind="parent", subject="Mathematik", topic="Brüche",
                                mandatory=True, done=False)
        db.add(assignment)
        db.flush()
        db.get(LearningUnit, uid).assignment_id = assignment.id
        assignment_id = assignment.id
    state = session(client, uid)
    draft = client.put(f"/api/units/{uid}/learning-session/draft", json={"request_key": "round-draft-0001",
        "revision": state["draft_revision"], "question_id": "sum", "answer": "1/3", "input_method": "typed"})
    assert draft.status_code == 200, draft.text
    state = session(client, uid)
    payload = {"request_key": "round-defer-0001", "revision": state["revision"], "reason": "already_done"}
    path = f"/api/units/{uid}/learning-session/defer"
    response = client.post(path, json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["round_deferred"] is True and response.json()["status"] == "paused"
    assert client.post(path, json=payload).status_code == 200
    assert client.post(path, json={**payload, "reason": "unknown"}).status_code == 422
    assert client.post(f"/api/units/{uid}/start").status_code == 409
    assert client.post(f"/api/units/{uid}/questions/sum/hint").status_code == 409
    assert client.put(f"/api/units/{uid}/learning-session/draft", json={"request_key": "stale-draft-0001",
        "revision": 1, "question_id": "sum", "answer": "2/9", "input_method": "typed"}).status_code == 409
    assert client.post(f"/api/units/{uid}/learning-session/restore", json={"request_key": "round-stale-restore-0001",
        "revision": payload["revision"]}).status_code == 409
    with DB() as db:
        assert not db.scalar(select(Attempt.id).where(Attempt.unit_id == uid))
        assert db.get(LearningUnit, uid).completed is None
        assert db.get(Assignment, assignment_id).mandatory and not db.get(Assignment, assignment_id).done
        assert db.get(LearningMemory, uid).working["draft"]["answer"] == "1/3"
        current = plan(db, db.get(Child, child["id"]))
        assert not any(item.get("id") == uid for item in current["today"] + current["voluntary"])
        assert any(item["id"] == uid and item["mandatory"] for item in current["deferred_rounds"])
        assert len(list(db.scalars(select(LearningEvent).where(LearningEvent.unit_id == uid,
            LearningEvent.kind == "round_deferred")))) == 1
    restore = {"request_key": "round-restore-0001", "revision": session(client, uid)["revision"]}
    restored = client.post(f"/api/units/{uid}/learning-session/restore", json=restore)
    assert restored.status_code == 200 and restored.json()["round_deferred"] is False
    assert client.post(f"/api/units/{uid}/learning-session/restore", json=restore).status_code == 200
    assert client.post(f"/api/units/{uid}/start").status_code == 200
    with DB() as db:
        assert db.get(LearningMemory, uid).working["draft"]["answer"] == "1/3"
        assert not db.get(Assignment, assignment_id).done


def test_changed_plan_revision_invalidates_old_deferral_without_completing(profile):
    client, uid, _, _, _, _ = profile
    state = session(client, uid)
    response = client.post(f"/api/units/{uid}/learning-session/defer", json={"request_key": "round-plan-change-0001",
        "revision": state["revision"], "reason": "already_done"})
    assert response.status_code == 200 and response.json()["round_deferred"] is True
    with DB.begin() as db:
        db.get(LearningMemory, uid).plan_revision += 1
    assert client.get(f"/api/units/{uid}").json()["round_deferred"] is False
    with DB() as db:
        assert db.get(LearningUnit, uid).completed is None
        assert not db.scalar(select(Attempt.id).where(Attempt.unit_id == uid))


def test_only_own_child_can_defer_round(profile, api):
    from conftest import HEADERS, create_child
    from fastapi.testclient import TestClient
    from schulpilot.main import app

    client, uid, _, _, parent, _ = profile
    state = session(client, uid)
    body = {"request_key": "unauthorized-defer-0001", "revision": state["revision"], "reason": "already_done"}
    assert api.post(f"/api/units/{uid}/learning-session/defer", json=body).status_code == 403
    create_child(api, parent, username="other-test-child")
    with TestClient(app, headers=HEADERS) as other:
        login = other.post("/api/auth/login", json={"username": "other-test-child", "password": "secure-child-pass-123"})
        assert login.status_code == 200
        other.headers["Authorization"] = "Bearer " + login.json()["token"]
        assert other.post(f"/api/units/{uid}/learning-session/defer", json=body).status_code == 404
    with DB() as db:
        assert not db.scalar(select(LearningEvent.id).where(LearningEvent.unit_id == uid,
            LearningEvent.kind == "round_deferred"))


def test_changed_source_does_not_keep_a_stale_deferral(profile):
    client, uid, mid, _, _, _ = profile
    state = session(client, uid)
    assert client.post(f"/api/units/{uid}/learning-session/defer", json={"request_key": "round-source-change-0001",
        "revision": state["revision"], "reason": "already_done"}).json()["round_deferred"]
    with DB.begin() as db:
        db.get(Material, mid).revision += 1
    assert client.get(f"/api/units/{uid}").json()["round_deferred"] is False


def test_pending_feedback_is_not_hidden_by_deferral(profile):
    client, uid, _, _, _, _ = profile
    answer = client.post(f"/api/units/{uid}/questions/sum/answer", json={"answer": "2/9",
        "request_id": "defer-feedback-test-0001", "guided_feedback": True})
    assert answer.status_code == 200
    state = session(client, uid)
    result = client.post(f"/api/units/{uid}/learning-session/defer", json={"request_key": "defer-pending-0001",
        "revision": state["revision"], "reason": "already_done"})
    assert result.status_code == 409
    with DB() as db:
        assert db.scalar(select(Attempt.id).where(Attempt.unit_id == uid))
        assert not db.scalar(select(LearningEvent.id).where(LearningEvent.unit_id == uid,
            LearningEvent.kind == "round_deferred"))


def test_new_ready_round_can_be_deferred_without_claiming_it_started(profile):
    client, uid, _, _, _, _ = profile
    with DB.begin() as db:
        memory = db.get(LearningMemory, uid)
        if memory:
            db.delete(memory)
        db.get(LearningUnit, uid).status = "ready"
    response = client.post(f"/api/units/{uid}/learning-session/defer", json={"request_key": "ready-defer-0001",
        "revision": 0, "reason": "already_done"})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ready" and response.json()["round_deferred"] is True


def test_study_path_does_not_recommend_deferred_round_or_skip_same_subject(study):
    from schulpilot import study_path
    from schulpilot.db import SchoolDay, UnitSource
    from schulpilot.synthetic import sample_unit

    client, child = study["client"], study["child"]
    with DB.begin() as db:
        day = db.get(SchoolDay, study["day_id"])
        page = db.get(Material, study["materials"][0])
        data = sample_unit()
        unit = LearningUnit(child_id=child["id"], school_day_id=day.id, subject=page.subject,
            topic=page.topic, explanation=data["explanation"], questions=data["questions"][:2],
            synthetic=False, provider="fixture")
        db.add(unit)
        db.flush()
        db.add(UnitSource(unit_id=unit.id, material_id=page.id, revision=page.revision))
        db.flush()
        unit_id = unit.id
        built = study_path.ensure_plan(db, day)
        block_id = next(block["id"] for block in built["blocks"] if block.get("unit_id") == unit_id)
    assert client.post(f"/api/units/{unit_id}/start").status_code == 200
    state = session(client, unit_id)
    response = client.post(f"/api/units/{unit_id}/learning-session/defer", json={"request_key": "path-defer-0001",
        "revision": state["revision"], "reason": "already_done"})
    assert response.status_code == 200, response.text
    path = client.get(f"/api/school-days/{study['day_id']}/study-path").json()
    assert next(block for block in path["blocks"] if block["id"] == block_id)["round_deferred"] is True
    assert path["next_block_id"] != block_id
    assert path["next_block_id"] is None or next(block for block in path["blocks"]
        if block["id"] == path["next_block_id"])["round_deferred"] is False


def test_pending_answer_serializes_before_deferral_on_postgres(profile, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    import time
    from fastapi.testclient import TestClient
    from sqlalchemy import text
    from schulpilot import learning
    from schulpilot.db import engine
    from schulpilot.main import app

    if engine.dialect.name != "postgresql":
        pytest.skip("Real PostgreSQL transaction race")
    client, uid, _, _, _, _ = profile
    revision = session(client, uid)["revision"]
    holding, release = Event(), Event()
    original = learning.record
    def gated(db, child_id, kind, detail=None, unit_id=None):
        result = original(db, child_id, kind, detail, unit_id)
        if kind == "feedback_pending":
            holding.set()
            assert release.wait(10)
        return result
    monkeypatch.setattr(learning, "record", gated)
    def answer():
        with TestClient(app, headers=dict(client.headers)) as other:
            return other.post(f"/api/units/{uid}/questions/sum/answer", json={"answer": "2/9",
                "request_id": "round-race-answer-0001", "guided_feedback": True}).status_code
    def defer():
        with TestClient(app, headers=dict(client.headers)) as other:
            return other.post(f"/api/units/{uid}/learning-session/defer", json={"request_key": "round-race-defer-0001",
                "revision": revision, "reason": "already_done"}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        answer_future = pool.submit(answer)
        assert holding.wait(10)
        defer_future = pool.submit(defer)
        deadline, blocked = time.monotonic() + 5, False
        while time.monotonic() < deadline:
            with engine.connect() as connection:
                blocked = bool(connection.execute(text("select count(*) from pg_stat_activity "
                    "where datname=current_database() and wait_event_type='Lock' "
                    "and query ilike '%learning_units%'" )).scalar_one())
            if blocked:
                break
            time.sleep(0.03)
        assert blocked and not defer_future.done()
        release.set()
        assert answer_future.result(timeout=10) == 200
        assert defer_future.result(timeout=10) == 409
    with DB() as db:
        assert len(list(db.scalars(select(Attempt).where(Attempt.unit_id == uid)))) == 1
        assert not db.scalar(select(LearningEvent.id).where(LearningEvent.unit_id == uid,
            LearningEvent.kind == "round_deferred"))
