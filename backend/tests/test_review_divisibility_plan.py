"""End-to-end synthetic review transport; never call a live model."""
import copy
import json
from types import SimpleNamespace
import httpx
import pytest
from schulpilot import db as storage, providers, visual_references
from schulpilot import review_divisibility_plan as plan
from schulpilot import review_divisibility_product as product
from schulpilot import unit_multiples_common as multiples
from schulpilot.package_prepared_graphics import _digest
from schulpilot.schemas import PracticeUnitOutput
from schulpilot.visual_reference_models import VisualReference
from test_review_fraction_compositions_142 import config, RECIPES, RecipeLookup

RULE = 'Das kleinste gemeinsame Vielfache zweier Zahlen ist die kleinste positive Zahl, die durch beide Zahlen ohne Rest teilbar ist.'
CONTENT = RULE + '\nTeiler: 3 · 4 = 12'

@pytest.fixture(autouse=True)
def clean_database(monkeypatch):
    monkeypatch.setattr(storage, 'DB', RecipeLookup)
    from schulpilot.config import settings
    previous = dict(settings.__dict__)
    object.__setattr__(settings, 'real_data_approved', True)
    object.__setattr__(settings, 'privacy_evidence', 'Synthetic fixture')
    monkeypatch.setattr(providers, 'runtime_settings', lambda: settings)
    yield
    settings.__dict__.clear()
    settings.__dict__.update(previous)


def original(reverse=False):
    source = {'ref': 'p1', 'subject': 'Mathematik', 'group_id': None, 'material_id': 'a'*32,
        'revision': 1, 'topic': 'kgV und Teiler', 'content': CONTENT, 'source_refs': [], 'factual_status': 'not_assessed'}
    goals = [{'id': 'g1', 'label': 'kgV und Vielfache', 'source_excerpt': RULE},
        {'id': 'g2', 'label': 'Teilbarkeit', 'source_excerpt': '3 · 4 = 12'}]
    return {'review': True, 'practice_kind': 'check', 'required_subject': 'Mathematik',
        'required_topic': 'kgV und Teiler', 'grade': 6, 'focus_goal_ids': ['g2', 'g1'] if reverse else ['g1', 'g2'],
        'learning_goals': goals, 'material': {'subject': 'Mathematik', 'topic': 'kgV und Teiler', 'content': CONTENT},
        'visual_context': {'version': 1, 'required': True, 'references': [], 'sources': [source]}}


def prepared(reverse=False):
    return plan.prepare(plan.with_history(plan.add_references(RecipeLookup(), original(reverse)), []))


def wire(payload):
    schema = providers.strict_schema(PracticeUnitOutput, preserve_limits=True)
    providers.indexed_choice_schema(schema, bounded_matches=True)
    providers.bind_practice_tasks(schema, providers.practice_tasks(payload))
    visual_references.bind_schema(schema, payload)
    binding = plan.bind_schema(schema, payload)
    def step(row):
        return {'id': row['id'], 'text': row['text'], 'competence_id': None,
            'disclosure': row['disclosure'], 'reference': row['reference'], 'source_refs': row['source_refs'],
            'presentation': {'version': 1, 'evidence_kind': 'knowledge', 'blocks': [row['id']]}}
    intro = binding.candidates[0]
    questions = []
    for task in providers.practice_tasks(payload):
        row = next(row for row in binding.candidates if row.get('question_core', {}).get('id') == task['id'])
        questions.append({**copy.deepcopy(row['question_core']), 'hints': row.get('question_hints', ['Bilde die Vielfachen.']),
            'explanation': row['text'], 'presentation': None, 'explanation_steps': [step(row)]})
    return binding, {'subject': 'Mathematik', 'topic': 'kgV und Teiler', 'explanation': intro['text'],
        'explanation_steps': [step(intro)], 'questions': questions}


@pytest.mark.parametrize('reverse', [False, True])
def test_real_provider_transport_bound_to_goals_source_and_graphics(monkeypatch, reverse):
    payload = prepared(reverse)
    binding, response = wire(payload)
    calls, real = [], httpx.Client
    def handler(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(response)}}],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 500, 'cost': .001}})
    monkeypatch.setattr(providers.httpx, 'Client', lambda **kw: real(transport=httpx.MockTransport(handler)))
    result = providers.request_provider(config(), 'unit', payload)
    assert len(calls) == 1
    assert [(q['id'], q['learning_goal_id']) for q in result.data['questions']] == [
        (f'q{i+1}', goal) for i, goal in enumerate(payload['focus_goal_ids'])]
    plan.validate_output(payload, result.data)
    visual_references.validate_output(RecipeLookup(), result.data, payload)
    from test_graphic_native_transport import subset_record
    subset_record(calls[0]['response_format']['json_schema']['schema'])
    outgoing = json.loads(calls[0]['messages'][1]['content'][0]['text'])
    assert plan.HISTORY not in outgoing
    assert all(q['explanation_steps'][0]['disclosure'] == 'solution' for q in result.data['questions'])


@pytest.mark.parametrize('fault', ['missing', 'wrong', 'revision', 'goal', 'history', 'changed_answer', 'changed_scene', 'hidden_scene_hint', 'hidden_kgv_hint'])
def test_rejects_unproven_or_tampered_data(fault):
    payload = original()
    if fault == 'missing': payload['learning_goals'][1]['source_excerpt'] = 'Teilbarkeit'
    if fault == 'wrong': payload['learning_goals'][1]['source_excerpt'] = '3 · 4 = 13'
    if fault in ('missing', 'wrong'):
        payload = plan.with_history(plan.add_references(RecipeLookup(), payload), [])
        with pytest.raises(ValueError, match="bestätigtes Rechenbeispiel"): plan.prepare(payload)
        return
    body = prepared()
    binding, response = wire(body)
    data = binding.hydrate(response)
    if fault == 'revision': body['visual_context']['sources'][0]['revision'] += 1
    if fault == 'goal': data['questions'][1]['learning_goal_id'] = 'g1'
    if fault == 'history':
        with pytest.raises(ValueError): plan.validate_history(body, data, ['Was sind die Teiler von 12?'])
        return
    if fault == 'changed_answer': data['questions'][1]['answer'] = '9'
    if fault == 'hidden_kgv_hint': data['questions'][0]['hints'] = ['Schau dir die Reihen in der Grafik an.']
    if fault == 'hidden_scene_hint': data['questions'][1]['hints'] = ['Schau dir die Gruppen in der Grafik an.']
    if fault == 'changed_scene': data['questions'][1]['explanation_steps'][0]['presentation']['blocks'][0]['scene']['objects'][0]['label'] = '●'
    with pytest.raises(ValueError): plan.validate_output(body, data)


def test_worker_review_adapter_and_stale_source(monkeypatch):
    from schulpilot import coaching, review_fraction_compositions as adapter, source_lineage
    from test_review_fraction_compositions_142 import ContextLookup
    from test_review_divisibility_plan import original
    child = SimpleNamespace(id='2'*32)
    source = original()['visual_context']['sources'][0]
    page = SimpleNamespace(id=source['material_id'], revision=1, child_id=child.id, purpose='notebook',
        confirmed=True, synthetic=False, fixture_id=None, subject='Mathematik', topic='kgV und Teiler')
    previous = SimpleNamespace(id='3'*32, child_id=child.id, material_id=page.id, status='completed',
        subject=page.subject, topic=page.topic, school_day_id=None, questions=[])
    job = SimpleNamespace(id='5'*32, kind='unit', status='running', child_id=child.id, payload={
        'material_id': page.id, 'material_revision': 1, 'review_of': previous.id, 'sources': [{'id': page.id, 'revision': 1}]})
    state = {'source': copy.deepcopy(source), 'goals': original()['learning_goals'], 'focus': ['g1','g2'], 'chain': [previous]}
    monkeypatch.setattr(coaching, 'goals_for', lambda *_: copy.deepcopy(state['goals']))
    monkeypatch.setattr(coaching, 'focus_ids', lambda *_: copy.deepcopy(state['focus']))
    monkeypatch.setattr(coaching, 'root_and_units', lambda *_: (previous, state['chain']))
    monkeypatch.setattr(source_lineage, 'learning_source', lambda *_args, **_kw: copy.deepcopy(state['source']))
    db, cfg = ContextLookup(previous), config()
    payload = original()
    payload.pop('practice_kind')
    body, receipt = adapter.prepare(db, job, child, page, [page], cfg, cfg._selected_route, payload)
    assert receipt and plan.KEY in body
    binding, output = wire(body)
    data = binding.hydrate(output)
    adapter.validate(db, job, child, page, [page], cfg, cfg._selected_route, body, data, receipt)
    state['source']['content'] += ' Geändert.'
    with pytest.raises(ValueError):
        adapter.validate(db, job, child, page, [page], cfg, cfg._selected_route, body, data, receipt)
    state['source'] = copy.deepcopy(source)
    payload['learning_goals'][1]['source_excerpt'] = 'Teilbarkeit'
    state['goals'][1]['source_excerpt'] = 'Teilbarkeit'
    with pytest.raises(ValueError):
        adapter.prepare(db, job, child, page, [page], cfg, cfg._selected_route, payload)


@pytest.mark.parametrize('reverse', [False, True])
def test_mixed_label_must_not_occupy_both_goal_slots(reverse):
    payload = original(reverse)
    payload['learning_goals'][0]['label'] = 'kgV und Teilbarkeit'
    payload['learning_goals'][1]['label'] = 'Zahlen verstehen'
    assert not plan.supported(payload)
    with pytest.raises(ValueError):
        plan.add_references(RecipeLookup(), payload)


def test_planner_independently_rejects_duplicate_prescribed_task(monkeypatch):
    payload = prepared()
    tasks = providers.practice_tasks(payload)
    tasks[1]['id'] = tasks[0]['id']
    monkeypatch.setattr(providers, 'practice_tasks', lambda _: tasks)
    with pytest.raises(ValueError):
        plan.prepare(payload)


@pytest.mark.parametrize('label', ['Gemeinsame Teiler bestimmen', 'Teilbarkeitsregeln anwenden',
    'Alle Teiler bestimmen', 'Teilbarkeit durch 3 prüfen', 'Teiler in Primfaktoren zerlegen'])
def test_rejects_more_specific_divisibility_goals(label):
    payload = original()
    payload['learning_goals'][1]['label'] = label
    assert not plan.supported(payload)
    task = {'id': 'q2', 'learning_goal_id': 'g2', 'label': label, 'source_excerpt': '3 · 4 = 12'}
    ctx = plan.add_references(RecipeLookup(), original())['visual_context']
    assert product.compile_candidate(ctx, task) is None


def test_divisor_hint_is_available_without_solution_graphic():
    payload = prepared()
    binding, output = wire(payload)
    item = next(item for item in payload[plan.KEY]['tasks'] if item['kind'] == 'divisor')
    question = next(q for q in output['questions'] if q['id'] == item['core']['id'])
    assert question['hints'] == ['Zähle in 3er-Schritten bis 12. Wie viele Schritte sind es?']
    assert question['explanation_steps'][0]['disclosure'] == 'solution'
    data = binding.hydrate(output)
    plan.validate_output(payload, data)


def test_kgv_hint_is_available_without_solution_graphic():
    payload = prepared()
    binding, output = wire(payload)
    item = next(item for item in payload[plan.KEY]['tasks'] if item['kind'] == 'kgv')
    question = next(q for q in output['questions'] if q['id'] == item['core']['id'])
    a, b = item['pair']
    assert question['hints'] == [f'Schreibe die Vielfachen von {a} und {b} auf und vergleiche sie.']
    assert question['explanation_steps'][0]['disclosure'] == 'solution'
    plan.validate_output(payload, binding.hydrate(output))
