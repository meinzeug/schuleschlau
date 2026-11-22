"""Separate public image review; no real child and no provider call."""
from uuid import uuid4
import pytest
from sqlalchemy import select
from schulpilot.db import DB, Job, Usage
from schulpilot.providers import Result
from schulpilot.public_image_jobs import process as create_image
from schulpilot.public_image_models import PublicImageReview
from schulpilot.public_image_review import enqueue_after_image, process as review_image
from test_learning_assets import prepared  # noqa: F401
from test_round_ready_notifications import case  # noqa: F401
from test_public_image_jobs import image_case, start  # noqa: F401


def generated(api, image_case):
    case, _, _ = image_case
    assert start(api, case).status_code == 202
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image'))
        job.status = 'running'
        creator = job.id
    create_image(creator)
    return case, creator


def test_auto_review_is_one_separately_reserved_public_job(api, image_case, monkeypatch):
    case, creator = generated(api, image_case)
    enqueue_after_image(creator)
    enqueue_after_image(creator)
    with DB.begin() as db:
        rows = list(db.scalars(select(Job).where(Job.kind == 'public_image_review')))
        assert len(rows) == 1
        review = rows[0]
        assert db.scalar(select(Usage).where(Usage.job_id == review.id)).status == 'reserved'
        review.status = 'running'
        jid = review.id
    calls = []
    def fake(client, config, image, public_input, **kwargs):
        calls.append((config.model, image.model, public_input))
        return Result({'verdict': 'consistent', 'observations': ['Sichtbar'], 'limitations': ['KI-Meinung']},
                      15, 20, 1000, cost_source='reported')
    monkeypatch.setattr('schulpilot.public_image_review.request_review', fake)
    review_image(jid)
    data = api.get('/api/units/' + case['unit'] + '/public-image').json()
    assert data['status'] == 'ready' and data['review_status'] == 'approved'
    assert data['review_reference_available'] is False
    assert calls[0][0] != calls[0][1]
    assert set(calls[0][2]) == {'subject', 'topic', 'public_facts', 'reference_available'}
    with DB() as db:
        assert db.get(Job, jid).status == 'completed'
        assert db.scalar(select(Usage).where(Usage.job_id == jid)).cost_micros == 1000
        row = db.scalar(select(PublicImageReview))
        assert row.status == 'approved' and row.reviewer_model == calls[0][0]


def test_rejected_review_hides_image_and_never_claims_mastery(api, image_case, monkeypatch):
    case, creator = generated(api, image_case)
    enqueue_after_image(creator)
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image_review'))
        job.status = 'running'; jid = job.id
    monkeypatch.setattr('schulpilot.public_image_review.request_review', lambda *a, **kw:
        Result({'verdict': 'incorrect', 'observations': ['Widerspruch'], 'limitations': []}, 1, 2, 1000, cost_source='reported'))
    review_image(jid)
    path = '/api/units/' + case['unit'] + '/public-image'
    value = api.get(path).json()
    assert value['status'] == 'missing' and value['review_status'] == 'rejected'
    assert value['image_rejected'] is True and value['retry_allowed'] is True
    assert api.get(path + '/file').status_code == 404
    assert start(api, case).json()['status'] == 'queued'


def test_review_failure_is_honest_and_retry_requires_explicit_action(api, image_case, monkeypatch):
    case, creator = generated(api, image_case)
    enqueue_after_image(creator)
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image_review'))
        job.status = 'running'; jid = job.id
    from schulpilot.providers import ProviderError
    def fail(*a, **kw):
        raise ProviderError('Prüfung fehlgeschlagen', code='provider_unavailable')
    monkeypatch.setattr('schulpilot.public_image_review.request_review', fail)
    review_image(jid)
    path = '/api/units/' + case['unit'] + '/public-image'
    assert api.get(path).json()['review_status'] == 'unavailable'
    with DB() as db:
        job = db.get(Job, jid)
        assert job.error_code == 'provider_unavailable'
        assert job.error == 'Die Bildprüfung konnte nicht abgeschlossen werden.'
        usage = db.scalar(select(Usage).where(Usage.job_id == jid))
        assert usage.status == 'failed_unknown' and usage.cost_micros is None
    enqueue_after_image(creator)
    with DB() as db:
        assert db.query(Job).filter_by(kind='public_image_review').count() == 1
    response = api.post(path + '/review', headers={'Idempotency-Key': uuid4().hex})
    assert response.status_code == 202 and response.json()['review_status'] == 'pending'
    with DB() as db:
        assert db.query(Job).filter_by(kind='public_image_review').count() == 2


def test_provider_review_sends_only_public_topic_and_pinned_vision(api, image_case, monkeypatch):
    import json
    import httpx
    from schulpilot.db import ProviderConfig
    from schulpilot.model_routing import select_route, selection
    from schulpilot.public_image_jobs import unit_spec
    from schulpilot.public_image_catalog import find_current
    from schulpilot.public_image_review_contract import public_review_input, request_review
    from schulpilot.providers import external_allowed

    case, _ = generated(api, image_case)
    with DB() as db:
        from schulpilot.db import LearningUnit
        selector, _ = unit_spec(db, db.get(LearningUnit, case['unit']))
        image = find_current(db, selector)
        _, value = public_review_input(db, selector, image)
        config = select_route(db.get(ProviderConfig, 1), 'public_image_review')
        route = selection(config)
        db.expunge(image)
    requests = []
    def handle(request):
        body = json.loads(request.content)
        requests.append(body)
        assert request.url.host == 'openrouter.ai'
        assert body['model'] == config.model and body['model'] != image.model
        assert body['provider']['only'] == route['route']['upstreams']
        assert body['provider']['data_collection'] == 'deny' and body['provider']['zdr'] is True
        assert body['provider']['allow_fallbacks'] is False
        text = body['messages'][1]['content'][0]['text']
        assert case['child'] not in text and case['unit'] not in text
        assert json.loads(text) == value
        assert body['messages'][1]['content'][1]['image_url']['url'].startswith('data:image/jpeg;base64,')
        return httpx.Response(200, json={'id': 'gen-test-001', 'choices': [{'finish_reason': 'stop',
            'message': {'content': json.dumps({'verdict': 'consistent', 'observations': ['Passt'], 'limitations': ['Keine Garantie']})}}],
            'usage': {'prompt_tokens': 9, 'completion_tokens': 8, 'cost': 0.001}}, request=request)
    monkeypatch.setattr('schulpilot.providers.external_allowed', lambda *args, **kwargs: None)
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        result = request_review(client, config, image, value, token='SYNTHETIC-NOT-A-REAL-KEY', route=route)
    assert result.data['verdict'] == 'consistent' and result.cost_micros == 1000
    assert len(requests) == 1


def test_billed_provider_error_is_settled_once_with_closed_category(api, image_case, monkeypatch):
    from schulpilot.providers import ProviderError
    _, creator = generated(api, image_case)
    enqueue_after_image(creator)
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image_review'))
        job.status = 'running'; jid = job.id
    receipt = Result({}, 9, 0, 1000, cost_source='reported',
                     telemetry={'provider_error_code': 429, 'error_type': 'rate_limit_exceeded'})
    def fail(*args, **kwargs):
        raise ProviderError('PRIVATE provider content', code='provider_busy', billing_result=receipt)
    monkeypatch.setattr('schulpilot.public_image_review.request_review', fail)
    review_image(jid)
    review_image(jid)
    with DB() as db:
        job = db.get(Job, jid)
        usage = db.scalar(select(Usage).where(Usage.job_id == jid))
        assert job.status == 'failed' and job.error_code == 'provider_busy'
        assert 'PRIVATE' not in job.error
        assert usage.cost_micros == 1000 and usage.cost_source == 'reported'
        assert usage.settlement_version == 1


def test_review_output_and_late_job_are_not_fabricated(api, image_case, monkeypatch):
    from schulpilot.providers import ProviderError
    case, creator = generated(api, image_case)
    enqueue_after_image(creator)
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image_review'))
        job.status = 'running'; jid = job.id
    def late(*args, **kwargs):
        with DB.begin() as db:
            db.get(Job, jid).status = 'failed'
        return Result({'verdict': 'consistent', 'observations': ['Okay'], 'limitations': []},
                      1, 2, 1000, cost_source='reported', telemetry={'generation_id': 'gen-test-001'})
    monkeypatch.setattr('schulpilot.public_image_review.request_review', late)
    review_image(jid)
    with DB() as db:
        row = db.scalar(select(PublicImageReview))
        assert row.status == 'pending' and row.assessment is None
        assert db.scalar(select(Usage).where(Usage.job_id == jid)).telemetry['late_discarded'] is True
    data = api.get('/api/units/' + case['unit'] + '/public-image').json()
    assert data['review_status'] == 'unavailable' and data['review_request_allowed'] is True


def test_stale_image_hash_or_spec_never_exposes_old_approval(api, image_case, monkeypatch):
    from schulpilot.public_image_models import PublicImage
    case, creator = generated(api, image_case)
    enqueue_after_image(creator)
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image_review'))
        job.status = 'running'; jid = job.id
    monkeypatch.setattr('schulpilot.public_image_review.request_review', lambda *a, **kw:
        Result({'verdict': 'consistent', 'observations': ['Okay'], 'limitations': []}, 1, 2, 1000, cost_source='reported'))
    review_image(jid)
    with DB.begin() as db:
        row = db.scalar(select(PublicImageReview))
        row.image_sha256 = '0' * 64
    data = api.get('/api/units/' + case['unit'] + '/public-image').json()
    assert data['status'] == 'ready' and data['review_status'] == 'unavailable'


def test_unauthorized_family_cannot_review_someone_elses_unit(api, image_case, mailbox):
    from conftest import HEADERS, register
    from fastapi.testclient import TestClient
    from schulpilot.main import app
    case, _ = generated(api, image_case)
    with TestClient(app, headers=HEADERS) as other:
        register(other, mailbox, email='review-other@example.org')
        assert other.post('/api/units/' + case['unit'] + '/public-image/review', headers={'Idempotency-Key': uuid4().hex}).status_code in (403, 404, 409)
    with DB() as db:
        assert db.query(Job).filter_by(kind='public_image_review').count() == 0


def test_uncertain_ai_opinion_never_claims_approval(api, image_case, monkeypatch):
    case, creator = generated(api, image_case)
    enqueue_after_image(creator)
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image_review'))
        job.status = 'running'; jid = job.id
    monkeypatch.setattr('schulpilot.public_image_review.request_review', lambda *a, **kw:
        Result({'verdict': 'uncertain', 'observations': [], 'limitations': ['Nicht sichtbar']}, 1, 2, 1000, cost_source='reported'))
    review_image(jid)
    data = api.get('/api/units/' + case['unit'] + '/public-image').json()
    assert data['review_status'] == 'uncertain' and data['review_request_allowed'] is True


def test_concurrent_families_share_one_review_reservation(api, image_case, mailbox):
    from concurrent.futures import ThreadPoolExecutor
    import pytest
    from conftest import HEADERS, create_child, register
    from fastapi.testclient import TestClient
    from schulpilot.db import engine, LearningUnit
    from schulpilot.main import app
    from schulpilot.synthetic import sample_unit
    if engine.dialect.name != 'postgresql':
        pytest.skip('Requires PostgreSQL row locking')
    case, _ = generated(api, image_case)
    with TestClient(app, headers=HEADERS) as other:
        parent = register(other, mailbox, email='other-review-race@example.org')
        second_child = create_child(other, parent, username='other-review-race')
        other.headers['X-Schulpilot-Account'] = parent['id']
        with DB.begin() as db:
            unit = LearningUnit(child_id=second_child['id'], synthetic=False, provider='synthetic-test', **sample_unit())
            unit.topic = 'Öffentliche Tierkunde'
            db.add(unit); db.flush(); second_id = unit.id
        first = '/api/units/' + case['unit'] + '/public-image/review'
        second = '/api/units/' + second_id + '/public-image/review'
        with ThreadPoolExecutor(max_workers=2) as pool:
            tasks = [pool.submit(api.post, first, headers={'Idempotency-Key': uuid4().hex}),
                     pool.submit(other.post, second, headers={'Idempotency-Key': uuid4().hex})]
            results = [task.result(timeout=15) for task in tasks]
        assert [r.status_code for r in results] == [202, 202]
        assert all(r.json()['review_status'] == 'pending' for r in results)
    with DB() as db:
        rows = list(db.scalars(select(Job).where(Job.kind == 'public_image_review')))
        assert len(rows) == 1
        assert len(list(db.scalars(select(Usage).where(Usage.job_id == rows[0].id)))) == 1


def test_opt_in_live_synthetic_review_through_reserved_job(api, image_case, monkeypatch):
    """Paid one-call probe using a fixed artificial picture and no child material."""
    import os
    import copy
    from pathlib import Path
    import httpx
    import pytest
    from schulpilot.config import settings
    from schulpilot.db import ProviderConfig, now
    from schulpilot.market_data import parse_prices
    if os.getenv('RUN_PUBLIC_IMAGE_REVIEW_PAID_PROBE') != '1':
        pytest.skip('Explicit paid synthetic probe only')
    assert os.getenv('ENVIRONMENT') == 'test' and str(settings.database_url).startswith('sqlite:///')
    token = (Path.home() / 'or.txt').read_text().strip()
    object.__setattr__(settings, 'openrouter_api_key', token)
    model, upstream = 'openai/gpt-6-luna', 'azure'
    with httpx.Client(timeout=20) as client:
        metadata = client.get('https://openrouter.ai/api/v1/models/' + model + '/endpoints').json()
        rates = parse_prices(metadata, model, [upstream])
        zdr = client.get('https://openrouter.ai/api/v1/endpoints/zdr', headers={'Authorization': 'Bearer ' + token}).json()
        assert (model, upstream) in {(r['model_id'], r['tag']) for r in zdr['data']}
    with DB.begin() as db:
        config = db.get(ProviderConfig, 1)
        policy = copy.deepcopy(config.routing_policy)
        route = policy['routes']['luna']
        route.update(model=model, upstreams=[upstream], image_capable=True, verified_at=int(now()),
                     input_per_million_micros=rates['prompt'], output_per_million_micros=rates['completion'],
                     reserve_micros=100000, max_output_tokens=3000,
                     vision_budget={'version': 1, 'basis': 'operator_estimate', 'model': model, 'upstreams': [upstream],
                         'image_tokens': 10000, 'max_side': 3200, 'max_pixels': 4_194_304,
                         'evidence': 'Artificial probe estimate, not an invoice limit', 'approved_at': int(now())})
        config.routing_policy = policy
    _, creator = generated(api, image_case)
    enqueue_after_image(creator)
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image_review'))
        assert db.scalar(select(Usage).where(Usage.job_id == job.id)).status == 'reserved'
        job.status = 'running'; jid = job.id
    review_image(jid)
    with DB() as db:
        job = db.get(Job, jid)
        usage = db.scalar(select(Usage).where(Usage.job_id == jid))
        assert job.status == 'completed', job.error
        assert usage.cost_micros is not None and usage.cost_source == 'reported'
        row = db.scalar(select(PublicImageReview))
        assert row.status in ('approved', 'rejected', 'uncertain')
        print('synthetic independent review billed USD micros:', usage.cost_micros, 'status:', row.status)


def test_backfill_uses_original_authority_once_and_no_automatic_retries(api, image_case, monkeypatch):
    from schulpilot.public_image_review import backfill_one
    case, _ = generated(api, image_case)
    assert backfill_one() is True
    assert backfill_one() is False
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image_review'))
        assert job is not None
        job.status = 'failed'
    assert api.get('/api/units/' + case['unit'] + '/public-image').json()['review_status'] == 'unavailable'
    assert backfill_one() is False
    with DB() as db:
        assert db.query(Job).filter_by(kind='public_image_review').count() == 1


def test_backfill_does_not_use_revoked_original_session(api, image_case):
    from schulpilot.db import Session
    from schulpilot.public_image_review import backfill_one
    case, _ = generated(api, image_case)
    with DB.begin() as db:
        db.get(Session, case['session']).revoked = True
    assert backfill_one() is True
    assert backfill_one() is False
    with DB() as db:
        row = db.scalar(select(PublicImageReview))
        assert row.status == 'unavailable' and row.attempts == 0
        assert db.query(Job).filter_by(kind='public_image_review').count() == 0


def test_review_idempotency_key_cannot_trigger_a_second_attempt(api, image_case, monkeypatch):
    from schulpilot.providers import ProviderError
    case, _ = generated(api, image_case)
    path = '/api/units/' + case['unit'] + '/public-image/review'
    key = uuid4().hex
    assert api.post(path, headers={'Idempotency-Key': key}).json()['review_status'] == 'pending'
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image_review'))
        job.status = 'running'; jid = job.id
    monkeypatch.setattr('schulpilot.public_image_review.request_review', lambda *a, **kw: (_ for _ in ()).throw(ProviderError('Prüfung fehlgeschlagen')))
    review_image(jid)
    assert api.post(path, headers={'Idempotency-Key': key}).json()['review_status'] == 'unavailable'
    with DB() as db:
        assert db.query(Job).filter_by(kind='public_image_review').count() == 1


def test_rejected_image_can_be_replaced_once_without_reusing_bad_picture(api, image_case, monkeypatch):
    import base64, io, json
    from PIL import Image
    from schulpilot.public_image_contract import parse_response
    case, creator = generated(api, image_case)
    enqueue_after_image(creator)
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image_review'))
        job.status = 'running'; jid = job.id
    monkeypatch.setattr('schulpilot.public_image_review.request_review', lambda *a, **kw:
        Result({'verdict': 'incorrect', 'observations': ['Falsch'], 'limitations': []}, 1, 2, 1000, cost_source='reported'))
    review_image(jid)
    data = io.BytesIO(); Image.new('RGB', (80, 80), 'green').save(data, 'PNG')
    receipt = parse_response(json.dumps({'data': [{'b64_json': base64.b64encode(data.getvalue()).decode()}],
        'usage': {'prompt_tokens': 1, 'completion_tokens': 2, 'cost': 0.001}}).encode())
    monkeypatch.setattr('schulpilot.public_image_jobs.request_resolved_image', lambda *a, **kw: receipt)
    assert start(api, case).json()['status'] == 'queued'
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image', Job.status == 'queued'))
        job.status = 'running'; replacement = job.id
    create_image(replacement)
    enqueue_after_image(replacement)
    path = '/api/units/' + case['unit'] + '/public-image'
    value = api.get(path).json()
    assert value['status'] == 'ready' and value['review_status'] == 'pending'
    assert api.get(path + '/file').status_code == 200


def test_revocation_during_review_preserves_cost_without_approval(api, image_case, monkeypatch):
    from schulpilot.db import Session
    case, creator = generated(api, image_case)
    enqueue_after_image(creator)
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image_review'))
        job.status = 'running'; jid = job.id
    def revoke(*args, **kwargs):
        with DB.begin() as db:
            db.get(Session, case['session']).revoked = True
        return Result({'verdict': 'consistent', 'observations': ['Okay'], 'limitations': []},
                      1, 2, 1000, cost_source='reported')
    monkeypatch.setattr('schulpilot.public_image_review.request_review', revoke)
    review_image(jid)
    with DB() as db:
        row = db.scalar(select(PublicImageReview))
        assert row.status == 'unavailable' and row.assessment is None
        assert db.get(Job, jid).status == 'failed'
        assert db.scalar(select(Usage).where(Usage.job_id == jid)).cost_micros == 1000


def test_source_change_during_review_never_approves_old_image(api, image_case, monkeypatch):
    from schulpilot.db import LearningUnit
    case, creator = generated(api, image_case)
    enqueue_after_image(creator)
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image_review'))
        job.status = 'running'; jid = job.id
    def change(*args, **kwargs):
        with DB.begin() as db:
            db.get(LearningUnit, case['unit']).topic = 'Ein anderes Thema'
        return Result({'verdict': 'consistent', 'observations': ['Okay'], 'limitations': []},
                      1, 2, 1000, cost_source='reported')
    monkeypatch.setattr('schulpilot.public_image_review.request_review', change)
    review_image(jid)
    with DB() as db:
        row = db.scalar(select(PublicImageReview))
        assert row.status == 'unavailable' and row.assessment is None
        assert db.get(Job, jid).status == 'failed'
        assert db.scalar(select(Usage).where(Usage.job_id == jid)).cost_micros == 1000


def test_concurrent_backfill_creates_only_one_review_job(api, image_case):
    from concurrent.futures import ThreadPoolExecutor
    import pytest
    from schulpilot.db import engine
    from schulpilot.public_image_review import backfill_one
    if engine.dialect.name != 'postgresql':
        pytest.skip('Requires PostgreSQL row locking')
    generated(api, image_case)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(backfill_one) for _ in range(2)]
        results = [future.result(timeout=15) for future in futures]
    assert results.count(True) == 1
    with DB() as db:
        assert db.query(Job).filter_by(kind='public_image_review').count() == 1
        assert db.query(PublicImageReview).count() == 1


def test_malformed_billed_review_preserves_provider_receipt(monkeypatch):
    import io, json
    from types import SimpleNamespace
    import httpx, pytest
    from PIL import Image
    from schulpilot.providers import ProviderError
    from schulpilot.public_image_review_contract import request_review
    png = io.BytesIO(); Image.new('RGB', (80, 80), 'blue').save(png, 'PNG')
    image = SimpleNamespace(png=png.getvalue(), model='test/image')
    config = SimpleNamespace(provider='openrouter', image_capable=True, model='test/vision', reserve_micros=100000,
        input_per_million_micros=1000, output_per_million_micros=1000, max_output_tokens=2000)
    route = {'region': 'standard', 'route': {'upstreams': ['azure']}}
    value = {'subject': 'Biologie', 'topic': 'Insekten', 'public_facts': '', 'reference_available': False}
    monkeypatch.setattr('schulpilot.providers.external_allowed', lambda *args, **kwargs: None)
    monkeypatch.setattr('schulpilot.provider_cost_preflight.projection', lambda *args: {'projected_micros': 1})
    def malformed(request):
        return httpx.Response(200, request=request, json={'id': 'gen-test-002',
            'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps({'verdict': 'consistent', 'observations': [], 'limitations': []})}}],
            'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'cost': 0.003}})
    with httpx.Client(transport=httpx.MockTransport(malformed)) as client, pytest.raises(ProviderError) as caught:
        request_review(client, config, image, value, token='SYNTHETIC', route=route)
    assert caught.value.billing_result.cost_micros == 3000
    assert caught.value.billing_result.cost_source == 'reported'


@pytest.mark.parametrize(('status', 'expected'), [
    (400, 'not_configured'), (403, 'not_configured'), (429, 'provider_busy'),
    (408, 'provider_timeout'), (504, 'provider_timeout'), (503, 'provider_unavailable'),
])
def test_review_http_errors_are_closed_categories_without_provider_text(monkeypatch, status, expected):
    import io
    from types import SimpleNamespace
    import httpx
    from PIL import Image
    from schulpilot.providers import ProviderError
    from schulpilot.public_image_review_contract import request_review

    png = io.BytesIO(); Image.new('RGB', (80, 80), 'blue').save(png, 'PNG')
    image = SimpleNamespace(png=png.getvalue(), model='test/image')
    config = SimpleNamespace(provider='openrouter', image_capable=True, model='test/vision', reserve_micros=100000,
        input_per_million_micros=1000, output_per_million_micros=1000, max_output_tokens=2000)
    route = {'region': 'standard', 'route': {'upstreams': ['azure']}}
    value = {'subject': 'Biologie', 'topic': 'Insekten', 'public_facts': '', 'reference_available': False}
    monkeypatch.setattr('schulpilot.providers.external_allowed', lambda *args, **kwargs: None)
    monkeypatch.setattr('schulpilot.provider_cost_preflight.projection', lambda *args: {'projected_micros': 1})
    def fail(request):
        return httpx.Response(status, request=request, text='PRIVATE upstream message')
    with httpx.Client(transport=httpx.MockTransport(fail)) as client, pytest.raises(ProviderError) as caught:
        request_review(client, config, image, value, token='SYNTHETIC', route=route)
    assert caught.value.code == expected
    assert 'PRIVATE' not in str(caught.value)
    assert caught.value.billing_result is None


def test_review_http_success_error_keeps_receipt_without_provider_text(monkeypatch):
    import io
    from types import SimpleNamespace
    import httpx
    from PIL import Image
    from schulpilot.providers import ProviderError
    from schulpilot.public_image_review_contract import request_review

    png = io.BytesIO(); Image.new('RGB', (80, 80), 'blue').save(png, 'PNG')
    image = SimpleNamespace(png=png.getvalue(), model='test/image')
    config = SimpleNamespace(provider='openrouter', image_capable=True, model='test/vision', reserve_micros=100000,
        input_per_million_micros=1000, output_per_million_micros=1000, max_output_tokens=2000)
    route = {'region': 'standard', 'route': {'upstreams': ['azure']}}
    value = {'subject': 'Biologie', 'topic': 'Insekten', 'public_facts': '', 'reference_available': False}
    monkeypatch.setattr('schulpilot.providers.external_allowed', lambda *args, **kwargs: None)
    monkeypatch.setattr('schulpilot.provider_cost_preflight.projection', lambda *args: {'projected_micros': 1})
    def error(request):
        return httpx.Response(200, request=request, json={'id': 'gen-test-003',
            'error': {'code': 429, 'message': 'PRIVATE provider message',
                      'metadata': {'error_type': 'rate_limit_exceeded', 'raw': 'PRIVATE raw data'}},
            'usage': {'prompt_tokens': 9, 'completion_tokens': 0, 'cost': 0.001}})
    with httpx.Client(transport=httpx.MockTransport(error)) as client, pytest.raises(ProviderError) as caught:
        request_review(client, config, image, value, token='SYNTHETIC', route=route)
    assert caught.value.code == 'provider_busy'
    assert caught.value.billing_result.cost_micros == 1000
    assert caught.value.billing_result.telemetry['provider_error_code'] == 429
    assert 'PRIVATE' not in str(caught.value.billing_result.telemetry)


def test_worker_dispatches_review_after_successful_image_commit(api, image_case):
    from schulpilot.worker import _process
    case, _, _ = image_case
    assert start(api, case).status_code == 202
    with DB.begin() as db:
        job = db.scalar(select(Job).where(Job.kind == 'public_image'))
        job.status = 'running'; jid = job.id
    _process(jid)
    with DB() as db:
        assert db.get(Job, jid).status == 'completed'
        review = db.scalar(select(Job).where(Job.kind == 'public_image_review'))
        assert review is not None and review.status == 'queued'
        assert db.scalar(select(Usage).where(Usage.job_id == review.id)).status == 'reserved'
