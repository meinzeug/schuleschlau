"""An explicit unit request cannot outlive its submitting session or family access."""

import pytest
from conftest import HEADERS
from fastapi.testclient import TestClient
from schulpilot import worker
from schulpilot.db import DB, Job, LearningUnit, Membership, Session, Usage, UsageBucket
from schulpilot.main import app
from schulpilot.providers import Result
from schulpilot.synthetic import sample_unit
from sqlalchemy import func, select
from test_learning_entry import source as source_fixture
from test_model_routing import setup_policy


@pytest.fixture
def source(api, household):
    return source_fixture.__wrapped__(api, household)


@pytest.mark.parametrize('when', ['before', 'after'])
@pytest.mark.parametrize('fault', ['revoked', 'membership'])
@pytest.mark.parametrize('provider_cost', [None, 2000])
def test_original_unit_submission_authority_is_rechecked(api, source, monkeypatch, when, fault, provider_cost):
    parent, child, mid = source
    family_id = parent['families'][0]['id']
    setup_policy(family_id)
    created = api.post(f"/api/children/{child['id']}/units", json={'material_id': mid},
                       headers={'Idempotency-Key': 'unit-authority-private-source'})
    assert created.status_code == 202, created.text
    job_id = created.json()['id']
    def change():
        with DB.begin() as db:
            job = db.get(Job, job_id)
            origin = job.payload['completion_origin']
            if fault == 'revoked':
                db.get(Session, origin['session_id']).revoked = True
            else:
                membership = db.scalar(select(Membership).where(Membership.user_id == origin['user_id'],
                                                                Membership.family_id == family_id))
                db.delete(membership)
    calls = []
    def transport(*args, **kwargs):
        calls.append(True)
        if when == 'after':
            change()
        return Result(sample_unit(), 10, 20, provider_cost, cost_source='reported' if provider_cost is not None else 'unknown')
    monkeypatch.setattr(worker, 'request_provider', transport)
    if when == 'before':
        change()
    with DB() as db:
        assert worker.claim(db) == job_id
    worker.process(job_id)
    assert len(calls) == (when == 'after')
    with DB() as db:
        job = db.get(Job, job_id)
        assert job.status == 'failed' and 'Anmeldung' in job.error
        assert db.scalar(select(func.count()).select_from(LearningUnit)) == 0
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        assert usage.settlement_version == 1
        assert usage.cost_micros == (0 if when == 'before' else provider_cost)
        bucket = db.get(UsageBucket, usage.bucket_ids[0])
        assert bucket.encumbered_micros == (usage.reserved_micros if when == 'after' and provider_cost is None
                                           else (provider_cost if when == 'after' else 0))
        assert bucket.unknown_calls == int(when == 'after' and provider_cost is None)


@pytest.mark.parametrize('legacy', [False, True])
def test_valid_and_legacy_unit_jobs_keep_their_existing_contract(api, source, monkeypatch, legacy):
    parent, child, mid = source
    setup_policy(parent['families'][0]['id'])
    created = api.post(f"/api/children/{child['id']}/units", json={'material_id': mid},
                       headers={'Idempotency-Key': 'valid-and-old-unit-submission'})
    assert created.status_code == 202, created.text
    job_id = created.json()['id']
    if legacy:
        with DB.begin() as db:
            job = db.get(Job, job_id)
            job.payload = {key: value for key, value in job.payload.items() if key != 'completion_origin'}
    calls = []
    def transport(*args, **kwargs):
        calls.append(True)
        return Result(sample_unit(), 10, 20, None)
    monkeypatch.setattr(worker, 'request_provider', transport)
    with DB() as db:
        assert worker.claim(db) == job_id
    worker.process(job_id)
    with DB() as db:
        assert db.get(Job, job_id).status == 'completed'
        assert db.scalar(select(func.count()).select_from(LearningUnit)) == 1
    assert calls == [True]


def test_invalid_recorded_origin_is_not_treated_as_legacy(api, source, monkeypatch):
    parent, child, mid = source
    setup_policy(parent['families'][0]['id'])
    created = api.post(f"/api/children/{child['id']}/units", json={'material_id': mid},
                       headers={'Idempotency-Key': 'invalid-unit-submission-origin'})
    assert created.status_code == 202, created.text
    job_id = created.json()['id']
    with DB.begin() as db:
        job = db.get(Job, job_id)
        job.payload = {**job.payload, 'completion_origin': None}
    calls = []
    monkeypatch.setattr(worker, 'request_provider', lambda *args, **kwargs: calls.append(True))
    with DB() as db:
        assert worker.claim(db) == job_id
    worker.process(job_id)
    assert calls == []
    with DB() as db:
        assert db.get(Job, job_id).status == 'failed'


@pytest.mark.parametrize('when', ['before', 'after'])
def test_child_session_revoked_before_or_during_unit_generation(source, monkeypatch, when):
    parent, child, mid = source
    setup_policy(parent['families'][0]['id'])
    with TestClient(app, headers=HEADERS) as client:
        login = client.post('/api/auth/login', json={'username': child['username'], 'password': 'secure-child-pass-123'})
        assert login.status_code == 200, login.text
        client.headers['Authorization'] = 'Bearer ' + login.json()['token']
        response = client.post(f"/api/children/{child['id']}/units", json={'material_id': mid},
                               headers={'Idempotency-Key': 'child-unit-session-revoked'})
        assert response.status_code == 202, response.text
        job_id = response.json()['id']
    def revoke():
        with DB.begin() as db:
            origin = db.get(Job, job_id).payload['completion_origin']
            db.get(Session, origin['session_id']).revoked = True
    calls = []
    def transport(*args, **kwargs):
        calls.append(True)
        if when == 'after':
            revoke()
        return Result(sample_unit(), 10, 20, None)
    monkeypatch.setattr(worker, 'request_provider', transport)
    if when == 'before':
        revoke()
    with DB() as db:
        assert worker.claim(db) == job_id
    worker.process(job_id)
    with DB() as db:
        assert db.get(Job, job_id).status == 'failed'
        assert db.scalar(select(func.count()).select_from(LearningUnit)) == 0
    assert len(calls) == (when == 'after')
