"""Synthetic PostgreSQL races: provider edits and bounded tutor commits."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from schulpilot import schulbuddy
from schulpilot.db import DB, Job, ProviderConfig, SchulbuddyTurn, Usage, engine
from sqlalchemy import select, update
from test_schulbuddy import ask, counts, finish
from test_schulbuddy import book as book_fixture
from test_schulbuddy import transport as transport_fixture


@pytest.fixture
def book(api, household, monkeypatch):
    yield from book_fixture.__wrapped__(api, household, monkeypatch)


@pytest.fixture
def transport(monkeypatch):
    return transport_fixture.__wrapped__(monkeypatch)


def verify_failed_with_retained_cost(turn_id, calls):
    with DB() as db:
        turn = db.get(SchulbuddyTurn, turn_id)
        assert turn.status == "failed" and turn.reply is None
        assert db.get(Job, turn.job_id).status == "failed"
        usage = db.scalar(select(Usage).where(Usage.job_id == turn.job_id))
        assert usage.status == "failed_unknown" and usage.cost_micros is None and usage.reserved_micros > 0
    assert len(calls) == 1 and counts() == (1, 1, 0, 0)


def test_notstop_committed_after_snapshot_discards_reply(api, book, transport, monkeypatch):
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL transaction interleaving required")
    turn_id = ask(book).json()["id"]
    paused, proceed = Event(), Event()
    original = schulbuddy.lock_provider_for_commit

    def before_lock(db):
        paused.set()
        assert proceed.wait(10)
        original(db)

    monkeypatch.setattr(schulbuddy, "lock_provider_for_commit", before_lock)
    with ThreadPoolExecutor(max_workers=1) as pool:
        running = pool.submit(finish)
        assert paused.wait(8)
        with DB.begin() as db:
            db.execute(update(ProviderConfig).where(ProviderConfig.id == 1)
                       .values(emergency_stop=True, revision=ProviderConfig.revision + 1))
        proceed.set()
        running.result(10)
    verify_failed_with_retained_cost(turn_id, transport["calls"])


def test_locked_provider_row_fails_closed_after_provider_call(api, book, transport):
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row locking required")
    turn_id = ask(book).json()["id"]
    with ThreadPoolExecutor(max_workers=1) as pool:
        with DB.begin() as editor:
            editor.execute(select(ProviderConfig).where(ProviderConfig.id == 1).with_for_update())
            pool.submit(finish).result(timeout=10)
    verify_failed_with_retained_cost(turn_id, transport["calls"])


def test_locked_provider_row_rolls_back_new_reservation(api, book, transport):
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row locking required")
    with ThreadPoolExecutor(max_workers=1) as pool:
        with DB.begin() as editor:
            editor.execute(select(ProviderConfig).where(ProviderConfig.id == 1).with_for_update())
            response = pool.submit(ask, book).result(timeout=10)
            assert response.status_code == 409, response.text
    assert transport["calls"] == [] and counts() == (0, 0, 0, 0)


def test_real_emergency_stop_waits_only_for_short_final_commit(api, book, transport, monkeypatch):
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row locking required")
    from time import monotonic, sleep

    from conftest import HEADERS
    from fastapi.testclient import TestClient
    from schulpilot.db import Session, User, now
    from schulpilot.main import app
    from schulpilot.security import digest
    from sqlalchemy import text

    with DB.begin() as db:
        admin = User(username="synthetic-admin-config", display_name="Admin", role="admin",
                     verified=True, password_hash="no-real-password")
        db.add(admin)
        db.flush()
        admin_id = admin.id
        db.add(Session(user_id=admin.id, token_hash=digest("synthetic-admin-config-token"),
                       device="Synthetic admin", expires=int(now()) + 3600))
    turn_id = ask(book).json()["id"]
    locked, proceed = Event(), Event()
    original = schulbuddy.lock_provider_for_commit

    def hold_after_lock(db):
        original(db)
        locked.set()
        assert proceed.wait(10)

    monkeypatch.setattr(schulbuddy, "lock_provider_for_commit", hold_after_lock)
    headers = {**HEADERS, "Authorization": "Bearer synthetic-admin-config-token", "X-Schulpilot-Account": admin_id}

    def stop():
        with TestClient(app, headers=headers) as client:
            return client.post("/api/admin/emergency-stop")

    with ThreadPoolExecutor(max_workers=2) as pool:
        running = pool.submit(finish)
        assert locked.wait(8)
        stopping = pool.submit(stop)
        deadline, blocked = monotonic() + 8, False
        while monotonic() < deadline and not blocked:
            with DB() as db:
                blocked = bool(db.scalar(text(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                    "AND wait_event_type='Lock' AND lower(query) LIKE '%provider_config%' "
                    "AND lower(query) LIKE '%for update%'"
                )))
            if not blocked:
                sleep(0.05)
        assert blocked and not stopping.done()
        proceed.set()
        running.result(10)
        assert stopping.result(10).status_code == 200
    with DB() as db:
        assert db.get(ProviderConfig, 1).emergency_stop
        turn = db.get(SchulbuddyTurn, turn_id)
        assert turn.status == "ready"
        assert db.scalar(select(Usage).where(Usage.job_id == turn.job_id)).status == "completed"
    assert len(transport["calls"]) == 1 and counts() == (1, 1, 0, 0)


@pytest.mark.parametrize("overrun", ["provider", "child_fee"])
def test_overrun_conflict_retains_exact_cost_and_sets_stop(api, book, transport, monkeypatch, overrun):
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row locking required")
    from fastapi import HTTPException
    from schulpilot.db import ChildCostBucket, CreditPurchase, LearningUnit, UsageBucket

    # An active exercise would normally record help, which itself explicitly
    # flushes; the config guard must precede that flush.
    with DB.begin() as db:
        unit = db.get(LearningUnit, book["unit_id"])
        unit.status = "active"
        unit.questions = [{"id": "q1", "type": "short", "prompt": "Was ist die Sonne?",
                           "answer": "Stern", "options": [], "hints": [], "explanation": "Künstlich"}]
    turn_id = ask(book).json()["id"]
    with DB.begin() as db:
        turn = db.get(SchulbuddyTurn, turn_id)
        usage = db.scalar(select(Usage).where(Usage.job_id == turn.job_id))
        reserved = usage.reserved_micros
        if overrun == "child_fee":
            # 100% documented synthetic provider fees exceed the reservation
            # even though the provider's base amount itself does not.
            cost = reserved * 3 // 4
            db.add(CreditPurchase(id="synthetic-fee-overrun", credits_micros=reserved * 2, fee_micros=reserved * 2))
        else:
            cost = reserved + 1
        assert cost > 0
        job_id, bucket_ids, child_bucket_id = turn.job_id, list(usage.bucket_ids), usage.child_budget_id
    original_provider = schulbuddy.request_provider

    def priced(*args):
        result = original_provider(*args)
        result.cost_micros = cost
        result.cost_source = "reported"
        return result

    original_guard = schulbuddy.lock_provider_for_commit
    conflict = Event()

    def observed_guard(db):
        try:
            return original_guard(db)
        except HTTPException as error:
            assert error.status_code == 409
            conflict.set()
            raise

    monkeypatch.setattr(schulbuddy, "request_provider", priced)
    monkeypatch.setattr(schulbuddy, "lock_provider_for_commit", observed_guard)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with DB.begin() as editor:
            editor.execute(select(ProviderConfig).where(ProviderConfig.id == 1).with_for_update())
            running = pool.submit(finish)
            assert conflict.wait(8), "a pending config autoflush bypassed the NOWAIT guard"
            # The failed-provider-cost transaction may wait for this brief
            # editor transaction; no cost receipt may be discarded.
            assert not running.done()
        running.result(12)
    with DB() as db:
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        assert usage.status == "failed_billed" and usage.cost_micros == cost
        assert usage.settlement_version == 1 and db.get(ProviderConfig, 1).emergency_stop
        assert db.get(SchulbuddyTurn, turn_id).reply is None
        assert db.get(Job, job_id).status == "failed"
        for bucket_id in bucket_ids:
            bucket = db.get(UsageBucket, bucket_id)
            assert bucket.calls == 1 and bucket.known_cost_micros == cost and bucket.unknown_calls == 0
        assert db.get(ChildCostBucket, child_bucket_id).calls == 1
        if overrun == "child_fee":
            assert usage.allocated_fee_micros == cost
    assert len(transport["calls"]) == 1 and counts() == (1, 1, 0, 0)


def test_known_cost_and_fee_without_prior_balance_remain_successful(api, book, transport, monkeypatch):
    from schulpilot.child_cost_models import UsageCostBalance
    from schulpilot.db import CreditPurchase

    turn_id = ask(book).json()["id"]
    with DB.begin() as db:
        turn = db.get(SchulbuddyTurn, turn_id)
        usage = db.scalar(select(Usage).where(Usage.job_id == turn.job_id))
        assert db.get(UsageCostBalance, usage.id) is None
        cost = min(100, usage.reserved_micros // 2)
        assert cost > 0
        db.add(CreditPurchase(id="synthetic-normal-fee", credits_micros=cost * 10, fee_micros=cost))
        job_id, usage_id = turn.job_id, usage.id
    original = schulbuddy.request_provider

    def priced(*args):
        result = original(*args)
        result.cost_micros = cost
        result.cost_source = "reported"
        return result

    monkeypatch.setattr(schulbuddy, "request_provider", priced)
    finish()
    with DB() as db:
        turn = db.get(SchulbuddyTurn, turn_id)
        assert turn.status == "ready" and turn.reply is not None
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        assert usage.status == "completed" and usage.cost_micros == cost and usage.settlement_version == 1
        assert usage.allocated_fee_micros == cost // 10
        assert db.get(UsageCostBalance, usage_id) is not None
    assert len(transport["calls"]) == 1 and counts() == (1, 1, 0, 0)
