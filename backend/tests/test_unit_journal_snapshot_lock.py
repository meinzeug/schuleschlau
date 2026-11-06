"""Unit deletion preserves snapshot and session locking order."""

import fcntl
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Event

import pytest
from conftest import HEADERS
from fastapi.testclient import TestClient
from schulpilot import erasure
from schulpilot.config import settings
from schulpilot.db import DB, ErasureRequest, LearningUnit, Session
from schulpilot.main import app
from schulpilot.security import digest
from sqlalchemy import select
from test_notebook_actions import photo, saved_round


@pytest.mark.parametrize("revoke_session", [False, True])
def test_unit_deletion_serializes_snapshot_and_rechecks_session(api, household, monkeypatch, revoke_session):
    _, child = household
    material, _ = photo(api, child)
    unit, _ = saved_round(child, material)
    preview = api.post(f"/api/units/{unit}/delete-preview", json={})
    assert preview.status_code == 200, preview.text
    selection = preview.json()["selection_token"]
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

    def delete_unit():
        with TestClient(app, headers=headers) as client:
            return client.post(f"/api/units/{unit}/delete", json={"selection_token": selection})

    with ThreadPoolExecutor(max_workers=1) as pool:
        with lockfile.open("rb") as snapshot:
            fcntl.flock(snapshot, fcntl.LOCK_SH)
            task = pool.submit(delete_unit)
            assert attempted.wait(8)
            with DB.begin() as db:
                assert db.get(LearningUnit, unit) is not None
                assert db.scalar(select(ErasureRequest.id).where(ErasureRequest.target == unit)) is None
                if revoke_session:
                    db.get(Session, session_id).revoked = True
        response = task.result(12)
    assert response.status_code == (401 if revoke_session else 200), response.text
    with DB() as db:
        assert (db.get(LearningUnit, unit) is not None) is revoke_session
        event = db.scalar(select(ErasureRequest).where(ErasureRequest.target == unit))
        assert (event is None) is revoke_session
        if event:
            assert event.published is True
