"""An intermediate fraction is not the requested reduced choice."""

import copy

import pytest
from conftest import HEADERS
from fastapi.testclient import TestClient
from schulpilot.db import DB, Activity, Attempt, LearningUnit
from schulpilot.learning_hints import clarify_fraction_product_hint, next_hint
from schulpilot.main import app
from sqlalchemy import select


def product_question():
    return {"id": "fraction", "type": "choice",
            "prompt": "Übung: Berechne 3/8 mal 12. Welcher vollständig gekürzte Bruch ist das Ergebnis?",
            "options": ["9/2", "9/8", "3/2", "3/32"], "answer": "9/2", "accepted": [],
            "hints": ["Multipliziere drei mit zwölf und behalte den Nenner acht bei.",
                      "Welche Zahl teilt Zähler und Nenner?"],
            "explanation": "Das Produkt ist 36/8; gekürzt ergibt das 9/2."}


@pytest.mark.parametrize("operator", ["mal", "×", "*", "·"])
def test_product_hint_names_the_intermediate_and_next_step(operator):
    question = product_question()
    question["prompt"] = question["prompt"].replace("mal", operator)
    first = next_hint(question, None, [])
    assert "zuerst 36/8" in first
    assert "Kürze" in first
    assert "9/2" not in first
    assert next_hint(question, None, [question["hints"][0]]) == question["hints"][1]


@pytest.mark.parametrize("fraction_command,product_command", [
    (r"\frac", r"\cdot"), (r"\dfrac", r"\times"), (r"\tfrac", r"\cdotp"),
])
def test_latex_product_uses_the_same_validated_intermediate(fraction_command, product_command):
    question = product_question()
    question["prompt"] = (rf"Übung: Berechne \({fraction_command}{{3}}{{8}}{product_command}12\). "
                          "Welcher vollständig gekürzte Bruch ist das Ergebnis?")
    assert "zuerst 36/8" in next_hint(question, None, [])


@pytest.mark.parametrize("text", [
    "Multipliziere Zähler und Nenner mit 12.",
    "Multipliziere den Zähler und den Nenner jeweils mit der Zahl 12!",
])
def test_multiply_both_is_corrected_for_a_verified_product(text):
    shown = clarify_fraction_product_hint(product_question(), text)
    assert shown == ("Multipliziere den Zähler mit 12 und behalte den Nenner bei. "
                     "Das ergibt zuerst 36/8. Kürze nun Zähler und Nenner durch dieselbe Zahl. "
                     "Wähle den vollständig gekürzten Bruch.")


def test_expansion_really_does_multiply_both_and_is_never_rewritten():
    question = product_question() | {"prompt": "Erweitere 3/8 mit dem Faktor 12.", "answer": "36/96"}
    hint = "Multipliziere Zähler und Nenner mit 12."
    assert clarify_fraction_product_hint(question, hint) == hint


@pytest.mark.parametrize("changes", [
    {"answer": "9/8"},
    {"options": ["9/2", "18/4", "3/2"]},
    {"options": ["9/8", "3/2", "3/32"]},
    {"prompt": "Berechne 3/8 mal 12. Gib einen Bruch an."},
    {"type": "short"},
    {"language": {"skill": "spelling"}},
    {"prompt": r"Berechne \(\frac{3}{8}\cdot12 + \frac{1}{2}\). Welcher vollständig gekürzte Bruch ist das Ergebnis?"},
    {"prompt": r"Berechne \(\frac{3}{8}\cdot12 + \frac{x}{2}\). Welcher vollständig gekürzte Bruch ist das Ergebnis?"},
])
def test_ambiguous_or_unverified_tasks_keep_the_original_hint(changes):
    question = product_question() | changes
    original = question["hints"][0]
    assert clarify_fraction_product_hint(question, original) == original


@pytest.mark.parametrize("old_hint", [
    "Multipliziere drei mit zwölf und behalte den Nenner acht bei.",
    "Multipliziere Zähler und Nenner mit 12.",
])
def test_saved_hint_projection_replay_and_assisted_answer(api, household, old_hint):
    _, child = household
    q = product_question()
    q["hints"][0] = old_hint
    q["prompt"] = (r"Übung: Berechne \(\frac{3}{8}\cdot12\). "
                   "Welcher vollständig gekürzte Bruch ist das Ergebnis?")
    original = copy.deepcopy(q)
    request_key = "old-synthetic-hint-001"
    with DB.begin() as db:
        unit = LearningUnit(child_id=child["id"], subject="Mathematik", topic="Brüche", questions=[q],
                            explanation=q["explanation"], status="active", provider="synthetic", synthetic=True)
        db.add(unit)
        db.flush()
        uid = unit.id
        db.add(Activity(child_id=child["id"], unit_id=uid, kind="hint", detail={
            "question_id": "fraction", "number": 1, "text": q["hints"][0], "request_key": request_key}))
    with TestClient(app, headers=HEADERS) as kid:
        login = kid.post("/api/auth/login", json={"username": "test-child", "password": "secure-child-pass-123"})
        kid.headers["Authorization"] = "Bearer " + login.json()["token"]
        overview = kid.get(f"/api/units/{uid}")
        assert overview.status_code == 200, overview.text
        shown = overview.json()["questions"][0]["shown_hints"]
        assert len(shown) == 1 and "zuerst 36/8" in shown[0]["text"]
        if "Zähler und Nenner" in old_hint:
            assert "Zähler mit 12" in shown[0]["text"] and old_hint not in shown[0]["text"]
        replay = kid.post(f"/api/units/{uid}/questions/fraction/hint", headers={"Idempotency-Key": request_key})
        assert replay.status_code == 200 and replay.json()["hint"] == shown[0]["text"]
        second = kid.post(f"/api/units/{uid}/questions/fraction/hint",
                          headers={"Idempotency-Key": "new-synthetic-hint-002"})
        assert second.status_code == 200 and second.json()["hint"] == q["hints"][1]
        answer = kid.post(f"/api/units/{uid}/questions/fraction/answer",
                          json={"answer": "9/2", "request_id": "synthetic-answer-0001"})
        assert answer.status_code == 200, answer.text
        assert answer.json()["outcome"] == "correct" and answer.json()["assisted"] is True
    with DB() as db:
        assert db.get(LearningUnit, uid).questions == [original]
        events = list(db.scalars(select(Activity).where(Activity.unit_id == uid, Activity.kind == "hint")))
        assert len(events) == 2 and events[0].detail["text"] == original["hints"][0]
        assert db.scalar(select(Attempt).where(Attempt.unit_id == uid)).assisted is True
