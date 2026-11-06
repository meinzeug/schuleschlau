"""Retention cannot commit a deletion while a journal snapshot is running."""

import fcntl
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Event

from schulpilot import erasure, worker
from schulpilot.config import settings
from schulpilot.db import DB, ErasureRequest, VocabularyItem, now
from sqlalchemy import select


def test_expired_word_retention_waits_for_journal_snapshot(household, monkeypatch):
    _, child = household
    with DB.begin() as db:
        item = VocabularyItem(child_id=child["id"], identity="c" * 64, target_locale="en-GB", word="synthetic",
                              meaning="künstlich", origin="manual", confirmed=True, created=int(now()) - 366 * 86400)
        db.add(item)
        db.flush()
        identifier = item.id
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
    with ThreadPoolExecutor(max_workers=1) as pool:
        with lockfile.open("rb") as snapshot:
            fcntl.flock(snapshot, fcntl.LOCK_SH)
            task = pool.submit(worker.maintenance)
            assert attempted.wait(8)
            with DB() as db:
                assert db.get(VocabularyItem, identifier) is not None
                assert db.scalar(select(ErasureRequest.id).where(ErasureRequest.target == identifier)) is None
        task.result(20)
    with DB() as db:
        assert db.get(VocabularyItem, identifier) is None
        event = db.scalar(select(ErasureRequest).where(ErasureRequest.target == identifier))
        assert event is not None and event.published is True


def test_retention_and_explicit_word_deletion_do_not_deadlock_or_duplicate(api, household, monkeypatch):
    from threading import Lock

    from conftest import HEADERS
    from fastapi.testclient import TestClient
    from schulpilot.main import app

    _, child = household
    with DB.begin() as db:
        item = VocabularyItem(child_id=child["id"], identity="d" * 64, target_locale="en-GB", word="synthetic",
                              meaning="künstlich", origin="manual", confirmed=True, created=int(now()) - 366 * 86400)
        db.add(item)
        db.flush()
        identifier = item.id
    held, proceed, other_attempt = Event(), Event(), Event()
    count, count_lock = [0], Lock()
    original = erasure.journal_write_lock

    @contextmanager
    def traced_lock():
        with count_lock:
            count[0] += 1
            current = count[0]
            if current == 2:
                other_attempt.set()
        with original():
            if current == 1:
                held.set()
                assert proceed.wait(10)
            yield

    monkeypatch.setattr(erasure, "journal_write_lock", traced_lock)
    headers = {**HEADERS, "Authorization": api.headers["Authorization"]}

    def delete_item():
        with TestClient(app, headers=headers) as client:
            return client.delete(f"/api/children/{child['id']}/vocabulary/{identifier}")

    with ThreadPoolExecutor(max_workers=2) as pool:
        retention = pool.submit(worker.maintenance)
        assert held.wait(8)
        explicit = pool.submit(delete_item)
        try:
            assert other_attempt.wait(8)
            assert not explicit.done()
        finally:
            proceed.set()
        retention.result(20)
        response = explicit.result(20)
    assert response.status_code == 404, response.text
    with DB() as db:
        assert db.get(VocabularyItem, identifier) is None
        events = list(db.scalars(select(ErasureRequest).where(ErasureRequest.target == identifier)))
        assert len(events) == 1 and events[0].published is True
