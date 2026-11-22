"""Real provider adapter/codec with synthetic data and mocked HTTP only."""
import copy
import json

import httpx
import pytest
from package_output_helpers import PackageOutputCapture
from schulpilot import package_fraction_plan as planner, package_fraction_reservation as reservation
from schulpilot import package_prepared_graphics, providers
from schulpilot.db import DB
from test_package_fraction_plan_groundwork import EXPAND, REDUCE
from test_package_fraction_reservation import running_job
from test_package_transport import config


def model_output(bound):
    plan = bound['package_fraction_plan']
    candidates = package_prepared_graphics.compile_candidates(bound)
    intro = next(row for row in candidates if row['kind'] == 'fraction' and row['disclosure'] == 'given'
                 and row['reference']['id'] == 'math.fraction.part_whole')
    def standard(row):
        return {'id': 'e1', 'text': row['text'], 'competence_id': None, 'disclosure': row['disclosure'],
                'reference': row['reference'], 'source_refs': row['source_refs'],
                'presentation': {'version': 1, 'evidence_kind': 'knowledge', 'blocks': [row['block']]}}
    questions = []
    used_prior_models = set()
    for row in plan['slots']:
        if row['task'] is None:
            fixed = next((candidate for candidate in candidates if candidate['disclosure'] == 'solution'
                          and candidate.get('question_core', {}).get('id') == row['slot']['id']
                          and candidate['reference']['id'] == 'math.fraction.part_whole'), None)
            if fixed is None:
                fixed = next(candidate for candidate in candidates if candidate['disclosure'] == 'solution'
                             and candidate['reference']['id'] == 'math.fraction.part_whole'
                             and not candidate.get('question_core')
                             and tuple(candidate['block']['numbers']) not in used_prior_models)
                used_prior_models.add(tuple(fixed['block']['numbers']))
                n, d = fixed['block']['numbers']
                core = {'id': row['slot']['id'], 'type': 'short', 'prompt': f'Was beschreibt {n}/{d}?',
                        'answer': f'{n} von {d} gleich großen Teilen', 'options': [], 'accepted': []}
            else:
                core = fixed['question_core']
            questions.append({**core, 'hints': ['Denke an gleich große Teile.'],
                'explanation': fixed['text'], 'presentation': None, 'field_group': None,
                'explanation_steps': [standard(fixed)]})
        else:
            step = planner.solution_step(plan, row)
            step['presentation']['blocks'] = [step['id']]
            questions.append({**row['task'], 'hints': ['Achte auf Zähler und Nenner.'],
                'explanation': step['text'], 'presentation': None, 'field_group': None,
                'explanation_steps': [step]})
    return {'units': [{'group_id': plan['group_id'], 'subject': 'Mathematik', 'topic': 'Brüche',
        'explanation': intro['text'], 'explanation_steps': [standard(intro)], 'questions': questions}]}


@pytest.mark.parametrize('content', [EXPAND, REDUCE])
@pytest.mark.parametrize('fault', [None, 'answer', 'graphic_id', 'source'])
def test_provider_bound_schema_codec_validation_and_private_plan_stripping(api, household, monkeypatch, content, fault):
    _, job_id, request = running_job(api, household, content)
    with DB.begin() as db:
        bound = reservation.prepare(db, job_id, request)
    plan = bound['package_fraction_plan']
    bound['visual_context']['package_fraction_plan'] = copy.deepcopy(plan)
    data = model_output(bound)
    if fault:
        question = next(q for q in data['units'][0]['questions'] if q['id'] in
                        {row['task']['id'] for row in plan['slots'] if row['task']})
        if fault == 'answer': question['answer'] = '1/99'
        if fault == 'graphic_id': question['explanation_steps'][0]['presentation']['blocks'] = ['foreign']
        if fault == 'source': question['explanation_steps'][0]['source_refs'] = ['foreign']
    capture, real_client, calls = PackageOutputCapture(monkeypatch), httpx.Client, []
    def handler(request):
        body = json.loads(request.content)
        value = json.loads(body['messages'][1]['content'][0]['text'])
        assert 'package_fraction_plan' not in value
        assert 'package_fraction_plan' not in value['visual_context']
        assert 'excluded_values' not in json.dumps(value, ensure_ascii=False)
        assert value['prepared_graphics']['revision'] == 'package-fraction-wire-1'
        calls.append(body)
        wire = capture.wire(data)
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {
            'content': json.dumps(wire, ensure_ascii=False)}}],
            'usage': {'prompt_tokens': 111, 'completion_tokens': 2223, 'cost': 0.0321}})
    monkeypatch.setattr(providers.httpx, 'Client', lambda **kw: real_client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(providers, 'external_allowed', lambda *a, **kw: None)
    monkeypatch.setattr(providers, 'decrypt', lambda _: 'synthetic-no-network-key')
    monkeypatch.setattr('schulpilot.model_routing.selection', lambda _: {'route': {'upstreams': ['azure']}, 'region': 'standard'})
    value = config()
    value.max_output_tokens, value.reserve_micros = 8000, 250000
    if fault:
        with pytest.raises(providers.ProviderError) as caught:
            providers.request_provider(value, 'package', bound)
        assert len(calls) == 1 and caught.value.billing_result.cost_micros == 32100
        return
    result = providers.request_provider(value, 'package', bound)
    assert len(calls) == 1 and result.cost_micros == 32100
    planned = next(q for q in result.data['units'][0]['questions'] if q['id'] in
                   {row['task']['id'] for row in plan['slots'] if row['task']})
    assert len(planned['explanation_steps'][0]['presentation']['blocks']) == 2
