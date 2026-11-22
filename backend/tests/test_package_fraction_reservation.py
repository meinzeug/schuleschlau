"""Real package authorization/locking on synthetic sources; never calls AI."""
import copy
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from schulpilot import learning_entry, package_fraction_reservation as reservation, visual_references, worker
from schulpilot import package_fraction_plan as fractions
from schulpilot.db import DB, Child, Job, LearningUnit, Material, SchoolDay, Session
from schulpilot.school_day import validate_package_sources
from schulpilot.providers import ProviderError
from test_package_fraction_plan_groundwork import EXPAND
from test_school_preparation_parts import make_day
from test_package_parts_worker import preparation


def running_job(api, household, content=EXPAND, *, count=1):
    day_id = make_day(household, count=count)
    with DB.begin() as db:
        for page in db.scalars(select(Material).where(Material.school_day_id == day_id)):
            page.subject, page.topic, page.content = 'Mathematik', 'Brüche', content
    preparation(api, day_id, 'synthetic-fraction-reservation')
    with DB() as db:
        job_id = worker.claim(db)
    assert job_id
    with DB() as db:
        job = db.get(Job, job_id)
        child = db.get(Child, job.child_id)
        _, pages = validate_package_sources(db, job)
        groups = job.payload['groups']
        selected = [{'id': g['id'], 'subject': g['subject'], 'estimated_minutes': g['estimated_minutes']} for g in groups]
        value = {'package_partition': job.payload['package_partition'],
                 'package_plan_digest': job.payload['package_plan_digest'], 'selected_groups': selected,
                 'materials': []}
        value = visual_references.with_visual_context(db, child, value, pages, groups=groups)
        value = learning_entry.with_learning_entry(db, child, value, pages, groups=groups, enabled=True)
        value = learning_entry.limit_partition_probes(value)
        value = visual_references.with_foundation_context(db, value)
    return day_id, job_id, value


def test_authorized_job_persists_one_immutable_plan_and_replays(api, household):
    _, job_id, request = running_job(api, household)
    with DB.begin() as db:
        result = reservation.prepare(db, job_id, request)
        plan = copy.deepcopy(result['package_fraction_plan'])
        assert plan['operation'] == 'expand'
        assert len([x for x in plan['slots'] if x['task']]) >= 1
    with DB.begin() as db:
        assert db.get(Job, job_id).payload['package_fraction_plan'] == plan
        replay = reservation.prepare(db, job_id, request)
        assert replay['package_fraction_plan'] == plan
    response = api.get(f'/api/jobs/{job_id}')
    assert response.status_code == 200
    assert 'package_fraction_plan' not in response.text and EXPAND not in response.text


@pytest.mark.parametrize('fault', ['changed_source', 'foreign_group', 'changed_partition', 'revoked_session',
                                   'forged_source_text', 'forged_source_ref', 'changed_minutes', 'same_revision'])
def test_changed_authority_or_source_never_persists_a_plan(api, household, fault):
    day_id, job_id, request = running_job(api, household)
    if fault == 'foreign_group': request['selected_groups'][0]['id'] = 'foreign'
    if fault == 'changed_partition': request['package_partition'] += 1
    if fault == 'changed_minutes': request['selected_groups'][0]['estimated_minutes'] += 1
    if fault == 'forged_source_text': request['visual_context']['sources'][0]['content'] += ' Erfundener Zusatz.'
    if fault == 'forged_source_ref': request['visual_context']['sources'][0]['ref'] = 'p999'
    if fault in ('changed_source', 'same_revision', 'revoked_session'):
        with DB.begin() as db:
            if fault in ('changed_source', 'same_revision'):
                page = db.scalar(select(Material).where(Material.school_day_id == day_id))
                page.content += ' Text geändert.'
                if fault == 'changed_source': page.revision += 1
            else:
                day = db.get(SchoolDay, day_id)
                db.get(Session, day.preparation['session_id']).revoked = True
    with pytest.raises((ValueError, HTTPException, ProviderError)):
        with DB.begin() as db:
            reservation.prepare(db, job_id, request)
    with DB() as db:
        assert 'package_fraction_plan' not in db.get(Job, job_id).payload


def test_later_saved_matching_question_rejects_replay_without_erasing_plan(api, household):
    _, job_id, request = running_job(api, household)
    with DB.begin() as db:
        plan = reservation.prepare(db, job_id, request)['package_fraction_plan']
        child_id = db.get(Job, job_id).child_id
    prompt = next(row['task']['prompt'] for row in plan['slots'] if row['task'])
    with DB.begin() as db:
        db.add(LearningUnit(child_id=child_id, subject='Mathematik', topic='Künstlich', explanation='',
                            provider='synthetic-test', questions=[{'prompt': prompt}]))
    with pytest.raises(ValueError):
        with DB.begin() as db:
            reservation.prepare(db, job_id, request)
    with DB() as db:
        assert db.get(Job, job_id).payload['package_fraction_plan'] == plan


def test_result_rechecks_actual_plan_task_and_both_graphics(api, household):
    _, job_id, request = running_job(api, household)
    with DB.begin() as db:
        bound = reservation.prepare(db, job_id, request)
    plan = bound['package_fraction_plan']
    questions = []
    for row in plan['slots']:
        if row['task'] is None:
            questions.append({**row['slot']})
        else:
            step = fractions.solution_step(plan, row)
            questions.append({**row['task'], 'explanation': step['text'], 'explanation_steps': [step]})
    data = {'units': [{'group_id': plan['group_id'], 'subject': 'Mathematik', 'questions': questions}]}
    with DB.begin() as db:
        reservation.validate_result(db, job_id, bound, data)
    altered = copy.deepcopy(data)
    planned_question = next(q for q in altered['units'][0]['questions'] if q.get('explanation_steps'))
    planned_question['explanation_steps'][0]['presentation']['blocks'][1]['numbers'][0] += 1
    with pytest.raises(ValueError):
        with DB.begin() as db:
            reservation.validate_result(db, job_id, bound, altered)
    with DB() as db:
        assert db.get(Job, job_id).payload['package_fraction_plan'] == plan


def test_result_rejects_revoked_session_after_reservation(api, household):
    day_id, job_id, request = running_job(api, household)
    with DB.begin() as db:
        bound = reservation.prepare(db, job_id, request)
    with DB.begin() as db:
        day = db.get(SchoolDay, day_id)
        db.get(Session, day.preparation['session_id']).revoked = True
    with pytest.raises(HTTPException) as caught:
        with DB.begin() as db:
            reservation.validate_result(db, job_id, bound, {'units': []})
    assert caught.value.status_code == 401


def test_concurrent_claims_of_same_job_store_one_identical_plan(api, household):
    _, job_id, request = running_job(api, household)
    with DB() as db:
        if db.bind.dialect.name != 'postgresql':
            pytest.skip('Row-lock ordering requires isolated PostgreSQL')
    barrier = Barrier(2)
    def reserve(_):
        barrier.wait(timeout=10)
        with DB.begin() as db:
            return reservation.prepare(db, job_id, copy.deepcopy(request))['package_fraction_plan']
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.map(reserve, (1, 2))
    assert first == second
    with DB() as db:
        assert db.get(Job, job_id).payload['package_fraction_plan'] == first
