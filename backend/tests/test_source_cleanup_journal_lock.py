"""The local operator apply must lock before any deletion transaction."""

import fcntl
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Event

from schulpilot import erasure, source_cleanup
from schulpilot.config import settings
from schulpilot.db import DB, Assignment, ErasureRequest
from sqlalchemy import select


def test_operator_apply_waits_for_snapshot_before_db_mutation(household, monkeypatch):
    _, child = household
    with DB.begin() as db:
        row = Assignment(child_id=child["id"], kind="parent", subject="Deutsch", topic="Synthetisch")
        db.add(row)
        db.flush()
        identifier = row.id
    with DB() as db:
        preview = source_cleanup.selection(db, child["id"], include_manual_assignments=True)
        assert identifier in preview["assignment_ids"]
    monkeypatch.setattr(sys, "argv", ["source_cleanup", "--child-id", child["id"], "--include-manual-assignments",
                                     "--apply-digest", preview["digest"]])
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
            task = pool.submit(source_cleanup.main)
            assert attempted.wait(8)
            with DB() as db:
                assert db.get(Assignment, identifier) is not None
                assert db.scalar(select(ErasureRequest.id).where(ErasureRequest.target == identifier)) is None
        task.result(12)
    with DB() as db:
        assert db.get(Assignment, identifier) is None
        event = db.scalar(select(ErasureRequest).where(ErasureRequest.target == identifier))
        assert event is not None and event.published is True
    records = [erasure.verify(line, settings.master_key)
               for line in (settings.data_dir / "erasure-ledger.jsonl").read_text().splitlines()]
    assert any(record["target"] == identifier and record.get("resource_kind") == "assignment" for record in records)
