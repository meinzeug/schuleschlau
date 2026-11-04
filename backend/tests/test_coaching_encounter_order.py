"""An answered task cannot become a new recall question through completion order."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from schulpilot import coaching
from schulpilot.db import DB, Attempt, Child, LearningUnit, UnitCoaching
from schulpilot.learning import local_day
from schulpilot.synthetic import CONTENT, sample_unit
from test_coaching import normal_unit as normal_unit


def make_round(db, root, material_id, *, answered, completed, prompt, outcome="correct"):
    question = dict(sample_unit()["questions"][0], id="q", learning_goal_id="g1", prompt=prompt)
    unit = LearningUnit(child_id=root.child_id, material_id=material_id, subject=root.subject, topic=root.topic,
        explanation="Künstliche Abrufprobe.", questions=[question], learning_root_id=root.id,
        round_kind="spaced_review", status="completed" if completed else "active", completed=completed,
        created=answered - 100, provider="synthetic", synthetic=True)
    db.add(unit)
    db.flush()
    attempt = Attempt(unit_id=unit.id, question_id="q", answer="künstliche Antwort", outcome=outcome,
        assisted=False, created=answered)
    db.add(attempt)
    db.flush()
    return unit, attempt


@pytest.mark.parametrize("first_outcome", ["correct", "incorrect", "uncertain"])
def test_open_round_exposure_cannot_become_new_recall(normal_unit, first_outcome):
    _, root_id, material_id, _, kid = normal_unit
    with DB.begin() as db:
        root = db.get(LearningUnit, root_id)
        today = local_day(db.get(Child, kid["id"]))
        zone = ZoneInfo("Europe/Berlin")
        stamp = int(datetime.combine(today, datetime.min.time(), zone).timestamp()) + 3600
        db.add(UnitCoaching(unit_id=root_id, status="ready", report={"learning_goals": [
            {"id": "g1", "label": "Brüche Lernziel", "source_excerpt": CONTENT[:100]}]}))
        _, previous = make_round(db, root, material_id, answered=stamp - 9 * 86400,
            completed=None, prompt="Addiere 1/4 + 1/4.", outcome=first_outcome)
        _, repeated = make_round(db, root, material_id, answered=stamp - 5 * 86400,
            completed=stamp - 5 * 86400 + 120, prompt="Wie viel ist 1/4 + 1/4?")
        goal = coaching.goal_states(db, root)[0]
        assert goal["successful_check_dates"] == []
        assert goal["practice"]["practiced_tasks"] == 2
        assert db.get(Attempt, previous.id).outcome == first_outcome
        assert db.get(Attempt, repeated.id).outcome == "correct"


def test_check_days_follow_answers_across_midnight_and_late_completion(normal_unit):
    _, root_id, material_id, _, kid = normal_unit
    with DB.begin() as db:
        root = db.get(LearningUnit, root_id)
        today = local_day(db.get(Child, kid["id"]))
        zone = ZoneInfo("Europe/Berlin")
        stamp = int(datetime.combine(today, datetime.min.time(), zone).timestamp()) + 3600
        db.add(UnitCoaching(unit_id=root_id, status="ready", report={"learning_goals": [
            {"id": "g1", "label": "Brüche Lernziel", "source_excerpt": CONTENT[:100]}]}))
        for days, prompt in ((9, "Addiere 1/4 + 1/4."), (5, "Addiere 2/5 + 1/5."),
                (1, "Addiere 1/3 + 1/3.")):
            answered = stamp - days * 86400
            # The oldest round is only finished after the other answers.
            completed = stamp if days == 9 else answered + 86400
            make_round(db, root, material_id, answered=answered, completed=completed, prompt=prompt)
        goal = coaching.goal_states(db, root)[0]
        assert goal["successful_check_dates"] == [(today - timedelta(days=n)).isoformat() for n in (9, 5, 1)]
        assert goal["secure_observation"]


def test_simultaneous_duplicate_answers_do_not_guess_which_was_first(normal_unit):
    _, root_id, material_id, _, kid = normal_unit
    with DB.begin() as db:
        root = db.get(LearningUnit, root_id)
        today = local_day(db.get(Child, kid["id"]))
        zone = ZoneInfo("Europe/Berlin")
        stamp = int(datetime.combine(today, datetime.min.time(), zone).timestamp()) + 3600
        db.add(UnitCoaching(unit_id=root_id, status="ready", report={"learning_goals": [
            {"id": "g1", "label": "Brüche Lernziel", "source_excerpt": CONTENT[:100]}]}))
        for index in range(2):
            make_round(db, root, material_id, answered=stamp, completed=stamp + index + 1,
                prompt="Addiere 1/4 + 1/4.")
        goal = coaching.goal_states(db, root)[0]
        assert goal["successful_check_dates"] == []
        assert goal["practice"]["practiced_tasks"] == 2


def test_late_completed_old_mistake_does_not_erase_newer_check_days(normal_unit):
    _, root_id, material_id, _, kid = normal_unit
    with DB.begin() as db:
        root = db.get(LearningUnit, root_id)
        today = local_day(db.get(Child, kid["id"]))
        zone = ZoneInfo("Europe/Berlin")
        stamp = int(datetime.combine(today, datetime.min.time(), zone).timestamp()) + 3600
        db.add(UnitCoaching(unit_id=root_id, status="ready", report={"learning_goals": [
            {"id": "g1", "label": "Brüche Lernziel", "source_excerpt": CONTENT[:100]}]}))
        _, original = make_round(db, root, material_id, answered=stamp - 10 * 86400, completed=stamp,
            prompt="Addiere 1/9 + 1/9.", outcome="incorrect")
        for days, prompt in ((9, "Addiere 1/4 + 1/4."), (5, "Addiere 2/5 + 1/5."),
                (1, "Addiere 1/3 + 1/3.")):
            answered = stamp - days * 86400
            make_round(db, root, material_id, answered=answered, completed=answered + 100, prompt=prompt)
        goal = coaching.goal_states(db, root)[0]
        assert goal["successful_check_dates"] == [(today - timedelta(days=n)).isoformat() for n in (9, 5, 1)]
        assert goal["secure_observation"]
        assert db.get(Attempt, original.id).outcome == "incorrect"


@pytest.mark.parametrize("previous_goal", [None, "g2"])
def test_previous_exposure_cannot_become_a_new_check_after_goal_reassignment(normal_unit, previous_goal):
    _, root_id, material_id, _, kid = normal_unit
    with DB.begin() as db:
        root = db.get(LearningUnit, root_id)
        today = local_day(db.get(Child, kid["id"]))
        zone = ZoneInfo("Europe/Berlin")
        stamp = int(datetime.combine(today, datetime.min.time(), zone).timestamp()) + 3600
        db.add(UnitCoaching(unit_id=root_id, status="ready", report={"learning_goals": [
            {"id": "g1", "label": "Brüche Lernziel", "source_excerpt": CONTENT[:100]},
            {"id": "g2", "label": "Weiteres Lernziel", "source_excerpt": CONTENT[:100]},
        ]}))
        old, previous = make_round(db, root, material_id, answered=stamp - 2 * 86400,
            completed=None, prompt="Addiere 1/4 + 1/4.")
        old.questions = [{**old.questions[0], "learning_goal_id": previous_goal}]
        _, repeated = make_round(db, root, material_id, answered=stamp - 86400,
            completed=stamp - 86400 + 30, prompt="Wie viel ist 1/4 + 1/4?")
        db.flush()
        states = {state["id"]: state for state in coaching.goal_states(db, root)}
        assert states["g1"]["successful_check_dates"] == []
        assert states["g1"]["practice"]["practiced_tasks"] == 1
        assert db.get(Attempt, previous.id).outcome == "correct"
        assert db.get(Attempt, repeated.id).outcome == "correct"
