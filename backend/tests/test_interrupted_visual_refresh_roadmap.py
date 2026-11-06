"""Real status reload race against the isolated visual worker."""
import threading

import pytest
from sqlalchemy import select
from schulpilot import visual_jobs, worker
from schulpilot.db import DB, Job, Attempt, engine
from schulpilot.visual_reference_models import UnitVisualSnapshot
from test_visual_jobs import generated_visual_unit, legacy, start  # noqa: F401


@pytest.mark.skipif(engine.dialect.name != 'postgresql', reason='real row locking requires PostgreSQL')
def test_expired_job_is_rechecked_before_a_late_graphic_is_published(api, legacy, monkeypatch):
    unit_id, _, _, calls = legacy
    job_id = start(api, unit_id).json()['id']
    with DB.begin() as db:
        job = db.get(Job, job_id)
        job.status, job.started = 'running', 1
    entered, resume = threading.Event(), threading.Event()
    original, seen, errors = visual_jobs.authority, [], []
    def authority(db, job):
        seen.append(1)
        if len(seen) == 2:
            entered.set()
            assert resume.wait(20)
        return original(db, job)
    monkeypatch.setattr(visual_jobs, 'authority', authority)
    def run():
        try:
            visual_jobs.process(job_id)
        except BaseException as error:
            errors.append(error)
    thread = threading.Thread(target=run)
    thread.start()
    try:
        assert entered.wait(20)
        assert worker.reap_interrupted() == 1
    finally:
        resume.set()
        thread.join(30)
    assert not thread.is_alive() and not errors
    with DB() as db:
        job = db.get(Job, job_id)
        assert job.status == 'failed' and job.error_code == 'interrupted'
        assert db.get(UnitVisualSnapshot, unit_id) is None
        assert db.scalar(select(Attempt).where(Attempt.unit_id == unit_id)).answer == '1/3'
    assert len(calls['provider']) == 1
