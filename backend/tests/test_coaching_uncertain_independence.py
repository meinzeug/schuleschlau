"""The coaching projection must not turn uncertain evidence into mastery."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from schulpilot import coaching
from schulpilot.db import DB, Attempt, Child, LearningUnit, UnitCoaching
from schulpilot.learning import local_day
from schulpilot.synthetic import CONTENT, sample_unit
from test_coaching import normal_unit as normal_unit


@pytest.mark.parametrize("assisted", [False, True])
def test_uncertain_first_attempt_does_not_create_or_erase_recall_days(normal_unit, assisted):
    _, root_id, material_id, _, kid = normal_unit
    with DB.begin() as db:
        root = db.get(LearningUnit, root_id)
        today = local_day(db.get(Child, kid["id"]))
        zone = ZoneInfo("Europe/Berlin")
        db.add(UnitCoaching(unit_id=root_id, status="ready", report={"learning_goals": [
            {"id": "g1", "label": "Brüche Lernziel", "source_excerpt": CONTENT[:100]}
        ]}))
        rounds = []
        for index, days in enumerate((9, 5, 1, 0)):
            stamp = int(datetime.combine(today - timedelta(days=days), datetime.min.time(), zone).timestamp()) + 100
            question = dict(sample_unit(index % 3)["questions"][0], id=f"q{index}", learning_goal_id="g1")
            unit = LearningUnit(child_id=kid["id"], material_id=material_id, subject=root.subject, topic=root.topic,
                explanation="Künstliche Abrufprobe.", questions=[question], learning_root_id=root_id,
                round_kind="spaced_review", status="completed", completed=stamp, created=stamp, provider="synthetic",
                synthetic=True)
            db.add(unit)
            db.flush()
            attempt = Attempt(unit_id=unit.id, question_id=question["id"], answer=question["answer"],
                outcome="correct", assisted=assisted if index == 3 else False, created=stamp,
                evaluation={"independence_uncertain": index == 3})
            db.add(attempt)
            rounds.append(unit)
        db.flush()
        assert not coaching.independently_correct(db, rounds[-1])
        assert coaching.open_assessment_only(db, rounds[-1])
        goal = coaching.goal_states(db, root)[0]
        assert goal["successful_check_dates"] == [(today - timedelta(days=n)).isoformat() for n in (9, 5, 1)]
        assert goal["secure_observation"]
        assert goal["practice"]["independent_tasks"] == 3
        assert goal["practice"]["uncertain_tasks"] == 1
        report = coaching.report_projection(db, rounds[-1], {"summary": "", "question_reviews": []})
        assert "0 beim ersten Versuch selbstständig richtig" in report["summary"]
        assert "1 richtig mit offenem Selbstständigkeitsnachweis" in report["summary"]
        # The uncertainty flag must never conceal an actual incorrect answer.
        attempt.outcome = "incorrect"
        db.flush()
        assert not coaching.open_assessment_only(db, rounds[-1])
        assert coaching.goal_states(db, root)[0]["successful_check_dates"] == []


def test_retry_with_uncertainty_is_supported_in_coaching(normal_unit):
    _, root_id, _, _, _ = normal_unit
    with DB.begin() as db:
        root = db.get(LearningUnit, root_id)
        root.questions = [dict(root.questions[0], learning_goal_id="g1")]
        db.add(UnitCoaching(unit_id=root_id, status="ready", report={"learning_goals": [
            {"id": "g1", "label": "Brüche Lernziel", "source_excerpt": CONTENT[:100]}
        ]}))
        question = root.questions[0]
        db.add_all([
            Attempt(unit_id=root_id, question_id=question["id"], answer="falsch", outcome="incorrect",
                assisted=False, created=100, evaluation={"attempt_number": 1}),
            Attempt(unit_id=root_id, question_id=question["id"], answer=question["answer"], outcome="correct",
                assisted=False, created=101, evaluation={"attempt_number": 2, "independence_uncertain": True}),
        ])
        db.flush()
        goal = coaching.goal_states(db, root)[0]
        assert goal["practice"]["assisted_tasks"] == 1
        assert goal["practice"]["uncertain_tasks"] == 0
        assert not coaching.open_assessment_only(db, root)
        report = coaching.report_projection(db, root, {"summary": "", "question_reviews": []})
        assert "1 mit Unterstützung oder erneut richtig" in report["summary"]
        assert "0 richtig mit offenem Selbstständigkeitsnachweis" in report["summary"]


def test_rephrased_fraction_question_is_not_a_new_recall_day(normal_unit):
    _, root_id, material_id, _, kid = normal_unit
    with DB.begin() as db:
        root = db.get(LearningUnit, root_id)
        today = local_day(db.get(Child, kid["id"]))
        zone = ZoneInfo("Europe/Berlin")
        db.add(UnitCoaching(unit_id=root_id, status="ready", report={"learning_goals": [
            {"id": "g1", "label": "Brüche Lernziel", "source_excerpt": CONTENT[:100]}
        ]}))
        attempts = []
        for index, (days, variant) in enumerate(((12, 0), (8, 0), (4, 1), (0, 2))):
            stamp = int(datetime.combine(today - timedelta(days=days), datetime.min.time(), zone).timestamp()) + 100
            question = dict(sample_unit(variant)["questions"][0], id=f"q{index}", learning_goal_id="g1")
            if index == 1:
                question["prompt"] = "Addiere 1/4 + 1/4."
            unit = LearningUnit(child_id=kid["id"], material_id=material_id, subject=root.subject, topic=root.topic,
                explanation="Künstliche Abrufprobe.", questions=[question], learning_root_id=root_id,
                round_kind="spaced_review", status="completed", completed=stamp, created=stamp, provider="synthetic",
                synthetic=True)
            db.add(unit)
            db.flush()
            attempt = Attempt(unit_id=unit.id, question_id=question["id"], answer=question["answer"],
                outcome="correct", assisted=False, created=stamp)
            attempts.append(attempt)
            db.add(attempt)
        db.flush()
        goal = coaching.goal_states(db, root)[0]
        assert goal["successful_check_dates"] == [(today - timedelta(days=n)).isoformat() for n in (12, 4, 0)]
        assert goal["secure_observation"]
        # All saved practice observations remain visible despite de-duplication.
        assert goal["practice"]["practiced_tasks"] == goal["practice"]["independent_tasks"] == 4
        # A question remains exposed even if its earlier answer was incorrect.
        attempts[0].outcome = "incorrect"
        db.flush()
        goal = coaching.goal_states(db, root)[0]
        assert goal["successful_check_dates"] == [(today - timedelta(days=n)).isoformat() for n in (4, 0)]
        assert not goal["secure_observation"]
        assert goal["practice"]["practiced_tasks"] == 4 and goal["practice"]["needs_practice_tasks"] == 1


def test_non_math_recall_keeps_chemistry_capitalization_distinct(normal_unit):
    _, root_id, material_id, _, kid = normal_unit
    with DB.begin() as db:
        root = db.get(LearningUnit, root_id)
        root.subject = "Chemie"
        today = local_day(db.get(Child, kid["id"]))
        zone = ZoneInfo("Europe/Berlin")
        db.add(UnitCoaching(unit_id=root_id, status="ready", report={"learning_goals": [
            {"id": "g1", "label": "Chemische Zeichen", "source_excerpt": CONTENT[:100]}
        ]}))
        for index, notation in enumerate(("CO", "Co")):
            stamp = int(datetime.combine(today - timedelta(days=1-index), datetime.min.time(), zone).timestamp()) + 100
            answer = "Kohlenmonoxid" if notation == "CO" else "Cobalt"
            question = dict(sample_unit()["questions"][0], id=f"q{index}", learning_goal_id="g1",
                prompt=f"Welcher Stoff wird mit {notation} bezeichnet?", answer=answer,
                options=["Kohlenmonoxid", "Cobalt"], explanation=f"{notation} bezeichnet {answer}.")
            unit = LearningUnit(child_id=kid["id"], material_id=material_id, subject="Chemie", topic="Zeichen",
                explanation="Künstliche Abrufprobe.", questions=[question], learning_root_id=root_id,
                round_kind="spaced_review", status="completed", completed=stamp, created=stamp, provider="synthetic",
                synthetic=True)
            db.add(unit)
            db.flush()
            db.add(Attempt(unit_id=unit.id, question_id=question["id"], answer=question["answer"],
                outcome="correct", assisted=False, created=stamp))
        db.flush()
        goal = coaching.goal_states(db, root)[0]
        assert len(goal["successful_check_dates"]) == 2
        assert goal["practice"]["independent_tasks"] == 2
