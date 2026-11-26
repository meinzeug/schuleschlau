"""Identical topic titles in different subjects are independent plans."""

from schulpilot import learning
from schulpilot.db import DB, Assignment, Child, Job, LearningUnit, Mastery, Material, Usage, now
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


def test_failed_visual_review_is_voluntary_but_not_the_automatic_today_step(api, household):
    from conftest import create_child
    from schulpilot.daily_planner import period_starts
    from schulpilot.learning_origins import next_item
    from schulpilot.schemas import Preferences

    parent, kid = household
    other = create_child(api, parent, username='other-review-failure')
    with DB.begin() as db:
        child = db.get(Child, kid['id'])
        child.preferences = {'weekdays': list(range(7)), 'daily_minutes': 30}
        today = learning.local_day(child).isoformat()
        unit = LearningUnit(child_id=child.id, **sample_unit(), provider='fixture', status='completed')
        db.add(unit)
        db.flush()
        path = {'subject': unit.subject, 'topic': unit.topic, 'next_unit_id': None, 'next_review': today,
                'latest_unit_id': unit.id, 'root_unit_id': unit.id}
        db.add(Job(child_id=other['id'], kind='unit', status='failed', error_code='visual_unavailable',
                   payload={'review_of': unit.id}, idempotency='other-child-visual-failure', created=int(now())))
        db.flush()
        before = learning.plan(db, child, learning_paths=[path])
        assert 'automatic_unavailable' not in next(item for item in before['voluntary'] if item['kind'] == 'review')
        db.add(Assignment(child_id=child.id, kind='parent', subject='Deutsch', topic='Lesen', mandatory=True))
        day_start, _ = period_starts(learning.local_day(child), Preferences(**child.preferences).timezone)
        # A job started before midnight but failing today is still today's failure.
        db.add(Job(child_id=child.id, kind='unit', status='failed', error_code='visual_unavailable',
                   payload={'review_of': unit.id}, idempotency='visual-review-failed',
                   created=day_start - 1, finished=int(now())))
        db.flush()
        result = learning.plan(db, child, learning_paths=[path])
        review = next(item for item in result['voluntary'] if item['kind'] == 'review')
        assert review['id'] == unit.id and review['automatic_unavailable'] is True
        assert not any(item['id'] == unit.id for item in result['today'])
        assert next_item(result)['kind'] == 'assignment' and next_item(result)['mandatory'] is True

        # A later successful retry clears the automatic hold; no learning
        # evidence, goals, or saved questions are changed by this projection.
        db.add(Job(child_id=child.id, kind='unit', status='completed',
                   payload={'review_of': unit.id}, idempotency='visual-review-recovered', created=int(now()) + 1))
        db.flush()
        recovered = learning.plan(db, child, learning_paths=[path])
        review = next(item for item in recovered['voluntary'] if item['kind'] == 'review')
        assert 'automatic_unavailable' not in review


def test_duplicate_material_failure_is_scoped_to_child_source_revision_and_today(api, household):
    from schulpilot.learning_origins import next_item
    from schulpilot.unit_novelty import DUPLICATE_ERROR

    _, kid = household
    with DB.begin() as db:
        child = db.get(Child, kid['id'])
        child.preferences = {'weekdays': list(range(7)), 'daily_minutes': 30}
        page = Material(child_id=child.id, title='Künstliches Blatt', subject='Biologie', topic='Bienen',
                        content='Bienen sind Insekten.', confirmed=True, status='confirmed')
        db.add(page)
        db.flush()
        db.add(Job(child_id=child.id, kind='unit', status='failed', error_code='unknown', error=DUPLICATE_ERROR,
                   payload={'material_id': page.id, 'material_revision': page.revision},
                   idempotency='duplicate-material-failed', created=int(now()), finished=int(now())))
        db.flush()
        result = learning.plan(db, child, learning_paths=[])
        item = next(item for item in result['voluntary'] if item['kind'] == 'material' and item['id'] == page.id)
        assert item['automatic_unavailable'] is True
        assert all(item['id'] != page.id for item in result['today'])
        assert next_item(result) is None or next_item(result)['id'] != page.id
        page.revision += 1
        db.flush()
        refreshed = learning.plan(db, child, learning_paths=[])
        item = next(item for item in refreshed['voluntary'] if item['kind'] == 'material' and item['id'] == page.id)
        assert 'automatic_unavailable' not in item
