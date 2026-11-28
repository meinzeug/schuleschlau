"""Automatic study stages use a private changing-evidence guard; no real AI."""

import json

from conftest import create_child
from schulpilot import study_path
from schulpilot.db import DB, Attempt, Job, LearningUnit, Usage
from schulpilot.school_preparation import advance_auto_rounds
from sqlalchemy import func, select
from test_study_path import arm_automatic_rounds, finish, generate, path

pytest_plugins = ["test_study_path"]


def make_practice(db, child_id, subject="Sachunterricht"):
    unit = LearningUnit(child_id=child_id, subject=subject, topic="Künstlich", explanation="Künstlich",
                        questions=[{"id": "evidence", "type": "short", "prompt": "Test?", "answer": "ja",
                                    "options": [], "accepted": [], "hints": [], "explanation": "Test."}],
                        status="paused", provider="fixture", synthetic=False)
    db.add(unit)
    db.flush()
    return unit.id


def add_attempt(db, unit_id):
    db.add(Attempt(unit_id=unit_id, question_id="evidence", answer="KÜNSTLICHE PRIVATANTWORT",
                   outcome="incorrect", assisted=False, evaluation={"attempt_number": 1}))
    db.flush()


def test_auto_change_during_call_preserves_paid_usage_and_existing_evidence(study, stage_transport, monkeypatch):
    with DB.begin() as db:
        previous = make_practice(db, study["child"]["id"])
    arm_automatic_rounds(study)
    def changed():
        with DB.begin() as db:
            add_attempt(db, previous)
    stage_transport["effect"] = changed
    provider = study_path.request_provider
    def paid(*args, **kwargs):
        value = provider(*args, **kwargs)
        value.cost_micros, value.cost_source = 1234, "reported"
        return value
    monkeypatch.setattr(study_path, "request_provider", paid)
    assert advance_auto_rounds(study["day_id"])
    job_id = finish()
    with DB() as db:
        job = db.get(Job, job_id)
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        assert job.status == "failed" and "Lernstand" in job.error
        assert usage.status == "failed_billed" and usage.cost_micros == 1234
        assert db.scalar(select(func.count()).select_from(LearningUnit)) == 1
        assert db.scalar(select(func.count()).select_from(Attempt)) == 1
        assert "automatic_evidence_observation" not in job.payload
    assert len(stage_transport["calls"]) == 1
    advance_auto_rounds(study["day_id"])
    assert not advance_auto_rounds(study["day_id"])
    assert len(stage_transport["calls"]) == 1


def test_auto_sibling_evidence_does_not_invalidate_or_expose_marker(api, study, stage_transport):
    sibling = create_child(api, study["parent"], username="evidence-sibling")
    with DB.begin() as db:
        other = make_practice(db, sibling["id"])
    arm_automatic_rounds(study)
    def changed():
        with DB.begin() as db:
            add_attempt(db, other)
    stage_transport["effect"] = changed
    assert advance_auto_rounds(study["day_id"])
    job_id = finish()
    with DB() as db:
        job = db.get(Job, job_id)
        assert job.status == "completed", job.error
        marker, unit_id = job.payload["automatic_evidence_observation"]["marker"], job.result["unit_id"]
        assert marker.keys() == {"version", "digest"}
    for endpoint in (f"/api/jobs/{job_id}", f"/api/units/{unit_id}", path(study)):
        response = study["client"].get(endpoint)
        assert response.status_code == 200
        assert marker["digest"] not in response.text and "automatic_evidence_observation" not in response.text
    assert "automatic_evidence_observation" not in json.dumps(stage_transport["calls"])


def test_manual_round_does_not_gain_automatic_evidence_guard(study, stage_transport):
    with DB.begin() as db:
        other = make_practice(db, study["child"]["id"])
    response = study["client"].post(path(study))
    assert response.status_code == 200
    block = response.json()["next_block_id"]
    def changed():
        with DB.begin() as db:
            add_attempt(db, other)
    stage_transport["effect"] = changed
    assert generate(study, block).status_code == 202
    job_id = finish()
    with DB() as db:
        job = db.get(Job, job_id)
        assert job.status == "completed", job.error
        assert "automatic_evidence_observation" not in job.payload


def test_legacy_auto_job_without_flag_keeps_original_behavior(study, stage_transport):
    with DB.begin() as db:
        prior = make_practice(db, study["child"]["id"])
    arm_automatic_rounds(study)
    assert advance_auto_rounds(study["day_id"])
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == "study_block", Job.status == "queued"))
        assert job is not None
        job.payload = {key: value for key, value in job.payload.items() if key != "automatic_study_stage"}

    def changed():
        with DB.begin() as db:
            add_attempt(db, prior)

    stage_transport["effect"] = changed
    job_id = finish()
    with DB() as db:
        job = db.get(Job, job_id)
        assert job.status == "completed", job.error
        assert "automatic_evidence_observation" not in job.payload
        assert db.scalar(select(func.count()).select_from(Attempt)) == 1


def test_auto_change_while_payload_is_built_does_not_call_provider(study, stage_transport, monkeypatch):
    from schulpilot import learning_evidence_marker

    with DB.begin() as db:
        previous = make_practice(db, study["child"]["id"])
    real_snapshot = learning_evidence_marker.snapshot
    count = 0

    def snapshot_then_answer(db, child_id, subject, **kwargs):
        nonlocal count
        marker = real_snapshot(db, child_id, subject, **kwargs)
        count += 1
        if count == 1:
            with DB.begin() as other:
                add_attempt(other, previous)
        return marker

    monkeypatch.setattr(learning_evidence_marker, "snapshot", snapshot_then_answer)
    arm_automatic_rounds(study)
    assert advance_auto_rounds(study["day_id"])
    job_id = finish()
    with DB() as db:
        job = db.get(Job, job_id)
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        assert job.status == "failed" and "Lernstand" in job.error
        assert usage.status == "failed_not_sent" and usage.cost_micros == 0
        assert db.scalar(select(func.count()).select_from(Attempt)) == 1
    assert stage_transport["calls"] == []
