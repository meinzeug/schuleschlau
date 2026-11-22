"""Synthetic beta enrollment, reviewed access and auditable accounting."""
import json
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from conftest import create_child
from schulpilot.beta_models import BetaApplication
from schulpilot.child_cost_models import ChildCostControl, UsageCostBalance
from schulpilot.commerce import access, usage_terms
from schulpilot.config import settings
from schulpilot.db import DB, Audit, Family, ProviderConfig, StoreConfiguration, Usage, UsageBucket, User, uid
from schulpilot.job_failures import generation_availability
from schulpilot.providers import Result, reserve, settle, usage_summary
from schulpilot.security import encrypt
from test_codex_models import operator as operator_fixture
from test_model_routing import setup_policy


@pytest.fixture
def operator():
    yield from operator_fixture.__wrapped__()


def enable_beta():
    object.__setattr__(settings, "smtp_host", "smtp.example.test")
    object.__setattr__(settings, "smtp_from", "sender@example.test")
    with DB.begin() as db:
        db.add(StoreConfiguration(id=1, encrypted_config=encrypt(json.dumps({"beta_enabled": True})), revision=1))


def application(api, mailbox):
    response = api.post("/api/auth/register", json={"email": "betaparent@example.org", "password": "secure-parent-pass-123",
        "display_name": "Beta parent", "family_name": "Beta family", "adult_consent": True, "beta_requested": True})
    assert response.status_code == 201, response.text
    return mailbox[-1]["token"]


def test_beta_is_opt_in_and_older_store_clients_preserve_it(api, mailbox, operator):
    response = api.post("/api/auth/register", json={"email": "betaparent@example.org", "password": "secure-parent-pass-123",
        "display_name": "Beta parent", "family_name": "Beta family", "adult_consent": True, "beta_requested": True})
    assert response.status_code == 403
    enable_beta()
    assert api.get("/api/store/catalog").json()["beta"]["enabled"] is True
    old = operator.get("/api/admin/store").json()
    old = {k: v for k, v in old.items() if k not in ("missing", "trial_missing", "beta_enabled")}
    response = operator.put("/api/admin/store", json=old)
    assert response.status_code == 200, response.text
    assert operator.get("/api/admin/store").json()["beta_enabled"] is True


def test_beta_requires_admin_and_verified_email_then_tracks_unlimited_costs(api, mailbox, operator):
    enable_beta()
    token = application(api, mailbox)
    entries = operator.get("/api/admin/beta-applications?status=pending").json()["items"]
    assert len(entries) == 1 and entries[0]["email_verified"] is False
    item = entries[0]
    path = f"/api/admin/beta-applications/{item['id']}/decision"
    assert api.get("/api/admin/beta-applications").status_code == 401
    assert operator.post(path, json={"revision": 1, "decision": "approve"}).status_code == 409
    assert api.post("/api/auth/verify", json={"token": token}).status_code == 200
    login = api.post("/api/auth/login", json={"username": "betaparent@example.org", "password": "secure-parent-pass-123"})
    assert login.status_code == 200, login.text
    api.headers["Authorization"] = "Bearer " + login.json()["token"]
    parent = login.json()["user"]
    fid = parent["families"][0]["id"]
    child = create_child(api, parent, username="beta-child")
    assert api.post(path, json={"revision": 1, "decision": "approve"}).status_code == 403
    result = operator.post(path, json={"revision": 1, "decision": "approve"})
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "approved" and result.json()["revision"] == 2
    assert operator.post(path, json={"revision": 1, "decision": "approve"}).status_code == 409
    setup_policy(fid)
    with DB.begin() as db:
        cfg = db.get(ProviderConfig, 1)
        cfg.global_limit_micros = 0
        db.add(ChildCostControl(child_id=child["id"], enabled=True, revision=1, timezone="Europe/Berlin",
            daily_limit_eur_micros=0, monthly_limit_eur_micros=0))
    with DB.begin() as db:
        family = db.get(Family, fid)
        assert access(db, family)["unlimited"] is True
        assert generation_availability(db, family, "unit", child_id=child["id"]) is None
        usage = reserve(db, family, child["id"], uid(), "unit")
        ident = usage.id
        assert usage.route_snapshot["child_cost_control"]["beta_unlimited"] is True
        settle(db, usage, Result({}, 30, 40, 1234, cost_source="reported"))
    with DB() as db:
        usage = db.get(Usage, ident)
        assert usage.cost_micros == 1234
        assert db.get(UsageCostBalance, ident) is not None
        assert all(db.get(UsageBucket, key).calls == 1 for key in usage.bucket_ids)
        assert usage_summary(db, db.get(Family, fid))["unlimited"] is True
    with DB.begin() as db:
        unknown = reserve(db, db.get(Family, fid), child["id"], uid(), "unit")
        unknown_id = unknown.id
        settle(db, unknown, None, failed=True)
    items = operator.get("/api/admin/beta-applications?status=approved").json()["items"]
    measured = items[0]["usage"]
    assert (measured["calls"], measured["known_usd_micros"], measured["unknown_calls"]) == (2, 1234, 1)
    assert (measured["input_tokens"], measured["output_tokens"]) == (30, 40)
    assert sum(row["calls"] for row in measured["by_model"].values()) == 2
    assert operator.post(path, json={"revision": 2, "decision": "revoke"}).json()["status"] == "revoked"
    with DB() as db:
        with pytest.raises(HTTPException) as error:
            usage_terms(db, db.get(Family, fid), enforce=True)
        assert error.value.status_code == 403
        assert db.get(Usage, ident).cost_micros == 1234
        assert db.get(Usage, unknown_id).cost_micros is None
        assert db.scalar(select(Audit.id).where(Audit.action == "beta.approved"))


def test_beta_does_not_disable_other_families_limits(api, mailbox, household, operator):
    normal_parent, normal_child = household
    normal_id = normal_parent["families"][0]["id"]
    enable_beta()
    token = application(api, mailbox)
    assert api.post("/api/auth/verify", json={"token": token}).status_code == 200
    result = api.post("/api/auth/login", json={"username": "betaparent@example.org", "password": "secure-parent-pass-123"})
    api.headers["Authorization"] = "Bearer " + result.json()["token"]
    parent = result.json()["user"]
    fid = parent["families"][0]["id"]
    child = create_child(api, parent, username="beta-second-child")
    item = operator.get("/api/admin/beta-applications").json()["items"][0]
    assert operator.post(f"/api/admin/beta-applications/{item['id']}/decision", json={"revision": 1, "decision": "approve"}).status_code == 200
    setup_policy(fid)
    with DB.begin() as db:
        db.get(ProviderConfig, 1).global_limit_micros = 20_000
    with DB.begin() as db:
        beta_usage = reserve(db, db.get(Family, fid), child["id"], uid(), "unit")
        assert beta_usage.bucket_ids[0].startswith("beta-global:")
    with DB.begin() as db:
        normal_usage = reserve(db, db.get(Family, normal_id), normal_child["id"], uid(), "unit")
        assert normal_usage.bucket_ids[0].startswith("global:")
    with DB() as db, pytest.raises(HTTPException) as error:
        reserve(db, db.get(Family, normal_id), normal_child["id"], uid(), "unit")
    assert error.value.status_code == 429


def test_beta_rejection_and_duplicate_registration_are_non_enumerating(api, mailbox, operator):
    enable_beta()
    token = application(api, mailbox)
    payload = {"email": "betaparent@example.org", "password": "secure-parent-pass-123", "display_name": "Beta parent",
        "family_name": "Beta family", "adult_consent": True, "beta_requested": True}
    duplicate = api.post("/api/auth/register", json=payload)
    assert duplicate.status_code == 201
    assert duplicate.json()["access_notice"] == "Nach E-Mail-Bestätigung wird die Beta-Anmeldung vom SchuleSchlau-Team geprüft."
    assert len(mailbox) == 1
    item = operator.get("/api/admin/beta-applications").json()["items"][0]
    path = f"/api/admin/beta-applications/{item['id']}/decision"
    assert operator.post(path, json={"revision": 1, "decision": "reject"}).json()["status"] == "rejected"
    assert operator.post(path, json={"revision": 2, "decision": "approve"}).status_code == 409
    assert api.post("/api/auth/verify", json={"token": token}).status_code == 200
    with DB() as db:
        row = db.get(BetaApplication, item["id"])
        assert row.status == "rejected" and row.approved_at is None
        with pytest.raises(HTTPException):
            usage_terms(db, db.get(Family, row.family_id), enforce=True)


def test_existing_authenticated_family_can_apply_and_reapply(api, household, operator):
    parent_user, _ = household
    fid = parent_user["families"][0]["id"]
    path = f"/api/families/{fid}/beta-application"
    assert api.get(path).json()["status"] == "none"
    assert api.post(path).status_code == 403
    enable_beta()
    first = api.post(path)
    assert first.status_code == 202 and first.json()["status"] == "pending"
    assert api.post(path).json() == first.json()
    item = operator.get("/api/admin/beta-applications").json()["items"][0]
    decision = f"/api/admin/beta-applications/{item['id']}/decision"
    assert operator.post(decision, json={"revision": 1, "decision": "reject"}).status_code == 200
    assert api.get(path).json()["status"] == "rejected"
    again = api.post(path)
    assert again.status_code == 202 and again.json()["status"] == "pending"
    assert again.json()["revision"] == 3
    assert api.post(path).json() == again.json()


def test_long_window_ai_limit_exempts_only_approved_beta(api, household):
    from schulpilot.beta import limit_ai_feature
    parent_user, child = household
    fid = parent_user["families"][0]["id"]
    with DB.begin() as db:
        db.add(BetaApplication(family_id=fid, user_id=parent_user["id"], status="pending"))
    with DB.begin() as db:
        limit_ai_feature(db, fid, "artificial-beta-hour", 1, 3600)
    with DB() as db, pytest.raises(HTTPException) as error:
        limit_ai_feature(db, fid, "artificial-beta-hour", 1, 3600)
    assert error.value.status_code == 429
    with DB.begin() as db:
        db.scalar(select(BetaApplication).where(BetaApplication.family_id == fid)).status = "approved"
    with DB.begin() as db:
        for _ in range(3):
            limit_ai_feature(db, fid, "artificial-beta-hour", 1, 3600)


def test_competing_admin_decisions_have_one_winner_on_postgres(api, mailbox, operator):
    from concurrent.futures import ThreadPoolExecutor
    from fastapi.testclient import TestClient
    from schulpilot.db import engine
    from schulpilot.main import app

    if engine.dialect.name != "postgresql":
        pytest.skip("Real PostgreSQL transaction race")
    enable_beta()
    token = application(api, mailbox)
    assert api.post("/api/auth/verify", json={"token": token}).status_code == 200
    item = operator.get("/api/admin/beta-applications").json()["items"][0]
    path = f"/api/admin/beta-applications/{item['id']}/decision"
    def decide(value):
        with TestClient(app, headers=dict(operator.headers)) as client:
            return client.post(path, json={"revision": 1, "decision": value}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = sorted(pool.map(decide, ("approve", "reject")))
    assert statuses == [200, 409]
    with DB() as db:
        assert db.get(BetaApplication, item["id"]).revision == 2


def test_revocation_waits_for_reservation_and_blocks_next_on_postgres(api, mailbox, operator):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    import time
    from fastapi.testclient import TestClient
    from sqlalchemy import text
    from schulpilot.db import engine
    from schulpilot.main import app

    if engine.dialect.name != "postgresql":
        pytest.skip("Real PostgreSQL transaction race")
    enable_beta()
    token = application(api, mailbox)
    assert api.post("/api/auth/verify", json={"token": token}).status_code == 200
    login = api.post("/api/auth/login", json={"username": "betaparent@example.org", "password": "secure-parent-pass-123"})
    api.headers["Authorization"] = "Bearer " + login.json()["token"]
    parent = login.json()["user"]
    fid = parent["families"][0]["id"]
    child = create_child(api, parent, username="race-beta-child")
    item = operator.get("/api/admin/beta-applications").json()["items"][0]
    path = f"/api/admin/beta-applications/{item['id']}/decision"
    assert operator.post(path, json={"revision": 1, "decision": "approve"}).status_code == 200
    setup_policy(fid)
    holding, release = Event(), Event()
    def claim():
        with DB.begin() as db:
            usage = reserve(db, db.get(Family, fid), child["id"], uid(), "unit")
            holding.set()
            assert release.wait(10)
            return usage.id
    def revoke():
        with TestClient(app, headers=dict(operator.headers)) as client:
            return client.post(path, json={"revision": 2, "decision": "revoke"}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        claim_future = pool.submit(claim)
        assert holding.wait(10)
        revoke_future = pool.submit(revoke)
        # Prove the decision really reached PostgreSQL and is waiting on the
        # application row, rather than merely waiting to start in the executor.
        deadline = time.monotonic() + 5
        blocked = False
        while time.monotonic() < deadline:
            with engine.connect() as connection:
                blocked = bool(connection.execute(text("select count(*) from pg_stat_activity "
                    "where datname=current_database() and wait_event_type='Lock' "
                    "and query ilike '%beta_applications%'" )).scalar_one())
            if blocked:
                break
            time.sleep(0.03)
        assert blocked and not revoke_future.done()
        release.set()
        identifier = claim_future.result(timeout=10)
        assert revoke_future.result(timeout=10) == 200
    with DB() as db:
        assert db.get(Usage, identifier) is not None
        with pytest.raises(HTTPException):
            usage_terms(db, db.get(Family, fid), enforce=True)
