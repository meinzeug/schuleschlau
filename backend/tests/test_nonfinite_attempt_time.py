"""Synthetic historical timestamps must not invent learning evidence."""
import math
import pytest
from sqlalchemy import select
from schulpilot.db import DB, Attempt, LearningUnit
from schulpilot.learning_progress import read_ledger, totals
from test_learning import child_client, prepared


@pytest.mark.parametrize('stamp', [float('inf'), float('-inf'), float('nan')], ids=['positive-infinity', 'negative-infinity', 'nan'])
def test_nonfinite_attempt_does_not_claim_independence_and_preserves_original(api, stamp):
    demo, unit_id = prepared(api)
    with DB.begin() as db:
        if math.isnan(stamp) and db.bind.dialect.name == 'sqlite':
            pytest.skip('SQLite normalizes NaN to NULL; the column disallows NULL')
        db.add(Attempt(unit_id=unit_id, question_id='sum', answer='synthetic', outcome='correct', assisted=False,
                       evaluation={'attempt_number': 1}, created=stamp))
    with DB() as db:
        progress = totals(read_ledger(db, demo['child_id']))
        assert progress['practiced_tasks'] == progress['uncertain_tasks'] == 1
        assert progress['independent_tasks'] == 0
        assert progress['last_activity'] is None
        original = db.scalar(select(Attempt).where(Attempt.unit_id == unit_id))
        assert math.isnan(original.created) if math.isnan(stamp) else original.created == stamp


def test_unknown_time_does_not_erase_other_question_evidence(api):
    from schulpilot.learning_progress import read_task_ledger

    demo, unit_id = prepared(api)
    with DB.begin() as db:
        db.add_all([
            Attempt(unit_id=unit_id, question_id='sum', answer='synthetic', outcome='correct', assisted=False,
                    evaluation={'attempt_number': 1}, created=float('inf')),
            Attempt(unit_id=unit_id, question_id='other', answer='synthetic', outcome='correct', assisted=False,
                    evaluation={'attempt_number': 1}, created=100),
        ])
    with DB() as db:
        result = totals(read_ledger(db, demo['child_id']))
        assert result['practiced_tasks'] == 2
        assert result['uncertain_tasks'] == 1 and result['independent_tasks'] == 1
        assert result['last_activity'] is None  # An unknown date may be later.
        by_question = {row['question_id']: row for row in read_task_ledger(db, demo['child_id'])}
        assert by_question['sum']['outcome'] == 'uncertain' and by_question['sum']['created'] is None
        assert by_question['other']['outcome'] == 'correct' and by_question['other']['created'] == 100


def test_unrelated_round_still_starts_with_unknown_other_round(api):
    import copy

    demo, unit_id = prepared(api)
    with DB.begin() as db:
        first = db.get(LearningUnit, unit_id)
        db.add(Attempt(unit_id=unit_id, question_id='sum', answer='synthetic', outcome='correct', assisted=False,
                       evaluation={'attempt_number': 1}, created=float('inf')))
        other = LearningUnit(child_id=first.child_id, subject='Biologie', topic='Pflanzen', explanation=first.explanation,
                             questions=copy.deepcopy(first.questions), provider='synthetic', synthetic=True)
        db.add(other)
        db.flush()
        other_id = other.id
    with child_client(demo) as child:
        response = child.post(f'/api/units/{other_id}/start')
        assert response.status_code == 200, response.text


def test_unordered_mixed_times_are_uncertain_without_fabricated_latest_date(api):
    from schulpilot.learning_progress import read_task_ledger

    demo, unit_id = prepared(api)
    with DB.begin() as db:
        db.add_all([
            Attempt(unit_id=unit_id, question_id='sum', answer='synthetic', outcome='incorrect', assisted=False,
                    evaluation={'attempt_number': 1}, created=float('-inf')),
            Attempt(unit_id=unit_id, question_id='sum', answer='synthetic', outcome='correct', assisted=False,
                    evaluation={'attempt_number': 2}, created=100),
        ])
    with DB() as db:
        result = totals(read_ledger(db, demo['child_id']))
        assert result['attempts'] == 2 and result['uncertain_tasks'] == 1
        assert result['last_activity'] is None and result['independent_tasks'] == result['assisted_tasks'] == 0
        item = read_task_ledger(db, demo['child_id'])[0]
        assert item['outcome'] == 'uncertain' and item['created'] is None


@pytest.mark.xfail(strict=True, reason='Coaching observations do not yet classify non-finite dates as uncertain')
def test_bad_times_must_not_become_coaching_success(api):
    from schulpilot.coaching import observations
    demo, unit_id = prepared(api)
    with DB.begin() as db:
        db.add(Attempt(unit_id=unit_id, question_id='sum', answer='synthetic', outcome='correct', assisted=False,
                       evaluation={'attempt_number': 1}, created=float('inf')))
    with DB() as db:
        value = next(q for q in observations(db, db.get(LearningUnit, unit_id)) if q['question_id'] == 'sum')
        assert value['deterministic_outcome'] == 'uncertain'


def test_nonfinite_ledger_does_not_cross_child_boundary(api):
    first, unit_id = prepared(api)
    second, _ = prepared(api)
    with DB.begin() as db:
        db.add(Attempt(unit_id=unit_id, question_id='sum', answer='synthetic', outcome='correct', assisted=False,
                       evaluation={'attempt_number': 1}, created=float('inf')))
    with DB() as db:
        assert totals(read_ledger(db, second['child_id']))['practiced_tasks'] == 0
        assert totals(read_ledger(db, first['child_id']))['uncertain_tasks'] == 1


def test_today_remains_available_with_completed_unrelated_round_and_unknown_time(api):
    demo, unit_id = prepared(api)
    with DB.begin() as db:
        unit = db.get(LearningUnit, unit_id)
        unit.status = 'completed'
        unit.completed = 100
        db.add(Attempt(unit_id=unit_id, question_id='sum', answer='synthetic', outcome='correct', assisted=False,
                       evaluation={'attempt_number': 1}, created=float('inf')))
    with child_client(demo) as child:
        response = child.get(f"/api/children/{demo['child_id']}/overview?compact=true")
        assert response.status_code == 200, response.text
        assert response.json()['subject_progress'][0]['independent_tasks'] == 0


@pytest.mark.xfail(strict=True, reason='Legacy overview still serializes the damaged raw timestamp')
def test_uncompacted_overview_lists_other_rounds_without_fake_questions(api):
    import copy

    demo, unit_id = prepared(api)
    with DB.begin() as db:
        first = db.get(LearningUnit, unit_id)
        db.add(Attempt(unit_id=unit_id, question_id='sum', answer='synthetic private', outcome='correct', assisted=False,
                       evaluation={'attempt_number': 1}, created=float('inf')))
        other = LearningUnit(child_id=first.child_id, subject='Biologie', topic='Pflanzen', explanation=first.explanation,
                             questions=copy.deepcopy(first.questions), provider='synthetic', synthetic=True)
        db.add(other)
        db.flush()
        other_id = other.id
    url = f"/api/children/{demo['child_id']}/overview"
    with child_client(demo) as child:
        for client in (child, api):
            response = client.get(url)
            assert response.status_code == 200, response.text
            units = {item['id']: item for item in response.json()['units']}
            assert other_id in units and unit_id in units


@pytest.mark.xfail(strict=True, reason='Round serialization still emits non-finite attempt timestamps')
def test_affected_round_should_not_return_an_internal_error(api):
    demo, unit_id = prepared(api)
    with DB.begin() as db:
        db.add(Attempt(unit_id=unit_id, question_id='sum', answer='synthetic', outcome='correct', assisted=False,
                       evaluation={'attempt_number': 1}, created=float('inf')))
    with child_client(demo) as child:
        response = child.get(f'/api/units/{unit_id}')
        assert response.status_code != 500
