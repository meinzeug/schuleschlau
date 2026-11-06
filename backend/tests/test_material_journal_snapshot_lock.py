"""Counted material deletion is serialized with journal snapshots."""

import fcntl
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Event

import pytest
from conftest import HEADERS
from fastapi.testclient import TestClient
from schulpilot import erasure
from schulpilot.config import settings
from schulpilot.db import DB, ErasureRequest, Material, SchoolDay, Session
from schulpilot.main import app
from schulpilot.security import digest
from sqlalchemy import select
from test_notebook_actions import photo, preview


@pytest.mark.parametrize("revoke_session", [False, True])
@pytest.mark.parametrize("route", ["bulk", "single", "school_day"])
def test_bulk_deletion_serializes_snapshot_and_rechecks_session(api, household, monkeypatch, revoke_session, route):
    _, child = household
    material, image = photo(api, child, confirmed=False)
    if route == "school_day":
        with DB.begin() as db:
            day = SchoolDay(child_id=child["id"], school_date="2026-10-20")
            db.add(day)
            db.flush()
            day_id = day.id
            db.get(Material, material).school_day_id = day_id
    selection = preview(api, child, ids=[material])["selection_token"] if route == "bulk" else None
    token = api.headers["Authorization"].removeprefix("Bearer ")
    with DB() as db:
        session_id = db.scalar(select(Session.id).where(Session.token_hash == digest(token)))
    lockfile = settings.data_dir / ".erasure-ledger.lock"
    lockfile.touch(mode=0o600, exist_ok=True)
    attempted = Event()
    original = erasure.journal_write_lock

    @contextmanager
    def traced_lock():
        attempted.set()
        with original():
            yield

    monkeypatch.setattr(erasure, "journal_write_lock", traced_lock)
    headers = {**HEADERS, "Authorization": "Bearer " + token}

    def delete_material():
        with TestClient(app, headers=headers) as client:
            if route == "single":
                return client.delete(f"/api/materials/{material}")
            if route == "school_day":
                return client.delete(f"/api/school-days/{day_id}/pages/{material}")
            return client.post(f"/api/children/{child['id']}/materials/bulk-delete", json={
                "selection_token": selection, "delete_linked_units": True})

    with ThreadPoolExecutor(max_workers=1) as pool:
        with lockfile.open("rb") as snapshot:
            fcntl.flock(snapshot, fcntl.LOCK_SH)
            task = pool.submit(delete_material)
            assert attempted.wait(8)
            with DB.begin() as db:
                assert db.get(Material, material) is not None
                assert db.scalar(select(ErasureRequest.id).where(ErasureRequest.target == material)) is None
                if revoke_session:
                    db.get(Session, session_id).revoked = True
        response = task.result(12)
    assert response.status_code == (401 if revoke_session else 200), response.text
    with DB() as db:
        assert (db.get(Material, material) is not None) is revoke_session
        event = db.scalar(select(ErasureRequest).where(ErasureRequest.target == material))
        assert (event is None) is revoke_session
        if event:
            assert event.published is True
    assert image.exists() is revoke_session


def test_child_single_page_delegation_takes_journal_lock_only_once(api, household, monkeypatch):
    from test_notebook_actions import kid

    _, child = household
    material, image = photo(api, child, confirmed=False)
    with DB.begin() as db:
        day = SchoolDay(child_id=child["id"], school_date="2026-10-20")
        db.add(day)
        db.flush()
        db.get(Material, material).school_day_id = day.id
    attempts = []
    original = erasure.journal_write_lock

    @contextmanager
    def traced_lock():
        attempts.append("acquire")
        with original():
            yield

    monkeypatch.setattr(erasure, "journal_write_lock", traced_lock)
    with kid() as client:
        response = client.delete(f"/api/materials/{material}")
    assert response.status_code == 200, response.text
    # A second acquisition is the ordinary flush after releasing the mutation
    # lock; a nested acquisition would deadlock before returning this response.
    assert attempts == ["acquire", "acquire"]
    assert not image.exists()
    with DB() as db:
        assert db.get(Material, material) is None
        event = db.scalar(select(ErasureRequest).where(ErasureRequest.target == material))
        assert event is not None and event.published is True
