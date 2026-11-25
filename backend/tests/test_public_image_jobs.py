"""Artificial public catalogue and controlled provider; no real child or call."""
import base64
import copy
import io
import json
from uuid import uuid4

import pytest
from PIL import Image
from schulpilot.catalog_models import CatalogContent, CatalogMembership, CatalogState
from schulpilot.db import DB, Job, LearningUnit, ProviderConfig, Usage, now
from schulpilot.public_image_contract import parse_response
from schulpilot.public_image_jobs import process
from schulpilot.public_image_models import PublicImage, PublicImageBuild
from sqlalchemy import select
from test_learning_assets import prepared as prepared
from test_round_ready_notifications import case as case


@pytest.fixture
def image_case(api, prepared, case, monkeypatch):
    _, child, _ = prepared
    with DB.begin() as db:
        db.add(CatalogState(provider="test", snapshot_id="public-artificial-v1"))
        db.add(CatalogContent(id="artificial:bee", title="Öffentliche Tierkunde",
            url="https://example.org/public", content_type="article", title_verified=True,
            data={}, snapshot_id="public-artificial-v1"))
        db.add(CatalogMembership(topic_id="artificial-mathematik", content_id="artificial:bee",
            url="https://example.org/public", curated=True, data={}, snapshot_id="public-artificial-v1"))
        db.get(LearningUnit, case["unit"]).topic = "Öffentliche Tierkunde"
        config = db.get(ProviderConfig, 1)
        policy = copy.deepcopy(config.routing_policy)
        image = copy.deepcopy(policy["routes"]["sol"])
        image.update(model="test/image-model", upstreams=["azure"], image_capable=False,
            image_output_budget={"version": 1, "basis": "operator_estimate", "model": "test/image-model",
                "upstream": "azure", "input_tokens": 200, "output_tokens": 2000,
                "evidence": "Artificial operator allowance for testing only", "approved_at": int(now())})
        policy["routes"]["image"] = image
        config.routing_policy = policy
    output = io.BytesIO()
    Image.new("RGB", (80, 80), "blue").save(output, "PNG")
    data = {"data": [{"b64_json": base64.b64encode(output.getvalue()).decode()}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 100, "cost": 0.003}}
    receipt = parse_response(json.dumps(data).encode())
    calls = []
    def request(client, prompt, **kwargs):
        calls.append((prompt, kwargs))
        return receipt
    monkeypatch.setattr("schulpilot.public_image_jobs.request_resolved_image", request)
    return case, child, calls


def start(api, case, key=None):
    return api.post('/api/units/' + case['unit'] + '/public-image', headers={'Idempotency-Key': key or uuid4().hex})


def test_reserved_image_is_reusable_without_private_data_or_duplicate_call(api, image_case):
    case, child, calls = image_case
    url = '/api/units/' + case['unit'] + '/public-image'
    assert api.get(url).json()['status'] == 'missing'
    key = uuid4().hex
    response = start(api, case, key)
    assert response.status_code == 202, response.text
    assert response.json()['status'] == 'queued'
    assert start(api, case, key).json()['status'] == 'queued'
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image'))
        usage = db.scalar(select(Usage).where(Usage.job_id == job.id))
        assert usage.model == 'test/image-model' and usage.status == 'reserved'
        job.status = 'running'
        jid = job.id
    process(jid)
    assert api.get(url).json()['status'] == 'ready'
    image = api.get(url + '/file')
    assert image.status_code == 200 and image.headers['content-type'] == 'image/png'
    assert image.content.startswith(b'\x89PNG')
    assert len(calls) == 1
    assert child['id'] not in calls[0][0] and case['material'] not in calls[0][0]
    with DB() as db:
        assert db.scalar(select(Usage).where(Usage.job_id == jid)).cost_micros == 3000
        assert db.get(Job, jid).status == 'completed'
        assert db.query(PublicImage).count() == 1
        assert db.query(PublicImageBuild).count() == 1
    trace = api.get(f'/api/jobs/{jid}/trace')
    assert trace.status_code == 200
    assert trace.json()['phase'] == 'visual' and trace.json()['status'] == 'completed'
    assert trace.json()['model']['model'] == 'test/image-model'
    assert trace.json()['sources'] == []
    assert 'Öffentliche Tierkunde' not in trace.text and 'b64_json' not in trace.text
    assert start(api, case).json()['status'] == 'ready'
    assert len(calls) == 1


def test_unit_completion_automatically_reserves_one_public_image(api, image_case, monkeypatch):
    from schulpilot.public_image_jobs import prepare_missing_unit_image

    case, _, calls = image_case
    monkeypatch.setattr('schulpilot.visual_references.projection', lambda db, unit: {
        'explanation_visual_status': 'incomplete', 'explanation_visual_reason': 'missing_steps'})
    assert prepare_missing_unit_image(case['job']) == 'queued'
    assert prepare_missing_unit_image(case['job']) == 'queued'
    with DB.begin() as db:
        jobs = list(db.scalars(select(Job).where(Job.kind == 'public_image')))
        assert len(jobs) == 1
        job = jobs[0]
        job.status = 'running'
        jid = job.id
    process(jid)
    assert prepare_missing_unit_image(case['job']) == 'ready'
    assert len(calls) == 1


def test_unit_completion_never_creates_image_after_logout(api, image_case, monkeypatch):
    from schulpilot.db import Session
    from schulpilot.providers import ProviderError
    from schulpilot.public_image_jobs import prepare_missing_unit_image

    case, _, calls = image_case
    monkeypatch.setattr('schulpilot.visual_references.projection', lambda db, unit: {
        'explanation_visual_status': 'incomplete', 'explanation_visual_reason': 'missing_steps'})
    with DB.begin() as db:
        db.get(Session, case['session']).revoked = True
    with pytest.raises(ProviderError):
        prepare_missing_unit_image(case['job'])
    with DB() as db:
        assert db.query(Job).filter(Job.kind == 'public_image').count() == 0
    assert not calls


def test_automatic_image_error_never_falls_back_to_another_paid_job(monkeypatch):
    from schulpilot import learning_assets, public_image_jobs, worker

    calls = []
    def fail(_):
        raise RuntimeError('synthetic failure')
    monkeypatch.setattr(public_image_jobs, 'prepare_missing_unit_image', fail)
    monkeypatch.setattr(learning_assets, 'prepare_missing_unit_visual', lambda job: calls.append(job))
    worker.prepare_public_visuals('synthetic-job')
    assert calls == []
    monkeypatch.setattr(public_image_jobs, 'prepare_missing_unit_image', lambda _: None)
    worker.prepare_public_visuals('synthetic-job')
    assert calls == ['synthetic-job']


def test_revoked_session_discards_result_and_preserves_billed_cost(api, image_case, monkeypatch):
    from schulpilot.db import Session
    case, _, calls = image_case
    assert start(api, case).status_code == 202
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image'))
        job.status = 'running'
        jid = job.id
    original = __import__('schulpilot.public_image_jobs', fromlist=['request_resolved_image']).request_resolved_image
    def revoke(*args, **kwargs):
        response = original(*args, **kwargs)
        with DB.begin() as db:
            db.get(Session, case['session']).revoked = True
        return response
    monkeypatch.setattr('schulpilot.public_image_jobs.request_resolved_image', revoke)
    process(jid)
    with DB() as db:
        assert db.get(Job, jid).status == 'failed'
        assert db.scalar(select(Usage).where(Usage.job_id == jid)).cost_micros == 3000
        assert db.query(PublicImage).count() == 0
        assert db.query(PublicImageBuild).one().status == 'failed'


def test_invalid_billed_image_is_not_published_or_treated_as_free(api, image_case, monkeypatch):
    from schulpilot.public_image_contract import ImageContractError

    case, _, _ = image_case
    assert start(api, case).status_code == 202
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image'))
        job.status = 'running'
        jid = job.id
    def invalid(*args, **kwargs):
        raise ImageContractError('image_invalid', {'cost_micros': 3000, 'input_tokens': 5,
            'output_tokens': 100, 'cost_source': 'reported', 'telemetry': {}})
    monkeypatch.setattr('schulpilot.public_image_jobs.request_resolved_image', invalid)
    process(jid)
    with DB() as db:
        usage = db.scalar(select(Usage).where(Usage.job_id == jid))
        assert db.get(Job, jid).error_code == 'invalid_output'
        assert usage.status == 'failed_billed' and usage.cost_micros == 3000
        assert db.query(PublicImage).count() == 0
        before = db.query(Job).count(), db.query(Usage).count(), db.query(PublicImage).count()
    for _ in range(2):
        trace = api.get(f'/api/jobs/{jid}/trace')
        assert trace.status_code == 200
        assert trace.json()['phase'] == 'visual' and trace.json()['error_code'] == 'invalid_output'
        assert trace.json()['sources'] == [] and 'b64_json' not in trace.text
    with DB() as db:
        assert (db.query(Job).count(), db.query(Usage).count(), db.query(PublicImage).count()) == before


def test_missing_image_route_never_falls_back_or_books(api, image_case):
    case, _, calls = image_case
    with DB.begin() as db:
        config = db.get(ProviderConfig, 1)
        policy = copy.deepcopy(config.routing_policy)
        del policy['routes']['image']
        config.routing_policy = policy
    assert api.get('/api/units/' + case['unit'] + '/public-image').json()['status'] == 'unavailable'
    response = start(api, case)
    assert response.status_code == 503
    with DB() as db:
        assert db.query(PublicImageBuild).count() == 0
        assert db.query(Job).filter(Job.kind == 'public_image').count() == 0
    assert calls == []


def test_cached_image_remains_available_when_generation_route_is_removed(api, image_case):
    case, _, _ = image_case
    assert start(api, case).status_code == 202
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image'))
        job.status = 'running'
        jid = job.id
    process(jid)
    with DB.begin() as db:
        config = db.get(ProviderConfig, 1)
        policy = copy.deepcopy(config.routing_policy)
        del policy['routes']['image']
        config.routing_policy = policy
    path = '/api/units/' + case['unit'] + '/public-image'
    assert api.get(path).json()['status'] == 'ready'
    assert api.get(path + '/file').status_code == 200


def test_image_estimated_cost_must_be_covered_by_reservation(api, image_case):
    case, _, calls = image_case
    with DB.begin() as db:
        config = db.get(ProviderConfig, 1)
        policy = copy.deepcopy(config.routing_policy)
        policy['routes']['image']['image_output_budget']['output_tokens'] = 1_000_000
        config.routing_policy = policy
    response = start(api, case)
    assert response.status_code == 503
    with DB() as db:
        assert db.query(Job).filter(Job.kind == 'public_image').count() == 0
    assert calls == []


def test_unverified_image_route_does_not_offer_or_start_generation(api, image_case):
    case, _, calls = image_case
    with DB.begin() as db:
        config = db.get(ProviderConfig, 1)
        policy = copy.deepcopy(config.routing_policy)
        policy['routes']['image']['verified_at'] = int(now()) - 32 * 86400
        config.routing_policy = policy
    path = '/api/units/' + case['unit'] + '/public-image'
    assert api.get(path).json()['status'] == 'unavailable'
    assert start(api, case).status_code == 503
    assert calls == []


def test_curated_focus_has_priority_over_public_content(api, image_case, monkeypatch):
    from schulpilot import public_image_jobs

    case, _, _ = image_case
    monkeypatch.setattr(public_image_jobs, 'public_focus_for_unit', lambda *_: 'public-focus')
    seen = []
    def resolved(db, selector):
        seen.append(selector)
        return {'subject': selector.subject, 'selector': selector.model_dump()}, 'public prompt'
    monkeypatch.setattr(public_image_jobs, 'public_prompt', resolved)
    with DB() as db:
        selector, _ = public_image_jobs.unit_spec(db, db.get(LearningUnit, case['unit']))
    assert selector['public_focus_id'] == 'public-focus'
    assert selector['catalog_content_id'] is None


def test_generic_honeybee_unit_uses_only_public_curated_focus(api, image_case):
    from schulpilot.catalog_models import CatalogTopic
    from schulpilot.learning_assets import profile_subjects

    case, _, calls = image_case
    with DB.begin() as db:
        biology = profile_subjects(db)['Biologie']
        db.add(CatalogTopic(id='sofatutor:topic:5690', subject_id=biology.id, title='Insekten',
            entry_url='https://example.org/insects', search_text='insects', empty_curated=True,
            data={}, snapshot_id='public-artificial-v1'))
        unit = db.get(LearningUnit, case['unit'])
        unit.subject, unit.topic = 'Biologie', 'Bienen: Merkmale und Eigenschaften'
    assert start(api, case).status_code == 202
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image'))
        job.status = 'running'
        jid = job.id
    process(jid)
    assert api.get('/api/units/' + case['unit'] + '/public-image').json()['status'] == 'ready'
    assert len(calls) == 1 and 'Honigbiene' in calls[0][0]
    assert 'Merkmale und Eigenschaften' not in calls[0][0]


def test_late_billed_receipt_does_not_publish_or_reopen_job(api, image_case, monkeypatch):
    from schulpilot.providers import settle
    from schulpilot.public_image_contract import ImageReceipt

    case, _, _ = image_case
    assert start(api, case).status_code == 202
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image'))
        job.status = 'running'
        jid = job.id
    original = __import__('schulpilot.public_image_jobs', fromlist=['request_resolved_image']).request_resolved_image
    def interrupted(*args, **kwargs):
        value = original(*args, **kwargs)
        with DB.begin() as db:
            job = db.get(Job, jid)
            job.status = 'failed'
            settle(db, db.scalar(select(Usage).where(Usage.job_id == jid)), failed=True)
        return ImageReceipt(value.png, value.width, value.height, {**value.billing,
            'telemetry': {'generation_id': 'gen-test-image', 'billed_usd': '0.003'}})
    monkeypatch.setattr('schulpilot.public_image_jobs.request_resolved_image', interrupted)
    process(jid)
    with DB() as db:
        usage = db.scalar(select(Usage).where(Usage.job_id == jid))
        assert db.get(Job, jid).status == 'failed' and db.query(PublicImage).count() == 0
        assert usage.status == 'failed_unknown' and usage.telemetry['generation_id'] == 'gen-test-image'
        assert usage.telemetry['late_cost_hint_micros'] == 3000


def test_other_family_cannot_read_or_request_a_unit_image(api, image_case, mailbox):
    from conftest import HEADERS, register
    from fastapi.testclient import TestClient
    from schulpilot.main import app

    case, _, calls = image_case
    with TestClient(app, headers=HEADERS) as other:
        register(other, mailbox, email='different-parent@example.org')
        path = '/api/units/' + case['unit'] + '/public-image'
        assert other.get(path).status_code in (403, 404)
        assert other.post(path, headers={'Idempotency-Key': uuid4().hex}).status_code in (403, 404, 409)
        assert other.get(path + '/file').status_code in (403, 404)
    assert calls == []


def test_different_family_reuses_same_public_picture_after_authorization(api, image_case, mailbox):
    from conftest import HEADERS, create_child, register
    from fastapi.testclient import TestClient
    from schulpilot.main import app
    from schulpilot.synthetic import sample_unit

    case, _, calls = image_case
    assert start(api, case).status_code == 202
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image'))
        job.status = 'running'
        jid = job.id
    process(jid)
    with TestClient(app, headers=HEADERS) as other:
        parent = register(other, mailbox, email='other-public-picture@example.org')
        second_child = create_child(other, parent, username='another-artificial-child')
        other.headers['X-Schulpilot-Account'] = parent['id']
        with DB.begin() as db:
            unit = LearningUnit(child_id=second_child['id'], synthetic=False, provider='synthetic-test', **sample_unit())
            unit.topic = 'Öffentliche Tierkunde'
            db.add(unit)
            db.flush()
            second_id = unit.id
        path = '/api/units/' + second_id + '/public-image'
        assert other.get(path).json()['status'] == 'ready'
        assert other.get(path + '/file').content.startswith(b'\x89PNG')
        assert other.post(path, headers={'Idempotency-Key': uuid4().hex}).json()['status'] == 'ready'
    assert len(calls) == 1


def test_two_families_concurrently_claim_only_one_paid_public_image(api, image_case, mailbox):
    from concurrent.futures import ThreadPoolExecutor

    from conftest import HEADERS, create_child, register
    from fastapi.testclient import TestClient
    from schulpilot.db import engine
    from schulpilot.main import app
    from schulpilot.synthetic import sample_unit

    if engine.dialect.name != 'postgresql':
        pytest.skip('Requires concurrent PostgreSQL transactions')
    case, _, _ = image_case
    with TestClient(app, headers=HEADERS) as other:
        parent = register(other, mailbox, email='racing-picture@example.org')
        second_child = create_child(other, parent, username='racing-image-child')
        other.headers['X-Schulpilot-Account'] = parent['id']
        with DB.begin() as db:
            unit = LearningUnit(child_id=second_child['id'], synthetic=False, provider='synthetic-test', **sample_unit())
            unit.topic = 'Öffentliche Tierkunde'
            db.add(unit)
            db.flush()
            second_id = unit.id
        with ThreadPoolExecutor(max_workers=2) as pool:
            one = pool.submit(start, api, case)
            two = pool.submit(other.post, '/api/units/' + second_id + '/public-image',
                              headers={'Idempotency-Key': uuid4().hex})
            responses = [one.result(), two.result()]
        assert all(r.status_code == 202 for r in responses), [r.text for r in responses]
        assert all(r.json()['status'] == 'queued' for r in responses)
    with DB() as db:
        assert db.query(Job).filter(Job.kind == 'public_image').count() == 1
        job = db.scalar(select(Job).where(Job.kind == 'public_image'))
        assert db.query(Usage).filter(Usage.job_id == job.id).count() == 1


def test_retry_is_explicit_and_bounded(api, image_case, monkeypatch):
    from schulpilot.public_image_contract import ImageContractError

    case, _, calls = image_case
    def fail(*args, **kwargs):
        raise ImageContractError('provider_transport')
    monkeypatch.setattr('schulpilot.public_image_jobs.request_resolved_image', fail)
    path = '/api/units/' + case['unit'] + '/public-image'
    key = uuid4().hex
    for index in range(2):
        response = start(api, case, key if index == 0 else uuid4().hex)
        assert response.status_code == 202, response.text
        with DB.begin() as db:
            job = db.scalar(select(Job).where(Job.kind == 'public_image', Job.status == 'queued'))
            job.status = 'running'
            jid = job.id
        process(jid)
        value = api.get(path).json()
        assert value['status'] == 'failed' and value['retry_allowed'] is (index == 0)
        if index == 0:
            assert start(api, case, key).json()['status'] == 'failed'
    assert start(api, case).status_code == 409
    assert calls == []


def test_opt_in_live_synthetic_image_through_reserved_job(api, image_case, monkeypatch):
    """Explicit paid probe; disposable test DB and fixed public data only."""
    import os
    from pathlib import Path

    import httpx
    from schulpilot.config import settings
    from schulpilot.market_data import parse_image_prices
    from schulpilot.public_image_contract import request_resolved_image

    if os.getenv('RUN_PUBLIC_IMAGE_PAID_PROBE') != '1':
        pytest.skip('Explicit paid synthetic probe only')
    assert os.getenv('ENVIRONMENT') == 'test' and str(settings.database_url).startswith('sqlite:///')
    key = (Path.home() / 'or.txt').read_text().strip()
    # Frozen runtime settings are restored by the per-test fixture. Avoid
    # assertion/traceback representations that could expose the credential.
    object.__setattr__(settings, 'openrouter_api_key', key)
    model, upstream = 'microsoft/mai-image-2.7-flash', 'azure'
    with httpx.Client(timeout=20) as client:
        meta = client.get('https://openrouter.ai/api/v1/images/models/' + model + '/endpoints').json()
        rates = parse_image_prices(meta, model, [upstream])
        zdr = client.get('https://openrouter.ai/api/v1/endpoints/zdr', headers={'Authorization': 'Bearer ' + key}).json()
        assert (model, upstream) in {(row['model_id'], row['tag']) for row in zdr['data']}
    with DB.begin() as db:
        config = db.get(ProviderConfig, 1)
        policy = copy.deepcopy(config.routing_policy)
        route = policy['routes']['image']
        route.update(model=model, upstreams=[upstream], input_per_million_micros=rates['prompt'],
            output_per_million_micros=rates['completion'], reserve_micros=100000,
            image_output_budget={'version': 1, 'basis': 'operator_estimate', 'model': model, 'upstream': upstream,
                'input_tokens': 500, 'output_tokens': 3000, 'approved_at': int(now()),
                'evidence': 'Artificial probe allowance; no API hard output-token limit'})
        config.routing_policy = policy
    monkeypatch.setattr('schulpilot.public_image_jobs.request_resolved_image', request_resolved_image)
    case, _, _ = image_case
    response = start(api, case)
    assert response.status_code == 202, response.text
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image'))
        usage = db.scalar(select(Usage).where(Usage.job_id == job.id))
        assert usage.model == model and usage.status == 'reserved'
        job.status = 'running'
        jid = job.id
    process(jid)
    with DB() as db:
        job = db.get(Job, jid)
        usage = db.scalar(select(Usage).where(Usage.job_id == jid))
        assert job.status == 'completed', job.error
        assert usage.cost_micros is not None and usage.cost_source == 'reported'
        print('synthetic public image billed USD micros:', usage.cost_micros)
    path = '/api/units/' + case['unit'] + '/public-image'
    assert api.get(path).json()['status'] == 'ready'
    assert api.get(path + '/file').content.startswith(b'\x89PNG')
