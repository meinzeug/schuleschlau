"""Synthetic start-time observation; no provider calls or real child data."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from fastapi.testclient import TestClient
from schulpilot import prepared_round_observation
from schulpilot.db import DB, Attempt, Job, LearningUnit, Material, UnitSource, Usage, engine
from schulpilot.learning_evidence_marker import snapshot
from schulpilot.main import app
from sqlalchemy import func, select
from test_automatic_evidence_guard import add_attempt, make_practice

pytest_plugins = ["test_study_path"]


def prepared(study):
    with DB.begin() as db:
        earlier = make_practice(db, study["child"]["id"])
        unit_id = make_practice(db, study["child"]["id"])
        unit = db.get(LearningUnit, unit_id)
        unit.status, unit.school_day_id, unit.round_kind = "not_started", study["day_id"], "study_block"
        page = db.get(Material, study["materials"][0])
        db.add(UnitSource(unit_id=unit_id, material_id=page.id, revision=page.revision))
        db.flush()
        marker = snapshot(db, unit.child_id, unit.subject)
        job = Job(child_id=unit.child_id, kind="study_block", status="completed",
                  payload={"automatic_study_stage": True,
                           "automatic_evidence_observation": {"consistency": "best_effort", "marker": marker}},
                  result={"unit_id": unit_id}, idempotency="artificial-prepared-start")
        db.add(job)
        db.flush()
        return earlier, unit_id, marker["digest"]


def test_start_rechecks_after_earlier_read_without_starting_new_job(study):
    earlier, unit_id, digest = prepared(study)
    client = study["client"]
    assert "practice_evidence_may_have_changed" not in client.get(f"/api/units/{unit_id}").json()
    with DB.begin() as db:
        add_attempt(db, earlier)
        before = tuple(db.scalar(select(func.count()).select_from(model)) for model in (Job, Usage, Attempt))
    response = client.post(f"/api/units/{unit_id}/start")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "active"
    assert response.json()["practice_evidence_may_have_changed"] is True
    assert digest not in response.text and "automatic_evidence_observation" not in response.text
    with DB() as db:
        assert tuple(db.scalar(select(func.count()).select_from(model)) for model in (Job, Usage, Attempt)) == before
    # An already-started unit does not produce a renewed warning or new evidence.
    assert "practice_evidence_may_have_changed" not in client.post(f"/api/units/{unit_id}/start").json()


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="Real PostgreSQL concurrent transactions")
def test_other_unit_answer_commits_while_start_waits_before_observation(study, monkeypatch):
    earlier, unit_id, _digest = prepared(study)
    client = study["client"]
    assert "practice_evidence_may_have_changed" not in client.get(f"/api/units/{unit_id}").json()
    entered, proceed = Event(), Event()
    real = prepared_round_observation.may_have_changed
    def held(db, unit):
        entered.set()
        assert proceed.wait(10)
        return real(db, unit)
    monkeypatch.setattr(prepared_round_observation, "may_have_changed", held)
    headers = dict(client.headers)
    def begin():
        with TestClient(app, headers=headers) as second:
            return second.post(f"/api/units/{unit_id}/start")
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(begin)
        assert entered.wait(10)
        with DB.begin() as db:
            add_attempt(db, earlier)
        proceed.set()
        result = pending.result(timeout=10)
    assert result.status_code == 200, result.text
    assert result.json()["practice_evidence_may_have_changed"] is True
    with DB() as db:
        assert db.get(LearningUnit, unit_id).status == "active"
        assert db.scalar(select(func.count()).select_from(Attempt).where(Attempt.unit_id == earlier)) == 1


@pytest.mark.parametrize("case", ["other_subject", "legacy", "sibling"])
def test_start_never_invents_a_warning_for_unrelated_or_unknown_evidence(api, study, case):
    from conftest import create_child

    earlier, unit_id, _digest = prepared(study)
    sibling = create_child(api, study["parent"], username="start-evidence-sibling") if case == "sibling" else None
    with DB.begin() as db:
        if case == "legacy":
            job = db.scalar(select(Job).where(Job.idempotency == "artificial-prepared-start"))
            job.payload = {"automatic_study_stage": True}
            add_attempt(db, earlier)
        else:
            unrelated = make_practice(db, sibling["id"] if sibling else study["child"]["id"],
                                      "Sachunterricht" if sibling else "Englisch")
            add_attempt(db, unrelated)
    result = study["client"].post(f"/api/units/{unit_id}/start")
    assert result.status_code == 200, result.text
    assert "practice_evidence_may_have_changed" not in result.json()
