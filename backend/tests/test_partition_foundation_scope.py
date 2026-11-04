"""Artificial short package probes are selected before any provider transport."""
import copy
import json

import httpx
import pytest
from package_output_helpers import PackageOutputCapture
from schulpilot import learning_entry, package_transport, providers, visual_references
from schulpilot.db import DB, Child, LearningUnit, Material
from schulpilot.visual_reference_models import UnitVisualSnapshot
from test_package_entry_graphics_145 import bind, fixture
from test_package_prepared_graphics import wire_step
from test_package_transport import config
from test_visual_references import generated_visual_unit, step  # noqa: F401


def test_short_partition_removes_unallocated_probe_from_every_input_path():
    payload, old_probes = fixture()
    payload['learning_entry']['units'][0]['allocation_version'] = 2
    # Recreate the worker's pre-foundation state; it adds foundations only after
    # the two-question partition has selected its actual entry question.
    payload['visual_context']['sources'] = [s for s in payload['visual_context']['sources']
        if s.get('source_type') != 'curated_foundation']
    before = copy.deepcopy(payload)
    selected = learning_entry.limit_partition_probes(payload)
    assert payload == before
    assert [p['id'] for p in selected['learning_entry']['units'][0]['probes']] == [old_probes[0]['id']]
    assert [x['reference_id'] for x in selected['learning_entry']['references']] == [old_probes[0]['reference_id']]
    assert learning_entry._specs(before['learning_entry']['units'][0], 2) == learning_entry._specs(selected['learning_entry']['units'][0], 2)
    assert [item['role'] for item in learning_entry._specs(selected['learning_entry']['units'][0], 2)] == ['prior_check', 'practice']
    with DB() as db:
        selected = visual_references.with_foundation_context(db, selected)
    assert [s['example_question_id'] for s in selected['visual_context']['sources']
        if s.get('source_type') == 'curated_foundation'] == [old_probes[0]['id']]
    from schulpilot.package_prepared_graphics import compile_candidates
    assert {r['question_core']['id'] for r in compile_candidates(selected) if r.get('question_core')} == {old_probes[0]['id']}
    wire = json.dumps(package_transport.payload_projection(selected), ensure_ascii=False)
    assert old_probes[1]['prompt'] not in wire
    assert old_probes[1]['visual_example']['text'] not in wire


@pytest.mark.parametrize('change', ['not_partition', 'legacy', 'other_group', 'multiple_groups', 'existing_contract'])
def test_nonmatching_contracts_remain_untouched(change):
    payload, _ = fixture()
    plan = payload['learning_entry']['units'][0]
    plan['allocation_version'] = 2
    if change == 'not_partition':
        payload.pop('package_partition')
    if change == 'legacy':
        plan.pop('allocation_version')
    if change == 'other_group':
        plan['group_id'] = 'other'
    if change == 'multiple_groups':
        payload['selected_groups'].append({'id': 'g2', 'subject': 'Deutsch'})
    if change == 'existing_contract':
        plan['entry_mode'] = 'existing_contract'
    assert learning_entry.limit_partition_probes(payload) is payload


def test_actual_adapter_transports_only_allocated_probe(monkeypatch):
    payload, probes = fixture()
    payload['learning_entry']['units'][0]['allocation_version'] = 2
    payload['visual_context']['sources'] = [s for s in payload['visual_context']['sources']
        if s.get('source_type') != 'curated_foundation']
    payload = learning_entry.limit_partition_probes(payload)
    with DB() as db:
        payload = visual_references.with_foundation_context(db, payload)
    _, binding = bind(payload)
    intro = next(c for c in binding.candidates if c['disclosure'] == 'given')
    fixed = next(c for c in binding.candidates if c.get('question_core', {}).get('id') == probes[0]['id']
        and c['disclosure'] == 'solution')
    practice = next(c for c in binding.candidates if c['kind'] == 'fraction' and c['disclosure'] == 'solution'
        and not c.get('question_core'))
    n, d = map(int, practice['block']['numbers'])
    fixed_question = {**{key: probes[0][key] for key in learning_entry.CORE},
        'hints': ['Schau auf die Teile.'], 'explanation': fixed['text'], 'presentation': None,
        'explanation_steps': [wire_step(fixed)]}
    practice_question = {'id': 'main_artificial_1', 'type': 'short',
        'prompt': f'Was zeigt der Bruch {n}/{d}?', 'answer': f'{n}/{d}', 'options': [], 'accepted': [],
        'hints': ['Zähle die Teile.'], 'explanation': practice['text'], 'presentation': None,
        'explanation_steps': [wire_step(practice)]}
    output = {'units': [{'group_id': 'g1', 'subject': 'Mathematik', 'topic': 'Brüche verstehen',
        'explanation': intro['text'], 'explanation_steps': [wire_step(intro)],
        'questions': [fixed_question, practice_question]}]}
    capture, calls, client = PackageOutputCapture(monkeypatch), [], httpx.Client

    def handler(request):
        body = json.loads(request.content)
        calls.append(body)
        wire = json.dumps(body, ensure_ascii=False)
        assert probes[0]['prompt'] in wire
        assert probes[1]['prompt'] not in wire
        assert probes[1]['visual_example']['text'] not in wire
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {
            'content': json.dumps(capture.wire(output))}}], 'usage': {'prompt_tokens': 100,
            'completion_tokens': 100, 'cost': 0.002}})

    monkeypatch.setattr(providers.httpx, 'Client', lambda **kw: client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(providers, 'external_allowed', lambda *a, **kw: None)
    monkeypatch.setattr(providers, 'decrypt', lambda _: 'artificial-no-network-key')
    monkeypatch.setattr('schulpilot.model_routing.selection', lambda _: {'route': {'upstreams': ['azure']}, 'region': 'standard'})
    route = config()
    route.max_output_tokens, route.reserve_micros = 8000, 250000
    try:
        result = providers.request_provider(route, 'package', payload)
    except providers.ProviderError as error:
        pytest.fail(str(getattr(error.billing_result, 'telemetry', None)))
    assert len(calls) == 1
    assert [q['id'] for q in result.data['units'][0]['questions']] == [probes[0]['id'], 'main_artificial_1']


def test_saved_snapshot_keeps_allocated_probe_and_material_checks(generated_visual_unit):  # noqa: F811
    uid, mid, cid = generated_visual_unit
    with DB.begin() as db:
        material, unit = db.get(Material, mid), db.get(LearningUnit, uid)
        material.content = ('Beim Erweitern werden Zähler und Nenner mit derselben Zahl multipliziert. '
            'Ein Bruch 1/2 beschreibt 1 von 2 gleich großen Teilen.')
        payload = visual_references.with_visual_context(db, db.get(Child, cid),
            {'material': {'subject': 'Mathematik', 'topic': 'Brüche', 'content': material.content}}, [material])
        payload = learning_entry.with_learning_entry(db, db.get(Child, cid), payload, [material], enabled=True)
        plan = payload['learning_entry']['units'][0]
        assert len(plan['probes']) >= 2
        plan.update(group_id='g1', allocation_version=2)
        payload.update(package_partition=0, selected_groups=[{'id': 'g1', 'subject': 'Mathematik'}])
        for source in payload['visual_context']['sources']:
            source['group_id'] = 'g1'
        old_payload = copy.deepcopy(payload)
        payload = learning_entry.limit_partition_probes(payload)
        payload = visual_references.with_foundation_context(db, payload)
        old_payload = visual_references.with_foundation_context(db, old_payload)
        probe = payload['learning_entry']['units'][0]['probes'][0]
        foundation = next(s for s in payload['visual_context']['sources'] if s.get('example_question_id') == probe['id'])
        n, d = probe['visual_example']['numerator'], probe['visual_example']['denominator']
        intro = step()
        intro.update(text=f'{n} von {d} gleich großen Teilen.', source_refs=[foundation['ref']])
        intro['presentation']['blocks'][0].update(numbers=[n, d], source_excerpt=foundation['content'])
        solved = copy.deepcopy(intro)
        solved['disclosure'] = 'solution'
        solved['presentation']['blocks'][0]['disclosure'] = 'solution'
        question = {key: probe[key] for key in learning_entry.CORE} | {
            'hints': ['Zähle die Teile.'], 'explanation': intro['text'], 'explanation_steps': [solved]}
        practice = {**copy.deepcopy(question), 'id': 'main_artificial_1'}
        value = {'subject': 'Mathematik', 'topic': 'Brüche', 'group_id': 'g1',
            'explanation': intro['text'], 'explanation_steps': [intro], 'questions': [question, practice]}
        db.delete(db.get(UnitVisualSnapshot, uid))
        db.flush()
        unit.questions = value['questions']
        visual_references.remember(db, unit, value, payload)
        db.flush()
        assert visual_references.projection(db, unit)['explanation_visual_status'] == 'ready'
        assert visual_references.source_bindings_current(db, unit, require_question_binding=True)
        row = db.get(UnitVisualSnapshot, uid)
        # A JSON export/import must retain every private binding and digest.
        original_bindings = copy.deepcopy(row.source_bindings)
        row.source_bindings = json.loads(json.dumps(row.source_bindings))
        db.flush()
        db.expire(row)
        assert row.source_bindings == original_bindings
        assert visual_references.projection(db, unit)['explanation_visual_status'] == 'ready'
        original_questions = copy.deepcopy(unit.questions)
        unit.questions = [{**original_questions[0], 'answer': 'tampered'}, original_questions[1]]
        db.flush()
        assert visual_references.projection(db, unit)['explanation_visual_reason'] == 'source_changed'
        unit.questions = original_questions
        db.flush()
        assert visual_references.projection(db, unit)['explanation_visual_status'] == 'ready'
        actual_bindings = copy.deepcopy(row.source_bindings)
        forged_bindings = copy.deepcopy(actual_bindings)
        next(b for b in forged_bindings if b.get('source_kind') == 'curated_foundation')['digest'] = 'forged'
        row.source_bindings = forged_bindings
        db.flush()
        assert visual_references.projection(db, unit)['explanation_visual_reason'] == 'source_changed'
        row.source_bindings = actual_bindings
        db.flush()
        assert visual_references.projection(db, unit)['explanation_visual_status'] == 'ready'
        old_source = next(s for s in old_payload['visual_context']['sources']
            if s.get('source_type') == 'curated_foundation' and s['example_question_id'] != probe['id'])
        row.source_bindings = [*row.source_bindings, visual_references.source_binding(old_source, question_source_bound=True)]
        db.flush()
        # Old snapshots keep the conservative check: the unallocated example
        # was sent in the provider context and cannot simply be discarded.
        assert visual_references.projection(db, unit)['explanation_visual_reason'] == 'source_changed'
        assert not visual_references.source_bindings_current(db, unit, require_question_binding=True)
        row.source_bindings = row.source_bindings[:-1]
        db.flush()
        assert visual_references.projection(db, unit)['explanation_visual_status'] == 'ready'
        material.revision += 1
        db.flush()
        assert visual_references.projection(db, unit)['explanation_visual_reason'] == 'source_changed'
