"""Synthetic automatic stage interruption; no actual provider or FCM calls."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from schulpilot import notifications, ready_notifications, school_preparation, study_path, worker
from schulpilot.db import DB, Job, Message, Usage, engine
from sqlalchemy import func, select
from test_automatic_evidence_guard import add_attempt, make_practice
from test_notebook_practice import stored_learning_evidence
from test_study_path import arm_automatic_rounds

pytest_plugins = ["test_study_path"]


def queued(study):
    with DB.begin() as db:
        prior = make_practice(db, study["child"]["id"])
        add_attempt(db, prior)
    evidence = stored_learning_evidence()
    arm_automatic_rounds(study)
    assert school_preparation.advance_auto_rounds(study["day_id"])
    with DB() as db:
        job_id = worker.claim(db)
    assert job_id
    with DB.begin() as db:
        job = db.get(Job, job_id)
        assert job.kind == "study_block" and job.status == "running"
        job.started = 1
        counts = tuple(db.scalar(select(func.count()).select_from(model)) for model in (Job, Usage))
    return job_id, evidence, counts


def check_interrupted(study, job_id, evidence, counts, calls):
    for _ in range(3):
        school_preparation.advance_auto_rounds(study["day_id"])
        worker.process(job_id)
        ready_notifications.advance_one()
        assert worker.reap_interrupted() == 0
    with DB() as db:
        job = db.get(Job, job_id)
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        assert job.status == "failed" and job.error_code == "interrupted"
        assert usage.status == "failed_unknown" and usage.cost_micros is None
        assert usage.reserved_micros > 0 and usage.settlement_version == 1
        assert tuple(db.scalar(select(func.count()).select_from(model)) for model in (Job, Usage)) == counts
        assert db.scalar(select(func.count()).select_from(Message).where(Message.kind == "round_ready")) == 0
    assert stored_learning_evidence() == evidence
    assert len(calls) <= 1


def test_repeated_recovery_of_interrupted_auto_stage_never_retries(study, stage_transport, monkeypatch):
    monkeypatch.setattr(notifications, "send_fcm", lambda *_a, **_k: pytest.fail("Unexpected FCM"))
    job_id, evidence, counts = queued(study)
    assert worker.reap_interrupted() == 1
    check_interrupted(study, job_id, evidence, counts, stage_transport["calls"])
    assert stage_transport["calls"] == []


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="PostgreSQL real lock ordering")
def test_reaper_wins_during_auto_stage_final_publication(study, stage_transport, monkeypatch):
    monkeypatch.setattr(notifications, "send_fcm", lambda *_a, **_k: pytest.fail("Unexpected FCM"))
    job_id, evidence, counts = queued(study)
    reached, proceed = Event(), Event()
    original = study_path.job_context
    def gate(db, job):
        if stage_transport["calls"]:
            reached.set()
            assert proceed.wait(15)
        return original(db, job)
    monkeypatch.setattr(study_path, "job_context", gate)
    with ThreadPoolExecutor(max_workers=1) as pool:
        task = pool.submit(worker.process, job_id)
        try:
            assert reached.wait(15)
            assert worker.reap_interrupted() == 1
        finally:
            proceed.set()
        task.result(timeout=15)
    assert len(stage_transport["calls"]) == 1
    check_interrupted(study, job_id, evidence, counts, stage_transport["calls"])


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="PostgreSQL real lock ordering")
def test_completed_auto_stage_wins_against_preselected_reaper(study, stage_transport, monkeypatch):
    import threading

    from sqlalchemy import event

    monkeypatch.setattr(notifications, "send_fcm", lambda *_a, **_k: pytest.fail("Unexpected FCM"))
    job_id, evidence, counts = queued(study)
    provider = study_path.request_provider
    def synthetic_cost(*args, **kwargs):
        result = provider(*args, **kwargs)
        result.cost_micros, result.cost_source = 123, "reported"
        return result
    monkeypatch.setattr(study_path, "request_provider", synthetic_cost)
    selected, proceed = Event(), Event()
    reaped, errors = [], []
    def gate(_conn, _cursor, statement, _parameters, _context, _executemany):
        if threading.current_thread().name == "auto-stage-reaper" and statement.lstrip().upper().startswith("UPDATE JOBS"):
            selected.set()
            assert proceed.wait(15)
    def reap():
        try:
            reaped.append(worker.reap_interrupted())
        except BaseException as error:
            errors.append(error)
    event.listen(engine, "before_cursor_execute", gate)
    thread = threading.Thread(target=reap, name="auto-stage-reaper")
    thread.start()
    try:
        assert selected.wait(15)
        worker.process(job_id)
    finally:
        proceed.set()
        thread.join(15)
        event.remove(engine, "before_cursor_execute", gate)
    assert not thread.is_alive() and not errors and reaped == [0]
    assert len(stage_transport["calls"]) == 1
    assert school_preparation.advance_auto_rounds(study["day_id"])
    worker.process(job_id)
    assert worker.reap_interrupted() == 0
    ready_notifications.advance_one()
    with DB() as db:
        job = db.get(Job, job_id)
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        assert job.status == "completed" and job.result["unit_id"]
        assert usage.status == "completed" and usage.cost_micros == 123 and usage.settlement_version == 1
        assert tuple(db.scalar(select(func.count()).select_from(model)) for model in (Job, Usage)) == counts
        assert db.scalar(select(func.count()).select_from(Message).where(Message.kind == "round_ready")) == 1
    actual = stored_learning_evidence()
    for model in ("learning_units", "attempts", "unit_sources"):
        assert all(row in actual[model] for row in evidence[model])
    assert len(stage_transport["calls"]) == 1
