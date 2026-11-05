"""Revision checks for synthetic parent learning preferences."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from conftest import HEADERS, create_child
from fastapi.testclient import TestClient
from schulpilot.db import DB, Assignment, Audit, Child, Job, PushDevice, Session, Usage, engine, now
from schulpilot.main import app
from sqlalchemy import func, select


def snapshot(child_id):
    with DB() as db:
        child = db.get(Child, child_id)
        return {
            "preferences": dict(child.preferences), "revision": child.preferences_revision,
            "assignments": sorted((a.id, a.subject, a.topic, a.done) for a in db.scalars(
                select(Assignment).where(Assignment.child_id == child_id))),
            "devices": sorted(db.scalars(select(PushDevice.id).where(PushDevice.user_id == child.user_id))),
            "audit": db.scalar(select(func.count()).select_from(Audit)),
            "jobs": db.scalar(select(func.count()).select_from(Job)),
            "usage": db.scalar(select(func.count()).select_from(Usage)),
        }


def test_preferences_requires_fresh_revision_before_any_side_effects(api, household):
    _, child = household
    endpoint = f"/api/children/{child['id']}/preferences"
    assert child["preferences_revision"] == 1
    initial = {"push_consent": True, "repeat_topics": ["Englisch: Wörter"]}
    assert api.put(endpoint, json=initial, headers={"If-Match": '"1"'}).status_code == 200
    with DB.begin() as db:
        user_id = db.get(Child, child["id"]).user_id
        session = Session(user_id=user_id, token_hash="a" * 64, device="synthetic", expires=int(now()) + 3600)
        db.add(session)
        db.flush()
        db.add(PushDevice(user_id=user_id, session_id=session.id, token_hash="b" * 64,
            encrypted_token="synthetic-only", platform="android", timezone="Europe/Berlin", quiet_start=20, quiet_end=8))
    before = snapshot(child["id"])
    assert before["revision"] == 2 and len(before["devices"]) == len(before["assignments"]) == 1
    stale = {"push_consent": False, "repeat_topics": ["Mathematik: Brüche"]}
    missing = api.put(endpoint, json=stale)
    assert missing.status_code == 428 and missing.json()["code"] == "preferences_revision_required"
    assert isinstance(missing.json()["detail"], str)
    conflict = api.put(endpoint, json=stale, headers={"If-Match": "1"})
    assert conflict.status_code == 409 and conflict.json()["code"] == "preferences_revision_conflict"
    assert isinstance(conflict.json()["detail"], str)
    for invalid in ('', '0', '"1', '01', '*', '2147483648'):
        assert api.put(endpoint, json=stale, headers={"If-Match": invalid}).status_code == 400
    assert snapshot(child["id"]) == before
    assert api.put(endpoint, json=stale, headers={"If-Match": "2"}).status_code == 200
    after = snapshot(child["id"])
    assert after["revision"] == 3 and not after["devices"]
    assert [(a[1], a[2]) for a in after["assignments"]] == [("Mathematik", "Brüche")]
    assert api.put(endpoint, json=initial, headers={"If-Match": "2"}).status_code == 409
    assert snapshot(child["id"]) == after


def test_preferences_version_is_child_scoped_and_detects_aba(api, household):
    parent, first = household
    second = create_child(api, parent, "second-synthetic-child")
    one = f"/api/children/{first['id']}/preferences"
    two = f"/api/children/{second['id']}/preferences"
    assert api.put(one, json={"daily_minutes": 30}, headers={"If-Match": "1"}).status_code == 200
    assert api.put(one, json={"daily_minutes": 40}, headers={"If-Match": "2"}).status_code == 200
    assert api.put(one, json={"daily_minutes": 30}, headers={"If-Match": "3"}).status_code == 200
    current = snapshot(first["id"])
    assert current["revision"] == 4 and current["preferences"]["daily_minutes"] == 30
    assert api.put(one, json={"daily_minutes": 45}, headers={"If-Match": "2"}).status_code == 409
    assert snapshot(first["id"]) == current
    assert api.get(f"/api/children/{second['id']}/overview").json()["child"]["preferences_revision"] == 1
    assert api.put(two, json={"daily_minutes": 25}, headers={"If-Match": "1"}).status_code == 200
    assert snapshot(first["id"])["revision"] == 4


def test_revision_exhaustion_rejects_without_mutation(api, household):
    _, child = household
    with DB.begin() as db:
        db.get(Child, child["id"]).preferences_revision = 2147483647
    before = snapshot(child["id"])
    result = api.put(f"/api/children/{child['id']}/preferences", json={"push_consent": True},
                     headers={"If-Match": "2147483647"})
    assert result.status_code == 409
    assert snapshot(child["id"]) == before


def test_synthetic_firebase_grant_increments_preference_revision(api, household, monkeypatch, capsys):
    import io
    import json
    import sys

    from schulpilot import firebase_ops
    from schulpilot.db import Family

    parent, child = household
    with DB.begin() as db:
        db.get(Family, parent["families"][0]["id"]).synthetic = True
    monkeypatch.setattr(sys, "argv", ["firebase_ops", "grant-synthetic-test"])
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"username": parent["username"]})))
    firebase_ops.run()
    capsys.readouterr()
    with DB() as db:
        current = db.get(Child, child["id"])
        assert current.preferences_revision == 2 and current.preferences["push_consent"] is True
    endpoint = f"/api/children/{child['id']}/preferences"
    assert api.put(endpoint, json={"push_consent": False}, headers={"If-Match": "1"}).status_code == 409
    with DB() as db:
        current = db.get(Child, child["id"])
        assert current.preferences_revision == 2 and current.preferences["push_consent"] is True


def test_parallel_preferences_same_revision_has_one_winner(api, household):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires genuine PostgreSQL row locking")
    _, child = household
    headers = {**HEADERS, "Authorization": api.headers["Authorization"], "If-Match": "1"}

    def save(minutes):
        with TestClient(app, headers=headers) as client:
            response = client.put(f"/api/children/{child['id']}/preferences", json={"daily_minutes": minutes})
            return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(save, [25, 35]))
    assert sorted(status for status, _ in results) == [200, 409]
    assert next(body for status, body in results if status == 409)["code"] == "preferences_revision_conflict"
    after = snapshot(child["id"])
    assert after["revision"] == 2 and after["preferences"]["daily_minutes"] in (25, 35)
