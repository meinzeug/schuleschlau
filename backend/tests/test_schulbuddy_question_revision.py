"""In-flight Tutor replies remain bound to the saved question's contents.

The HTTP request, worker and persistence are real. Data and provider responses
are artificial; no remote provider is contacted.
"""

import copy

import pytest
from schulpilot.db import DB, Activity, Attempt, Job, LearningUnit, Membership, SchulbuddyTurn, Session, Usage
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


@pytest.mark.parametrize("field,value", [("prompt", "Eine andere Frage?"),
                                         ("answer", "Ein anderer Wert"),
                                         ("options", ["Eine andere Auswahl"])])
def test_answered_chat_is_not_reused_after_question_correction(book, transport, field, value):
    with DB.begin() as db:
        unit = db.get(LearningUnit, book["unit_id"])
        unit.status = "active"
        unit.questions = [{"id": "sun", "type": "short", "prompt": "Was ist die Sonne?", "options": [],
                           "answer": "Stern", "accepted": ["Stern"], "hints": [], "explanation": "Ein Stern."}]
        db.add(Attempt(unit_id=unit.id, question_id="previous", answer="Eigene frühere Antwort",
                       outcome="correct", assisted=False, evaluation={"support_reasons": []}))
    sent = ask(book)
    assert sent.status_code == 202, sent.text
    finish()
    url = "/api/schulbuddy/questions/" + sent.json()["id"]
    assert not book["client"].get(url).json()["source_changed"]
    with DB() as db:
        events_before = [(a.id, copy.deepcopy(a.detail)) for a in db.scalars(select(Activity))]
        attempts_before = [(a.id, a.answer, a.outcome, a.assisted) for a in db.scalars(select(Attempt))]
    assert len(events_before) == 1 and len(attempts_before) == 1
    with DB.begin() as db:
        unit = db.get(LearningUnit, book["unit_id"])
        questions = copy.deepcopy(unit.questions)
        questions[0][field] = value
        unit.questions = questions
    old = book["client"].get(url).json()
    assert old["source_changed"] and "Aufgabenfassung" in old["notice"]
    before = len(transport["calls"])
    followup = ask(book, reply_to=sent.json()["id"])
    assert followup.status_code == 409
    assert len(transport["calls"]) == before
    with DB() as db:
        assert [(a.id, a.detail) for a in db.scalars(select(Activity))] == events_before
        assert [(a.id, a.answer, a.outcome, a.assisted) for a in db.scalars(select(Attempt))] == attempts_before


def test_unchanged_question_keeps_same_context_for_followup(book, transport):
    with DB.begin() as db:
        unit = db.get(LearningUnit, book["unit_id"])
        unit.status = "active"
        unit.questions = [{"id": "sun", "type": "short", "prompt": "Was ist die Sonne?", "options": [],
                           "answer": "Stern", "accepted": ["Stern"], "hints": [], "explanation": "Ein Stern."}]
    sent = ask(book)
    assert sent.status_code == 202, sent.text
    finish()
    followup = ask(book, reply_to=sent.json()["id"])
    assert followup.status_code == 202, followup.text
    finish()
    assert transport["calls"][-1]["history"][0]["answer"] == "Die Sonne ist ein Stern."


def test_legacy_answer_without_question_fingerprint_cannot_be_reused(book, transport):
    with DB.begin() as db:
        unit = db.get(LearningUnit, book["unit_id"])
        unit.status = "active"
        unit.questions = [{"id": "sun", "type": "short", "prompt": "Was ist die Sonne?", "options": [],
                           "answer": "Stern", "accepted": ["Stern"], "hints": [], "explanation": "Ein Stern."}]
    sent = ask(book)
    assert sent.status_code == 202, sent.text
    finish()
    with DB.begin() as db:
        turn = db.get(SchulbuddyTurn, sent.json()["id"])
        job = db.get(Job, turn.job_id)
        job.payload = {key: value for key, value in job.payload.items() if key != "question_fingerprint"}
    old = book["client"].get("/api/schulbuddy/questions/" + sent.json()["id"]).json()
    assert old["source_changed"] and "Aufgabenfassung" in old["notice"]
    assert ask(book, reply_to=sent.json()["id"]).status_code == 409


@pytest.mark.parametrize("when", ["before_dispatch", "during_provider"])
@pytest.mark.parametrize("change", ["read_only", "removed"])
def test_parent_losing_family_write_access_never_persists_response(api, book, transport, when, change):
    sent = ask(book, client=api)
    assert sent.status_code == 202, sent.text

    def revoke():
        with DB.begin() as db:
            member = db.scalar(select(Membership).where(Membership.user_id == book["parent"]["id"]))
            assert member is not None
            if change == "read_only":
                member.permission = "view"
            else:
                db.delete(member)

    if when == "before_dispatch":
        revoke()
    else:
        transport["effect"] = revoke
    finish()
    assert len(transport["calls"]) == (0 if when == "before_dispatch" else 1)
    with DB() as db:
        turn = db.get(SchulbuddyTurn, sent.json()["id"])
        assert turn.status == "failed" and turn.reply is None
        assert list(db.scalars(select(Attempt))) == []
        assert list(db.scalars(select(Activity).where(Activity.kind == "explanation"))) == []


def test_revoked_session_before_dispatch_does_not_send_or_save(book, transport):
    sent = ask(book)
    assert sent.status_code == 202, sent.text
    with DB.begin() as db:
        turn = db.get(SchulbuddyTurn, sent.json()["id"])
        db.get(Session, turn.session_id).revoked = True
    finish()
    with DB() as db:
        turn = db.get(SchulbuddyTurn, sent.json()["id"])
        assert turn.status == "failed" and turn.reply is None
        assert db.scalar(select(Usage)).status == "failed_not_sent"
        assert list(db.scalars(select(Activity).where(Activity.kind == "explanation"))) == []
    assert not transport["calls"]
