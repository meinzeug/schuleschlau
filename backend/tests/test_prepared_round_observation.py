"""Only the owning child sees a conservative, read-only observation."""

from conftest import create_child
from schulpilot.db import DB, Attempt, Job, LearningUnit, Usage
from schulpilot.school_preparation import advance_auto_rounds
from sqlalchemy import func, select
from test_automatic_evidence_guard import add_attempt, make_practice
from test_study_path import arm_automatic_rounds, finish

pytest_plugins = ["test_study_path"]


def generated(study):
    arm_automatic_rounds(study)
    assert advance_auto_rounds(study["day_id"])
    job_id = finish()
    with DB() as db:
        job = db.get(Job, job_id)
        assert job.status == "completed", job.error
        return job_id, job.result["unit_id"]


def test_read_only_notice_and_no_private_marker_or_implicit_repreparation(study, stage_transport):
    with DB.begin() as db:
        previous = make_practice(db, study["child"]["id"])
    job_id, unit_id = generated(study)
    first = study["client"].get(f"/api/units/{unit_id}")
    assert first.status_code == 200
    assert "practice_evidence_may_have_changed" not in first.json()
    with DB.begin() as db:
        add_attempt(db, previous)
        original_questions = db.get(LearningUnit, unit_id).questions
        original_jobs = db.scalar(select(func.count()).select_from(Job))
        original_usage = db.scalar(select(func.count()).select_from(Usage))
        digest = db.get(Job, job_id).payload["automatic_evidence_observation"]["marker"]["digest"]
    for _ in range(2):
        response = study["client"].get(f"/api/units/{unit_id}")
        assert response.status_code == 200
        assert response.json()["practice_evidence_may_have_changed"] is True
        assert digest not in response.text and "automatic_evidence_observation" not in response.text
    with DB() as db:
        assert db.get(LearningUnit, unit_id).questions == original_questions
        assert db.scalar(select(func.count()).select_from(Job)) == original_jobs
        assert db.scalar(select(func.count()).select_from(Usage)) == original_usage
        assert db.scalar(select(func.count()).select_from(Attempt)) == 1
    assert len(stage_transport["calls"]) == 1


def test_started_answered_or_legacy_round_never_gets_the_notice(study, stage_transport):
    with DB.begin() as db:
        prior = make_practice(db, study["child"]["id"])
    job_id, unit_id = generated(study)
    with DB.begin() as db:
        add_attempt(db, prior)
        db.get(LearningUnit, unit_id).status = "active"
    assert "practice_evidence_may_have_changed" not in study["client"].get(f"/api/units/{unit_id}").json()
    with DB.begin() as db:
        unit = db.get(LearningUnit, unit_id)
        unit.status = "not_started"
        add_attempt(db, unit_id)
    assert "practice_evidence_may_have_changed" not in study["client"].get(f"/api/units/{unit_id}").json()
    with DB.begin() as db:
        unit = db.get(LearningUnit, unit_id)
        for attempt in db.scalars(select(Attempt).where(Attempt.unit_id == unit_id)):
            db.delete(attempt)
        job = db.get(Job, job_id)
        job.payload = {k: v for k, v in job.payload.items() if k != "automatic_evidence_observation"}
    assert "practice_evidence_may_have_changed" not in study["client"].get(f"/api/units/{unit_id}").json()


def test_foreign_job_cannot_supply_a_marker(api, study, stage_transport):
    sibling = create_child(api, study["parent"], username="observation-sibling")
    with DB.begin() as db:
        prior = make_practice(db, study["child"]["id"])
    job_id, unit_id = generated(study)
    with DB.begin() as db:
        add_attempt(db, prior)
        db.get(Job, job_id).child_id = sibling["id"]
    result = study["client"].get(f"/api/units/{unit_id}")
    assert result.status_code == 200
    assert "practice_evidence_may_have_changed" not in result.json()
