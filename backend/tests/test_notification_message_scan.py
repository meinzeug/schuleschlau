"""Stale notices must not occupy the visible window or cross family bounds."""

from schulpilot.db import DB, Job, Message, NotificationRead, now
from sqlalchemy import func, select


def test_invalid_preparations_do_not_hide_valid_messages_at_same_timestamp(api, household):
    _, child = household
    stamp = int(now())
    with DB.begin() as db:
        db.add_all([
            Message(id=f"{index:032x}", child_id=child["id"], kind="preparation",
                body="Synthetic", context={"material_id": "f" * 32}, created=stamp)
            for index in range(100, 160)
        ])
        db.add_all([
            Message(id=f"{index:032x}", child_id=child["id"], kind="help",
                body="Synthetic", created=stamp)
            for index in range(1, 52)
        ])

    response = api.get("/api/notifications/inbox")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [
        f"message:{index:032x}" for index in range(51, 1, -1)
    ]
    # A real, displaced notice remains acknowledgeable. A stale reference
    # cannot be made valid by requesting it directly.
    assert api.post("/api/notifications/inbox/read", json={"ids": [f"message:{1:032x}"]}).status_code == 200
    assert api.post("/api/notifications/inbox/read", json={"ids": [f"message:{159:032x}"]}).status_code == 404
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Job)) == 0
        assert db.scalar(select(func.count()).select_from(NotificationRead)) == 1


def test_scan_stays_bounded_and_get_does_not_write(api, household, monkeypatch):
    from schulpilot import notification_inbox

    _, child = household
    monkeypatch.setattr(notification_inbox, "MESSAGE_SCAN_LIMIT", 100)
    stamp = int(now())
    with DB.begin() as db:
        db.add_all([
            Message(id=f"{index:032x}", child_id=child["id"], kind="preparation",
                body="Synthetic", context={"material_id": "f" * 32}, created=stamp)
            for index in range(100, 205)
        ])
        db.add(Message(id=f"{1:032x}", child_id=child["id"], kind="help", body="Synthetic", created=stamp))
    assert api.get("/api/notifications/inbox").json()["items"] == []
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Job)) == 0
        assert db.scalar(select(func.count()).select_from(NotificationRead)) == 0
