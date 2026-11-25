"""Exact-disclosure regressions use synthetic questions and model responses."""

import pytest
from schulpilot.db import DB, Activity, Attempt, Job, LearningUnit, Usage
from schulpilot.schulbuddy_solution_guard import reveals_exact_answer
from sqlalchemy import func, select
from test_schulbuddy import ask, counts, finish
from test_schulbuddy import book as book  # noqa: F401
from test_schulbuddy import transport as transport  # noqa: F401
from test_schulbuddy_graphics import ask as ask_graphic
from test_schulbuddy_graphics import graphic_book as graphic_book  # noqa: F401


def output(answer="Prüfe deinen ersten Schritt.", next_question=None, starters=None, sources=None):
    return {"answer": answer, "next_question": next_question, "starters": starters or [], "sources": sources or []}


@pytest.mark.parametrize("reply", [
    output("Es ist ein STERN."),
    output(next_question="Ist es ein Stern?"),
    output(starters=["Stern"]),
    output(sources=[{"ref": "p1", "quote": "Die Sonne ist ein Stern."}]),
])
def test_exact_answer_is_not_allowed_in_any_visible_field(reply):
    assert reveals_exact_answer({"type": "short", "prompt": "Was ist die Sonne?", "answer": "Stern"}, reply)


def test_boundaries_known_prompt_and_supported_variants():
    question = {"type": "short", "prompt": "Was ist die Sonne?", "answer": "Stern", "accepted": ["Fixstern"]}
    assert not reveals_exact_answer(question, output("Schau dir das Sternbild an."))
    assert reveals_exact_answer(question, output("Es ist ein Fixstern."))
    assert not reveals_exact_answer({"type": "short", "prompt": "Was bedeutet Stern?", "answer": "Stern"},
                                    output("Überlege, was Stern bedeutet."))
    assert reveals_exact_answer({"type": "choice", "prompt": "Wähle aus", "answer": "Stern"},
                                output("Wähle Stern."))
    assert reveals_exact_answer({"type": "short", "prompt": "Berechne 1/3 + 1/6", "answer": "1/2"},
                                output(r"Das ergibt \(\frac{1}{2}\)."))
    assert reveals_exact_answer({"type": "short", "prompt": "Berechne 1/3 + 1/6", "answer": "1/2"},
                                output("Das ergibt ½."))
    assert not reveals_exact_answer({"type": "short", "prompt": "Was ist 12 + 3?", "answer": "2"},
                                    output("Die Zahl 12 steht dort."))
    assert not reveals_exact_answer({"type": "short", "prompt": "Rechne!", "answer": "2"},
                                    output("Betrachte 1/2 und 1,2."))
    assert not reveals_exact_answer({"type": "short", "prompt": "Welcher Bruch?", "answer": "1/2"},
                                    output("Das ist 1/2."), visible_explanation="Die geöffnete Grafik zeigt 1/2.")
    assert reveals_exact_answer({"type": "choice", "prompt": "Wähle aus", "answer": "Stern"},
                                output("Wähle Stern."), visible_explanation="Es gibt Stern und Planet.")


def test_disclosing_model_result_is_not_published_or_counted_as_help(api, book, transport):
    with DB.begin() as db:
        unit = db.get(LearningUnit, book["unit_id"])
        unit.status = "active"
        unit.questions = [{"id": "q1", "type": "short", "prompt": "Was ist die Sonne?", "options": [],
                           "answer": "Stern", "accepted": [], "hints": [], "explanation": "Künstlich"}]
    before = counts()
    turn_id = ask(book, question_id="q1").json()["id"]
    job_id = finish()
    response = book["client"].get("/api/schulbuddy/questions/" + turn_id).json()
    assert response["status"] == "failed" and response["answer"] is None
    assert "verrät zu viel" in response["error"]
    assert "answer" not in transport["calls"][0]["current_question"]
    assert counts()[2:] == before[2:]
    with DB() as db:
        assert db.get(Job, job_id).error_code == "invalid_output"
        assert db.scalar(select(Usage).where(Usage.job_id == job_id)).status.startswith("failed")
        assert db.scalar(select(func.count()).select_from(Attempt)) == 0
        assert db.scalar(select(func.count()).select_from(Activity).where(Activity.kind == "explanation")) == 0


def test_explicitly_opened_question_solution_remains_explainable(graphic_book, transport):
    with DB.begin() as db:
        unit = db.get(LearningUnit, graphic_book["unit_id"])
        unit.status = "active"
        db.add(Activity(child_id=graphic_book["child"]["id"], unit_id=unit.id, kind="explanation",
                        detail={"question_id": "q1"}))
    transport["output"] = {"answer": "Ein von zwei Teilen ist 1/2.", "next_question": None,
                           "sources": [], "starters": []}
    sent = ask_graphic(graphic_book, explanation_kind="question", question_id="q1", graphic_phase="initial")
    assert sent.status_code == 202, sent.text
    finish()
    result = graphic_book["client"].get("/api/schulbuddy/questions/" + sent.json()["id"]).json()
    assert result["status"] == "ready" and result["answer"] == transport["output"]["answer"]
    assert transport["calls"][0]["current_explanation"]["disclosure"] == "solution"


def test_existing_feedback_is_explainable_without_rewriting_answer(book, transport):
    with DB.begin() as db:
        unit = db.get(LearningUnit, book["unit_id"])
        unit.status = "active"
        unit.questions = [{"id": "q1", "type": "short", "prompt": "Was ist die Sonne?", "options": [],
                           "answer": "Stern", "accepted": [], "hints": [], "explanation": "Künstlich"}]
        attempt = Attempt(unit_id=unit.id, question_id="q1", answer="Stern", outcome="correct", assisted=False)
        db.add(attempt)
        db.flush()
        attempt_id = attempt.id
        db.add(Activity(child_id=book["child"]["id"], unit_id=unit.id, kind="feedback_pending",
                        detail={"attempt_id": attempt_id, "question_id": "q1"}))
    turn = ask(book, question_id="q1")
    assert turn.status_code == 202, turn.text
    finish()
    result = book["client"].get("/api/schulbuddy/questions/" + turn.json()["id"]).json()
    assert result["status"] == "ready" and result["answer"] == "Die Sonne ist ein Stern."
    with DB() as db:
        assert db.get(Attempt, attempt_id).assisted is False
        assert db.scalar(select(func.count()).select_from(Activity).where(Activity.kind == "explanation")) == 0


def test_incorrect_feedback_does_not_automatically_disclose_solution(book, transport):
    with DB.begin() as db:
        unit = db.get(LearningUnit, book["unit_id"])
        unit.status = "active"
        unit.questions = [{"id": "q1", "type": "short", "prompt": "Was ist die Sonne?", "options": [],
                           "answer": "Stern", "accepted": [], "hints": [], "explanation": "Künstlich"}]
        attempt = Attempt(unit_id=unit.id, question_id="q1", answer="Planet", outcome="incorrect", assisted=False)
        db.add(attempt)
        db.flush()
        attempt_id = attempt.id
        db.add(Activity(child_id=book["child"]["id"], unit_id=unit.id, kind="feedback_pending",
                        detail={"attempt_id": attempt_id, "question_id": "q1"}))
    turn = ask(book, question_id="q1")
    assert turn.status_code == 202, turn.text
    finish()
    result = book["client"].get("/api/schulbuddy/questions/" + turn.json()["id"]).json()
    assert result["status"] == "failed" and result["answer"] is None
    assert transport["calls"][0]["current_question"]["observed_outcome"] == "incorrect"
    with DB() as db:
        assert db.get(Attempt, attempt_id).answer == "Planet"


def test_hint_on_wrong_feedback_marks_only_later_retry_as_assisted(book, transport):
    with DB.begin() as db:
        unit = db.get(LearningUnit, book["unit_id"])
        unit.status = "active"
        unit.questions = [{"id": "q1", "type": "short", "prompt": "Was ist die Sonne?", "options": [],
                           "answer": "Stern", "accepted": [], "hints": [], "explanation": "Künstlich"}]
        attempt = Attempt(unit_id=unit.id, question_id="q1", answer="Planet", outcome="incorrect", assisted=False)
        db.add(attempt)
        db.flush()
        attempt_id = attempt.id
        db.add(Activity(child_id=book["child"]["id"], unit_id=unit.id, kind="feedback_pending",
                        detail={"attempt_id": attempt_id, "question_id": "q1"}))
    transport["output"] = {"answer": "Überlege, welche Art Himmelskörper selbst leuchtet.",
                           "sources": [{"ref": "p1", "quote": "Die Erde dreht sich um die Sonne."}],
                           "next_question": None, "starters": []}
    turn = ask(book, question_id="q1")
    assert turn.status_code == 202, turn.text
    finish()
    result = book["client"].get("/api/schulbuddy/questions/" + turn.json()["id"]).json()
    assert result["status"] == "ready"
    ack = book["client"].post(f"/api/units/{book['unit_id']}/feedback/acknowledge", json={"attempt_id": attempt_id})
    assert ack.status_code == 200, ack.text
    retried = book["client"].post(f"/api/units/{book['unit_id']}/questions/q1/answer", json={"answer": "Stern"})
    assert retried.status_code == 200 and retried.json()["assisted"] is True
    with DB() as db:
        saved = db.get(Attempt, attempt_id)
        assert saved.answer == "Planet" and saved.outcome == "incorrect" and saved.assisted is False
