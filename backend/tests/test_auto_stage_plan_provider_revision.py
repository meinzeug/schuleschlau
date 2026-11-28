"""Synthetic automatic stage must not publish stale plans or provider config."""

import pytest
from schulpilot import notifications, study_path, worker
from schulpilot.db import DB, Child, Job, Message, ProviderConfig, SchoolDay, Usage
from schulpilot.school_preparation import advance_auto_rounds
from sqlalchemy import func, select
from test_automatic_evidence_guard import add_attempt, make_practice
from test_notebook_practice import stored_learning_evidence
from test_study_path import arm_automatic_rounds, finish

pytest_plugins = ["test_study_path"]


@pytest.mark.parametrize("changed", ["parent_plan", "provider_revision"])
@pytest.mark.parametrize("when", ["before", "during"])
def test_auto_stage_aborts_when_plan_or_provider_revision_changes(study, stage_transport, monkeypatch, changed, when):
    # All provider responses and accounting values are synthetic and local.
    def forbidden(*_args, **_kwargs):
        pytest.fail("A notification must not send FCM")
    monkeypatch.setattr(notifications, "send_fcm", forbidden)
    with DB.begin() as db:
        prior = make_practice(db, study["child"]["id"])
        add_attempt(db, prior)
    saved = stored_learning_evidence()
    arm_automatic_rounds(study)
    assert advance_auto_rounds(study["day_id"])
    with DB() as db:
        job = db.scalar(select(Job).where(Job.kind == "study_block"))
        assert job and job.status == "queued"
        job_id = job.id
        before = tuple(db.scalar(select(func.count()).select_from(model)) for model in (Job, Usage))

    def change():
        with DB.begin() as db:
            if changed == "parent_plan":
                child = db.get(Child, study["child"]["id"])
                child.preferences = {**child.preferences, "daily_minutes": 45}
            else:
                db.get(ProviderConfig, 1).revision += 1
    if when == "before":
        change()
    else:
        stage_transport["effect"] = change
    provider = study_path.request_provider
    def synthetic_cost(*args, **kwargs):
        result = provider(*args, **kwargs)
        result.cost_micros, result.cost_source = 1234, "reported"
        return result
    monkeypatch.setattr(study_path, "request_provider", synthetic_cost)
    assert finish() == job_id
    assert len(stage_transport["calls"]) == (0 if when == "before" else 1)
    with DB() as db:
        job = db.get(Job, job_id)
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        assert job.status == "failed"
        assert usage.status == ("failed_not_sent" if when == "before" else "failed_billed")
        assert usage.cost_micros == (0 if when == "before" else 1234)
    assert stored_learning_evidence() == saved
    for _ in range(3):
        advance_auto_rounds(study["day_id"])
        worker.process(job_id)
    with DB() as db:
        assert db.get(Job, job_id).status == "failed"
        assert db.get(SchoolDay, study["day_id"]).preparation["auto_rounds"]["status"] == "blocked"
        assert tuple(db.scalar(select(func.count()).select_from(model)) for model in (Job, Usage)) == before
        assert db.scalar(select(func.count()).select_from(Message).where(Message.kind == "round_ready")) == 0
    assert len(stage_transport["calls"]) == (0 if when == "before" else 1)
    assert stored_learning_evidence() == saved
