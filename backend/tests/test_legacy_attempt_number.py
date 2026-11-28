"""Malformed historic metadata never breaks reads or invents independent evidence."""

import pytest
from sqlalchemy import select
from schulpilot.db import DB, Activity, Attempt, LearningUnit
from schulpilot.learning_progress import read_ledger, read_task_ledger, totals
from test_learning import child_client, prepared


@pytest.mark.parametrize('number', ['not-a-number', '2', True, False, 1.2, -1, 0, 10**25, [], {}])
def test_invalid_number_never_claims_independent_success(api, number):
    demo, unit_id = prepared(api)
    with DB.begin() as db:
        db.add(Attempt(unit_id=unit_id, question_id='sum', answer='synthetic', outcome='correct', assisted=False,
                       evaluation={'attempt_number': number}, created=100))
    with DB() as db:
        summary = totals(read_ledger(db, demo['child_id']))
        assert summary['practiced_tasks'] == summary['uncertain_tasks'] == 1
        assert summary['independent_tasks'] == summary['assisted_tasks'] == 0
        row = read_task_ledger(db, demo['child_id'])[0]
        assert row['independence_uncertain'] is True
        assert db.scalar(select(Attempt).where(Attempt.unit_id == unit_id)).evaluation['attempt_number'] == number


def test_equal_timestamp_with_invalid_sequence_has_uncertain_outcome(api):
    demo, unit_id = prepared(api)
    with DB.begin() as db:
        db.add_all([
            Attempt(id='0'*32, unit_id=unit_id, question_id='sum', answer='synthetic first', outcome='correct', assisted=False,
                    evaluation={'attempt_number': 1}, created=100),
            Attempt(id='f'*32, unit_id=unit_id, question_id='sum', answer='synthetic other', outcome='incorrect', assisted=False,
                    evaluation={'attempt_number': 'not-a-number'}, created=100),
        ])
    with DB() as db:
        summary = totals(read_ledger(db, demo['child_id']))
        assert summary['practiced_tasks'] == summary['uncertain_tasks'] == 1
        assert summary['attempts'] == 2 and summary['independent_tasks'] == summary['needs_practice_tasks'] == 0
        assert read_task_ledger(db, demo['child_id'])[0]['outcome'] == 'uncertain'
        assert db.scalar(select(Attempt).where(Attempt.id == 'f'*32)).outcome == 'incorrect'


def test_legacy_metadata_does_not_break_start_or_modify_attempt(api):
    demo, unit_id = prepared(api)
    with DB.begin() as db:
        db.add(Attempt(unit_id=unit_id, question_id='sum', answer='synthetic', outcome='incorrect', assisted=False,
                       evaluation={'attempt_number': 'not-a-number'}, created=100))
    with child_client(demo) as child:
        first = child.post(f'/api/units/{unit_id}/start')
        assert first.status_code == 200, first.text
        second = child.post(f'/api/units/{unit_id}/start')
        assert second.status_code == 200, second.text
    with DB() as db:
        assert db.get(LearningUnit, unit_id).status == 'active'
        rows = list(db.scalars(select(Attempt).where(Attempt.unit_id == unit_id)))
        assert len(rows) == 1 and rows[0].evaluation == {'attempt_number': 'not-a-number'}
        assert len(list(db.scalars(select(Activity).where(Activity.unit_id == unit_id, Activity.kind == 'unit_started')))) == 1


def test_failed_start_projection_rolls_back_status_and_start_event(api, monkeypatch):
    from schulpilot import learning

    demo, unit_id = prepared(api)
    with DB() as db:
        original_status = db.get(LearningUnit, unit_id).status
    def broken_projection(*args, **kwargs):
        raise RuntimeError('synthetic projection failure')
    monkeypatch.setattr(learning, 'unit_data', broken_projection)
    with child_client(demo) as child:
        assert child.post(f'/api/units/{unit_id}/start').status_code == 500
    with DB() as db:
        assert db.get(LearningUnit, unit_id).status == original_status
        assert not list(db.scalars(select(Activity).where(Activity.unit_id == unit_id, Activity.kind == 'unit_started')))


@pytest.mark.parametrize('value', ['broken', 'false', 'true', 0, 1, [], {}])
def test_invalid_independence_marker_never_claims_independent_success(api, value):
    demo, unit_id = prepared(api)
    with DB.begin() as db:
        db.add(Attempt(unit_id=unit_id, question_id='sum', answer='synthetic', outcome='correct', assisted=False,
                       evaluation={'attempt_number': 1, 'independence_uncertain': value}, created=100))
    with DB() as db:
        summary = totals(read_ledger(db, demo['child_id']))
        assert summary['practiced_tasks'] == summary['uncertain_tasks'] == 1
        assert summary['independent_tasks'] == summary['assisted_tasks'] == 0
        assert read_task_ledger(db, demo['child_id'])[0]['independence_uncertain'] is True
        assert db.scalar(select(Attempt).where(Attempt.unit_id == unit_id)).evaluation['independence_uncertain'] == value
