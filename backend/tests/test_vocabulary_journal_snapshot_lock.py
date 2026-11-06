"""A word deletion cannot commit while an erasure snapshot holds its lock."""

import fcntl
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Event

import pytest
from conftest import HEADERS
from fastapi.testclient import TestClient
from schulpilot import erasure
from schulpilot.config import settings
from schulpilot.db import DB, ErasureRequest, VocabularyCollection, VocabularyImport, VocabularyItem
from schulpilot.main import app
from schulpilot.vocabulary import collection_data
from sqlalchemy import select


@pytest.mark.parametrize("kind", ["vocab_item", "vocab_import", "vocab_set"])
def test_word_deletion_waits_before_child_lock_and_outbox_commit(api, household, monkeypatch, kind):
    parent, child = household
    model = {"vocab_item": VocabularyItem, "vocab_import": VocabularyImport, "vocab_set": VocabularyCollection}[kind]
    with DB.begin() as db:
        if kind == "vocab_item":
            row = VocabularyItem(child_id=child["id"], identity="a" * 64, target_locale="en-GB", word="apple",
                                 meaning="Apfel", origin="manual", confirmed=True)
        elif kind == "vocab_import":
            row = VocabularyImport(child_id=child["id"], user_id=parent["id"], request_key="synthetic-lock-test",
                                   request_digest="a" * 64, target_locale="en-GB", title="Test", pairs=[], status="review")
        else:
            row = VocabularyCollection(child_id=child["id"], title="Test", target_locale="en-GB")
        db.add(row)
        db.flush()
        identifier = row.id
        snapshot_token = collection_data(db, row)["snapshot"] if kind == "vocab_set" else None
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

    def delete_word():
        with TestClient(app, headers=headers) as client:
            base = f"/api/children/{child['id']}/vocabulary"
            if kind == "vocab_import":
                return client.delete(f"{base}/imports/{identifier}")
            if kind == "vocab_set":
                return client.request("DELETE", f"{base}/collections/{identifier}", json={"snapshot": snapshot_token})
            return client.delete(f"{base}/{identifier}")

    with ThreadPoolExecutor(max_workers=1) as pool:
        with lockfile.open("rb") as snapshot:
            fcntl.flock(snapshot, fcntl.LOCK_SH)
            deletion = pool.submit(delete_word)
            assert attempted.wait(8)
            assert not acquired.wait(.2)
            with DB() as db:
                assert db.get(model, identifier) is not None
                assert db.scalar(select(ErasureRequest.id).where(ErasureRequest.target == identifier)) is None
        response = deletion.result(12)
    assert response.status_code == 200, response.text
    with DB() as db:
        assert db.get(model, identifier) is None
        event = db.scalar(select(ErasureRequest).where(ErasureRequest.target == identifier))
        assert event is not None and event.published is True
    records = [erasure.verify(line, settings.master_key)
               for line in (settings.data_dir / "erasure-ledger.jsonl").read_text().splitlines()]
    assert any(record["target"] == identifier and record.get("resource_kind") == kind for record in records)


def test_revoked_session_cannot_delete_word_after_waiting_for_snapshot(api, household, monkeypatch):
    from schulpilot.db import Session
    from schulpilot.security import digest

    _, child = household
    token = api.headers["Authorization"].removeprefix("Bearer ")
    with DB.begin() as db:
        word = VocabularyItem(child_id=child["id"], identity="b" * 64, target_locale="en-GB", word="book",
                              meaning="Buch", origin="manual", confirmed=True)
        db.add(word)
        db.flush()
        identifier = word.id
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

    def delete_word():
        with TestClient(app, headers=headers) as client:
            return client.delete(f"/api/children/{child['id']}/vocabulary/{identifier}")

    with ThreadPoolExecutor(max_workers=1) as pool:
        with lockfile.open("rb") as snapshot:
            fcntl.flock(snapshot, fcntl.LOCK_SH)
            deletion = pool.submit(delete_word)
            assert attempted.wait(8)
            with DB.begin() as db:
                db.get(Session, session_id).revoked = True
        response = deletion.result(12)
    assert response.status_code == 401, response.text
    with DB() as db:
        assert db.get(VocabularyItem, identifier) is not None
        assert db.scalar(select(ErasureRequest.id).where(ErasureRequest.target == identifier)) is None
