"""Synthetic multi-day journey through actual planner and worker entry points.

No network/model call is made. Only fixture school content and independent test
accounts are used; a clock is applied before each answer is inserted.
"""
import copy
from datetime import datetime, timedelta, timezone

import pytest
from schulpilot import auth, coaching, learning, security, study_authority, worker
from schulpilot import db as database
from schulpilot.db import DB, Assignment, Attempt, Child, Family, Job, LearningUnit, Material, UnitSource, now
from schulpilot.providers import Result
from sqlalchemy import event, func, select
from test_coaching import normal_unit as original_profile
from test_coaching import process_next


@pytest.fixture
def profile(api, household):
    yield from original_profile.__wrapped__(api, household)


def test_actual_planner_creates_source_bound_recall_over_multiple_days(profile, monkeypatch, request):
    client, root_id, material_id, _, child = profile
    child_id = child['id']
    today = datetime.fromtimestamp(int(now()), timezone.utc).date()
    base = int(datetime(today.year, today.month, today.day, 12, tzinfo=timezone.utc).timestamp())
    clock = [base]
    for module in (database, auth, security, study_authority):
        monkeypatch.setattr(module, 'now', lambda: clock[0])
    monkeypatch.setattr(learning, 'now', lambda: clock[0])
    monkeypatch.setattr(learning, 'local_day', lambda _: datetime.fromtimestamp(clock[0], timezone.utc).date())
    def stamp_attempt(_mapper, _connection, attempt):
        if attempt.created is None:
            attempt.created = clock[0]
    event.listen(Attempt, 'before_insert', stamp_attempt)
    request.addfinalizer(lambda: event.remove(Attempt, 'before_insert', stamp_attempt))
    with DB.begin() as db:
        kid = db.get(Child, child_id)
        family = db.get(Family, kid.family_id)
        family.call_limit, family.budget_micros = 100, 100_000_000
        kid.preferences = {**kid.preferences, 'timezone': 'UTC', 'weekdays': list(range(7)), 'daily_minutes': 20}
        later = Assignment(child_id=child_id, kind='parent', subject='Englisch', topic='Künstlicher Auftrag',
            mandatory=True, scheduled_for=(today + timedelta(days=60)).isoformat())
        db.add(later)
        db.flush()
        assignment_id = later.id
        revision = db.get(Material, material_id).revision

    provider_calls = []
    current_unit = [root_id]
    def coach_provider(_config, function, payload):
        assert function == 'coach' and payload['defer_practice'] is True
        provider_calls.append(('coach', current_unit[0]))
        with DB() as db:
            output = coaching.synthetic_report(db, db.get(LearningUnit, current_unit[0]), payload['next_action'])
            output['next_unit'] = None
        return Result(output, 100, 100, 0)
    def exercise_provider(_config, function, payload, *_args, **_kwargs):
        assert function == 'unit' and payload['review'] is True
        provider_calls.append(('unit', current_unit[0]))
        with DB() as db:
            output = coaching.synthetic_report(db, db.get(LearningUnit, current_unit[0]), 'check')['next_unit']
        return Result(output, 100, 100, 0)
    monkeypatch.setattr(coaching, 'request_provider', coach_provider)
    monkeypatch.setattr(worker, 'request_provider', exercise_provider)

    def complete(unit_id):
        current_unit[0] = unit_id
        r = client.post(f'/api/units/{unit_id}/start')
        assert r.status_code == 200, r.text
        with DB() as db:
            questions = copy.deepcopy(db.get(LearningUnit, unit_id).questions)
        for i, question in enumerate(questions):
            r = client.post(f"/api/units/{unit_id}/questions/{question['id']}/answer",
                json={'answer': question['answer'], 'request_id': f'journey-{unit_id}-{i}'})
            assert r.status_code == 200, r.text
            assert r.json()['outcome'] == 'correct' and not r.json()['assisted']
        assert r.json()['unit']['status'] == 'completed'
        process_next()
        result = client.get(f'/api/units/{unit_id}').json()
        assert result['coaching']['status'] == 'ready', result['coaching']
        return questions

    seen = {q['prompt'] for q in complete(root_id)}
    with DB() as db:
        before_jobs = db.scalar(select(func.count()).select_from(Job))
    for _ in range(2):
        assert client.get(f'/api/children/{child_id}/overview?compact=true').status_code == 200
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Job)) == before_jobs
    generated = []
    for index in range(12):
        with DB() as db:
            path = coaching.progress(db, db.get(LearningUnit, root_id))
            due = path['next_review']
            assert due is not None
        day = datetime.fromisoformat(due).replace(hour=12, tzinfo=timezone.utc)
        clock[0] = int(day.timestamp())
        # Each simulated school day starts with an actual new session. This
        # exercises expiry rather than extending a real or stored session.
        client.headers.pop('Authorization', None)
        login = client.post('/api/auth/login', json={'username': 'test-child', 'password': 'secure-child-pass-123'})
        assert login.status_code == 200, login.text
        client.headers['Authorization'] = 'Bearer ' + login.json()['token']
        overview = client.get(f'/api/children/{child_id}/overview?compact=true')
        assert overview.status_code == 200, overview.text
        plan = overview.json()['plan']
        review = next(x for x in plan['today'] if x['kind'] == 'review' and x['learning_root_id'] == root_id)
        assert review['due'] == due
        response = client.post(f'/api/children/{child_id}/units', json={'review_of': review['id']},
            headers={'Idempotency-Key': f'recall-journey-{index:04}'})
        assert response.status_code == 202, response.text
        job_id = response.json()['id']
        repeat = client.post(f'/api/children/{child_id}/units', json={'review_of': review['id']},
            headers={'Idempotency-Key': f'recall-journey-{index:04}'})
        assert repeat.status_code == 202 and repeat.json()['id'] == job_id
        assert process_next() == job_id
        with DB() as db:
            job = db.get(Job, job_id)
            assert job.status == 'completed', job.error
            unit_id = job.result['unit_id']
            unit = db.get(LearningUnit, unit_id)
            assert unit.learning_root_id == root_id and unit.round_kind == 'spaced_review'
            assert db.scalar(select(UnitSource.revision).where(UnitSource.unit_id == unit_id,
                UnitSource.material_id == material_id)) == revision
        questions = complete(unit_id)
        assert not seen.intersection(q['prompt'] for q in questions)
        seen.update(q['prompt'] for q in questions)
        generated.append(unit_id)
        with DB() as db:
            assert db.get(Assignment, assignment_id).scheduled_for == (today + timedelta(days=60)).isoformat()
            states = [g for g in coaching.goal_states(db, db.get(LearningUnit, root_id))
                      if g['assessment_applicable']]
            assert states
            selected = {q['learning_goal_id'] for q in questions}
            assert all(g['successful_check_dates'] for g in states if g['id'] in selected)
            status = coaching.progress(db, db.get(LearningUnit, root_id))
        if status['secure_observation']:
            break
    assert (datetime.fromtimestamp(clock[0], timezone.utc).date() - today).days >= 7
    with DB() as db:
        progress = coaching.progress(db, db.get(LearningUnit, root_id))
        assert progress['secure_observation']
        goals = [goal for goal in progress['learning_goals'] if goal['assessment_applicable']]
        assert goals
        for goal in goals:
            dates = [datetime.fromisoformat(day).date() for day in goal['successful_check_dates']]
            assert len(set(dates)) >= 3 and (max(dates) - min(dates)).days >= 7
        old_attempts = [(a.id, a.answer, a.created, a.outcome) for a in
            db.scalars(select(Attempt).where(Attempt.unit_id.in_([root_id, *generated])).order_by(Attempt.id))]
    with DB.begin() as db:
        db.get(Material, material_id).revision += 1
    with DB() as db:
        progress = coaching.progress(db, db.get(LearningUnit, root_id))
        assert progress['needs_source_review'] and not progress['secure_observation']
        assert [(a.id, a.answer, a.created, a.outcome) for a in
            db.scalars(select(Attempt).where(Attempt.unit_id.in_([root_id, *generated])).order_by(Attempt.id))] == old_attempts
        assert all(db.scalar(select(UnitSource.revision).where(UnitSource.unit_id == uid,
            UnitSource.material_id == material_id)) == revision for uid in generated)
    assert len([call for call in provider_calls if call[0] == 'unit']) == len(generated) >= 3
