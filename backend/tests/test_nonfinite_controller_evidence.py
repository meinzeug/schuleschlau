"""Synthetic legacy timestamps cannot count as independent controller evidence."""
import math

import pytest
from sqlalchemy import select
from schulpilot.db import DB, Attempt
from test_adaptive_plan import fraction_profile as fraction_profile


@pytest.mark.parametrize('stamp', [float('inf'), float('-inf'), float('nan')], ids=['positive-infinity', 'negative-infinity', 'nan'])
def test_controller_does_not_claim_independent_answer_with_nonfinite_time(fraction_profile, stamp):
    client, uid, _, _, _, _ = fraction_profile
    with DB.begin() as db:
        if math.isnan(stamp) and db.bind.dialect.name == 'sqlite':
            pytest.skip('SQLite stores NaN as NULL, disallowed by Attempt.created')
        db.add(Attempt(unit_id=uid, question_id='sum', answer='synthetic', outcome='correct', assisted=False,
                       evaluation={'attempt_number': 1}, created=stamp))
    response = client.get(f'/api/units/{uid}/learning-session')
    assert response.status_code == 200, response.text
    assert response.json()['observations']['independent_first_answers'] == 0
    assert response.json()['observations']['attempts'] == 1
    with DB() as db:
        attempt = db.scalar(select(Attempt).where(Attempt.unit_id == uid))
        assert attempt.outcome == 'correct' and attempt.assisted is False
        assert math.isnan(attempt.created) if math.isnan(stamp) else attempt.created == stamp


@pytest.mark.parametrize('assisted,marker,expected', [(False, False, 1), (True, False, 0), (False, True, 0)])
def test_valid_time_preserves_actual_help_and_independence(fraction_profile, assisted, marker, expected):
    client, uid, _, _, _, _ = fraction_profile
    with DB.begin() as db:
        db.add(Attempt(unit_id=uid, question_id='sum', answer='synthetic', outcome='correct', assisted=assisted,
                       evaluation={'attempt_number': 1, 'independence_uncertain': marker}, created=1700000000))
    response = client.get(f'/api/units/{uid}/learning-session')
    assert response.status_code == 200, response.text
    assert response.json()['observations']['independent_first_answers'] == expected
    with DB() as db:
        attempt = db.scalar(select(Attempt).where(Attempt.unit_id == uid))
        assert attempt.assisted is assisted and attempt.evaluation['independence_uncertain'] is marker
