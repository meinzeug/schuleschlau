"""In-flight Tutor replies remain bound to the saved question's contents.

The HTTP request, worker and persistence are real. Data and provider responses
are artificial; no remote provider is contacted.
"""

import copy

import pytest
from schulpilot.db import DB, Activity, Attempt, LearningUnit
from sqlalchemy import select
from test_schulbuddy import ask, finish
from test_schulbuddy import book as book_fixture
from test_schulbuddy import transport as transport_fixture


@pytest.fixture
def book(api, household, monkeypatch):
    yield from book_fixture.__wrapped__(api, household, monkeypatch)


@pytest.fixture
def transport(monkeypatch):
    return transport_fixture.__wrapped__(monkeypatch)


@pytest.mark.parametrize("field,value", [("prompt", "Eine andere Frage?"),
                                         ("answer", "Ein anderer Wert"),
                                         ("options", ["Eine andere Auswahl"])])
def test_changed_current_question_discards_late_reply(book, transport, field, value):
    with DB.begin() as db:
        unit = db.get(LearningUnit, book["unit_id"])
        unit.status = "active"
        unit.questions = [{"id": "sun", "type": "short", "prompt": "Was ist die Sonne?", "options": [],
                           "answer": "Stern", "accepted": ["Stern"], "hints": [], "explanation": "Ein Stern."}]
    sent = ask(book)
    assert sent.status_code == 202, sent.text

    def change_question():
        with DB.begin() as db:
            unit = db.get(LearningUnit, book["unit_id"])
            questions = copy.deepcopy(unit.questions)
            questions[0][field] = value
            unit.questions = questions

    transport["effect"] = change_question
    finish()
    saved = book["client"].get("/api/schulbuddy/questions/" + sent.json()["id"]).json()
    assert saved["status"] == "failed" and saved["answer"] is None
    with DB() as db:
        assert list(db.scalars(select(Activity).where(Activity.kind == "explanation"))) == []
        assert list(db.scalars(select(Attempt))) == []
