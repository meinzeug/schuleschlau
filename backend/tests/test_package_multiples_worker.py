"""Actual queued package worker and transport; artificial source and mock HTTP."""
import json

import httpx
import pytest
from package_output_helpers import PackageOutputCapture
from schulpilot import package_multiples_sequence as sequence
from schulpilot import providers, school_preparation, worker
from schulpilot.db import DB, Job, LearningUnit, Material, SchoolDay, Session, Usage
from schulpilot.visual_reference_models import UnitVisualSnapshot
from sqlalchemy import select
from test_package_multiples_sequence import SOURCE
from test_package_parts_worker import preparation
from test_package_prepared_graphics import wire_step
from test_package_transport import config
from test_school_preparation_parts import make_day
from test_unconfirmed_deletion import child_client


@pytest.mark.parametrize('fault', [None, 'changed_source', 'revoked_session', 'concurrent_question', 'wrong_answer'])
def test_real_worker_saves_only_current_source_bound_round(api, household, monkeypatch, fault):
    day_id = make_day(household, count=1)
    with DB.begin() as db:
        page = db.scalar(select(Material).where(Material.school_day_id == day_id))
        page.subject, page.topic, page.content = 'Mathematik', 'Vielfache', SOURCE
    preparation(api, day_id, 'synthetic-multiples-worker')
    with DB() as db:
        job_id = worker.claim(db)
    assert job_id
    capture, real_client, calls, encoded = PackageOutputCapture(monkeypatch), httpx.Client, [], {}

    def handler(request):
        body = json.loads(request.content)
        outgoing = json.loads(body['messages'][1]['content'][0]['text'])
        assert sequence.HISTORY not in outgoing
        if fault in ('changed_source', 'revoked_session', 'concurrent_question'):
            with DB.begin() as db:
                job, day = db.get(Job, job_id), db.get(SchoolDay, day_id)
                if fault == 'changed_source':
                    page = db.scalar(select(Material).where(Material.school_day_id == day_id))
                    page.content += '\nKünstliche Änderung.'
                    page.revision += 1
                elif fault == 'revoked_session':
                    db.get(Session, day.preparation['session_id']).revoked = True
                else:
                    db.add(LearningUnit(child_id=job.child_id, subject='Mathematik', topic='Synthetisch',
                        explanation='', provider='synthetic-test', questions=[{
                            'prompt': encoded['output']['units'][0]['questions'][0]['prompt']}]))
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {
            'content': json.dumps(capture.wire(encoded['output']), ensure_ascii=False)}}],
            'usage': {'prompt_tokens': 111, 'completion_tokens': 2223, 'cost': 0.0321}})

    monkeypatch.setattr(providers.httpx, 'Client', lambda **kw: real_client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(providers, 'external_allowed', lambda *a, **kw: None)
    monkeypatch.setattr(providers, 'decrypt', lambda _: 'synthetic-no-network-key')

    def request_provider(_config, function, payload, image_bytes=None, *, synthetic_fixture=False):
        calls.append(function)
        intro, *questions = sequence.compile_candidates(payload)
        encoded['output'] = {'units': [{'group_id': intro['group_id'], 'subject': 'Mathematik',
            'topic': 'Vielfache', 'explanation': intro['text'], 'explanation_steps': [wire_step(intro)],
            'questions': [{**row['question_core'], 'hints': ['Zähle in gleichen Schritten.'],
                'explanation': row['text'], 'presentation': None, 'field_group': None,
                'explanation_steps': [wire_step(row)]} for row in questions]}]}
        if fault == 'wrong_answer':
            encoded['output']['units'][0]['questions'][0]['answer'] = '999'
        value = config()
        value.max_output_tokens, value.reserve_micros = 8000, 250000
        with monkeypatch.context() as patch:
            patch.setattr('schulpilot.model_routing.selection', lambda _: {'route': {'upstreams': ['azure']}, 'region': 'standard'})
            return providers.request_provider(value, function, payload, image_bytes, synthetic_fixture=synthetic_fixture)

    monkeypatch.setattr(worker, 'request_provider', request_provider)
    worker.process(job_id)
    with DB() as db:
        job = db.get(Job, job_id)
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        assert calls == ['package'], (job.error_code, job.error)
        if fault:
            assert job.status == 'failed' and usage.status == 'failed_billed'
            assert db.query(LearningUnit).filter(LearningUnit.school_day_id == day_id).count() == 0
            return
        assert job.status == 'completed', (job.error_code, job.error)
        assert usage.status == 'completed' and usage.cost_micros == 32100
    school_preparation.advance_one()
    with DB() as db:
        unit = db.scalar(select(LearningUnit).where(LearningUnit.school_day_id == day_id))
        assert unit is not None and len(unit.questions) == 2
        assert db.get(UnitVisualSnapshot, unit.id).status == 'ready'
        unit_id = unit.id
    with child_client() as kid:
        response = kid.get('/api/units/' + unit_id,
                           headers={'X-Schulpilot-Capabilities': 'visual-v1,learning-entry-v1'})
        assert response.status_code == 200, response.text
        for question in response.json()['questions']:
            assert 'answer' not in question and 'hints' not in question and 'explanation' not in question
            assert not question['explanation_steps']
