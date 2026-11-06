"""Synthetic group-scope groundwork; no package request or provider call."""
import copy

from schulpilot import study_fraction_expansions as expansion
from test_study_fraction_expansions import prepared


def grouped(household):
    _, _, planned, _, _, _ = prepared(household)
    context = copy.deepcopy(planned['visual_context'])
    original = context['sources'][0]
    original['group_id'] = 'g1'
    other = copy.deepcopy(original)
    other.update(ref='p2', group_id='g2', material_id='2' * 32,
                 content='Beim Erweitern multiplizierst du Zähler und Nenner mit derselben Zahl. 1/2')
    unrelated = copy.deepcopy(original)
    unrelated.update(ref='p3', group_id='g1', subject='Deutsch', material_id='3' * 32)
    curated = copy.deepcopy(original)
    curated.update(ref='p4', source_type='curated_foundation')
    context['sources'] = [original, other, unrelated, curated]
    return context, planned['math_tasks'][0]


def test_selected_package_group_never_receives_another_groups_or_curated_source(household):
    context, task = grouped(household)
    assert expansion._sources(context) == []
    assert [row['ref'] for row in expansion._sources(context, group_id='g1')] == ['p1']
    assert [row['ref'] for row in expansion._sources(context, group_id='g2')] == ['p2']
    first = expansion._candidate(context, task, 'apply', group_id='g1')
    second = expansion._candidate(context, task, 'apply', group_id='g2')
    assert first['group_id'] == 'g1' and first['source_refs'] == ['p1']
    assert second['group_id'] == 'g2' and second['source_refs'] == ['p2']
    assert first['id'] != second['id']
    assert first['proof']['source_digest'] != second['proof']['source_digest']
    assert first['proof']['task'] == second['proof']['task']
    assert expansion._candidate(context, task, 'apply', group_id='g3') is None


def test_grouped_introduction_preserves_scope_and_never_adopts_task_solution(household):
    context, task = grouped(household)
    candidate = expansion._candidate(context, task, 'apply', group_id='g1')
    intros = expansion._introductions(context, [candidate], group_id='g1')
    assert intros
    assert all(row['group_id'] == 'g1' and row['source_refs'] == ['p1'] for row in intros)
    assert all(row['disclosure'] == 'given' for row in intros)
    assert all(row['block']['numbers'] != candidate['proof']['output'] for row in intros)
    assert expansion._introductions(context, [candidate], group_id='missing') == []


def test_grouped_source_revision_and_reference_digest_bind_distinct_proof_ids(household):
    context, task = grouped(household)
    original = expansion._candidate(context, task, 'apply', group_id='g1')
    revised = copy.deepcopy(context)
    revised['sources'][0]['revision'] += 1
    changed_source = expansion._candidate(revised, task, 'apply', group_id='g1')
    assert changed_source['proof']['source_digest'] != original['proof']['source_digest']
    assert changed_source['id'] != original['id']
    changed = copy.deepcopy(context)
    reference = next(row for row in changed['references'] if row['id'] == expansion.RECIPE)
    reference['digest'] = '0' * 64
    changed_reference = expansion._candidate(changed, task, 'apply', group_id='g1')
    assert changed_reference['proof']['reference_digest'] != original['proof']['reference_digest']
    assert changed_reference['id'] != original['id']
    # The higher-level validator must still verify the reference digest against
    # its stored immutable recipe. This helper binds it but does not certify it.
