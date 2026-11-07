"""An opened hint is support, even if a saved hint exposed the answer."""

import copy

from schulpilot.db import DB, Activity, Attempt, LearningUnit
from schulpilot.learning_hints import next_hint
from sqlalchemy import select
from test_learning import child_client, prepared


def test_divisor_set_second_hint_explains_method_without_complete_solution():
    question = {"type": "short", "prompt": "Nenne alle positiven Teiler von 6. Trenne sie durch Kommas.",
        "answer": "1, 2, 3, 6", "hints": ["Teile die Zahl durch mögliche Teiler. Wo bleibt kein Rest?"],
        "explanation": "Die Teiler von 6 sind 1, 2, 3 und 6."}
    first = next_hint(question, None, [])
    second = next_hint(question, None, [first])
    assert first == question["hints"][0]
    assert "der Reihe nach" in second and "ohne Rest" in second
    assert question["answer"] not in second
    assert "2, 3" not in second
    unrelated = {**question, "prompt": "Was ist das Ergebnis?"}
    assert "Beginne bei 1" not in next_hint(unrelated, None, [first])


def _prepare_lcm(api):
    demo, unit_id = prepared(api)
    with DB.begin() as db:
        unit = db.get(LearningUnit, unit_id)
        questions = copy.deepcopy(unit.questions)
        question = next(item for item in questions if item["id"] == "name")
        question.update(
            prompt="Was ist das kleinste gemeinsame Vielfache von 3 und 7?",
            answer="21",
            accepted=[],
            hints=["Schreibe die Vielfachen von 3 und 7 auf."],
            explanation="Das kleinste gemeinsame Vielfache von 3 und 7 ist 21.",
        )
        unit.questions = questions
    return demo, unit_id


def test_two_hints_do_not_copy_explanation_and_answer_counts_as_supported(api):
    demo, unit_id = _prepare_lcm(api)
    with child_client(demo) as child:
        assert child.post(f"/api/units/{unit_id}/start").status_code == 200
        path = f"/api/units/{unit_id}/questions/name"
        first = child.post(path + "/hint", headers={"Idempotency-Key": "first-hint-key-123"})
        assert first.status_code == 200, first.text
        replay = child.post(path + "/hint", headers={"Idempotency-Key": "first-hint-key-123"})
        assert replay.json() == first.json()
        second = child.post(path + "/hint", headers={"Idempotency-Key": "second-hint-key-12"})
        assert second.status_code == 200, second.text
        assert second.json()["hints_used"] == 2
        assert "21" not in first.json()["hint"]
        assert "21" not in second.json()["hint"]
        result = child.post(path + "/answer", json={"answer": "21"})
        assert result.status_code == 200, result.text
        assert result.json()["outcome"] == "correct"
        assert result.json()["assisted"] is True
        assert result.json()["evaluation"]["independent_evidence"] is False
        assert "hint" in result.json()["evaluation"]["support_reasons"]
        progress = child.get(f"/api/children/{demo['child_id']}/learning-progress").json()["totals"]
        assert progress["assisted_tasks"] == 1
        assert progress["independent_tasks"] == 0
        assert progress["hints_used"] == 2
    assert api.get(f"/api/children/{demo['child_id']}/learning-progress").json()["totals"] == progress
    with DB() as db:
        assert len(list(db.scalars(select(Activity).where(Activity.unit_id == unit_id, Activity.kind == "hint")))) == 2
        attempt = db.scalar(select(Attempt).where(Attempt.unit_id == unit_id, Attempt.question_id == "name"))
        assert attempt.assisted is True


def test_saved_solution_hint_replay_is_preserved_and_counts_as_support(api):
    demo, unit_id = _prepare_lcm(api)
    with child_client(demo) as child:
        assert child.post(f"/api/units/{unit_id}/start").status_code == 200
        with DB.begin() as db:
            db.add(Activity(child_id=demo["child_id"], unit_id=unit_id, kind="hint", detail={
                "question_id": "name", "text": "Gemeinsamer Schritt: Das Ergebnis ist 21.",
                "number": 1, "request_key": "historic-hint-key-1",
            }))
        path = f"/api/units/{unit_id}/questions/name"
        replay = child.post(path + "/hint", headers={"Idempotency-Key": "historic-hint-key-1"})
        assert replay.status_code == 200, replay.text
        assert replay.json()["hint"] == "Gemeinsamer Schritt: Das Ergebnis ist 21."
        response = child.post(path + "/answer", json={"answer": "21"})
        assert response.status_code == 200, response.text
        assert response.json()["outcome"] == "correct"
        assert response.json()["assisted"] is True
        assert response.json()["evaluation"]["independent_evidence"] is False
