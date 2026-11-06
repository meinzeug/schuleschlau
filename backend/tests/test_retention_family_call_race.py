"""Synthetic retention, outbox and concurrent family-call regressions."""

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from conftest import HEADERS
from fastapi.testclient import TestClient
from schulpilot import erasure, family_calls, worker
from schulpilot.config import settings
from schulpilot.db import DB, Child, ErasureRequest, Family, SchoolGrade, engine, now
from schulpilot.main import app
from sqlalchemy import select
from test_family_calls import start

pytest_plugins = ["test_family_calls"]


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="PostgreSQL row locks required")
def test_family_retention_defers_during_real_call_and_flushes_previous_outbox(
    household, api, child_api, turn, monkeypatch
):
    parent, child = household
    family_id = parent["families"][0]["id"]
    call = start(child_api)
    with DB.begin() as db:
        db.get(Family, family_id).expires = int(now()) - 1
        grade = SchoolGrade(child_id=child["id"], subject="Synthetic", topic="Synthetic", kind="test",
                            scale="grade_1_6", value=3, weight=1, assessed_on="2025-01-01", note="",
                            created=int(now()) - 366 * 86400)
        db.add(grade)
        db.flush()
        target = grade.id
    # Grade retention really commits separately, before the concurrent family
    # cleanup below must defer and publish the already committed grade event.
    exports = settings.data_dir / "exports"
    exports.mkdir(exist_ok=True)
    stale = exports / "family-synthetic.zip"
    stale.write_bytes(b"synthetic export")
    os.utime(stale, (int(now()) - 7200, int(now()) - 7200))
    held, release = Event(), Event()
    original = family_calls.lock

    def pause_after_session(db, call, *, unit=False):
        held.set()
        assert release.wait(15)
        return original(db, call, unit=unit)

    monkeypatch.setattr(family_calls, "lock", pause_after_session)
    headers = {**HEADERS, "Authorization": api.headers["Authorization"]}

    def accept():
        with TestClient(app, headers=headers) as client:
            return client.post(f"/api/family-calls/{call['id']}/accept")

    with ThreadPoolExecutor(max_workers=2) as pool:
        accepted = pool.submit(accept)
        try:
            assert held.wait(10)
            pool.submit(worker.maintenance).result(timeout=15)
            with DB() as db:
                assert db.get(Family, family_id) is not None
                assert db.get(Child, child["id"]) is not None
                assert db.get(SchoolGrade, target) is None
                event = db.scalar(select(ErasureRequest).where(ErasureRequest.target == target))
                assert event is not None and event.scope == "grade" and event.published
            assert stale.exists(), "Deferred cleanup must not unlink the export"
        finally:
            release.set()
        response = accepted.result(timeout=15)
        # This synthetic family has expired, so accepting its call is no
        # longer authorized. What matters is a clean response, not a deadlock.
        assert response.status_code == 409, response.text
        assert "bereits beendet" in response.json()["detail"]
    # A later scheduled pass may remove the expired family and export only
    # after the concurrent operation releases its database locks.
    worker.maintenance()
    with DB() as db:
        assert db.get(Family, family_id) is None
        assert db.get(Child, child["id"]) is None
    assert not stale.exists()


def test_unexpected_retention_error_publishes_earlier_outbox_and_preserves_export(household, monkeypatch):
    from contextlib import contextmanager

    target = "e" * 32
    with erasure.journal_write_lock(), DB.begin() as db:
        erasure.request(db, "user", target)
    exports = settings.data_dir / "exports"
    exports.mkdir(exist_ok=True)
    stale = exports / "child-synthetic.zip"
    stale.write_bytes(b"synthetic export")
    os.utime(stale, (int(now()) - 7200, int(now()) - 7200))

    @contextmanager
    def fail_pass():
        raise RuntimeError("synthetic failed retention pass")
        yield  # pragma: no cover

    monkeypatch.setattr(worker, "_retention_transaction", fail_pass)
    with pytest.raises(RuntimeError, match="synthetic failed retention pass"):
        worker.maintenance()
    with DB() as db:
        event = db.scalar(select(ErasureRequest).where(ErasureRequest.target == target))
        assert event is not None and event.published
    assert stale.exists()
