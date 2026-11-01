"""One synthetic journey joins adaptive work, recall, planning and activity."""

import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from schulpilot import db as database
from schulpilot import learning
from schulpilot.db import DB, Activity, Assignment, Attempt, Child, LearningUnit, Material, UnitSource, now
from schulpilot.learning_knowledge import evidence
from schulpilot.main import app
from sqlalchemy import event, select
from test_adaptive_plan import action, session, submit
from test_adaptive_plan import fraction_profile as original_profile


@pytest.fixture
def profile(api, household):
    yield from original_profile.__wrapped__(api, household)


def test_source_bound_multiday_journey_preserves_parent_plan_and_shared_activity(profile, api, monkeypatch, request):
    client, root_id, material_id, _, _, child = profile
    child_id = child["id"]
    stamp = int(now())
    today = datetime.fromtimestamp(stamp, timezone.utc).date()
    parent_date = (today + timedelta(days=12)).isoformat()
    clock = [int(datetime(today.year, today.month, today.day, 12, tzinfo=timezone.utc).timestamp())]
    beginning = clock[0]
    # Simulate preceding tests that compiled the normal INSERT. Roll the
    # fixture attempt back so it cannot become a learning observation.
    with DB() as db:
        db.add(Attempt(unit_id=root_id, question_id="cache-warmup", answer="fixture", outcome="incorrect"))
        db.flush()
        db.rollback()
    monkeypatch.setattr(database, "now", lambda: clock[0])
    monkeypatch.setattr(learning, "now", lambda: clock[0])
    monkeypatch.setattr(learning, "local_day", lambda _: datetime.fromtimestamp(clock[0], timezone.utc).date())
    # An already compiled INSERT can retain the original column default, even
    # when the default is monkeypatched. Set the timestamp on new test-only
    # objects before INSERT instead, including when the statement cache is warm.
    def timestamp_attempt(_mapper, _connection, attempt):
        if attempt.created is None:
            attempt.created = clock[0]

    event.listen(Attempt, "before_insert", timestamp_attempt)
    request.addfinalizer(lambda: event.remove(Attempt, "before_insert", timestamp_attempt))
    with DB.begin() as db:
        profile_row = db.get(Child, child_id)
        profile_row.preferences = {**profile_row.preferences, "timezone": "UTC", "weekdays": list(range(7))}
        assignment = Assignment(child_id=child_id, kind="parent", subject="Englisch",
            topic="Künstlicher Elternauftrag", mandatory=True, scheduled_for=parent_date)
        db.add(assignment)
        db.flush()
        parent_id = assignment.id

    def future_assignment():
        result = api.get(f"/api/children/{child_id}/learning", params={"section": "later", "subject": "Englisch"})
        assert result.status_code == 200
        return next(item for item in result.json()["items"] if item["id"] == parent_id)

    assert future_assignment()["scheduled_for"] == parent_date
    wrong = submit(client, root_id, "sum", "2/9")
    assert wrong["outcome"] == "incorrect"
    assert action(client, root_id, "review_prerequisite", "journey-probe-0001").status_code == 200
    probe_id = session(client, root_id)["action"]["question_id"]
    submit(client, root_id, probe_id, "2/6", key="journey-probe-answer-0001")
    assert action(client, root_id, "visual_example", "journey-example-0001").status_code == 200
    assert action(client, root_id, "check_understanding", "journey-fresh-0001").status_code == 200
    fresh_id = session(client, root_id)["action"]["question_id"]
    submit(client, root_id, fresh_id, "3/8", key="journey-fresh-answer-0001")
    with DB.begin() as db:
        template = copy.deepcopy(db.get(LearningUnit, root_id).questions[0])
        revision = db.get(Material, material_id).revision

    units, attempt_ids, prompts = [], [], set()
    for index, (days, prompt, answer) in enumerate((
        (1, "Berechne 2/5 + 1/10.", "1/2"),
        (5, "Berechne 1/4 + 1/6.", "5/12"),
        (9, "Berechne 1/3 + 1/12.", "5/12"),
    )):
        clock[0] = beginning + days * 86400
        assert prompt not in prompts
        prompts.add(prompt)
        with DB.begin() as db:
            q = dict(template, id="recall", prompt=prompt, answer=answer, explanation=prompt + " Ergebnis: " + answer)
            unit = LearningUnit(child_id=child_id, material_id=material_id, subject="Mathematik", topic="Brüche",
                explanation="Erinnere dich an die gemeinsame Einteilung.", questions=[q],
                learning_root_id=root_id, followup_of=root_id, round_kind="spaced_review", introduction_seen=True,
                provider="openai", model="synthetic-model-fixture", synthetic=False)
            db.add(unit)
            db.flush()
            db.add(UnitSource(unit_id=unit.id, material_id=material_id, revision=revision))
            units.append(unit.id)
        assert client.post(f"/api/units/{units[-1]}/start").status_code == 200
        answer_result = submit(client, units[-1], "recall", answer, key=f"journey-recall-answer-{index:04}")
        assert answer_result["outcome"] == "correct" and not answer_result["assisted"]
        attempt_ids.append(answer_result["attempt_id"])
        with DB.begin() as db:
            assert db.get(Attempt, answer_result["attempt_id"]).created == clock[0]
            state = next(row for row in evidence(db, db.get(LearningUnit, root_id), [db.get(Material, material_id)])
                if row["label"] == "Brüche addieren")
            assert len(state["successful_check_dates"]) == index + 1
            assert (state["confidence"] == "repeated_recall") is (index == 2)
        assert future_assignment()["scheduled_for"] == parent_date

    # A pause is a recommendation, even with a future parent assignment. Two
    # devices covering the same interval must not create duplicate learning time.
    current_day = datetime.fromtimestamp(clock[0], timezone.utc).date()
    with DB.begin() as db:
        profile_row = db.get(Child, child_id)
        profile_row.preferences = {**profile_row.preferences, "daily_minutes": 5, "weekly_minutes": 5}
        db.add(Activity(child_id=child_id, kind="active_time", detail={"seconds": 300}, created=clock[0] - 60))
        voluntary = LearningUnit(child_id=child_id, material_id=material_id, subject="Mathematik", topic="Brüche",
            explanation="Künstliche freiwillige Runde.", questions=[copy.deepcopy(template)],
            provider="openai", model="synthetic-model-fixture", synthetic=False, break_until=clock[0] + 600)
        db.add(voluntary)
        db.flush()
        db.add(UnitSource(unit_id=voluntary.id, material_id=material_id, revision=revision))
        voluntary_id = voluntary.id
    measured = client.get(f"/api/units/{root_id}").json()["learning_time"]
    assert measured["daily_goal_met"] is True and measured["weekly_goal_met"] is True
    with DB.begin() as db:
        profile_row = db.get(Child, child_id)
        profile_row.preferences = {**profile_row.preferences, "pause_until": (current_day + timedelta(days=1)).isoformat()}
    started = client.post(f"/api/units/{voluntary_id}/start")
    assert started.status_code == 200 and started.json()["status"] == "active"
    assert started.json()["break_until"] is None
    assert started.json()["learning_time"]["goal_required"] is False
    assert started.json()["learning_time"]["daily_active_seconds"] == 300
    assert started.json()["learning_time"]["weekly_goal_met"] is True
    with DB.begin() as db:
        for unit_id in (root_id, voluntary_id):
            unit = db.get(LearningUnit, unit_id)
            assert unit.status == "active"
            unit.heartbeat = clock[0] - 20
        before = sum(row.detail["seconds"] for row in db.scalars(select(Activity).where(
            Activity.child_id == child_id, Activity.kind == "active_time")))

    def beat(unit_id):
        with TestClient(app, headers=dict(client.headers)) as device:
            return device.post(f"/api/units/{unit_id}/heartbeat")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(beat, (root_id, voluntary_id)))
    assert all(result.status_code == 200 for result in results)
    with DB() as db:
        after = sum(row.detail["seconds"] for row in db.scalars(select(Activity).where(
            Activity.child_id == child_id, Activity.kind == "active_time")))
        assert after - before == 20
        assert db.get(Assignment, parent_id).scheduled_for == parent_date
        assert db.get(Attempt, wrong["attempt_id"]).outcome == "incorrect"
    with DB.begin() as db:
        snapshots = [(db.get(Attempt, aid).created, db.get(Attempt, aid).answer) for aid in attempt_ids]
        db.get(Material, material_id).revision += 1
    assert not client.get(f"/api/units/{root_id}/learning-session/knowledge").json()["source_valid"]
    with DB() as db:
        assert [(db.get(Attempt, aid).created, db.get(Attempt, aid).answer) for aid in attempt_ids] == snapshots
        assert all(db.scalar(select(UnitSource.revision).where(UnitSource.unit_id == unit_id,
            UnitSource.material_id == material_id)) == revision for unit_id in units)
