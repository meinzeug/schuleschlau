"""Synthetic reproduction of the source-bound timestamp contract gap."""
import math

import pytest
from sqlalchemy import select

from schulpilot.db import Attempt, DB
from test_adaptive_plan import fraction_profile as fraction_profile


@pytest.mark.parametrize("stamp", [float("inf"), float("-inf"), float("nan")], ids=["positive-infinity", "negative-infinity", "nan"])
def test_knowledge_read_preserves_original_evidence_even_on_error(fraction_profile, stamp):
    client, uid, _, _, _, _ = fraction_profile
    with DB.begin() as db:
        if math.isnan(stamp) and db.bind.dialect.name == "sqlite":
            pytest.skip("SQLite converts NaN to NULL, which Attempt.created disallows")
        attempt = Attempt(unit_id=uid, question_id="sum", answer="synthetic", outcome="correct", assisted=False,
                          evaluation={"attempt_number": 1}, created=stamp)
        db.add(attempt)
        db.flush()
        attempt_id = attempt.id
    client.get(f"/api/units/{uid}/learning-session/knowledge")
    with DB() as db:
        original = db.scalar(select(Attempt).where(Attempt.id == attempt_id))
        assert original.answer == "synthetic" and original.outcome == "correct" and not original.assisted
        assert original.evaluation == {"attempt_number": 1}
        assert math.isnan(original.created) if math.isnan(stamp) else original.created == stamp


@pytest.mark.xfail(strict=True, reason="Source-bound knowledge still treats non-finite dates as dated evidence")
@pytest.mark.parametrize("stamp", [float("inf"), float("-inf"), float("nan")], ids=["positive-infinity", "negative-infinity", "nan"])
def test_knowledge_must_not_promote_unknown_timestamp(fraction_profile, stamp):
    client, uid, _, _, _, _ = fraction_profile
    with DB.begin() as db:
        if math.isnan(stamp) and db.bind.dialect.name == "sqlite":
            pytest.skip("SQLite converts NaN to NULL, which Attempt.created disallows")
        attempt = Attempt(unit_id=uid, question_id="sum", answer="synthetic", outcome="correct", assisted=False,
                          evaluation={"attempt_number": 1}, created=stamp)
        db.add(attempt)
        db.flush()
        attempt_id = attempt.id
    response = client.get(f"/api/units/{uid}/learning-session/knowledge")
    with DB() as db:
        original = db.scalar(select(Attempt).where(Attempt.id == attempt_id))
        assert original.answer == "synthetic" and original.outcome == "correct" and not original.assisted
        assert math.isnan(original.created) if math.isnan(stamp) else original.created == stamp
    assert response.status_code == 200, response.text
    goals = response.json()["long_term"]
    assert any(goal["attempts"] for goal in goals)
    assert all(goal["independent"] == 0 and not goal["successful_check_dates"] for goal in goals)
