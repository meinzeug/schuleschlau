"""Personal contributions in mixed units are not evidence of ability or mistakes."""

import copy

import pytest
from schulpilot import coaching
from schulpilot.db import DB, Attempt, LearningUnit, UnitCoaching, now
from schulpilot.synthetic import CONTENT
from test_coaching import mocked_review, process_next
from test_coaching import normal_unit as normal_unit
from test_subject_content import CASES


@pytest.mark.parametrize("outcome,expected_action,assessment_open", [
    ("correct", "check", False), ("incorrect", "repair", False), ("uncertain", "repair", True),
])
def test_mixed_round_plans_from_assessed_answers_only(normal_unit, outcome, expected_action, assessment_open):
    _, unit_id, _, _, _ = normal_unit
    with DB.begin() as db:
        unit = db.get(LearningUnit, unit_id)
        question = dict(copy.deepcopy(unit.questions[0]), learning_goal_id="g1")
        reflection = dict(copy.deepcopy(unit.questions[1]), id="own-idea", learning_goal_id="g2", type="short",
            prompt="Was fällt dir dazu ein?", answer="", accepted=[], options=[],
            presentation=copy.deepcopy(next(c["question"]["presentation"] for c in CASES if c["id"] == "ETH01")))
        unit.questions = [question, reflection]
        stamp = int(now())
        unit.status, unit.completed = "completed", stamp
        db.add(UnitCoaching(unit_id=unit_id, status="ready", report={"learning_goals": [
            {"id": "g1", "label": "Brüche Lernziel", "source_excerpt": CONTENT[:100]},
            {"id": "g2", "label": "Eigene Gedanken", "source_excerpt": CONTENT[:100]},
        ]}))
        knowledge = Attempt(unit_id=unit_id, question_id=question["id"], answer="synthetisch", outcome=outcome,
            assisted=False, created=stamp)
        contribution = Attempt(unit_id=unit_id, question_id=reflection["id"], answer="synthetisch",
            outcome="uncertain", assisted=False, created=stamp, evaluation={"method": "open_learning_v1"})
        db.add_all([knowledge, contribution])
        db.flush()
        assert coaching.independently_correct(db, unit) is (outcome == "correct")
        assert coaching.open_assessment_only(db, unit) is assessment_open
        assert coaching.plan_review(db, unit)["next_action"] == expected_action
        assert coaching.focus_ids(db, unit, "check") == ["g1"]
        if outcome == "incorrect":
            assert coaching.focus_ids(db, unit, "repair") == ["g1"]
        states = {item["id"]: item for item in coaching.goal_states(db, unit)}
        assert states["g2"]["practice"]["reflection_tasks"] == 1
        assert states["g2"]["assessment_applicable"] is False
        assert states["g1"]["assessment_applicable"] is True
        assert states["g2"]["practice"]["uncertain_tasks"] == 0
        assert states["g2"]["successful_check_dates"] == []
        stored = {"summary": "", "question_reviews": [
            {"question_id": "own-idea", "outcome": "correct", "feedback": "Das ist richtig."}]}
        unchanged = copy.deepcopy(stored)
        projected = coaching.report_projection(db, unit, stored)
        assert stored == unchanged
        assert "1 eigener Beitrag ohne Leistungsbewertung" in projected["summary"]
        review = projected["question_reviews"][0]
        assert review["outcome"] == "uncertain" and review["assessment_kind"] == "reflection"
        assert "nicht als richtig oder falsch bewertet" in review["feedback"]
        assert db.get(Attempt, knowledge.id).outcome == outcome
        assert db.get(Attempt, contribution.id).outcome == "uncertain"


def test_historic_open_method_remains_ungraded_even_with_stale_presentation(normal_unit):
    _, unit_id, _, _, _ = normal_unit
    with DB.begin() as db:
        unit = db.get(LearningUnit, unit_id)
        question = copy.deepcopy(unit.questions[0])
        unit.questions = [question]
        unit.status, unit.completed = "completed", int(now())
        db.add(Attempt(unit_id=unit_id, question_id=question["id"], answer="synthetisch", outcome="correct",
            assisted=False, created=unit.completed, evaluation={"method": "open_learning_v1"}))
        db.flush()
        assert not coaching.independently_correct(db, unit)
        assert not coaching.open_assessment_only(db, unit)
        projected = coaching.report_projection(db, unit, {"summary": "", "question_reviews": []})
        assert "0 beim ersten Versuch selbstständig richtig" in projected["summary"]
        assert "1 eigener Beitrag ohne Leistungsbewertung" in projected["summary"]


def test_child_api_keeps_open_contribution_out_of_coach_assessment(normal_unit, monkeypatch):
    client, unit_id, _, _, _ = normal_unit
    client.headers["X-Schulpilot-Capabilities"] = "visual-v1"
    mocked_review(monkeypatch)
    with DB.begin() as db:
        unit = db.get(LearningUnit, unit_id)
        knowledge = copy.deepcopy(unit.questions[0])
        reflection = dict(copy.deepcopy(unit.questions[1]), id="own-idea", type="short",
            prompt="Was fällt dir dazu ein?", answer="", accepted=[], options=[],
            presentation=copy.deepcopy(next(c["question"]["presentation"] for c in CASES if c["id"] == "ETH01")))
        unit.questions = [knowledge, reflection]
    assert client.post(f"/api/units/{unit_id}/start").status_code == 200
    correct = client.post(f"/api/units/{unit_id}/questions/{knowledge['id']}/answer",
        json={"answer": knowledge["answer"]})
    assert correct.status_code == 200 and correct.json()["outcome"] == "correct"
    own = client.post(f"/api/units/{unit_id}/questions/own-idea/answer", json={"answer": "Meine Idee"})
    assert own.status_code == 200 and own.json()["outcome"] == "uncertain"
    assert own.json()["unit"]["status"] == "completed"
    assert own.json()["unit"]["coaching"]["decision"] == "check"
    process_next()
    detail = client.get(f"/api/units/{unit_id}")
    assert detail.status_code == 200
    coach = detail.json()["coaching"]
    assert coach["status"] == "ready" and coach["decision"] == "check"
    report = coach["report"]
    assert "1 eigener Beitrag ohne Leistungsbewertung" in report["summary"]
    review = next(item for item in report["question_reviews"] if item["question_id"] == "own-idea")
    assert review["outcome"] == "uncertain" and review["assessment_kind"] == "reflection"
    with DB() as db:
        saved = copy.deepcopy(db.get(UnitCoaching, unit_id).report)
    assert client.get(f"/api/units/{unit_id}").status_code == 200
    with DB() as db:
        assert db.get(UnitCoaching, unit_id).report == saved
