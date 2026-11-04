import io
import json
import zipfile
from concurrent.futures import ThreadPoolExecutor

from conftest import HEADERS, create_child, register
from fastapi.testclient import TestClient
from schulpilot import notifications as n
from schulpilot.db import (
    DB,
    Child,
    FamilyCall,
    Job,
    LanguageProject,
    Membership,
    Message,
    NotificationRead,
    PushDevice,
    Session,
    User,
    VocabularyImport,
    now,
    uid,
)
from schulpilot.main import app
from sqlalchemy import delete, func, select
from test_notifications import device, enable


def test_two_devices_acknowledge_one_event_once(api, household):
    _, child = household
    with DB.begin() as db:
        message = Message(id=uid(), child_id=child["id"], kind="help", body="Synthetic request")
        db.add(message)
        key = "message:" + message.id
    authorization = api.headers["Authorization"]

    def acknowledge(_):
        with TestClient(app, headers={**HEADERS, "Authorization": authorization}) as device_client:
            return device_client.post("/api/notifications/inbox/read", json={"ids": [key]}).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(acknowledge, range(2))) == [200, 200]
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(NotificationRead)) == 1


def test_inbox_is_real_private_and_acknowledgements_idempotent(api, household):
    owner, child = household
    with DB.begin() as db:
        message = Message(id=uid(), child_id=child["id"], kind="help", body="PRIVATE WORDS NEVER IN THE FEED")
        db.add(message)
        key = "message:" + message.id
    for _ in range(3):
        response = api.get("/api/notifications/inbox")
        assert response.status_code == 200
        assert response.json()["unread"] == 1
        assert "PRIVATE WORDS" not in response.text
    assert api.post("/api/notifications/inbox/read", json={"ids": [key, key]}).status_code == 200
    assert api.post("/api/notifications/inbox/read", json={"ids": [key]}).status_code == 200
    assert api.get("/api/notifications/inbox").json()["unread"] == 0
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(NotificationRead)) == 1
        assert db.scalar(select(func.count()).select_from(Job)) == 0
    with TestClient(app, headers=HEADERS) as kid:
        token = kid.post(
            "/api/auth/login", json={"username": "test-child", "password": "secure-child-pass-123"}
        ).json()["token"]
        kid.headers["Authorization"] = "Bearer " + token
        assert kid.get("/api/notifications/inbox").json()["items"] == []
        assert kid.post("/api/notifications/inbox/read", json={"ids": [key]}).status_code == 404
    archive = api.get(f"/api/families/{owner['families'][0]['id']}/export")
    with zipfile.ZipFile(io.BytesIO(archive.content)) as file:
        assert json.loads(file.read("family.json"))["notification_reads"][0]["event_key"] == key
    with DB.begin() as db:
        db.execute(delete(Child).where(Child.id == child["id"]))
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(NotificationRead)) == 0


def test_inbox_denies_other_families_admin_and_revoked_membership(api, household, mailbox):
    owner, child = household
    with DB.begin() as db:
        db.add(Message(child_id=child["id"], kind="help", body="PRIVATE", created=int(now())))
    assert api.get("/api/notifications/inbox").json()["unread"] == 1
    register(api, mailbox, "other@example.org")
    assert api.get("/api/notifications/inbox").json()["items"] == []
    with DB.begin() as db:
        other = db.scalar(select(User).where(User.email == "other@example.org"))
        other.role = "admin"
    assert api.get("/api/notifications/inbox").status_code == 403
    with DB.begin() as db:
        other.role = "parent"
        db.merge(other)
        db.add(Membership(user_id=other.id, family_id=owner["families"][0]["id"], permission="view"))
    key = api.get("/api/notifications/inbox").json()["items"][0]["id"]
    with DB.begin() as db:
        db.execute(
            delete(Membership).where(Membership.user_id == other.id, Membership.family_id == owner["families"][0]["id"])
        )
    assert api.get("/api/notifications/inbox").json()["items"] == []
    assert api.post("/api/notifications/inbox/read", json={"ids": [key]}).status_code == 404


def test_child_reply_bell_does_not_require_push_consent_and_is_bounded(api, household):
    owner, child = household
    sibling = create_child(api, owner, "sibling")
    with DB.begin() as db:
        db.add(Message(child_id=sibling["id"], kind="reply", body="SIBLING PRIVATE"))
        db.add(Message(child_id=child["id"], kind="reply", body="OLD", created=int(now()) - 31 * 86400))
        for index in range(60):
            db.add(Message(child_id=child["id"], kind="reply", body="PRIVATE", created=int(now()) - index))
    login = api.post("/api/auth/login", json={"username": "test-child", "password": "secure-child-pass-123"}).json()
    api.headers["Authorization"] = "Bearer " + login["token"]
    assert api.get("/api/notifications/config").json()["available"] is False
    data = api.get("/api/notifications/inbox").json()
    assert data["unread"] == len(data["items"]) == data["limit"] == 50
    assert all(row["child_id"] == child["id"] for row in data["items"])
    assert api.post("/api/auth/logout").status_code == 200
    assert api.get("/api/notifications/inbox").status_code == 401


def test_own_messages_do_not_crowd_other_notices_out_of_the_bell(api, household):
    owner, child = household
    current = int(now())
    with DB.begin() as db:
        notice = Message(id=uid(), child_id=child["id"], kind="help",
                         body="Synthetic request", created=current - 60)
        db.add(notice)
        for index in range(55):
            db.add(Message(child_id=child["id"], sender_id=owner["id"], kind="help",
                           body="Own synthetic message", created=current - index))
        expected = "message:" + notice.id
    result = api.get("/api/notifications/inbox")
    assert result.status_code == 200
    assert [row["id"] for row in result.json()["items"]] == [expected]
    assert api.post("/api/notifications/inbox/read", json={"ids": [expected]}).status_code == 200


def test_visible_message_can_be_acknowledged_after_new_events_displace_it(api, household):
    _, child = household
    current = int(now())
    with DB.begin() as db:
        old = Message(id=uid(), child_id=child["id"], kind="help",
                      body="Synthetic request", created=current - 1)
        db.add(old)
        key = "message:" + old.id
    assert key in [row["id"] for row in api.get("/api/notifications/inbox").json()["items"]]
    with DB.begin() as db:
        for _ in range(55):
            db.add(Message(id=uid(), child_id=child["id"], kind="help",
                           body="Synthetic request", created=current))
    assert key not in [row["id"] for row in api.get("/api/notifications/inbox").json()["items"]]
    assert api.post("/api/notifications/inbox/read", json={"ids": [key]}).status_code == 200
    assert api.post("/api/notifications/inbox/read", json={"ids": [key]}).status_code == 200
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(NotificationRead).where(
            NotificationRead.event_key == key)) == 1


def test_acknowledgement_checks_only_requested_sources_and_is_atomic(api, household, monkeypatch):
    from schulpilot import exam_notifications, ready_notifications

    _, child = household
    with DB.begin() as db:
        one = Message(id=uid(), child_id=child["id"], kind="help", body="Synthetic")
        two = Message(id=uid(), child_id=child["id"], kind="help", body="Synthetic")
        db.add_all([one, two])
        first, second = "message:" + one.id, "message:" + two.id

    def unrelated_scan(*args, **kwargs):
        raise AssertionError("unrelated event kinds must not be projected")

    monkeypatch.setattr(exam_notifications, "events_for_child", unrelated_scan)
    monkeypatch.setattr(ready_notifications, "events_for_child", unrelated_scan)
    assert api.post("/api/notifications/inbox/read", json={"ids": [first]}).status_code == 200
    assert api.post("/api/notifications/inbox/read", json={"ids": [second, "message:" + uid()]}).status_code == 404
    with DB() as db:
        assert set(db.scalars(select(NotificationRead.event_key))) == {first}


def test_acknowledging_two_still_valid_preparation_notices_for_same_day(api, household):
    from schulpilot.db import Material, SchoolDay

    _, child = household
    with DB.begin() as db:
        day = SchoolDay(id=uid(), child_id=child["id"], school_date="2026-10-20",
                        preparation={"status": "needs_review"})
        db.add(day)
        db.flush()
        db.add(Material(child_id=child["id"], school_day_id=day.id, title="Synthetic", subject="Mathematik"))
        messages = [Message(id=uid(), child_id=child["id"], kind="preparation", body="Synthetic",
                            context={"day_id": day.id}, created=int(now()) - i) for i in range(2)]
        db.add_all(messages)
        keys = ["message:" + message.id for message in messages]
    assert len(api.get("/api/notifications/inbox").json()["items"]) == 1
    assert api.post("/api/notifications/inbox/read", json={"ids": keys}).status_code == 200
    with DB() as db:
        assert set(db.scalars(select(NotificationRead.event_key))) == set(keys)


def test_displaced_message_acknowledgement_keeps_family_and_source_checks(api, household):
    owner, child = household
    sibling = create_child(api, owner, "other-notification-child")
    current = int(now())
    with DB.begin() as db:
        other = Message(id=uid(), child_id=sibling["id"], kind="reply",
                        body="Synthetic", created=current - 1)
        expired = Message(id=uid(), child_id=child["id"], kind="reply",
                          body="Synthetic", created=current - 31 * 86400)
        invalid = Message(id=uid(), child_id=child["id"], kind="preparation",
                          body="Synthetic", context={"material_id": uid()}, created=current - 1)
        db.add_all([other, expired, invalid])
        keys = ["message:" + row.id for row in (other, expired, invalid)]
    login = api.post("/api/auth/login", json={"username": "test-child", "password": "secure-child-pass-123"}).json()
    api.headers["Authorization"] = "Bearer " + login["token"]
    for key in keys:
        assert api.post("/api/notifications/inbox/read", json={"ids": [key]}).status_code == 404
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(NotificationRead)) == 0


def test_displaced_message_cannot_be_acknowledged_after_membership_revocation(api, household, mailbox):
    owner, child = household
    current = int(now())
    with DB.begin() as db:
        old = Message(id=uid(), child_id=child["id"], kind="help",
                      body="Synthetic", created=current - 1)
        db.add(old)
        key = "message:" + old.id
    register(api, mailbox, "temporary-notification-reader@example.org")
    with DB.begin() as db:
        reader = db.scalar(select(User).where(User.email == "temporary-notification-reader@example.org"))
        reader_id = reader.id
        db.add(Membership(user_id=reader_id, family_id=owner["families"][0]["id"], permission="view"))
    assert key in [row["id"] for row in api.get("/api/notifications/inbox").json()["items"]]
    with DB.begin() as db:
        for _ in range(55):
            db.add(Message(id=uid(), child_id=child["id"], kind="help",
                           body="Synthetic", created=current))
        db.execute(delete(Membership).where(Membership.user_id == reader_id,
                                          Membership.family_id == owner["families"][0]["id"]))
    assert api.post("/api/notifications/inbox/read", json={"ids": [key]}).status_code == 404
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(NotificationRead)) == 0


def test_displaced_saved_notices_keep_ownership_and_source_validity(api, household, mailbox):
    from schulpilot.parent_reminder_models import ParentGoalReminderEvent

    owner, child = household
    current = int(now())
    with DB.begin() as db:
        session = db.scalar(select(Session).where(Session.user_id == owner["id"]))
        call = FamilyCall(id=uid(), family_id=owner["families"][0]["id"], child_id=child["id"],
            caller_session_id=session.id, idempotency=uid(), instance=uid(), context_kind="general",
            status="ended", created=current - 10, ring_expires=current - 5, expires=current,
            caller_seen=current - 5)
        goal = ParentGoalReminderEvent(id=uid(), user_id=owner["id"], child_id=child["id"],
            rule_revision=1, date="2026-01-01", scheduled=current - 10, created=current - 10,
            daily_remaining_seconds=60, exam_sessions=[])
        word_job = Job(id=uid(), child_id=child["id"], kind="vocabulary_import", status="completed",
            payload={}, result={}, finished=current - 10, idempotency=uid())
        language_job = Job(id=uid(), child_id=child["id"], kind="language_project", status="completed",
            payload={}, result={}, finished=current - 10, idempotency=uid())
        db.add_all([call, goal, word_job, language_job])
        db.flush()
        word = VocabularyImport(id=uid(), child_id=child["id"], user_id=owner["id"], request_key=uid(),
            request_digest="x" * 64, target_locale="en-GB", title="Synthetic", status="review", job_id=word_job.id)
        language = LanguageProject(id=uid(), child_id=child["id"], user_id=owner["id"], request_key=uid(),
            request_digest="x" * 64, target_locale="en-GB", mode="dialog", inputs={},
            status="ready", job_id=language_job.id)
        db.add_all([word, language])
        keys = ["family_call:" + call.id, "parent_goal:" + goal.id,
                "words_ready:" + word.id, "language_ready:" + language.id]
        word_id, language_job_id = word.id, language_job.id
    loaded = {row["id"] for row in api.get("/api/notifications/inbox").json()["items"]}
    assert set(keys) <= loaded
    with DB.begin() as db:
        for _ in range(55):
            db.add(Message(id=uid(), child_id=child["id"], kind="help", body="Synthetic", created=current))
    loaded = {row["id"] for row in api.get("/api/notifications/inbox").json()["items"]}
    assert not set(keys) & loaded
    assert api.post("/api/notifications/inbox/read", json={"ids": keys}).status_code == 200
    assert api.post("/api/notifications/inbox/read", json={"ids": keys}).status_code == 200
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(NotificationRead)) == 4
    with DB.begin() as db:
        db.get(VocabularyImport, word_id).status = "confirmed"
        db.get(Job, language_job_id).result = {"deleted": True}
    assert api.post("/api/notifications/inbox/read", json={"ids": [keys[2]]}).status_code == 404
    assert api.post("/api/notifications/inbox/read", json={"ids": [keys[3]]}).status_code == 404
    register(api, mailbox, "other-displaced-notices@example.org")
    for key in keys:
        assert api.post("/api/notifications/inbox/read", json={"ids": [key]}).status_code == 404


def test_displaced_word_notice_remains_bound_to_the_current_child(api, household):
    owner, child = household
    sibling = create_child(api, owner, "word-notice-sibling")
    current = int(now())
    with DB.begin() as db:
        keys = []
        for entry in (child, sibling):
            job = Job(id=uid(), child_id=entry["id"], kind="vocabulary_import", status="completed",
                      payload={}, result={}, finished=current - 10, idempotency=uid())
            db.add(job)
            db.flush()
            word = VocabularyImport(id=uid(), child_id=entry["id"], user_id=owner["id"], request_key=uid(),
                request_digest="x" * 64, target_locale="en-GB", title="Synthetic", status="review", job_id=job.id)
            db.add(word)
            keys.append("words_ready:" + word.id)
    login = api.post("/api/auth/login", json={"username": "test-child", "password": "secure-child-pass-123"}).json()
    api.headers["Authorization"] = "Bearer " + login["token"]
    loaded = {row["id"] for row in api.get("/api/notifications/inbox").json()["items"]}
    assert keys[0] in loaded and keys[1] not in loaded
    with DB.begin() as db:
        for _ in range(55):
            db.add(Message(id=uid(), child_id=child["id"], kind="reply", body="Synthetic", created=current))
    assert keys[0] not in {row["id"] for row in api.get("/api/notifications/inbox").json()["items"]}
    assert api.post("/api/notifications/inbox/read", json={"ids": [keys[0]]}).status_code == 200
    assert api.post("/api/notifications/inbox/read", json={"ids": [keys[1]]}).status_code == 404


def test_confirmed_word_imports_do_not_hide_unreviewed_import(api, household):
    owner, child = household
    current = int(now())
    with DB.begin() as db:
        for index in range(56):
            job = Job(id=uid(), child_id=child["id"], kind="vocabulary_import", status="completed",
                      payload={}, result={}, finished=current - (60 if index == 0 else 0), idempotency=uid())
            db.add(job)
            db.flush()
            word = VocabularyImport(id=uid(), child_id=child["id"], user_id=owner["id"], request_key=uid(),
                request_digest="x" * 64, target_locale="en-GB", title="Synthetic",
                status="review" if index == 0 else "confirmed", job_id=job.id)
            db.add(word)
            if index == 0:
                key = "words_ready:" + word.id
    assert key in {x["id"] for x in api.get("/api/notifications/inbox").json()["items"]}
    assert api.post("/api/notifications/inbox/read", json={"ids": [key]}).status_code == 200


def test_foreign_view_only_calls_do_not_hide_eligible_call(api, household, mailbox):
    owner, child = household
    with TestClient(app, headers=HEADERS) as other_api:
        other = register(other_api, mailbox, "other-call-family@example.org")
        foreign_child = create_child(other_api, other, "other-call-child")
    current = int(now())
    with DB.begin() as db:
        db.add(Membership(user_id=owner["id"], family_id=other["families"][0]["id"], permission="view"))
        session = db.scalar(select(Session).where(Session.user_id == owner["id"]))
        for index in range(56):
            call = FamilyCall(id=uid(), family_id=owner["families"][0]["id"] if index == 0 else other["families"][0]["id"],
                child_id=child["id"] if index == 0 else foreign_child["id"], caller_session_id=session.id,
                idempotency=uid(), instance=uid(), context_kind="general", status="ended",
                created=current - (60 if index == 0 else 0), ring_expires=current, expires=current, caller_seen=current)
            db.add(call)
            if index == 0:
                key = "family_call:" + call.id
    items = api.get("/api/notifications/inbox").json()["items"]
    assert [x["id"] for x in items if x["kind"] == "family_call"] == [key]
    assert api.post("/api/notifications/inbox/read", json={"ids": [key]}).status_code == 200


def test_revoked_child_goal_events_do_not_hide_current_events(api, household, mailbox):
    from datetime import date, timedelta

    from schulpilot.parent_reminder_models import ParentGoalReminderEvent

    owner, child = household
    with TestClient(app, headers=HEADERS) as other_api:
        other = register(other_api, mailbox, "other-goal-family@example.org")
        foreign_child = create_child(other_api, other, "other-goal-child")
    current = int(now())
    with DB.begin() as db:
        for index in range(56):
            event = ParentGoalReminderEvent(id=uid(), user_id=owner["id"],
                child_id=child["id"] if index == 0 else foreign_child["id"],
                rule_revision=1, date=(date(2026, 1, 1) + timedelta(days=index)).isoformat(), scheduled=current - 60,
                created=current - (60 if index == 0 else 0), daily_remaining_seconds=60, exam_sessions=[])
            db.add(event)
            if index == 0:
                key = "parent_goal:" + event.id
    items = api.get("/api/notifications/inbox").json()["items"]
    assert [x["id"] for x in items if x["kind"] == "parent_goal"] == [key]
    assert api.post("/api/notifications/inbox/read", json={"ids": [key]}).status_code == 200


def test_childs_own_messages_do_not_hide_parent_reply(api, household):
    owner, child = household
    current = int(now())
    with DB.begin() as db:
        child_user_id = db.get(Child, child["id"]).user_id
        reply = Message(id=uid(), child_id=child["id"], sender_id=owner["id"],
                        kind="reply", body="Synthetic reply", created=current - 60)
        db.add(reply)
        for index in range(55):
            db.add(Message(child_id=child["id"], sender_id=child_user_id, kind="reply",
                           body="Own synthetic message", created=current - index))
        expected = "message:" + reply.id
    login = api.post("/api/auth/login", json={"username": "test-child", "password": "secure-child-pass-123"}).json()
    api.headers["Authorization"] = "Bearer " + login["token"]
    result = api.get("/api/notifications/inbox")
    assert result.status_code == 200
    assert [row["id"] for row in result.json()["items"]] == [expected]
    assert api.post("/api/notifications/inbox/read", json={"ids": [expected]}).status_code == 200


def test_completed_word_import_notifies_with_consent_quiet_and_source_session_recheck(api, household, tmp_path):
    owner, child = household
    enable(tmp_path)
    parent_session = None
    with DB() as db:
        parent_session = db.scalar(select(Session).where(Session.user_id == owner["id"])).id
    with TestClient(app, headers=HEADERS) as separate_device:
        login = separate_device.post(
            "/api/auth/login", json={"username": "test-child", "password": "secure-child-pass-123"}
        ).json()
    api.headers["Authorization"] = "Bearer " + login["token"]
    with DB.begin() as db:
        db.get(Child, child["id"]).preferences = {
            "push_consent": True,
            "reminders": False,
            "quiet_start": 0,
            "quiet_end": 0,
        }
        job = Job(
            id=uid(),
            child_id=child["id"],
            kind="vocabulary_import",
            status="completed",
            payload={},
            finished=int(now()),
            idempotency=uid(),
        )
        db.add(job)
        db.flush()
        row = VocabularyImport(
            id=uid(),
            child_id=child["id"],
            user_id=owner["id"],
            session_id=parent_session,
            request_key=uid(),
            request_digest="x" * 64,
            target_locale="en-GB",
            title="Synthetic words",
            status="review",
            job_id=job.id,
        )
        db.add(row)
    d = device(api)
    with DB.begin() as db:
        stored = db.get(PushDevice, d["id"])
        assert "learning_ready" in n.due_kinds(db, stored, int(now()))
        n.prepare(db)
        n.prepare(db)
        from schulpilot.db import PushDelivery

        assert (
            db.scalar(select(func.count()).select_from(PushDelivery).where(PushDelivery.kind == "learning_ready")) == 1
        )
        db.get(Session, parent_session).revoked = True
        assert "learning_ready" not in n.due_kinds(db, stored, int(now()))
        db.get(Session, parent_session).revoked = False
        db.get(Child, child["id"]).preferences = {"push_consent": False, "quiet_start": 0, "quiet_end": 0}
        assert n.due_kinds(db, stored, int(now())) == []
    assert any(row["kind"] == "words_ready" for row in api.get("/api/notifications/inbox").json()["items"])


def test_human_notices_open_message_reader_only_for_capable_clients(api, household):
    owner, child = household
    with DB.begin() as db:
        db.add(Message(child_id=child["id"], kind="help", body="Synthetic request",
                       context={"unit_id": "synthetic-unit"}))
    new = api.get("/api/notifications/inbox", headers={"X-Schulpilot-Capabilities": "visual-v1,messages-v1"}).json()
    assert new["items"][0]["route"] == f"/messages/{child['id']}"
    # Existing Android clients do not know the new route.
    for capabilities in ("visual-v1", "messages-v10"):
        old = api.get("/api/notifications/inbox", headers={"X-Schulpilot-Capabilities": capabilities}).json()
        assert old["items"][0]["route"] == f"/child/{child['id']}"
    with DB.begin() as db:
        db.add(Message(child_id=child["id"], sender_id=owner["id"], kind="reply", body="Synthetic reply",
                       context={"unit_id": "synthetic-unit"}))
    login = api.post("/api/auth/login", json={"username": "test-child", "password": "secure-child-pass-123"}).json()
    api.headers["Authorization"] = "Bearer " + login["token"]
    new = api.get("/api/notifications/inbox", headers={"X-Schulpilot-Capabilities": "messages-v1"}).json()
    assert new["items"][0]["route"] == f"/messages/{child['id']}"
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Job)) == 0
        assert db.scalar(select(func.count()).select_from(NotificationRead)) == 0


def test_empty_deleted_day_is_not_offered_as_a_zero_page_notice(api, household):
    from schulpilot.db import Material, SchoolDay

    _, child = household
    with DB.begin() as db:
        empty = SchoolDay(id=uid(), child_id=child["id"], school_date="2026-10-19")
        full = SchoolDay(id=uid(), child_id=child["id"], school_date="2026-10-20", preparation={"status": "needs_review"})
        db.add_all([empty, full])
        db.flush()
        db.add(Material(child_id=child["id"], school_day_id=full.id, title="Synthetic source", subject="Mathematik"))
        db.add_all([Message(child_id=child["id"], kind="preparation", body="Synthetic preparation", context={"day_id": d.id})
                    for d in (empty, full)])
        full_id = full.id
    for _ in range(2):
        data = api.get("/api/notifications/inbox").json()
        assert data["unread"] == len(data["items"]) == 1
        assert data["items"][0]["title"] == "1 Heftseite · Mathematik · Bitte prüfen"
        assert data["items"][0]["route"].endswith(full_id)
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Message)) == 2
        assert db.scalar(select(func.count()).select_from(NotificationRead)) == 0
        assert db.scalar(select(func.count()).select_from(Job)) == 0


def test_confirmed_word_import_does_not_keep_asking_for_review(api, household):
    owner, child = household
    with DB.begin() as db:
        job = Job(id=uid(), child_id=child["id"], kind="vocabulary_import", status="completed", payload={},
                  finished=int(now()), idempotency=uid())
        db.add(job)
        db.flush()
        row = VocabularyImport(id=uid(), child_id=child["id"], user_id=owner["id"], request_key=uid(),
                               request_digest="x" * 64, target_locale="en-GB", title="Synthetic words",
                               status="review", job_id=job.id)
        db.add(row)
        row_id = row.id
    assert api.get("/api/notifications/inbox").json()["unread"] == 1
    with DB.begin() as db:
        db.get(VocabularyImport, row_id).status = "confirmed"
    assert api.get("/api/notifications/inbox").json()["items"] == []
    with DB() as db:
        assert db.get(VocabularyImport, row_id).status == "confirmed"
        assert db.scalar(select(func.count()).select_from(Job)) == 1


def test_message_reader_keeps_text_but_hides_deleted_or_foreign_context_without_writes(api, household):
    from schulpilot.db import Activity, Material

    owner, child = household
    sibling = create_child(api, owner, "message-sibling")
    with DB.begin() as db:
        own = Material(id=uid(), child_id=child["id"], title="Synthetic own source")
        foreign = Material(id=uid(), child_id=sibling["id"], title="Synthetic sibling source")
        db.add_all([own, foreign])
        db.flush()
        db.add_all([Message(child_id=child["id"], kind="reply", body=body, context={"material_id": target})
                    for body, target in (("Own context", own.id), ("Deleted context", uid()), ("Foreign context", foreign.id))])
        expected = {m.body: m.context for m in db.scalars(select(Message).where(Message.child_id == child["id"]))}
        before = db.scalar(select(func.count()).select_from(Activity))
    rows = api.get(f"/api/children/{child['id']}/overview?compact=true").json()["messages"]
    assert len(rows) == 3
    own = next(row for row in rows if row["body"] == "Own context")
    assert own["context"] and own["context_unavailable"] is False
    for row in rows:
        if row["body"] != "Own context":
            assert row["context"] is None and row["context_unavailable"] is True
    with DB() as db:
        assert {m.body: m.context for m in db.scalars(select(Message).where(Message.child_id == child["id"]))} == expected
        assert db.scalar(select(func.count()).select_from(Activity)) == before
        assert db.scalar(select(func.count()).select_from(Job)) == 0


def test_deleted_language_round_tombstone_is_not_advertised_as_ready(api, household):
    from schulpilot.db import LanguageProject

    owner, child = household
    with DB.begin() as db:
        job = Job(child_id=child['id'], kind='language_project', status='completed', payload={},
                  result={'deleted': True}, finished=int(now()), idempotency=uid())
        db.add(job)
        db.flush()
        project = LanguageProject(child_id=child['id'], user_id=owner['id'], request_key=uid(),
            request_digest='x'*64, target_locale='en-GB', mode='dialog', inputs={},
            status='failed', job_id=job.id)
        db.add(project)
        job_id = job.id
    assert api.get('/api/notifications/inbox').json()['items'] == []
    with DB() as db:
        assert db.get(Job, job_id).status == 'completed'
        assert db.scalar(select(func.count()).select_from(NotificationRead)) == 0


def test_legacy_notification_links_validate_the_own_child_target(api, household):
    from schulpilot.db import Material

    owner, child = household
    sibling = create_child(api, owner, 'notice-sibling')
    with DB.begin() as db:
        own = Material(child_id=child['id'], title='Own artificial page')
        other = Material(child_id=sibling['id'], title='Sibling artificial page')
        db.add_all([own, other])
        db.flush()
        for value in [own.id, other.id, uid(), ['malformed']]:
            db.add(Message(child_id=child['id'], kind='help', body='Synthetic help', context={'material_id':value}))
        own_id, foreign_id = own.id, other.id
    data = api.get('/api/notifications/inbox',headers={'X-Schulpilot-Capabilities':'visual-v1'}).json()
    assert len(data['items']) == 4
    assert sum(row['route'] == '/material/'+own_id for row in data['items']) == 1
    assert sum(row['route'] == f"/child/{child['id']}" for row in data['items']) == 3
    assert foreign_id not in str(data)


def test_partial_automatic_package_notice_never_claims_all_photos_are_ready(api, household):
    from schulpilot.db import Material, SchoolDay
    _, child = household
    with DB.begin() as db:
        day = SchoolDay(id=uid(), child_id=child["id"], school_date="2026-10-26", preparation={"status": "ready"})
        db.add(day)
        db.flush()
        for index in range(4):
            db.add(Material(child_id=child["id"], school_day_id=day.id, title="Artificial page", subject="Mathematik",
                            confirmed=index != 1, status="confirmed" if index != 1 else "uploaded"))
        db.add(Message(child_id=child["id"], kind="preparation", body="Artificial ready notice", context={"day_id": day.id}))
    for _ in range(2):
        items = api.get("/api/notifications/inbox").json()["items"]
        assert len(items) == 1
        assert "Lernpaket bereit · 1 von 4 Fotos noch offen" in items[0]["title"]
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Job)) == 0
        assert db.scalar(select(func.count()).select_from(NotificationRead)) == 0
