"""Synthetic staged package history; no provider requests or real answers."""
import copy
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from schulpilot import package_decimal_addition as decimal
from schulpilot import package_partitions as parts
from schulpilot.db import DB, Child, Job, SchoolDay, Usage, User, now, uid
from schulpilot.package_question_history import unpublished_prompts_for_exclusion as unpublished_prompts
from test_package_partitions import output, plan, source


def staged(db, child, *, day_date, subject='Mathematik', first='Wie viel ist 1,2 + 3,4?',
           second='Wie viel ist 2,3 + 4,5?'):
    day = SchoolDay(child_id=child.id, school_date=day_date, stage='review')
    db.add(day)
    db.flush()
    planned = plan([source(0, subject=subject)], school_day_id=day.id, child_id=child.id)
    payload = output(planned['parts'][0])
    for question, prompt in zip(payload['units'][0]['questions'], (first, second), strict=True):
        question['prompt'] = prompt
        if prompt == 'Erweitere 2/3 mit dem Faktor 4.':
            question['answer'] = '8/12'
            question['explanation'] = 'Multipliziere Zähler und Nenner mit vier.'
    job_id = uid()
    job = Job(id=job_id, child_id=child.id, kind='package', status='completed',
        idempotency='history-' + job_id, payload={'school_day_id': day.id,
            'package_partition': 0, 'package_plan_digest': planned['digest']})
    usage = Usage(family_id=child.family_id, child_id=child.id, job_id=job_id,
        provider='synthetic', model='synthetic-model', config_revision=32, function='package',
        status='completed', reserved_micros=1000, bucket_ids=[])
    day.preparation = parts.store_validated_part({}, planned, 0, payload, job_id=job_id,
        provider='synthetic', model='synthetic-model', config_revision=32)
    db.add_all([job, usage])
    db.flush()
    return day, job


def sibling_for(db, child):
    user = User(username=f'synthetic-sibling-{uid()}@example.invalid', role='child',
        display_name='Synthetic sibling', password_hash='synthetic-unused')
    db.add(user)
    db.flush()
    sibling = Child(family_id=child.family_id, grade=6, user_id=user.id)
    db.add(sibling)
    db.flush()
    return sibling


def test_staged_prompts_are_child_subject_and_job_scoped(household):
    owner, child = household
    with DB.begin() as db:
        own = db.get(Child, child['id'])
        sibling = sibling_for(db, own)
        day, job = staged(db, own, day_date='2026-11-01')
        staged(db, own, day_date='2026-11-02', subject='Deutsch', first='Deutsch privat', second='Noch Deutsch')
        staged(db, sibling, day_date='2026-11-01', first='Sibling 7/8', second='Sibling 1/8')
        prompts = unpublished_prompts(db, own.id, 'Mathematik')
        assert prompts == ['Wie viel ist 1,2 + 3,4?', 'Wie viel ist 2,3 + 4,5?']
        assert unpublished_prompts(db, own.id, 'Mathematik', ignore_job_ids={job.id}) == []
        assert decimal.history(db, own.id) == [['1.2', '3.4'], ['2.3', '4.5']]
        assert day.preparation['package_outputs']['0']['output']['units'][0]['questions'][0]['prompt'] == prompts[0]


@pytest.mark.parametrize('damage', ['output', 'missing_job', 'wrong_child', 'wrong_usage', 'wrong_model', 'wrong_source'])
def test_unpublished_history_rejects_corrupt_or_wrong_owner(household, damage):
    owner, child = household
    with DB.begin() as db:
        own = db.get(Child, child['id'])
        day, job = staged(db, own, day_date='2026-11-01')
        if damage == 'output':
            state = copy.deepcopy(day.preparation)
            state['package_outputs']['0']['output']['units'][0]['questions'][0]['prompt'] = 'changed'
            day.preparation = state
        elif damage == 'missing_job':
            db.delete(job)
        elif damage == 'wrong_child':
            sibling = sibling_for(db, own)
            job.child_id = sibling.id
        elif damage == 'wrong_source':
            state = copy.deepcopy(day.preparation)
            state['package_outputs']['0']['source_signature'] = '0' * 64
            day.preparation = state
        else:
            usage = db.query(Usage).filter(Usage.job_id == job.id).one()
            if damage == 'wrong_model':
                usage.model = 'different-synthetic-model'
            else:
                usage.config_revision += 1
        db.flush()
        with pytest.raises(ValueError, match='Teilrundenbeleg'):
            unpublished_prompts(db, own.id, 'Mathematik')
def test_decimal_validation_rejects_matching_unpublished_part(household):
    from test_package_decimal_addition import wire

    _, child = household
    value, _, _, binding = wire()
    data = binding.hydrate(value)
    prompt = data['units'][0]['questions'][0]['prompt']
    with DB.begin() as db:
        own = db.get(Child, child['id'])
        _, job = staged(db, own, day_date='2026-11-01', first=prompt)
        with pytest.raises(ValueError, match='zwischenzeitlich'):
            decimal.validate_history(db, own.id, data)
        decimal.validate_history(db, own.id, data, ignore_job_ids={job.id})


def test_child_lock_serializes_two_identical_staged_candidates(household):
    from sqlalchemy import update

    _, child = household
    with DB() as db:
        if db.bind.dialect.name != 'postgresql':
            pytest.skip('Row-lock ordering needs isolated PostgreSQL')
    barrier = Barrier(2)
    prompt = 'Erweitere 2/3 mit dem Faktor 4.'

    def candidate(index):
        barrier.wait(timeout=10)
        with DB.begin() as db:
            db.execute(update(Child).where(Child.id == child['id']).values(grade=Child.grade))
            if prompt in unpublished_prompts(db, child['id'], 'Mathematik'):
                return 'rejected'
            staged(db, db.get(Child, child['id']), day_date=f'2026-11-0{index}', first=prompt)
            return 'stored'

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(candidate, [1, 2]))
    assert sorted(results) == ['rejected', 'stored']
    with DB() as db:
        assert unpublished_prompts(db, child['id'], 'Mathematik').count(prompt) == 1


def test_history_reloads_already_cached_day_after_other_transaction(household):
    _, child = household
    with DB.begin() as db:
        if db.bind.dialect.name != 'postgresql':
            pytest.skip('Concurrent transaction needs isolated PostgreSQL')
        day, _ = staged(db, db.get(Child, child['id']), day_date='2026-11-01')
        day_id = day.id
    with DB() as stale:
        cached = stale.get(SchoolDay, day_id)
        assert cached.preparation['package_outputs']
        with DB.begin() as fresh:
            fresh.get(SchoolDay, day_id).preparation = {}
        assert unpublished_prompts(stale, child['id'], 'Mathematik') == []
        assert cached.preparation == {}


@pytest.mark.parametrize('status', ['postponed', 'saved'])
@pytest.mark.parametrize('age_days', [31, 91])
def test_expired_inactive_receipt_is_only_an_unverified_exclusion(household, caplog, status, age_days):
    from schulpilot.preparation_retention import purge
    from sqlalchemy import select

    _, child = household
    stamp = int(now())
    with DB.begin() as db:
        own = db.get(Child, child['id'])
        day, job = staged(db, own, day_date='2026-08-01')
        job_id = job.id
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        day.created = job.created = usage.created = stamp - age_days * 86400
        state = copy.deepcopy(day.preparation)
        state.update(status=status)
        day.preparation = state
        db.flush()
        purge(db, stamp)
        db.flush()
        db.expire_all()
        assert db.get(Job, job_id) is None
        assert (db.scalar(select(Usage).where(Usage.job_id == job_id)) is None) == (age_days > 90)
        assert unpublished_prompts(db, own.id, 'Mathematik') == [
            'Wie viel ist 1,2 + 3,4?', 'Wie viel ist 2,3 + 4,5?']
        assert decimal.history(db, own.id) == [['1.2', '3.4'], ['2.3', '4.5']]
        assert 'expired_unverified_package_receipt_used_only_for_exclusion' in caplog.text
        assert 'Wie viel' not in caplog.text and 'Katze' not in caplog.text and own.id not in caplog.text


def test_missing_recent_or_active_job_remains_an_error(household):
    _, child = household
    with DB.begin() as db:
        own = db.get(Child, child['id'])
        day, job = staged(db, own, day_date='2026-08-01')
        state = copy.deepcopy(day.preparation)
        state['status'] = 'postponed'
        day.preparation = state
        db.delete(job)
        db.flush()
        with pytest.raises(ValueError, match='Teilrundenbeleg'):
            unpublished_prompts(db, own.id, 'Mathematik')
        day.created = int(now()) - 91 * 86400
        state['status'] = 'processing'
        day.preparation = state
        db.flush()
        with pytest.raises(ValueError, match='Teilrundenbeleg'):
            unpublished_prompts(db, own.id, 'Mathematik')


@pytest.mark.parametrize('status', ['postponed', 'saved'])
def test_old_inactive_job_without_usage_is_only_negative_exclusion(household, caplog, status):
    from sqlalchemy import select

    _, child = household
    with DB.begin() as db:
        own = db.get(Child, child['id'])
        day, job = staged(db, own, day_date='2026-08-01')
        day.created = job.created = int(now()) - 91 * 86400
        state = copy.deepcopy(day.preparation)
        state['status'] = status
        day.preparation = state
        usage = db.scalar(select(Usage).where(Usage.job_id == job.id))
        db.delete(usage)
        db.flush()
        assert unpublished_prompts(db, own.id, 'Mathematik') == [
            'Wie viel ist 1,2 + 3,4?', 'Wie viel ist 2,3 + 4,5?']
        assert 'expired_unverified_package_receipt_used_only_for_exclusion' in caplog.text
        assert 'Wie viel' not in caplog.text and own.id not in caplog.text
        job.kind = 'unit'
        db.flush()
        with pytest.raises(ValueError, match='Teilrundenbeleg'):
            unpublished_prompts(db, own.id, 'Mathematik')


@pytest.mark.parametrize('missing', ['job', 'usage'])
def test_old_day_does_not_excuse_a_recent_missing_receipt(household, missing):
    from sqlalchemy import select

    _, child = household
    with DB.begin() as db:
        own = db.get(Child, child['id'])
        day, job = staged(db, own, day_date='2026-08-01')
        day.created = int(now()) - 100 * 86400
        state = copy.deepcopy(day.preparation)
        state['status'] = 'saved'
        day.preparation = state
        if missing == 'job':
            db.delete(job)
        else:
            db.delete(db.scalar(select(Usage).where(Usage.job_id == job.id)))
        db.flush()
        with pytest.raises(ValueError, match='Teilrundenbeleg'):
            unpublished_prompts(db, own.id, 'Mathematik')


def test_normal_maintenance_still_removes_expired_day_and_receipts(household):
    from schulpilot import worker
    from sqlalchemy import select

    _, child = household
    with DB.begin() as db:
        day, job = staged(db, db.get(Child, child['id']), day_date='2025-10-01')
        day_id, job_id = day.id, job.id
        usage = db.scalar(select(Usage).where(Usage.job_id == job.id))
        day.created = job.created = usage.created = int(now()) - 366 * 86400
        state = copy.deepcopy(day.preparation)
        state['status'] = 'postponed'
        day.preparation = state
    worker.maintenance()
    with DB() as db:
        assert db.get(SchoolDay, day_id) is None
        assert db.get(Job, job_id) is None
        assert db.scalar(select(Usage).where(Usage.job_id == job_id)) is None
