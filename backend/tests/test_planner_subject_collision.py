"""Identical topic titles in different subjects are independent plans."""

from schulpilot import learning
from schulpilot.db import DB, Assignment, Child, Job, LearningUnit, Mastery, Material, Usage
from schulpilot.synthetic import sample_unit
from sqlalchemy import func, select


def test_due_review_uses_the_correct_subject_despite_other_subjects_with_same_topic(api, household):
    _, kid = household
    with DB.begin() as db:
        child = db.get(Child, kid["id"])
        child.preferences = {"weekdays": list(range(7)), "daily_minutes": 30}
        today = learning.local_day(child).isoformat()
        questions = sample_unit()["questions"]
        maths = LearningUnit(child_id=child.id, subject="Mathematik", topic="Kräfte",
            explanation="Künstliche Mathematikrunde.", questions=questions, provider="fixture", status="completed", created=1)
        # This newer unit previously became the target for the maths review.
        physics = LearningUnit(child_id=child.id, subject="Physik", topic="Kräfte",
            explanation="Künstliche Physikrunde.", questions=questions, provider="fixture", status="completed", created=2)
        db.add_all([maths, physics, Mastery(child_id=child.id, subject="Mathe", topic="Kräfte",
            next_review=today, last_practiced=today)])
        db.flush()
        maths_id = maths.id
        # A same-topic assignment in another subject must not hide the review.
        db.add(Assignment(child_id=child.id, kind="parent", subject="Physik", topic="Kräfte", mandatory=True))
        db.flush()
        before = (db.scalar(select(func.count()).select_from(Job)), db.scalar(select(func.count()).select_from(Usage)))
        options = learning.plan(db, child, learning_paths=[])["voluntary"]
        review = [item for item in options if item["kind"] == "review"]
        assert len(review) == 1
        assert review[0]["id"] == maths_id and review[0]["subject"] == "Mathematik"
        assert (db.scalar(select(func.count()).select_from(Job)), db.scalar(select(func.count()).select_from(Usage))) == before


def test_confirmed_material_of_another_subject_is_not_hidden(api, household):
    _, kid = household
    with DB.begin() as db:
        child = db.get(Child, kid["id"])
        child.preferences = {"weekdays": list(range(7)), "daily_minutes": 30}
        page = Material(child_id=child.id, title="Künstliches Blatt", subject="Geschichte", topic="Zeit",
            content="Eine Zeitachse zeigt die Reihenfolge von Ereignissen.", confirmed=True, status="confirmed")
        db.add_all([page, Assignment(child_id=child.id, kind="parent", subject="Mathematik", topic="Zeit", mandatory=True)])
        db.flush()
        options = learning.plan(db, child, learning_paths=[])["voluntary"]
        assert any(item["kind"] == "material" and item["id"] == page.id for item in options)
        assert any(item["kind"] == "assignment" and item["subject"] == "Mathematik" for item in options)


def test_review_without_a_matching_subject_does_not_borrow_another_subjects_unit(api, household):
    _, kid = household
    with DB.begin() as db:
        child = db.get(Child, kid["id"])
        child.preferences = {"weekdays": list(range(7)), "daily_minutes": 30}
        today = learning.local_day(child).isoformat()
        db.add(Mastery(child_id=child.id, subject="Geschichte", topic="Zeit", next_review=today, last_practiced=today))
        db.add(LearningUnit(child_id=child.id, **(sample_unit() | {"topic": "Zeit"}),
            provider="fixture", status="completed"))
        db.flush()
        options = learning.plan(db, child, learning_paths=[])["voluntary"]
        assert not any(item["kind"] == "review" for item in options)


def test_subject_alias_still_deduplicates_an_existing_learning_path(api, household):
    _, kid = household
    with DB.begin() as db:
        child = db.get(Child, kid["id"])
        child.preferences = {"weekdays": list(range(7)), "daily_minutes": 30}
        today = learning.local_day(child).isoformat()
        db.add(Mastery(child_id=child.id, subject="Mathe", topic="Brüche", next_review=today, last_practiced=today))
        unit = LearningUnit(child_id=child.id, **sample_unit(), provider="fixture", status="completed")
        db.add(unit)
        db.flush()
        path = {"subject": "Mathematik", "topic": "Brüche", "next_unit_id": None, "next_review": today,
            "latest_unit_id": unit.id, "root_unit_id": unit.id}
        options = learning.plan(db, child, learning_paths=[path])["voluntary"]
        assert len([item for item in options if item["kind"] == "review" and item["id"] == unit.id]) == 1
