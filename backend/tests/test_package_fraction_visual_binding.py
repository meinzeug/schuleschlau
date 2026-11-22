"""Synthetic source-only visual validation for private package plans."""
import copy

import pytest
from schulpilot import package_fraction_plan as planner, visual_references
from schulpilot.db import DB
from test_package_fraction_plan_groundwork import EXPAND, REDUCE, payload, slots


def sample(db, content):
    request = payload(content)
    request['visual_context']['references'] = []
    request = planner.add_reference(db, request)
    plan = planner.prepare(request, slots('practice', 'practice'), [])
    request['visual_context']['package_fraction_plan'] = copy.deepcopy(plan)
    row = plan['slots'][0]
    step = planner.solution_step(plan, row)
    question = {**row['task'], 'explanation': step['text']}
    return request, plan, question, step


@pytest.mark.parametrize('content', [EXPAND, REDUCE])
def test_original_plan_proves_both_fraction_models(household, content):
    with DB() as db:
        request, plan, question, step = sample(db, content)
        checked = visual_references.validate_steps(db, [step], 'Mathematik', request['visual_context'],
                                                   question=question, group_id='g1')
        assert checked == [step] and len(checked[0]['presentation']['blocks']) == 2


@pytest.mark.parametrize('fault', ['missing_plan', 'changed_plan', 'changed_source', 'changed_revision',
                                    'foreign_group', 'wrong_ref', 'wrong_answer', 'wrong_step', 'wrong_graphic',
                                    'premature', 'wrong_recipe', 'curated_source'])
def test_no_forged_or_foreign_fraction_proof_is_accepted(household, fault):
    with DB() as db:
        request, plan, question, step = sample(db, REDUCE)
        context = request['visual_context']
        group, intro = 'g1', False
        if fault == 'missing_plan': context.pop('package_fraction_plan')
        if fault == 'changed_plan': context['package_fraction_plan']['slots'][0]['task']['answer'] = '1/99'
        if fault == 'changed_source': context['sources'][0]['content'] += ' Altered.'
        if fault == 'changed_revision': context['sources'][0]['revision'] += 1
        if fault == 'foreign_group': group = 'other'
        if fault == 'wrong_ref': context['references'][0]['digest'] = 'f' * 64
        if fault == 'wrong_answer': question['answer'] = '1/99'
        if fault == 'wrong_step': step['id'] = 'pf_other'
        if fault == 'wrong_graphic': step['presentation']['blocks'][1]['numbers'][0] += 1
        if fault == 'premature': intro = True
        if fault == 'wrong_recipe': step['reference']['id'] = 'math.fraction.expansion'
        if fault == 'curated_source': context['sources'][0]['source_type'] = 'curated_foundation'
        with pytest.raises(ValueError):
            visual_references.validate_steps(db, [step], 'Mathematik', context,
                                             question=question, group_id=group, introduction=intro)
