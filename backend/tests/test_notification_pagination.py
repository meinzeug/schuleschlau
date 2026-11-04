"""Synthetic pagination regressions: stable ties, validation, and family isolation."""
from datetime import date, timedelta

from schulpilot.db import DB, FamilyCall, Job, LanguageProject, Message, NotificationRead, Session, now
from schulpilot.parent_reminder_models import ParentGoalReminderEvent
from sqlalchemy import func, select


def collect(api, max_pages=100):
    items, cursor, counts = [], None, []
    for _ in range(max_pages):
        params = {"paginate": "1"}
        if cursor:
            params["cursor"] = cursor
        response = api.get("/api/notifications/inbox", params=params)
        assert response.status_code == 200, response.text
        data = response.json()
        counts.append(len(data["items"]))
        items.extend(data["items"])
        next_cursor = data["next_cursor"]
        if next_cursor is None:
            return items, counts
        assert next_cursor != cursor
        cursor = next_cursor
    raise AssertionError("pagination did not terminate")


def test_many_tied_notices_from_several_sources_have_stable_complete_order(api, household):
    owner, child = household
    stamp = int(now())
    with DB.begin() as db:
        session = db.scalar(select(Session).where(Session.user_id == owner["id"]))
        for index in range(65):
            db.add(Message(id=f"{index + 1:032x}", child_id=child["id"], kind="help", body="Synthetic", created=stamp))
            db.add(FamilyCall(id=f"{index + 1:032x}", family_id=owner["families"][0]["id"],
                child_id=child["id"], caller_session_id=session.id, idempotency=f"call-{index}",
                instance=f"instance-{index}", context_kind="general", status="ended",
                created=stamp, ring_expires=stamp, expires=stamp, caller_seen=stamp))
            db.add(ParentGoalReminderEvent(id=f"{index + 1:032x}", user_id=owner["id"], child_id=child["id"],
                date=(date(2026, 1, 1) + timedelta(days=index)).isoformat(), rule_revision=1,
                scheduled=stamp, created=stamp, daily_remaining_seconds=60, exam_sessions=[]))
            job = Job(id=f"{1000-index:032x}", child_id=child["id"], kind="language_project",
                status="completed", payload={}, result={}, finished=stamp, idempotency=f"job-{index}")
            db.add(job)
            db.flush()
            db.add(LanguageProject(id=f"{index + 1:032x}", child_id=child["id"], user_id=owner["id"],
                request_key=f"project-{index}", request_digest="a" * 64, target_locale="en-GB",
                mode="dialog", inputs={}, status="ready", job_id=job.id))
    items, counts = collect(api)
    keys = [item["id"] for item in items]
    expected = sorted((f"{kind}:{index:032x}" for kind in
        ("message", "family_call", "parent_goal", "language_ready") for index in range(1, 66)), reverse=True)
    assert keys == expected
    assert counts == [50, 50, 50, 50, 50, 10]
    assert api.post("/api/notifications/inbox/read", json={"ids": [keys[-1]]}).status_code == 200
    assert next(x for x in collect(api)[0] if x["id"] == keys[-1])["read"]


def test_empty_validation_block_has_continuation_and_reaches_older_event(api, household):
    _, child = household
    stamp = int(now())
    with DB.begin() as db:
        db.add_all([Message(id=f"{index:032x}", child_id=child["id"], kind="preparation",
            body="Synthetic", context={"material_id": "f" * 32}, created=stamp) for index in range(2, 552)])
        db.add(Message(id=f"{1:032x}", child_id=child["id"], kind="help", body="Synthetic", created=stamp))
    items, counts = collect(api)
    assert counts == [0, 1]
    assert [item["id"] for item in items] == [f"message:{1:032x}"]
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(NotificationRead)) == 0


def test_invalid_cursor_is_rejected_and_legacy_shape_stays_unchanged(api, household):
    assert api.get("/api/notifications/inbox", params={"paginate": "1", "cursor": "!"}).status_code == 400
    assert api.get("/api/notifications/inbox", params={"cursor": "anything"}).status_code == 400
    assert "next_cursor" not in api.get("/api/notifications/inbox").json()


def test_cursor_rechecks_family_access_after_membership_revocation(api, household):
    from schulpilot.db import Membership
    from sqlalchemy import delete

    owner, child = household
    stamp = int(now())
    with DB.begin() as db:
        db.add_all([Message(id=f"{index:032x}", child_id=child["id"], kind="help",
            body="Synthetic", created=stamp) for index in range(1, 55)])
    first = api.get("/api/notifications/inbox", params={"paginate": "1"}).json()
    assert len(first["items"]) == 50 and first["next_cursor"]
    with DB.begin() as db:
        db.execute(delete(Membership).where(Membership.user_id == owner["id"]))
    following = api.get("/api/notifications/inbox", params={"paginate": "1", "cursor": first["next_cursor"]})
    assert following.status_code == 200
    assert following.json()["items"] == []
    assert following.json()["next_cursor"] is None


def test_removed_message_cannot_be_reached_or_marked_read_from_old_cursor(api, household):
    from sqlalchemy import delete

    _, child = household
    stamp = int(now())
    with DB.begin() as db:
        db.add_all([Message(id=f"{index:032x}", child_id=child["id"], kind="help",
            body="Synthetic", created=stamp) for index in range(1, 55)])
    first = api.get("/api/notifications/inbox", params={"paginate": "1"}).json()
    with DB.begin() as db:
        db.execute(delete(Message).where(Message.id == f"{1:032x}"))
    following = api.get("/api/notifications/inbox", params={"paginate": "1", "cursor": first["next_cursor"]}).json()
    assert f"message:{1:032x}" not in {item["id"] for item in following["items"]}
    assert api.post("/api/notifications/inbox/read", json={"ids": [f"message:{1:032x}"]}).status_code == 404


def test_paged_round_receipt_rechecks_source_and_direct_link(api, case):
    from schulpilot.db import Material
    from test_round_ready_notifications import remember

    assert remember(case)
    with DB.begin() as db:
        db.add_all([Message(id=f"{index:032x}", child_id=case["child"], kind="help",
            body="Synthetic", created=int(now())) for index in range(1, 55)])
    notices, _ = collect(api)
    ready = next(item for item in notices if item["kind"] == "round_ready")
    assert ready["route"] == "/unit/" + case["unit"]
    with DB.begin() as db:
        db.get(Material, case["material"]).revision += 1
    assert ready["id"] not in {item["id"] for item in collect(api)[0]}
    assert api.post("/api/notifications/inbox/read", json={"ids": [ready["id"]]}).status_code == 404


def test_paged_exam_reminder_and_ready_respect_capabilities(api, book):
    from test_exam_notifications import planned, ready_round

    planned(api, book)
    client = book["client"]
    headers = {"X-Schulpilot-Capabilities": "messages-v1,exams-v1"}
    reminders = client.get("/api/notifications/inbox", params={"paginate": "1"}, headers=headers).json()["items"]
    reminder = next(item for item in reminders if item["kind"] == "exam_reminder")
    assert reminder["route"].startswith("/exams/")
    ready_round(api, book)
    notices = client.get("/api/notifications/inbox", params={"paginate": "1"}, headers=headers).json()["items"]
    assert any(item["kind"] == "exam_ready" and item["route"].startswith("/unit/") for item in notices)


from test_exams import book as book  # noqa: E402,F401
from test_round_ready_notifications import case as case  # noqa: E402,F401


def test_concurrent_new_messages_do_not_duplicate_or_skip_older_page(api, household):
    _, child = household
    stamp = int(now())
    with DB.begin() as db:
        db.add_all([Message(id=f"{index:032x}", child_id=child["id"], kind="help",
            body="Synthetic", created=stamp) for index in range(1, 56)])
    first = api.get("/api/notifications/inbox", params={"paginate": "1"}).json()
    with DB.begin() as db:
        db.add_all([Message(id=f"{index:032x}", child_id=child["id"], kind="help",
            body="Synthetic", created=stamp) for index in (0, 100)])
    second = api.get("/api/notifications/inbox", params={
        "paginate": "1", "cursor": first["next_cursor"]}).json()
    first_keys = {item["id"] for item in first["items"]}
    second_keys = [item["id"] for item in second["items"]]
    assert not first_keys.intersection(second_keys)
    assert second_keys == [f"message:{index:032x}" for index in range(5, -1, -1)]
    assert f"message:{100:032x}" not in second_keys


def test_paginated_human_message_opens_the_same_capability_bound_route(api, household):
    _, child = household
    with DB.begin() as db:
        db.add(Message(child_id=child["id"], kind="help", body="Synthetic", created=int(now())))
    headers = {"X-Schulpilot-Capabilities": "messages-v1"}
    modern = api.get("/api/notifications/inbox", params={"paginate": "1"}, headers=headers).json()
    assert modern["items"][0]["route"] == "/messages/" + child["id"]
    legacy = api.get("/api/notifications/inbox", params={"paginate": "1"}).json()
    assert legacy["items"][0]["route"] == "/child/" + child["id"]


def test_preparation_day_is_deduplicated_across_pages_but_old_receipt_remains_valid(api, household):
    from schulpilot.db import Material, SchoolDay, uid

    _, child = household
    stamp = int(now())
    with DB.begin() as db:
        day = SchoolDay(id=uid(), child_id=child["id"], school_date="2026-10-20",
            preparation={"status": "needs_review"})
        db.add(day)
        db.flush()
        db.add(Material(child_id=child["id"], school_day_id=day.id, title="Synthetic", subject="Mathematik"))
        newer, older = uid(), uid()
        db.add_all([
            Message(id=newer, child_id=child["id"], kind="preparation", body="Synthetic",
                context={"day_id": day.id}, created=stamp),
            Message(id=older, child_id=child["id"], kind="preparation", body="Synthetic",
                context={"day_id": day.id}, created=stamp - 20),
            *[Message(child_id=child["id"], kind="help", body="Synthetic", created=stamp - 10) for _ in range(55)],
        ])
    items, _ = collect(api)
    preparations = [row for row in items if row["kind"] == "preparation"]
    assert [row["id"] for row in preparations] == ["message:" + newer]
    assert api.post("/api/notifications/inbox/read", json={"ids": ["message:" + older]}).status_code == 200


def test_preparation_dedup_ignores_more_than_500_other_context_shapes(api, household):
    from schulpilot.db import Material, SchoolDay, uid

    _, child = household
    stamp = int(now())
    with DB.begin() as db:
        day = SchoolDay(id=uid(), child_id=child["id"], school_date="2026-10-20",
            preparation={"status": "needs_review"})
        db.add(day)
        db.flush()
        db.add(Material(child_id=child["id"], school_day_id=day.id,
            title="Synthetic", subject="Mathematik"))
        newest, older = uid(), uid()
        db.add_all([
            Message(id=newest, child_id=child["id"], kind="preparation", body="Synthetic",
                context={"day_id": day.id}, created=stamp - 1),
            Message(id=older, child_id=child["id"], kind="preparation", body="Synthetic",
                context={"day_id": day.id}, created=stamp - 2),
            *[Message(child_id=child["id"], kind="preparation", body="Synthetic",
                context={"day_id": day.id, "extra": index}, created=stamp)
              for index in range(501)],
        ])
    items, counts = collect(api)
    assert len(counts) >= 2
    assert [row["id"] for row in items if row["kind"] == "preparation"] == ["message:" + newest]
    assert api.post("/api/notifications/inbox/read", json={"ids": ["message:" + older]}).status_code == 200


def test_preparation_dedup_compares_decoded_json_not_escape_spelling(api, household):
    from schulpilot.db import Material, SchoolDay, uid
    from sqlalchemy import text

    _, child = household
    stamp = int(now())
    with DB.begin() as db:
        day = SchoolDay(id=uid(), child_id=child["id"], school_date="2026-10-20",
            preparation={"status": "needs_review"})
        db.add(day)
        db.flush()
        db.add(Material(child_id=child["id"], school_day_id=day.id,
            title="Synthetic", subject="Mathematik"))
        newer, older = uid(), uid()
        db.add_all([
            Message(id=newer, child_id=child["id"], kind="preparation", body="Synthetic",
                context={"day_id": day.id}, created=stamp),
            Message(id=older, child_id=child["id"], kind="preparation", body="Synthetic",
                context={"day_id": day.id}, created=stamp - 1),
        ])
        db.flush()
        encoded_id = "\\u%04x" % ord(day.id[0]) + day.id[1:]
        raw_json = '{ "day_id" : "' + encoded_id + '" }'
        db.execute(text("UPDATE messages SET context = :raw WHERE id = :id"),
            {"raw": raw_json, "id": newer})
    items, _ = collect(api)
    assert [row["id"] for row in items if row["kind"] == "preparation"] == ["message:" + newer]
