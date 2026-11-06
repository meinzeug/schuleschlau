"""Synthetic PostgreSQL tests for simultaneous operator consent revocation."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from schulpilot import schulbuddy
from schulpilot.db import DB, Job, SchulbuddyTurn, Usage, engine
from sqlalchemy import select
from test_admin_users import operator as operator_fixture
from test_schulbuddy import ask, counts, finish
from test_schulbuddy import book as book_fixture
from test_schulbuddy import transport as transport_fixture


@pytest.fixture
def book(api, household, monkeypatch):
    yield from book_fixture.__wrapped__(api, household, monkeypatch)


@pytest.fixture
def transport(monkeypatch):
    return transport_fixture.__wrapped__(monkeypatch)


@pytest.fixture
def operator():
    yield from operator_fixture.__wrapped__()


@pytest.mark.parametrize("stage", ["enqueue", "publish"])
def test_completed_revocation_before_installation_lock_discards_work(api, book, transport, operator, monkeypatch, stage):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL transaction isolation")
    turn_id = ask(book).json()["id"] if stage == "publish" else None
    paused, resume = Event(), Event()
    original = schulbuddy.lock_installation_for_commit

    def before_lock(db):
        paused.set()
        assert resume.wait(10)
        return original(db)

    monkeypatch.setattr(schulbuddy, "lock_installation_for_commit", before_lock)
    with ThreadPoolExecutor(max_workers=1) as pool:
        active = pool.submit(ask, book) if stage == "enqueue" else pool.submit(finish)
        assert paused.wait(8)
        response = operator.put("/api/admin/installation/site", json={"real_data_approved": False})
        assert response.status_code == 200, response.text
        resume.set()
        result = active.result(12)
    if stage == "enqueue":
        assert result.status_code == 503
        assert counts() == (0, 0, 0, 0) and transport["calls"] == []
    else:
        with DB() as db:
            turn = db.get(SchulbuddyTurn, turn_id)
            assert turn.status == "failed" and turn.reply is None
            assert db.get(Job, turn.job_id).status == "failed"
            usage = db.scalar(select(Usage).where(Usage.job_id == turn.job_id))
            assert usage.status == "failed_unknown" and usage.cost_micros is None and usage.reserved_micros > 0
        assert counts() == (1, 1, 0, 0) and len(transport["calls"]) == 1


@pytest.mark.parametrize("stage", ["enqueue", "publish"])
def test_operator_revocation_waits_for_guarded_commit(api, book, transport, operator, monkeypatch, stage):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL row locking")
    from time import monotonic, sleep

    from sqlalchemy import text

    turn_id = ask(book).json()["id"] if stage == "publish" else None
    locked, resume = Event(), Event()
    original = schulbuddy.lock_installation_for_commit

    def pause_after_lock(db):
        original(db)
        locked.set()
        assert resume.wait(10)

    monkeypatch.setattr(schulbuddy, "lock_installation_for_commit", pause_after_lock)
    with ThreadPoolExecutor(max_workers=2) as pool:
        active = pool.submit(ask, book) if stage == "enqueue" else pool.submit(finish)
        assert locked.wait(8)
        revoking = pool.submit(operator.put, "/api/admin/installation/site", json={"real_data_approved": False})
        blocked, deadline = False, monotonic() + 8
        while monotonic() < deadline and not blocked:
            with DB() as db:
                blocked = bool(db.scalar(text(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                    "AND wait_event_type='Lock' AND lower(query) LIKE '%update installation%'"
                )))
            if not blocked:
                sleep(0.05)
        assert blocked and not revoking.done()
        resume.set()
        result = active.result(12)
        if stage == "enqueue":
            assert result.status_code == 202, result.text
            turn_id = result.json()["id"]
        assert revoking.result(12).status_code == 200
    with DB() as db:
        turn = db.get(SchulbuddyTurn, turn_id)
        assert turn.status == ("queued" if stage == "enqueue" else "ready")
    if stage == "enqueue":
        # A later worker observes revocation before dispatch, without extra cost.
        finish()
        with DB() as db:
            turn = db.get(SchulbuddyTurn, turn_id)
            usage = db.scalar(select(Usage).where(Usage.job_id == turn.job_id))
            assert turn.status == "failed" and turn.reply is None
            assert usage.status == "failed_not_sent" and usage.cost_micros == 0
        assert transport["calls"] == []
    assert counts() == (1, 1, 0, 0)


@pytest.mark.parametrize("cost", [None, 42])
def test_admin_can_revoke_during_provider_call_and_known_cost_survives(api, book, transport, operator, monkeypatch, cost):
    turn_id = ask(book).json()["id"]
    entered, resume = Event(), Event()
    original = schulbuddy.request_provider

    def delayed(*args):
        result = original(*args)
        result.cost_micros = cost
        result.cost_source = "reported" if cost is not None else "unknown"
        entered.set()
        assert resume.wait(10)
        return result

    monkeypatch.setattr(schulbuddy, "request_provider", delayed)
    with ThreadPoolExecutor(max_workers=1) as pool:
        running = pool.submit(finish)
        assert entered.wait(8)
        # The actual operator endpoint must not wait for the model call.
        response = operator.put("/api/admin/installation/site", json={"real_data_approved": False})
        assert response.status_code == 200, response.text
        resume.set()
        running.result(12)
    with DB() as db:
        turn = db.get(SchulbuddyTurn, turn_id)
        usage = db.scalar(select(Usage).where(Usage.job_id == turn.job_id))
        assert turn.status == "failed" and turn.reply is None and db.get(Job, turn.job_id).status == "failed"
        assert usage.status == ("failed_unknown" if cost is None else "failed_billed")
        assert usage.cost_micros == cost and usage.reserved_micros > 0 and usage.settlement_version == 1
    assert len(transport["calls"]) == 1 and counts() == (1, 1, 0, 0)


@pytest.mark.parametrize("stage", ["enqueue", "publish"])
def test_busy_installation_row_fails_closed_with_no_duplicate_cost(api, book, transport, stage):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL row locking")
    from schulpilot.db import Installation

    turn_id = ask(book).json()["id"] if stage == "publish" else None
    with ThreadPoolExecutor(max_workers=1) as pool:
        with DB.begin() as editor:
            editor.execute(select(Installation).where(Installation.id == 1).with_for_update())
            result = (pool.submit(ask, book) if stage == "enqueue" else pool.submit(finish)).result(timeout=10)
    if stage == "enqueue":
        assert result.status_code == 409
        assert counts() == (0, 0, 0, 0) and not transport["calls"]
    else:
        with DB() as db:
            turn = db.get(SchulbuddyTurn, turn_id)
            usage = db.scalar(select(Usage).where(Usage.job_id == turn.job_id))
            assert turn.status == "failed" and turn.reply is None
            assert usage.status == "failed_unknown" and usage.settlement_version == 1 and usage.reserved_micros > 0
        assert counts() == (1, 1, 0, 0) and len(transport["calls"]) == 1


def test_installation_first_actor_never_deadlocks_with_tutor_usage_and_provider(api, book, transport, monkeypatch):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL row locking")
    from schulpilot.db import Installation, ProviderConfig

    paused, resume = Event(), Event()
    original = schulbuddy.lock_installation_for_commit

    def before_installation(db):
        paused.set()  # The tutor already has its usage and provider rows.
        assert resume.wait(10)
        return original(db)

    monkeypatch.setattr(schulbuddy, "lock_installation_for_commit", before_installation)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with DB.begin() as reverse:
            reverse.execute(select(Installation).where(Installation.id == 1).with_for_update())
            active = pool.submit(ask, book)
            assert paused.wait(8)
            resume.set()
            # NOWAIT returns instead of waiting while holding provider rows.
            assert active.result(10).status_code == 409
            reverse.execute(select(ProviderConfig).where(ProviderConfig.id == 1).with_for_update(nowait=True))
    assert counts() == (0, 0, 0, 0) and transport["calls"] == []


@pytest.mark.parametrize("overrun", ["provider", "child_fee"])
def test_busy_installation_keeps_overrun_cost_once_and_sets_stop(api, book, transport, monkeypatch, overrun):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL row locking")
    from fastapi import HTTPException
    from schulpilot.db import CreditPurchase, Installation, LearningUnit, ProviderConfig, UsageBucket

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
            cost = reserved * 3 // 4
            db.add(CreditPurchase(id="synthetic-install-fee", credits_micros=reserved * 2, fee_micros=reserved * 2))
        else:
            cost = reserved + 1
        assert cost > 0
        job_id, bucket_ids = turn.job_id, list(usage.bucket_ids)
    original_provider, original_guard = schulbuddy.request_provider, schulbuddy.lock_installation_for_commit
    conflicted = Event()

    def priced(*args):
        result = original_provider(*args)
        result.cost_micros, result.cost_source = cost, "reported"
        return result

    def observed_guard(db):
        try:
            return original_guard(db)
        except HTTPException as error:
            assert error.status_code == 409
            conflicted.set()
            raise

    monkeypatch.setattr(schulbuddy, "request_provider", priced)
    monkeypatch.setattr(schulbuddy, "lock_installation_for_commit", observed_guard)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with DB.begin() as editor:
            editor.execute(select(Installation).where(Installation.id == 1).with_for_update())
            active = pool.submit(finish)
            assert conflicted.wait(8), "an autoflush blocked before the NOWAIT check"
            active.result(12)
    with DB() as db:
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        assert usage.status == "failed_billed" and usage.cost_micros == cost and usage.settlement_version == 1
        assert db.get(ProviderConfig, 1).emergency_stop
        assert db.get(SchulbuddyTurn, turn_id).reply is None and db.get(Job, job_id).status == "failed"
        for bucket_id in bucket_ids:
            bucket = db.get(UsageBucket, bucket_id)
            assert bucket.calls == 1 and bucket.known_cost_micros == cost and bucket.unknown_calls == 0
        if overrun == "child_fee":
            assert usage.allocated_fee_micros == cost
    assert len(transport["calls"]) == 1 and counts() == (1, 1, 0, 0)
