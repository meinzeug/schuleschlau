"""Administrator deletion waits for a consistent deletion-journal snapshot."""

import fcntl
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Event

import pytest
from fastapi.testclient import TestClient
from schulpilot import erasure
from schulpilot.config import settings
from schulpilot.db import DB, ErasureRequest, Session, User
from schulpilot.main import app
from sqlalchemy import select
from test_admin_users import child_user, confirm, preview

pytest_plugins = ["test_admin_users"]


@pytest.mark.parametrize("revoke_session", [False, True])
def test_admin_deletion_waits_and_revalidates_session(operator, household, monkeypatch, revoke_session):
    _, child = household
    target = child_user(child)
    selection = preview(operator, target)
    assert selection["can_delete"]
    headers = dict(operator.headers)
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

    def delete_account():
        with TestClient(app, headers=headers) as client:
            return confirm(client, target, selection)

    with ThreadPoolExecutor(max_workers=1) as pool:
        with lockfile.open("rb") as snapshot:
            fcntl.flock(snapshot, fcntl.LOCK_SH)
            deletion = pool.submit(delete_account)
            assert attempted.wait(8)
            with DB.begin() as db:
                assert db.get(User, target) is not None
                assert db.scalar(select(ErasureRequest.id).where(ErasureRequest.target == target)) is None
                if revoke_session:
                    db.get(Session, operator.session_id).revoked = True
        response = deletion.result(15)
    assert response.status_code == (401 if revoke_session else 200), response.text
    with DB() as db:
        assert (db.get(User, target) is not None) is revoke_session
        event = db.scalar(select(ErasureRequest).where(ErasureRequest.target == target))
        assert (event is None) is revoke_session
        if event:
            assert event.published is True
