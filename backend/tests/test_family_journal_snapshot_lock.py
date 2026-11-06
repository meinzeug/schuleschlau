"""A family revocation cannot commit inside an active journal snapshot."""

import fcntl
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Event

from conftest import HEADERS
from fastapi.testclient import TestClient
from schulpilot import erasure
from schulpilot.config import settings
from schulpilot.db import DB, ErasureRequest, Membership, User
from schulpilot.main import app
from sqlalchemy import select


def test_membership_revoke_waits_before_family_and_child_locks(api, household, monkeypatch):
    parent, _ = household
    family_id = parent["families"][0]["id"]
    with DB.begin() as db:
        guest = User(username="synthetic-guest@example.org", email="synthetic-guest@example.org",
                     display_name="Synthetic guest", password_hash="unused", role="parent", verified=True)
        db.add(guest)
        db.flush()
        membership = Membership(family_id=family_id, user_id=guest.id, permission="view")
        db.add(membership)
        db.flush()
        identifier = membership.id
    lockfile = settings.data_dir / ".erasure-ledger.lock"
    lockfile.touch(mode=0o600, exist_ok=True)
    attempted, acquired = Event(), Event()
    original = erasure.journal_write_lock

    @contextmanager
    def traced_lock():
        attempted.set()
        with original():
            acquired.set()
            yield

    monkeypatch.setattr(erasure, "journal_write_lock", traced_lock)
    headers = {**HEADERS, "Authorization": api.headers["Authorization"]}

    def revoke():
        with TestClient(app, headers=headers) as client:
            return client.delete(f"/api/families/{family_id}/members/{identifier}")

    with ThreadPoolExecutor(max_workers=1) as pool:
        with lockfile.open("rb") as snapshot:
            fcntl.flock(snapshot, fcntl.LOCK_SH)
            deletion = pool.submit(revoke)
            assert attempted.wait(8)
            assert not acquired.wait(.2)
            with DB() as db:
                assert db.get(Membership, identifier) is not None
                assert db.scalar(select(ErasureRequest.id).where(ErasureRequest.target == identifier)) is None
        response = deletion.result(12)
    assert response.status_code == 200, response.text
    with DB() as db:
        assert db.get(Membership, identifier) is None
        event = db.scalar(select(ErasureRequest).where(ErasureRequest.target == identifier))
        assert event is not None and event.published is True
    records = [erasure.verify(line, settings.master_key)
               for line in (settings.data_dir / "erasure-ledger.jsonl").read_text().splitlines()]
    assert any(record["target"] == identifier and record["scope"] == "membership" for record in records)



def test_revoked_owner_session_cannot_revoke_member_after_snapshot_wait(api, household, monkeypatch):
    from schulpilot.db import Session
    from schulpilot.security import digest

    parent, _ = household
    family_id = parent["families"][0]["id"]
    token = api.headers["Authorization"].removeprefix("Bearer ")
    with DB.begin() as db:
        guest = User(username="synthetic-guest@example.org", email="synthetic-guest@example.org",
                     display_name="Synthetic guest", password_hash="unused", role="parent", verified=True)
        db.add(guest)
        db.flush()
        membership = Membership(family_id=family_id, user_id=guest.id, permission="view")
        db.add(membership)
        db.flush()
        identifier = membership.id
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

    def revoke():
        with TestClient(app, headers=headers) as client:
            return client.delete(f"/api/families/{family_id}/members/{identifier}")

    with ThreadPoolExecutor(max_workers=1) as pool:
        with lockfile.open("rb") as snapshot:
            fcntl.flock(snapshot, fcntl.LOCK_SH)
            deletion = pool.submit(revoke)
            assert attempted.wait(8)
            with DB.begin() as db:
                db.get(Session, session_id).revoked = True
        response = deletion.result(12)
    assert response.status_code == 401, response.text
    with DB() as db:
        assert db.get(Membership, identifier) is not None
        assert db.scalar(select(ErasureRequest.id).where(ErasureRequest.target == identifier)) is None
