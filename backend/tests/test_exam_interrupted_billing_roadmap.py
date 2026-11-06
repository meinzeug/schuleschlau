"""Artificial exam deletion preserves unknown costs of dispatched calls."""
import uuid

import pytest
from schulpilot import exam_review
from schulpilot.db import DB, Job, Usage
from sqlalchemy import select
from test_exam_reviews import paper, transport  # noqa: F401  (pytest fixtures)


@pytest.mark.parametrize('path', ['analysis', 'practice'])
@pytest.mark.parametrize('state', ['queued', 'running'])
def test_exam_cancellation_settles_once_without_assuming_running_call_is_free(paper, path, state):  # noqa: F811
    with DB.begin() as db:
        payload = {'exam_id': paper['exam_id']} if path == 'analysis' else {
            'exam_review_practice': {'exam_id': paper['exam_id']}}
        job = Job(child_id=paper['child_id'], kind='exam_review' if path == 'analysis' else 'unit',
                  payload=payload, status=state, idempotency=uuid.uuid4().hex)
        db.add(job)
        db.flush()
        job_id = job.id
        usage = Usage(family_id=paper['parent']['families'][0]['id'], child_id=paper['child_id'], job_id=job_id,
                      provider='openrouter', model='synthetic/model', config_revision=1, function='unit',
                      status='reserved', reserved_micros=1000, bucket_ids=[])
        db.add(usage)
    for _ in range(2):
        with DB.begin() as db:
            if path == 'analysis':
                exam_review.cancel_jobs(db, paper['exam_id'])
            else:
                exam_review.purge_exam_review(db, paper['exam_id'])
    with DB() as db:
        job = db.get(Job, job_id)
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        assert job.status == 'failed' and usage.settlement_version == 1
        if state == 'running':
            assert usage.status == 'failed_unknown' and usage.cost_micros is None
            assert usage.reserved_micros == 1000
        else:
            assert usage.cost_micros == 0


def test_running_exam_provider_result_after_source_cancellation_stays_discarded(paper, transport):  # noqa: F811
    import threading

    from schulpilot.worker import claim
    from test_exam_reviews import analyze

    job_id = analyze(paper)['id']
    with DB() as db:
        assert claim(db) == job_id
    entered, resume = threading.Event(), threading.Event()
    errors = []
    def blocked_call():
        entered.set()
        assert resume.wait(20)
    transport['effect'] = blocked_call
    def run():
        try:
            exam_review.process(job_id)
        except BaseException as error:
            errors.append(error)
    thread = threading.Thread(target=run)
    thread.start()
    try:
        assert entered.wait(20)
        with DB.begin() as db:
            exam_review.cancel_jobs(db, paper['exam_id'])
    finally:
        resume.set()
        thread.join(30)
    assert not thread.is_alive() and not errors and len(transport['calls']) == 1
    with DB() as db:
        job = db.get(Job, job_id)
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        assert job.status == 'failed' and job.result is None
        assert usage.status == 'failed_unknown' and usage.settlement_version == 1
        assert usage.cost_micros is None and usage.reserved_micros > 0
