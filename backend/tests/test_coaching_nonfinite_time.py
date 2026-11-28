"""Non-finite historical attempt dates are not independent coaching evidence."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import math

import pytest
from sqlalchemy import select
from schulpilot import coaching
from schulpilot.db import DB, Attempt, Child, LearningUnit, UnitCoaching
from schulpilot.learning import local_day
from schulpilot.synthetic import CONTENT
from test_coaching import normal_unit as normal_unit
from test_coaching_encounter_order import make_round


def _new_round(db, root, material_id, timestamp, prompt):
    unit, attempt = make_round(db, root, material_id, answered=timestamp,
                               completed=timestamp + 100, prompt=prompt)
    return unit, attempt


@pytest.mark.parametrize('bad', [float('inf'), float('-inf'), float('nan')], ids=['positive-infinity', 'negative-infinity', 'nan'])
def test_unknown_attempt_time_is_never_a_coaching_success(normal_unit, bad):
    _, root_id, material_id, _, kid = normal_unit
    with DB.begin() as db:
        if math.isnan(bad) and db.bind.dialect.name == 'sqlite':
            pytest.skip('SQLite maps NaN to NULL, which is prohibited for Attempt.created')
        root = db.get(LearningUnit, root_id)
        stamp = 1700000000
        db.add(UnitCoaching(unit_id=root_id, status='ready', report={'learning_goals': [
            {'id': 'g1', 'label': 'Brüche Lernziel', 'source_excerpt': CONTENT[:100]}]}))
        unit, attempt = _new_round(db, root, material_id, stamp, 'Addiere 1/4 + 1/4.')
        attempt.created = bad
        db.flush()
        observation = coaching.observations(db, unit)[0]
        assert observation['deterministic_outcome'] == 'uncertain'
        assert observation['time_uncertain'] is True
        assert observation['attempts'][0]['outcome'] == 'correct'  # Preserve the actual stored verdict.
        assert coaching.independently_correct(db, unit) is False
        goal = coaching.goal_states(db, root)[0]
        assert goal['practice']['uncertain_tasks'] == 1
        assert goal['practice']['independent_tasks'] == 0
        assert goal['successful_check_dates'] == []
        assert not goal['secure_observation']
        assert math.isnan(attempt.created) if math.isnan(bad) else attempt.created == bad
        assert attempt.outcome == 'correct'
        attempt_id = attempt.id
    with DB() as db:
        preserved = db.get(Attempt, attempt_id)
        assert math.isnan(preserved.created) if math.isnan(bad) else preserved.created == bad
        assert preserved.outcome == 'correct'


def test_unknown_earlier_exposure_cannot_make_an_identical_later_question_fresh(normal_unit):
    _, root_id, material_id, _, kid = normal_unit
    with DB.begin() as db:
        root = db.get(LearningUnit, root_id)
        today = local_day(db.get(Child, kid['id']))
        stamp = int(datetime.combine(today, datetime.min.time(), ZoneInfo('Europe/Berlin')).timestamp()) + 3600
        db.add(UnitCoaching(unit_id=root_id, status='ready', report={'learning_goals': [
            {'id': 'g1', 'label': 'Brüche Lernziel', 'source_excerpt': CONTENT[:100]}]}))
        _, invalid = _new_round(db, root, material_id, stamp - 9 * 86400, 'Addiere 1/4 + 1/4.')
        invalid.created = float('inf')
        _new_round(db, root, material_id, stamp - 5 * 86400, 'Addiere 1/4 + 1/4.')
        _new_round(db, root, material_id, stamp - 86400, 'Addiere 1/3 + 1/3.')
        db.flush()
        goal = coaching.goal_states(db, root)[0]
        assert goal['practice']['practiced_tasks'] == 3
        assert goal['practice']['uncertain_tasks'] == 1
        assert goal['practice']['independent_tasks'] == 2
        assert goal['successful_check_dates'] == [(today - timedelta(days=1)).isoformat()]
        assert not goal['secure_observation']
        assert db.get(Attempt, invalid.id).outcome == 'correct'


def test_unknown_retry_order_does_not_claim_a_supported_or_independent_latest_answer(normal_unit):
    _, root_id, material_id, _, _ = normal_unit
    with DB.begin() as db:
        root = db.get(LearningUnit, root_id)
        db.add(UnitCoaching(unit_id=root_id, status='ready', report={'learning_goals': [
            {'id': 'g1', 'label': 'Brüche Lernziel', 'source_excerpt': CONTENT[:100]}]}))
        unit, first = _new_round(db, root, material_id, 1700000000, 'Addiere 1/4 + 1/4.')
        first.created = float('-inf')
        first.outcome = 'incorrect'
        db.add(Attempt(unit_id=unit.id, question_id='q', answer='synthetic retry', outcome='correct', assisted=False,
                       created=1700000001, evaluation={'attempt_number': 2}))
        db.flush()
        result = coaching.observations(db, unit)[0]
        assert result['deterministic_outcome'] == 'uncertain'
        assert len(result['attempts']) == 2
        goal = coaching.goal_states(db, root)[0]
        assert goal['practice']['uncertain_tasks'] == 1
        assert goal['practice']['assisted_tasks'] == goal['practice']['independent_tasks'] == 0
        assert goal['successful_check_dates'] == []
        assert db.scalar(select(Attempt).where(Attempt.id == first.id)).outcome == 'incorrect'


def test_coaching_paths_keep_a_separate_subject_visible_when_one_time_is_unknown(normal_unit):
    import copy
    _, root_id, material_id, _, kid = normal_unit
    with DB.begin() as db:
        root = db.get(LearningUnit, root_id)
        root.status = 'completed'
        root.completed = 1700000000
        db.add(UnitCoaching(unit_id=root_id, status='ready', report={'learning_goals': [
            {'id': 'g1', 'label': 'Brüche Lernziel', 'source_excerpt': CONTENT[:100]}]}))
        _, bad = _new_round(db, root, material_id, 1700000000, 'Addiere 1/4 + 1/4.')
        bad.created = float('inf')
        other = LearningUnit(child_id=root.child_id, subject='Biologie', topic='Pflanzen',
                             explanation=root.explanation, questions=copy.deepcopy(root.questions),
                             provider='synthetic', synthetic=True, status='completed', completed=1700000000)
        db.add(other)
        db.flush()
        paths = coaching.paths(db, kid['id'], ledger=[])
        assert {p['root_unit_id'] for p in paths} >= {root.id, other.id}
        affected = next(p for p in paths if p['root_unit_id'] == root.id)
        assert not affected['secure_observation']
        assert affected['learning_goals'][0]['practice']['uncertain_tasks'] == 1
        assert affected['successful_check_dates'] == []
