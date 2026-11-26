"""Synthetic source, actual schemas and source-bound graphics."""
import copy

import pytest
from schulpilot import package_multiples_sequence as sequence
from schulpilot import package_output_transport, package_transport, visual_references
from schulpilot.db import DB
from schulpilot.schemas import PackageOutput
from schulpilot.subject_content import public_presentation
from test_package_prepared_graphics import bind, payload_for, wire_step

SOURCE = 'Vielfache und Teilbarkeit\n' + r'\(V_{4} = \{4; 8; 12; 16\ldots\}\)'


def payload(content=SOURCE):
    value = payload_for(content)
    with DB() as db:
        return sequence.add_reference(db, value)


def wire(context=None):
    context = context or payload()
    schema, binding = bind(context)
    assert isinstance(binding, sequence.Binding)
    intro, *questions = binding.candidates
    data = {'units': [{'group_id': 'g1', 'subject': 'Mathematik', 'topic': 'Vielfache',
        'explanation': intro['text'], 'explanation_steps': [wire_step(intro)],
        'questions': [{**row['question_core'], 'hints': ['Zähle in gleichen Schritten.'],
                       'explanation': row['text'], 'presentation': None, 'field_group': None,
                       'explanation_steps': [wire_step(row)]} for row in questions]}]}
    return data, context, schema, binding


@pytest.mark.parametrize('content', [SOURCE, SOURCE.replace(r'\ldots', '…'),
    SOURCE.replace(r'\(', '').replace(r'\)', '').replace(r'\{', '{').replace(r'\}', '}')])
def test_exact_correct_sequence_is_accepted(content):
    proof = sequence.evidence(content)
    assert proof and proof['base'] == 4 and proof['values'] == [4, 8, 12, 16]
    assert proof['quote'] in content


@pytest.mark.parametrize('content', [SOURCE.replace('12', '13'), SOURCE.replace('V_{4}', 'T_{4}'),
    SOURCE.replace('Vielfache', 'Zahlen'), SOURCE.replace('4; 8; 12; 16', '0; 4; 8; 12'),
    SOURCE.replace('4; 8; 12; 16', '4; 8; x; 16'), SOURCE + ' = 77',
    SOURCE.replace('16', '16 + 1'), SOURCE.replace('V_{4}', 'V_{0}')])
def test_incorrect_or_ambiguous_sequences_are_not_accepted(content):
    assert sequence.evidence(content) is None
    assert not sequence.compile_candidates(payload(content))


def test_real_codec_and_canonical_validation_hide_solutions():
    data, context, schema, binding = wire()
    codec = package_output_transport.bind(package_transport.schema_projection(schema))
    output = binding.hydrate(codec.decode(codec.encode(data)))
    output = PackageOutput.model_validate(output).model_dump(mode='json')
    with DB() as db:
        visual_references.validate_output(db, output, context)
    questions = output['units'][0]['questions']
    assert len({q['prompt'] for q in questions}) == len(questions)
    assert len({q['answer'] for q in questions}) == len(questions)
    assert all(q['answer'] not in {'4', '8', '12', '16'} for q in questions)
    assert public_presentation(questions[0]['explanation_steps'][0]['presentation'])['blocks'] == []


@pytest.mark.parametrize('mutation', ['answer', 'prompt', 'hint', 'scene', 'source', 'reference', 'disclosure', 'duplicate'])
def test_tampering_is_rejected(mutation):
    data, context, _, binding = wire()
    if mutation in ('answer', 'prompt'):
        data['units'][0]['questions'][0][mutation] = '999'
    elif mutation == 'hint':
        data['units'][0]['questions'][0]['hints'] = ['Das Ergebnis ist 20.']
    elif mutation == 'duplicate':
        data['units'][0]['questions'][1] = copy.deepcopy(data['units'][0]['questions'][0])
    elif mutation == 'reference':
        data['units'][0]['questions'][0]['explanation_steps'][0]['reference']['id'] = 'foreign'
    elif mutation == 'disclosure':
        data['units'][0]['questions'][0]['explanation_steps'][0]['disclosure'] = 'given'
    else:
        decoded = binding.hydrate(data)
        block = decoded['units'][0]['questions'][0]['explanation_steps'][0]['presentation']['blocks'][0]
        if mutation == 'scene':
            block['scene']['objects'][0]['label'] = '999'
        else:
            block['source_excerpt'] = r'\(V_{4} = \{4; 8; 13; 16\ldots\}\)'
        with DB() as db, pytest.raises(ValueError):
            visual_references.validate_output(db, decoded, context)
        return
    with pytest.raises(ValueError):
        binding.hydrate(data)


def test_prior_examples_are_excluded_and_fixed_prerequisites_preserved():
    context = payload()
    rows = sequence.compile_candidates(context)
    previous = [list(sequence.prompt_pair(row['question_core']['prompt'])) for row in rows[1:]]
    context[sequence.HISTORY] = previous
    fresh = sequence.compile_candidates(context)
    assert not {tuple(pair) for pair in previous} & {
        sequence.prompt_pair(row['question_core']['prompt']) for row in fresh[1:]}
    context[sequence.HISTORY] = [[4, factor] for factor in range(5, 50)]
    with pytest.raises(ValueError, match='fehlen ausreichend'):
        sequence.compile_candidates(context)


def test_five_slots_have_distinct_answers_and_recoverable_exercise_identity():
    rows = sequence.compile_candidates(payload(), count=5)[1:]
    assert len(rows) == 5
    assert len({row['question_core']['answer'] for row in rows}) == 5
    assert len({sequence.prompt_pair(row['question_core']['prompt']) for row in rows}) == 5
    assert all(sequence.prompt_pair(row['question_core']['prompt']) for row in rows)


def test_number_visible_elsewhere_on_selected_page_is_not_a_new_example():
    rows = sequence.compile_candidates(payload(SOURCE + '\n4 · 5 = 20'))[1:]
    assert all(sequence.prompt_pair(row['question_core']['prompt']) != (4, 5) for row in rows)
    assert all(row['question_core']['answer'] != '20' for row in rows)


@pytest.mark.parametrize('mutation', ['wrong_group', 'wrong_subject', 'foreign_source', 'blocked',
    'bad_revision', 'bad_digest', 'not_partition', 'missing_reference'])
def test_only_eligible_versioned_sources_can_produce_a_graphic(mutation):
    context = payload()
    source = context['visual_context']['sources'][0]
    reference = next(r for r in context['visual_context']['references'] if r['id'] == sequence.REFERENCE)
    if mutation == 'wrong_group':
        source['group_id'] = 'foreign'
    elif mutation == 'wrong_subject':
        source['subject'] = 'Deutsch'
    elif mutation == 'foreign_source':
        source['source_type'] = 'curated_foundation'
    elif mutation == 'blocked':
        source['factual_status'] = 'blocked'
    elif mutation == 'bad_revision':
        source['revision'] = 0
    elif mutation == 'bad_digest':
        reference['digest'] = 'incorrect'
    elif mutation == 'not_partition':
        context['package_partition'] = None
    else:
        context['visual_context']['references'].remove(reference)
    assert sequence.compile_candidates(context) == []


@pytest.mark.parametrize('mode', ['source_probe', 'reuse_evidence'])
def test_entry_plan_keeps_its_question_ids_and_validates(mode):
    from schulpilot import learning_entry
    from test_package_entry_graphics_145 import bind as bind_entry

    context = payload()
    context['learning_entry'] = {'units': [{'group_id': 'g1', 'subject': 'Mathematik',
        'entry_mode': mode, 'prefix': 'test', 'probes': [], 'allocation_version': 2}]}
    _, binding = bind_entry(context)
    intro, *tasks = binding.candidates
    value = {'units': [{'group_id': 'g1', 'subject': 'Mathematik', 'topic': 'Vielfache',
        'explanation': intro['text'], 'explanation_steps': [wire_step(intro)],
        'questions': [{**row['question_core'], 'hints': ['Zähle in gleichen Schritten.'],
            'explanation': row['text'], 'presentation': None, 'field_group': None,
            'explanation_steps': [wire_step(row)]} for row in tasks]}]}
    output = binding.hydrate(value)
    learning_entry.validate_entry_output(context, output)
    with DB() as db:
        visual_references.validate_output(db, output, context)


def test_history_is_scoped_to_child_and_publication_rechecks_it():
    from schulpilot.db import Child, Family, LearningUnit, User

    data, _, _, binding = wire()
    output = binding.hydrate(data)
    with DB.begin() as db:
        family = Family(name='Synthetische Familie')
        db.add(family)
        db.flush()
        users = [User(username=f'seq-{i}@example.invalid', role='child', display_name='Test',
                      password_hash='synthetic-unused') for i in range(2)]
        db.add_all(users)
        db.flush()
        first, second = [Child(family_id=family.id, grade=6, user_id=user.id) for user in users]
        db.add_all([first, second])
        db.flush()
        question = output['units'][0]['questions'][0]
        db.add(LearningUnit(child_id=second.id, subject='Mathematik', topic='Vielfache',
                            questions=[question], explanation='', provider='synthetic-test'))
        db.flush()
        assert sequence.history(db, first.id) == []
        sequence.validate_history(db, first.id, output)
        db.add(LearningUnit(child_id=first.id, subject='Mathematik', topic='Vielfache',
                            questions=[question], explanation='', provider='synthetic-test'))
        db.flush()
        with pytest.raises(ValueError, match='bereits vorbereitet'):
            sequence.validate_history(db, first.id, output)


def test_other_wording_of_prior_arithmetic_is_conservatively_excluded():
    from schulpilot.db import Child, Family, LearningUnit, User

    with DB.begin() as db:
        family = Family(name='Synthetische Familie')
        user = User(username='seq-other@example.invalid', role='child', display_name='Test', password_hash='unused')
        db.add_all([family, user])
        db.flush()
        child = Child(family_id=family.id, grade=6, user_id=user.id)
        db.add(child)
        db.flush()
        db.add(LearningUnit(child_id=child.id, subject='Mathematik', topic='Vielfache',
            questions=[{'prompt': 'Berechne 4 mal 6.'}], explanation='', provider='synthetic-test'))
        db.flush()
        assert [4, 6] in sequence.history(db, child.id)


def test_actual_provider_adapter_sends_one_schema_bound_request(monkeypatch):
    import json

    import httpx
    from package_output_helpers import PackageOutputCapture
    from schulpilot import providers
    from test_package_transport import config

    data, context, _, _ = wire()
    output, real_client, calls = PackageOutputCapture(monkeypatch), httpx.Client, []

    def handler(request):
        calls.append(request)
        assert sequence.HISTORY not in request.content.decode()
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {
            'content': json.dumps(output.wire(data), ensure_ascii=False)}}],
            'usage': {'prompt_tokens': 111, 'completion_tokens': 2223, 'cost': 0.0321}})

    context[sequence.HISTORY] = [[4, 49]]
    monkeypatch.setattr(providers.httpx, 'Client', lambda **kw: real_client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(providers, 'external_allowed', lambda *a, **kw: None)
    monkeypatch.setattr(providers, 'decrypt', lambda _: 'synthetic-no-network-key')
    monkeypatch.setattr('schulpilot.model_routing.selection', lambda _: {'route': {'upstreams': ['azure']}, 'region': 'standard'})
    value = config()
    value.max_output_tokens, value.reserve_micros = 8000, 250000
    result = providers.request_provider(value, 'package', context)
    assert len(calls) == 1 and result.cost_micros == 32100
    assert [q['prompt'] for q in result.data['units'][0]['questions']] == [q['prompt'] for q in data['units'][0]['questions']]
