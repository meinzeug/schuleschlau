"""Synthetic PostgreSQL stale-worker publication race; no external calls."""
import threading

import pytest
from schulpilot import school_preparation, worker
from schulpilot.db import DB, Attempt, Job, LearningUnit, Usage, engine
from schulpilot.providers import Result
from sqlalchemy import func, select
from test_package_parts_worker import artificial_day, bounded_output, preparation, snapshot


@pytest.mark.skipif(engine.dialect.name != 'postgresql', reason='real row locking requires PostgreSQL')
def test_interrupted_package_never_publishes_a_late_provider_result(api, household, monkeypatch):
    day_id, _, old = artificial_day(api, household)
    before_return, resume = threading.Event(), threading.Event()
    observed = []

    def provider(config, function, payload, image_bytes=None, *, synthetic_fixture=False):
        observed.append(payload['package_partition'])
        return Result(bounded_output(payload), 20, 40, 101, cost_source='reported')

    original = worker.job_config
    def gate(db, job, *args, **kwargs):
        if observed and not before_return.is_set():
            before_return.set()
            assert resume.wait(20)
        return original(db, job, *args, **kwargs)

    monkeypatch.setattr(worker, 'request_provider', provider)
    monkeypatch.setattr(worker, 'job_config', gate)
    preparation(api, day_id, 'interrupted-race-first')
    school_preparation.advance_one()
    with DB() as db:
        job_id = worker.claim(db)
    assert job_id
    with DB.begin() as db:
        db.get(Job, job_id).started = 1
    errors = []
    def run():
        try:
            worker.process(job_id)
        except BaseException as error:
            errors.append(error)
    thread = threading.Thread(target=run)
    thread.start()
    try:
        assert before_return.wait(20)
        worker.maintenance()
    finally:
        resume.set()
        thread.join(30)
    assert not thread.is_alive() and not errors
    school_preparation.advance_one()
    with DB() as db:
        job = db.get(Job, job_id)
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        assert job.status == 'failed' and job.error_code == 'interrupted'
        assert usage.status == 'failed_unknown' and usage.cost_micros is None
        assert usage.reserved_micros > 0 and usage.settlement_version == 1
        assert db.scalar(select(func.count()).select_from(LearningUnit)) == 1
        assert db.get(Attempt, old['attempt']).answer == 'Künstliche Altantwort'
    assert snapshot(day_id).get('package_outputs', {}) == {}
    assert observed == [0]


@pytest.mark.skipif(engine.dialect.name != 'postgresql', reason='real row locking requires PostgreSQL')
def test_completed_package_wins_over_an_already_selected_reaper(api, household, monkeypatch):
    from sqlalchemy import event

    day_id, _, _ = artificial_day(api, household)
    selected, resume = threading.Event(), threading.Event()
    results, errors = [], []
    monkeypatch.setattr(worker, 'request_provider', lambda config, function, payload, image_bytes=None,
        *, synthetic_fixture=False: Result(bounded_output(payload), 20, 40, 101, cost_source='reported'))
    preparation(api, day_id, 'finished-before-reaper')
    school_preparation.advance_one()
    with DB() as db:
        job_id = worker.claim(db)
    with DB.begin() as db:
        db.get(Job, job_id).started = 1

    def pause_reaper(conn, cursor, statement, parameters, context, executemany):
        if threading.current_thread().name == 'synthetic-reaper' and statement.lstrip().upper().startswith('UPDATE JOBS'):
            selected.set()
            assert resume.wait(20)

    def reap():
        try:
            results.append(worker.reap_interrupted())
        except BaseException as error:
            errors.append(error)

    event.listen(engine, 'before_cursor_execute', pause_reaper)
    thread = threading.Thread(target=reap, name='synthetic-reaper')
    thread.start()
    try:
        assert selected.wait(20)
        worker.process(job_id)
    finally:
        resume.set()
        thread.join(30)
        event.remove(engine, 'before_cursor_execute', pause_reaper)
    assert not thread.is_alive() and not errors and results == [0]
    with DB() as db:
        job = db.get(Job, job_id)
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        assert job.status == 'completed' and job.error_code is None
        assert usage.status == 'completed' and usage.cost_micros == 101 and usage.settlement_version == 1
    school_preparation.advance_one()
    assert '0' in snapshot(day_id)['package_outputs']


@pytest.mark.parametrize('winner', ['failed', 'completed'])
def test_optimistic_job_status_rolls_back_other_changes_for_every_orm_worker(api, household, winner):
    from sqlalchemy.orm.exc import StaleDataError

    day_id, _, old = artificial_day(api, household)
    preparation(api, day_id, 'worker-state-guard')
    school_preparation.advance_one()
    with DB() as db:
        job_id = worker.claim(db)
    with DB() as late:
        job = late.get(Job, job_id)
        assert job.status == 'running'
        with DB.begin() as winning:
            winning.get(Job, job_id).status = winner
        late.get(Attempt, old['attempt']).answer = 'Unzulässige verspätete Änderung'
        job.status = 'completed' if winner == 'failed' else 'failed'
        with pytest.raises(StaleDataError):
            late.commit()
        late.rollback()
    with DB() as db:
        assert db.get(Job, job_id).status == winner
        assert db.get(Attempt, old['attempt']).answer == 'Künstliche Altantwort'


def test_late_failed_provider_does_not_replace_the_interruption(api, household, monkeypatch):
    from schulpilot.providers import ProviderError

    day_id, _, old = artificial_day(api, household)
    in_call, resume = threading.Event(), threading.Event()
    calls, errors = [], []
    def provider(*args, **kwargs):
        calls.append(1)
        in_call.set()
        assert resume.wait(20)
        raise ProviderError('Künstlicher verspäteter Anbieterfehler', code='provider_unavailable')
    monkeypatch.setattr(worker, 'request_provider', provider)
    preparation(api, day_id, 'late-error-after-interruption')
    school_preparation.advance_one()
    with DB() as db:
        job_id = worker.claim(db)
    with DB.begin() as db:
        db.get(Job, job_id).started = 1
    def run():
        try:
            worker.process(job_id)
        except BaseException as error:
            errors.append(error)
    thread = threading.Thread(target=run)
    thread.start()
    try:
        assert in_call.wait(20)
        assert worker.reap_interrupted() == 1
    finally:
        resume.set()
        thread.join(30)
    assert not thread.is_alive() and not errors and calls == [1]
    with DB() as db:
        job = db.get(Job, job_id)
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        assert job.status == 'failed' and job.error_code == 'interrupted'
        assert 'verspäteter Anbieterfehler' not in job.error
        assert usage.status == 'failed_unknown' and usage.cost_micros is None
        assert usage.reserved_micros > 0 and usage.settlement_version == 1
        assert db.get(Attempt, old['attempt']).answer == 'Künstliche Altantwort'
    assert snapshot(day_id).get('package_outputs', {}) == {}


def test_retry_never_reactivates_an_interrupted_job(api, household, monkeypatch):
    day_id, _, _ = artificial_day(api, household)
    requests = []
    monkeypatch.setattr(worker, 'request_provider', lambda config, function, payload, image_bytes=None,
        *, synthetic_fixture=False: requests.append(payload['package_partition']) or
        Result(bounded_output(payload), 20, 40, 101, cost_source='reported'))
    preparation(api, day_id, 'original-before-interruption')
    school_preparation.advance_one()
    with DB() as db:
        original = worker.claim(db)
    with DB.begin() as db:
        db.get(Job, original).started = 1
    assert worker.reap_interrupted() == 1
    school_preparation.advance_one()
    with DB() as db:
        assert worker.claim(db) is None
    preparation(api, day_id, 'explicit-new-job-after-interruption')
    school_preparation.advance_one()
    with DB() as db:
        replacement = worker.claim(db)
    assert replacement and replacement != original
    worker.process(replacement)
    assert requests == [0]
    with DB() as db:
        old_job, new_job = db.get(Job, original), db.get(Job, replacement)
        assert old_job.status == 'failed' and old_job.error_code == 'interrupted'
        assert new_job.status == 'completed'
        old_usage = db.scalar(select(Usage).where(Usage.job_id == original))
        assert old_usage.status == 'failed_unknown' and old_usage.settlement_version == 1


def test_covered_noop_package_settles_only_after_completion_and_never_calls_provider(api, household, monkeypatch):
    from schulpilot import school_day

    day_id, _, old = artificial_day(api, household)
    preparation(api, day_id, 'covered-sources-noop')
    school_preparation.advance_one()
    with DB() as db:
        job_id = worker.claim(db)
    assert job_id
    monkeypatch.setattr(school_day, 'package_plan', lambda *args: {'groups': []})
    monkeypatch.setattr(worker, 'request_provider', lambda *a, **kw: pytest.fail('No-op must not dispatch provider'))
    with DB.begin() as db:
        assert school_preparation.defer_package(db, db.get(Job, job_id), before_call=True)
    assert worker.reap_interrupted(cutoff=2_000_000_000) == 0
    with DB() as db:
        job = db.get(Job, job_id)
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        assert job.status == 'completed' and job.result['deferred'] is True
        assert usage.settlement_version == 1 and usage.cost_micros == 0
        assert db.get(Attempt, old['attempt']).answer == 'Künstliche Altantwort'
