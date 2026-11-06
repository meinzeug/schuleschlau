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
            # The separate general retention transaction has succeeded; its
            # own old-export cleanup is independent of the deferred family.
            assert not stale.exists()
        finally:
            release.set()
        response = accepted.result(timeout=15)
        # This synthetic family has expired, so accepting its call is no
        # longer authorized. What matters is a clean response, not a deadlock.
        assert response.status_code == 409, response.text
        assert "bereits beendet" in response.json()["detail"]
    # A later scheduled pass removes the family after the concurrent
    # operation releases its database locks.
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


def test_family_retention_batches_rotate_past_busy_family_and_publish_each(household, monkeypatch):
    identifiers = ["f" + f"{number:031x}" for number in range(8)]
    with DB.begin() as db:
        db.add_all([Family(id=identifier, name="Synthetic", synthetic=True, expires=int(now()) - 1)
                    for identifier in identifiers])
    monkeypatch.setattr(worker, "_FAMILY_RETENTION_BATCH", 3)
    original = worker._lock_expiring_family
    busy = True

    def collision(db, family_id):
        if busy and family_id == identifiers[0]:
            raise worker._MaintenanceDeferred
        return original(db, family_id)

    monkeypatch.setattr(worker, "_lock_expiring_family", collision)
    for expected in (6, 3, 1):
        worker._expire_families()
        with DB() as db:
            remaining = list(db.scalars(select(Family.id).where(Family.id.in_(identifiers))))
            assert len(remaining) == expected
            assert identifiers[0] in remaining
            events = list(db.scalars(select(ErasureRequest).where(ErasureRequest.target.in_(identifiers))))
            assert len(events) == 8 - expected and all(event.published for event in events)
    busy = False
    worker._expire_families()
    with DB() as db:
        assert not list(db.scalars(select(Family.id).where(Family.id.in_(identifiers))))
        events = list(db.scalars(select(ErasureRequest).where(ErasureRequest.target.in_(identifiers))))
        assert len(events) == 8 and all(event.published for event in events)


def test_family_retention_commit_survives_journal_flush_failure(household, monkeypatch):
    family_id = "f" * 31 + "0"
    with DB.begin() as db:
        db.add(Family(id=family_id, name="Synthetic", synthetic=True, expires=int(now()) - 1))
    original = erasure.flush_journal

    def fail_flush():
        raise OSError("synthetic journal interruption")

    monkeypatch.setattr(erasure, "flush_journal", fail_flush)
    with pytest.raises(OSError, match="synthetic journal interruption"):
        worker._expire_families()
    with DB() as db:
        assert db.get(Family, family_id) is None
        events = list(db.scalars(select(ErasureRequest).where(ErasureRequest.target == family_id)))
        assert len(events) == 1 and not events[0].published
    monkeypatch.setattr(erasure, "flush_journal", original)
    original()
    worker._expire_families()
    with DB() as db:
        events = list(db.scalars(select(ErasureRequest).where(ErasureRequest.target == family_id)))
        assert len(events) == 1 and events[0].published


def test_family_retention_replays_parent_child_and_family_from_prior_backup(household):
    from schulpilot.db import Base, User
    from test_grade_erasure_restore_regression import isolated_restore

    parent, child = household
    family_id, parent_id, child_id = parent["families"][0]["id"], parent["id"], child["id"]
    with DB.begin() as db:
        child_user_id = db.get(Child, child_id).user_id
        db.get(Family, family_id).expires = int(now()) - 1
    with DB() as db:
        snapshot = {table: list(db.execute(table.select()).mappings()) for table in Base.metadata.sorted_tables}
    worker._expire_families()
    with DB() as db:
        assert db.get(Family, family_id) is None
        assert db.get(Child, child_id) is None
        assert db.get(User, parent_id) is None
        assert db.get(User, child_user_id) is None
        published = list(db.scalars(select(ErasureRequest).where(ErasureRequest.target == parent_id)))
        assert len(published) == 1 and published[0].scope == "user" and published[0].published
    records = [erasure.verify(line, settings.master_key)
               for line in (settings.data_dir / "erasure-ledger.jsonl").read_text().splitlines()]
    with isolated_restore() as restored:
        from sqlalchemy.orm import Session

        Base.metadata.create_all(restored)
        with restored.begin() as connection:
            for table, rows in snapshot.items():
                if rows:
                    connection.execute(table.insert(), [dict(row) for row in rows])
        with Session(restored) as db:
            assert db.get(Family, family_id) is not None
            assert db.get(Child, child_id) is not None
            assert db.get(User, parent_id) is not None
            erasure.reconcile(db, records)
            db.commit()
            assert db.get(Family, family_id) is None
            assert db.get(Child, child_id) is None
            assert db.get(User, parent_id) is None
            assert db.get(User, child_user_id) is None


def test_family_retention_claims_are_serialized_and_survive_worker_restart(household, monkeypatch):
    import json
    import os
    import subprocess
    import sys
    from pathlib import Path

    identifiers = ["f" + f"{number:031x}" for number in range(12)]
    with DB.begin() as db:
        db.add_all([Family(id=identifier, name="Synthetic", synthetic=True, expires=int(now()) - 1)
                    for identifier in identifiers])
    monkeypatch.setattr(worker, "_FAMILY_RETENTION_BATCH", 3)
    with ThreadPoolExecutor(max_workers=2) as pool:
        batches = list(pool.map(lambda _: worker._claim_expiring_family_batch(), range(2)))
    assert all(len(batch) == 3 for batch in batches)
    assert len(set(batches[0] + batches[1])) == 6
    assert set(batches[0] + batches[1]) == set(identifiers[:6])
    # A fresh Python worker has no in-process cursor. It must continue from
    # the committed database position, including after simulated worker death.
    # pytest can add backend to sys.path without exporting PYTHONPATH. Give the
    # fresh worker the same source tree explicitly, regardless of invocation.
    env = os.environ.copy()
    backend_path = str(Path(__file__).resolve().parents[1])
    env["PYTHONPATH"] = os.pathsep.join(filter(None, (backend_path, env.get("PYTHONPATH", ""))))
    result = subprocess.run(
        [sys.executable, "-c", "import json; from schulpilot import worker; "
         "worker._FAMILY_RETENTION_BATCH = 3; print(json.dumps(worker._claim_expiring_family_batch()))"],
        check=True, capture_output=True, text=True, timeout=20, env=env,
    )
    assert json.loads(result.stdout) == identifiers[6:9]
    assert worker._claim_expiring_family_batch() == identifiers[9:12]


def test_expired_family_replay_preserves_parent_and_other_family(household):
    from schulpilot.db import Base, Membership, User
    from test_grade_erasure_restore_regression import isolated_restore

    parent, child = household
    expired_id, parent_id, child_id = parent["families"][0]["id"], parent["id"], child["id"]
    with DB.begin() as db:
        db.get(Family, expired_id).expires = int(now()) - 1
        other = Family(name="Other synthetic household", synthetic=True)
        db.add(other)
        db.flush()
        other_id = other.id
        db.add(Membership(family_id=other_id, user_id=parent_id, permission="owner"))
        other_user = User(username="retention-other-child", display_name="Synthetic child",
                          password_hash="unused", role="child", verified=True)
        db.add(other_user)
        db.flush()
        other_user_id = other_user.id
        other_child = Child(family_id=other_id, user_id=other_user_id, grade=6)
        db.add(other_child)
        db.flush()
        other_child_id = other_child.id
    with DB() as db:
        snapshot = {table: list(db.execute(table.select()).mappings()) for table in Base.metadata.sorted_tables}
    worker._expire_families()
    with DB() as db:
        assert db.get(Family, expired_id) is None and db.get(Child, child_id) is None
        assert db.get(Family, other_id) is not None and db.get(Child, other_child_id) is not None
        assert db.get(User, parent_id) is not None
        assert db.scalar(select(ErasureRequest.id).where(ErasureRequest.scope == "user",
                                                        ErasureRequest.target == parent_id)) is None
    records = [erasure.verify(line, settings.master_key)
               for line in (settings.data_dir / "erasure-ledger.jsonl").read_text().splitlines()]
    with isolated_restore() as restored:
        from sqlalchemy.orm import Session

        Base.metadata.create_all(restored)
        with restored.begin() as connection:
            for table, rows in snapshot.items():
                if rows:
                    connection.execute(table.insert(), [dict(row) for row in rows])
        with Session(restored) as db:
            erasure.reconcile(db, records)
            db.commit()
            assert db.get(Family, expired_id) is None and db.get(Child, child_id) is None
            assert db.get(Family, other_id) is not None and db.get(Child, other_child_id) is not None
            assert db.get(User, parent_id) is not None and db.get(User, other_user_id) is not None
            assert db.scalar(select(Membership.id).where(Membership.family_id == other_id,
                                                          Membership.user_id == parent_id)) is not None
