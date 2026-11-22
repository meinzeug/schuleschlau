"""Persisted synthetic worker + real adapter/codec; HTTP is mocked."""
import json

import httpx
import pytest
from package_output_helpers import PackageOutputCapture
from sqlalchemy import select
from schulpilot import providers, school_preparation, worker
from schulpilot.db import DB, Job, LearningUnit, Material, SchoolDay, Session, Usage
from schulpilot.visual_reference_models import UnitVisualSnapshot
from test_package_fraction_plan_groundwork import EXPAND, REDUCE
from test_package_fraction_provider import model_output
from test_package_fraction_reservation import running_job
from test_package_transport import config


@pytest.mark.parametrize('content', [EXPAND, REDUCE])
@pytest.mark.parametrize(('mode', 'fault'), [('default', None), ('default', 'wrong_answer'),
    ('default', 'revoked_session'), ('default', 'changed_source'), ('default', 'concurrent_question'),
    ('source_probe', None), ('reuse_evidence', None), ('source_only', None)])
def test_worker_reserves_before_provider_and_checks_before_publication(api, household, monkeypatch, content, mode, fault):
    day_id, job_id, _ = running_job(api, household, content)
    if mode != 'default':
        import copy
        from schulpilot import learning_entry
        original_entry = learning_entry.with_learning_entry
        def entry_without_fixed_probe(*args, **kwargs):
            result = original_entry(*args, **kwargs)
            entry = copy.deepcopy(result['learning_entry'])
            entry['units'][0]['entry_mode'] = 'source_probe' if mode == 'source_only' else mode
            entry['units'][0]['probes'] = []
            if mode == 'source_only':
                entry['units'][0]['allocation_version'] = 1
            entry['references'] = []
            return {**result, 'learning_entry': entry}
        monkeypatch.setattr(learning_entry, 'with_learning_entry', entry_without_fixed_probe)
    capture, real_client, seen, encoded = PackageOutputCapture(monkeypatch), httpx.Client, [], {}
    def handler(request):
        body = json.loads(request.content)
        from schulpilot.graphic_table_transport import nesting_depth
        assert nesting_depth(body['response_format']['json_schema']['schema']) <= 10
        outgoing = json.loads(body['messages'][1]['content'][0]['text'])
        assert 'package_fraction_plan' not in outgoing and 'excluded_values' not in json.dumps(outgoing)
        value = encoded['output']
        if fault in ('revoked_session', 'changed_source', 'concurrent_question'):
            with DB.begin() as db:
                job = db.get(Job, job_id)
                day = db.get(SchoolDay, day_id)
                if fault == 'revoked_session':
                    db.get(Session, day.preparation['session_id']).revoked = True
                elif fault == 'changed_source':
                    page = db.scalar(select(Material).where(Material.school_day_id == day_id))
                    page.content += ' Geänderte Quelle.'
                    page.revision += 1
                else:
                    prompt = next(row['task']['prompt'] for row in seen[0]['slots'] if row['task'])
                    db.add(LearningUnit(child_id=job.child_id, subject='Mathematik', topic='Künstlich',
                        explanation='', provider='synthetic-test', questions=[{'prompt': prompt}]))
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {
            'content': json.dumps(capture.wire(value), ensure_ascii=False)}}],
            'usage': {'prompt_tokens': 111, 'completion_tokens': 2223, 'cost': 0.0321}})
    monkeypatch.setattr(providers.httpx, 'Client', lambda **kw: real_client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(providers, 'external_allowed', lambda *a, **kw: None)
    monkeypatch.setattr(providers, 'decrypt', lambda _: 'synthetic-no-network-key')
    def request_provider(_config, function, payload, image_bytes=None, *, synthetic_fixture=False):
        with DB() as db:
            stored = db.get(Job, job_id).payload.get('package_fraction_plan')
        assert stored == payload['package_fraction_plan'] == payload['visual_context']['package_fraction_plan']
        seen.append(stored)
        encoded['output'] = model_output(payload)
        if fault == 'wrong_answer':
            question = next(q for q in encoded['output']['units'][0]['questions'] if q['id'] in
                            {r['task']['id'] for r in stored['slots'] if r['task']})
            question['answer'] = '1/99'
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
        assert len(seen) == 1, (job.error_code, job.error)
        if fault:
            assert job.status == 'failed' and usage.status == 'failed_billed'
            assert db.query(LearningUnit).filter(LearningUnit.school_day_id == day_id).count() == 0
            assert job.payload['package_fraction_plan'] == seen[0]
            return
        assert job.status == 'completed', (job.error_code, job.error)
        assert usage.status == 'completed' and usage.cost_micros == 32100
        receipt = db.get(SchoolDay, day_id).preparation['package_outputs']['0']
        assert receipt['context']['visual_context']['package_fraction_plan'] == seen[0]
    school_preparation.advance_one()
    with DB() as db:
        unit = db.scalar(select(LearningUnit).where(LearningUnit.school_day_id == day_id))
        assert unit is not None
        snapshot = db.get(UnitVisualSnapshot, unit.id)
        assert snapshot.status == 'ready'
        task_ids = [row['task']['id'] for row in seen[0]['slots'] if row['task']]
        if mode == 'source_only':
            assert not task_ids
        else:
            assert all(len(snapshot.question_steps[task_id][0]['presentation']['blocks']) == 2 for task_id in task_ids)
