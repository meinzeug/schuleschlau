"""Synthetic, local proof tests; no provider or child data."""
import copy
import pytest
from schulpilot import review_divisibility_product as product
from schulpilot.package_prepared_graphics import _digest


@pytest.fixture(autouse=True)
def clean_database():
    # Pure functions only: do not create or mutate any database.
    yield


def context():
    recipe = product.public_recipe()
    return {'sources': [{'ref': 'p1', 'subject': 'Mathematik', 'group_id': None, 'material_id': 'a'*32,
        'revision': 1, 'content': 'Teiler: 3 · 4 = 12', 'factual_status': 'not_assessed'}],
        'references': [{'id': recipe['id'], 'version': 1, 'subject': 'Mathematik',
            'kind': 'scene', 'digest': _digest(recipe)}]}


def task():
    return {'id': 'q2', 'learning_goal_id': 'g2', 'label': 'Teilbarkeit', 'source_excerpt': '3 · 4 = 12'}


def test_binds_math_goal_and_solution_only():
    ctx = context()
    question, candidate = product.compile_candidate(ctx, task())
    assert question['id'] == 'q2' and question['learning_goal_id'] == 'g2'
    assert question['answer'] == '4'
    block = candidate['block']
    assert block['disclosure'] == 'solution'
    assert len(block['scene']['objects']) == 3
    assert all(o['label'].count('●') == 4 for o in block['scene']['objects'])
    assert len(block['scene']['steps']) == 2
    product.validate_step(product.step_for(candidate), ctx, question, task())
    for mutate in ('question', 'goal', 'scene', 'disclosure', 'reference', 'source'):
        q, step, changed = copy.deepcopy(question), copy.deepcopy(product.step_for(candidate)), copy.deepcopy(ctx)
        if mutate == 'question': q['answer'] = '5'
        if mutate == 'goal': q['learning_goal_id'] = 'g1'
        if mutate == 'scene': step['presentation']['blocks'][0]['scene']['objects'][0]['label'] = '●'
        if mutate == 'disclosure': step['disclosure'] = 'given'
        if mutate == 'reference': step['reference']['version'] = 2
        if mutate == 'source': changed['sources'][0]['revision'] = 2
        with pytest.raises(ValueError): product.validate_step(step, changed, q, task())


@pytest.mark.parametrize('quote', ['3 · 4 = 13', '3 · 4 = 12 falsch', '3 · 4 = 12 und 2 · 6 = 12',
    'Teilbarkeit', '3 : 4 = 12', '23 · 4 = 12', '-3 · 4 = 12', '3 · 4 = 12,5'])
def test_invalid_or_unsupported_examples_are_not_generated(quote):
    ctx, t = context(), task()
    ctx['sources'][0]['content'] = quote
    t['source_excerpt'] = quote
    assert product.compile_candidate(ctx, t) is None


def test_source_scope_and_history():
    ctx, t = context(), task()
    assert product.compile_candidate(ctx, t, ['Wie viele Teiler hat 12?']) is None
    t['label'] = 'kgV'
    assert product.compile_candidate(ctx, t) is None
    t = task()
    t['source_excerpt'] = '3 · 4 = 12'
    ctx['sources'][0]['content'] = 'Ein Teilerabschnitt ohne Multiplikation'
    assert product.compile_candidate(ctx, t) is None
    ctx = context()
    ctx['sources'].append({**ctx['sources'][0], 'ref': 'p2'})
    assert product.compile_candidate(ctx, t) is None


def test_rejects_hidden_correction_and_blocked_source():
    ctx = context()
    ctx['sources'][0]['content'] += ' – falsch'
    assert product.compile_candidate(ctx, task()) is None
    ctx = context()
    ctx['sources'][0]['factual_status'] = 'blocked'
    assert product.compile_candidate(ctx, task()) is None
