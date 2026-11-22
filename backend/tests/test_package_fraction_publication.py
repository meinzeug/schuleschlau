"""Private post-provider package guard using synthetic sources and sessions."""
import copy

import pytest
from sqlalchemy import select, update
from schulpilot import package_fraction_plan as planner, package_fraction_reservation as reservation
from schulpilot.db import DB, Child, Job, LearningUnit, Material
from schulpilot.school_day import validate_package_sources
from test_package_fraction_reservation import running_job


def prepared(api, household):
    day_id, job_id, request = running_job(api, household)
    with DB.begin() as db:
        bound = reservation.prepare(db, job_id, request)
    plan = bound['package_fraction_plan']
    context = {'visual_context': copy.deepcopy(bound['visual_context']), 'learning_entry': bound['learning_entry']}
    context['visual_context']['package_fraction_plan'] = copy.deepcopy(plan)
    questions = []
    for row in plan['slots']:
        if row['task'] is None:
            questions.append({**row['slot']})
        else:
            step = planner.solution_step(plan, row)
            questions.append({**row['task'], 'explanation': step['text'], 'explanation_steps': [step]})
    output = {'units': [{'group_id': plan['group_id'], 'subject': 'Mathematik', 'questions': questions}]}
    with DB.begin() as db:
        db.get(Job, job_id).status = 'completed'
    return day_id, job_id, context, output, plan


def check(job_id, context, output):
    with DB.begin() as db:
        child_id = db.get(Job, job_id).child_id
        db.execute(update(Child).where(Child.id == child_id).values(grade=Child.grade))
        job = db.get(Job, job_id, populate_existing=True)
        child = db.get(Child, child_id, populate_existing=True)
        _, pages = validate_package_sources(db, job)
        return reservation.validate_publication(db, job, child, context, output, pages)


def test_publication_requires_both_identical_private_plans(api, household):
    _, job_id, context, output, plan = prepared(api, household)
    assert check(job_id, context, output) == plan
    del context['visual_context']['package_fraction_plan']
    with pytest.raises(ValueError):
        check(job_id, context, output)


@pytest.mark.parametrize('fault', ['plan', 'source', 'picture', 'answer', 'history'])
def test_publication_rejects_changed_source_output_or_history(api, household, fault):
    day_id, job_id, context, output, plan = prepared(api, household)
    if fault == 'plan': context['visual_context']['package_fraction_plan']['digest'] = '0' * 64
    if fault == 'source': context['visual_context']['sources'][0]['content'] += ' verändert'
    if fault in ('picture', 'answer'):
        q = next(q for q in output['units'][0]['questions'] if q.get('explanation_steps'))
        if fault == 'picture': q['explanation_steps'][0]['presentation']['blocks'][1]['numbers'][0] += 1
        else: q['answer'] = '1/99'
    if fault == 'history':
        prompt = next(row['task']['prompt'] for row in plan['slots'] if row['task'])
        with DB.begin() as db:
            job = db.get(Job, job_id)
            db.add(LearningUnit(child_id=job.child_id, subject='Mathematik', topic='Künstlich',
                explanation='', provider='synthetic-test', questions=[{'prompt': prompt}]))
    with pytest.raises(ValueError):
        check(job_id, context, output)
    with DB() as db:
        assert db.get(Job, job_id).payload['package_fraction_plan'] == plan


def test_legacy_receipt_without_plan_remains_unchanged(api, household):
    _, job_id, context, output, _ = prepared(api, household)
    del context['visual_context']['package_fraction_plan']
    with DB.begin() as db:
        job = db.get(Job, job_id)
        job.payload = {key: value for key, value in job.payload.items() if key != 'package_fraction_plan'}
    assert check(job_id, context, output) is None


def test_real_publish_endpoint_rejects_unmatched_private_plan_atomically(api, household, monkeypatch):
    from sqlalchemy import func
    from schulpilot.db import SchoolDay
    from test_package_prefix_publication import staged, publish

    day_id, _, _, calls = staged(api, household, monkeypatch)
    with DB.begin() as db:
        day = db.get(SchoolDay, day_id)
        job_id = day.preparation['package_outputs']['0']['job_id']
        job = db.get(Job, job_id)
        job.payload = {**job.payload, 'package_fraction_plan': {'invalid': True}}
    response = publish(api, household, day_id)
    assert response.status_code == 409
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(LearningUnit).where(LearningUnit.school_day_id == day_id)) == 0
        day = db.get(SchoolDay, day_id)
        assert day.package_version == 0 and '0' in day.preparation['package_outputs']
    assert len(calls) == 1


@pytest.mark.parametrize('content', [
    'Beim Erweitern multipliziert man Zähler und Nenner mit derselben Zahl. Beispiel: 1/2 = 2/4.',
    'Beim Kürzen teilt man Zähler und Nenner durch dieselbe Zahl. Beispiel: 2/4 = 1/2.'])
def test_planned_receipt_publishes_with_both_validated_models(api, household, content):
    from schulpilot import package_part_output, package_partitions, package_prepared_graphics, school_preparation, visual_references
    from schulpilot.db import SchoolDay, Usage
    from schulpilot.package_publication import publish_prefix
    from schulpilot.providers import Result, settle
    from schulpilot.schemas import PackageOutput

    day_id, job_id, request = running_job(api, household, content)
    with DB.begin() as db:
        bound = reservation.prepare(db, job_id, request)
    plan = bound['package_fraction_plan']
    bound['visual_context']['package_fraction_plan'] = copy.deepcopy(plan)
    candidates = package_prepared_graphics.compile_candidates(bound)
    intro = next(row for row in candidates if row['kind'] == 'fraction' and row['disclosure'] == 'given')
    prior = next(row for row in candidates if row['kind'] == 'fraction' and row['disclosure'] == 'solution' and not row.get('question_core'))
    def standard_step(row):
        return {'id': 'e1', 'text': row['text'], 'competence_id': None, 'disclosure': row['disclosure'],
                'reference': row['reference'], 'source_refs': row['source_refs'],
                'presentation': {'version': 1, 'evidence_kind': 'knowledge', 'blocks': [row['block']]}}
    questions = []
    for row in plan['slots']:
        if row['task'] is None:
            if row['slot'].get('type'):
                fixed = next(candidate for candidate in candidates if candidate['disclosure'] == 'solution'
                             and candidate.get('question_core', {}).get('id') == row['slot']['id'])
                core = fixed['question_core']
            else:
                fixed = prior
                numbers = prior['block']['numbers']
                core = {'id': row['slot']['id'], 'type': 'short',
                    'prompt': f'Was beschreibt der Bruch {numbers[0]}/{numbers[1]}?',
                    'answer': f'{numbers[0]} von {numbers[1]} gleich großen Teilen', 'options': [], 'accepted': []}
            questions.append({**core, 'hints': ['Denke an gleich große Teile.'],
                'explanation': fixed['text'], 'presentation': None, 'explanation_steps': [standard_step(fixed)]})
        else:
            step = planner.solution_step(plan, row)
            questions.append({**row['task'], 'hints': ['Achte auf Zähler und Nenner.'],
                'explanation': step['text'], 'presentation': None, 'explanation_steps': [step]})
    output = PackageOutput.model_validate({'units': [{'group_id': plan['group_id'], 'subject': 'Mathematik',
        'topic': 'Brüche', 'explanation': intro['text'],
        'explanation_steps': [standard_step(intro)], 'questions': questions}]}).model_dump(mode='json')
    package_part_output.validate(output, fraction_plan=plan)
    with DB() as db:
        visual_references.validate_output(db, output, bound)
    with DB.begin() as db:
        job = db.get(Job, job_id)
        day = db.get(SchoolDay, day_id)
        state = school_preparation._state(day)
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        state = package_partitions.store_validated_part(state, state['package_plan'], 0, output,
            job_id=job_id, provider=usage.provider, model=usage.model, config_revision=usage.config_revision,
            context={'visual_context': bound['visual_context'], 'learning_entry': bound['learning_entry']})
        school_preparation._write(day, state)
        settle(db, usage, Result({}, 1, 1, 1, cost_source='reported'))
        job.status = 'completed'
    with DB.begin() as db:
        job = db.get(Job, job_id)
        db.execute(update(Child).where(Child.id == job.child_id).values(grade=Child.grade))
        day, child = db.get(SchoolDay, day_id), db.get(Child, job.child_id)
        result = publish_prefix(db, day, child, day.preparation['package_plan'], complete=True)
        assert len(result['unit_ids']) == 1
        unit_id = result['unit_ids'][0]
    with DB() as db:
        unit = db.get(LearningUnit, unit_id)
        from schulpilot.visual_reference_models import UnitVisualSnapshot
        snapshot = db.get(UnitVisualSnapshot, unit.id)
        assert snapshot.status == 'ready'
        task_id = next(row['task']['id'] for row in plan['slots'] if row['task'])
        assert len(snapshot.question_steps[task_id][0]['presentation']['blocks']) == 2
        assert visual_references.public_steps(snapshot.question_steps[task_id], closed=False) == []
        assert len(visual_references.public_steps(snapshot.question_steps[task_id], closed=True)[0]['presentation']['blocks']) == 2
