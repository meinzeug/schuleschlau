"""Bounded inbox sources must choose the same tie order as the merged feed."""

from datetime import date, timedelta

from schulpilot.db import DB, FamilyCall, Job, LanguageProject, Session, now
from schulpilot.parent_reminder_models import ParentGoalReminderEvent
from sqlalchemy import select


def test_same_second_family_calls_use_notice_id_before_limiting(api, household):
    owner, child = household
    stamp = int(now())
    with DB.begin() as db:
        session = db.scalar(select(Session).where(Session.user_id == owner["id"]))
        for index in range(55):
            db.add(FamilyCall(id=f"{index + 1:032x}", family_id=owner["families"][0]["id"],
                child_id=child["id"], caller_session_id=session.id, idempotency=f"call-{index}",
                instance=f"instance-{index}", context_kind="general", status="ended",
                created=stamp, ring_expires=stamp, expires=stamp, caller_seen=stamp))
    response = api.get("/api/notifications/inbox")
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["items"]] == [
        f"family_call:{index:032x}" for index in range(55, 5, -1)
    ]


def test_same_second_parent_checks_use_event_id_before_limiting(api, household):
    owner, child = household
    stamp = int(now())
    with DB.begin() as db:
        for index in range(55):
            db.add(ParentGoalReminderEvent(
                id=f"{index + 1:032x}", user_id=owner["id"], child_id=child["id"],
                date=(date(2026, 1, 1) + timedelta(days=index)).isoformat(),
                rule_revision=1, scheduled=stamp, created=stamp,
                daily_remaining_seconds=60, exam_sessions=[],
            ))
    response = api.get("/api/notifications/inbox")
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["items"]] == [
        f"parent_goal:{index:032x}" for index in range(55, 5, -1)
    ]


def test_same_second_language_jobs_are_limited_by_notice_id_not_job_id(api, household):
    owner, child = household
    stamp = int(now())
    with DB.begin() as db:
        for index in range(55):
            # Job and notice IDs deliberately run in opposite directions.
            job = Job(id=f"{1000 - index:032x}", child_id=child["id"], kind="language_project",
                status="completed", payload={}, result={}, finished=stamp, idempotency=f"job-{index}")
            db.add(job)
            db.flush()
            db.add(LanguageProject(id=f"{index + 1:032x}", child_id=child["id"], user_id=owner["id"],
                request_key=f"project-{index}", request_digest="a" * 64, target_locale="en-GB",
                mode="dialog", inputs={}, status="ready", job_id=job.id))
    response = api.get("/api/notifications/inbox")
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["items"]] == [
        f"language_ready:{index:032x}" for index in range(55, 5, -1)
    ]
