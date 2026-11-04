"""Artificial homework source quarantine and provider-boundary regression tests."""
import json
import uuid

import pytest
from schulpilot import homework, worker
from schulpilot.db import DB, Assignment, Job, LearningUnit, Material, UnitCoaching, now
from schulpilot.providers import Result
from sqlalchemy import select
from test_homework import FRACTION_HOMEWORK, TEXT, finish, practice, practice_unit, prepare
from test_homework import book as _book


@pytest.fixture
def book(api, household):
    yield from _book.__wrapped__(api, household)

MARK = "Vertrauliche synthetische Schülerlösung 12345"


def set_blocks(material, safe, hidden):
    material.content = safe + "\n\n" + hidden
    material.source_blocks = [{"kind": "paragraph", "text": safe},
                              {"kind": "paragraph", "text": hidden, "literal_role": "student_work"}]


def test_homework_provider_never_receives_excluded_original_but_local_check_keeps_it(book, monkeypatch):
    prepare(book)
    with DB.begin() as db:
        page = db.get(Material, book["material_id"])
        set_blocks(page, TEXT, MARK)
    response = practice(book)
    assert response.status_code == 202, response.text
    calls = []

    def generate(config, function, payload, *args, **kwargs):
        calls.append(payload)
        assert TEXT in payload["material"]["content"]
        assert MARK not in json.dumps(payload, ensure_ascii=False)
        return Result(practice_unit(), 50, 80, 12)

    monkeypatch.setattr(worker, "request_provider", generate)
    finish()
    with DB() as db:
        assert db.get(Job, response.json()["id"]).status == "completed"
        assert any(MARK in x for x in homework.practice_exclusions(db, db.get(Material, book["material_id"])))
    assert len(calls) == 1


def test_homework_recall_provider_never_receives_excluded_original(book, monkeypatch):
    prepare(book)
    with DB.begin() as db:
        source, unit = db.get(Material, book["material_id"]), db.get(LearningUnit, book["unit_id"])
        set_blocks(source, FRACTION_HOMEWORK, MARK)
        source.topic = "Brüche addieren"
        unit.subject, unit.topic, unit.status, unit.completed = "Mathematik", source.topic, "completed", int(now())
        unit.questions = [{"id": "q1", "type": "short", "prompt": "Erweitere 2/7 mit dem Faktor 3.",
            "answer": "6/21", "accepted": [], "options": [], "hints": ["Multipliziere beide Zahlen."],
            "explanation": "Beide Zahlen werden mit drei multipliziert.", "learning_goal_id": "g2"}]
        db.add(UnitCoaching(unit_id=unit.id, status="ready", decision="check", report={"learning_goals": [
            {"id": "g2", "label": "Brüche erweitern", "source_excerpt": "Erweitere Zähler und Nenner mit\nderselben Zahl."}]}))
    response = book["client"].post(f"/api/children/{book['child']['id']}/units", json={"review_of": book["unit_id"]},
        headers={"Idempotency-Key": uuid.uuid4().hex})
    assert response.status_code == 202, response.text
    calls = []

    def generate(config, function, payload, *args, **kwargs):
        calls.append(payload)
        assert payload["homework_original_prompts"] == [FRACTION_HOMEWORK]
        assert MARK not in json.dumps(payload, ensure_ascii=False)
        return Result({"subject": "Mathematik", "topic": "Brüche addieren", "explanation": "Prüfe erneut das Erweitern.",
            "questions": [{"id": f"q{i}", "type": "short", "prompt": f"Erweitere {a}/{b} mit dem Faktor 2.",
                "answer": f"{a * 2}/{b * 2}", "accepted": [], "options": [], "hints": ["Multipliziere beide Zahlen."],
                "explanation": "Beide Zahlen werden verdoppelt.", "learning_goal_id": "g2"} for i, (a, b) in enumerate(((3, 7), (4, 9)), 1)]}, 50, 80, 12)

    monkeypatch.setattr(worker, "request_provider", generate)
    finish()
    with DB() as db:
        job = db.get(Job, response.json()["id"])
        assert job.status == "completed", job.error
    assert len(calls) == 1


def assignment_fixture(book, *, initially_safe):
    prepare(book)
    with DB.begin() as db:
        first = db.get(Material, book["material_id"])
        first.content = MARK
        first.source_blocks = [{"kind": "paragraph", "text": MARK, **({} if initially_safe else {"literal_role": "student_work"})}]
        second = Material(child_id=first.child_id, school_day_id=first.school_day_id, page_number=2, title="Sichere Seite",
            subject="Mathematik", topic="Flächen", content=TEXT, confirmed=True, status="confirmed")
        db.add(second)
        db.flush()
        assignment = Assignment(child_id=first.child_id, material_id=first.id, kind="homework", origin_kind="homework",
            subject="Mathematik", topic="Flächen", note=MARK, source_status="confirmed", mandatory=True,
            source_revisions=[{"id": first.id, "revision": first.revision}, {"id": second.id, "revision": second.revision}])
        db.add(assignment)
        db.flush()
        return assignment.id


def start(book, assignment_id):
    return book["client"].post(f"/api/children/{book['child']['id']}/units", json={"assignment_id": assignment_id},
        headers={"Idempotency-Key": uuid.uuid4().hex})


def test_second_safe_page_cannot_launder_unsafe_homework_note(book):
    assignment_id = assignment_fixture(book, initially_safe=False)
    response = start(book, assignment_id)
    assert response.status_code == 409, response.text
    with DB() as db:
        assert not db.scalar(select(Job).where(Job.child_id == book["child"]["id"]))


@pytest.mark.parametrize("timing", ["before", "during"])
def test_homework_source_quarantine_rechecked_before_and_after_provider(book, monkeypatch, timing):
    assignment_id = assignment_fixture(book, initially_safe=True)
    response = start(book, assignment_id)
    assert response.status_code == 202, response.text
    calls = []

    def quarantine():
        with DB.begin() as db:
            db.get(Material, book["material_id"]).source_blocks = [{"kind": "paragraph", "text": MARK, "literal_role": "student_work"}]

    def generate(config, function, payload, *args, **kwargs):
        calls.append(payload)
        if timing == "during":
            quarantine()
        return Result(practice_unit(), 50, 80, 12)

    if timing == "before":
        quarantine()
    monkeypatch.setattr(worker, "request_provider", generate)
    finish()
    with DB() as db:
        job = db.get(Job, response.json()["id"])
        assert job.status == "failed" and job.result is None
    assert len(calls) == (0 if timing == "before" else 1)


def test_explicit_parent_assignment_still_allowed_even_with_attached_photo(api, book):
    prepare(book)
    response = api.post(f"/api/children/{book['child']['id']}/assignments", json={"kind": "parent", "subject": "Mathematik",
        "topic": "Flächen", "note": "Bitte übe die Berechnung von Flächen.", "material_id": book["material_id"]})
    assert response.status_code == 201, response.text
    from schulpilot.material_tasks import homework_note_supported
    with DB() as db:
        assert homework_note_supported(db, db.get(Assignment, response.json()["id"]))


def test_explicit_ocr_task_from_quarantined_mark_is_needs_review(api, household):
    from schulpilot.material_tasks import preview

    _, child = household
    original = "Hausaufgabe: Rechne 3 + 4 = 9."
    corrected = "Hausaufgabe: Rechne 3 + 4 = 8."
    with DB.begin() as db:
        page = Material(child_id=child["id"], title="Künstliche Aufgabe", subject="Mathematik", topic="Addition",
            content=original, source_blocks=[{"kind": "paragraph", "text": original, "literal_role": "student_work"}],
            status="review", confirmed=False, uncertainties=[])
        db.add(page)
        db.flush()
        page_id = page.id
    key = preview(corrected, [corrected])[0]["key"]
    result = api.put(f"/api/materials/{page_id}/confirm", json={"revision": 1, "subject": "Mathematik", "topic": "Addition",
        "content": corrected, "homework": [corrected], "uncertainties_resolved": True,
        "task_decisions": [{"key": key, "classification": "homework"}]})
    assert result.status_code == 200, result.text
    with DB() as db:
        assignment = db.scalar(select(Assignment).where(Assignment.child_id == child["id"]))
        assert assignment is not None and assignment.source_status == "needs_review"
        assert not db.scalar(select(Job).where(Job.child_id == child["id"]))
