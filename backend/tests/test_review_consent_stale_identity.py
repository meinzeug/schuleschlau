"""Independent regression probes using only synthetic test data."""

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from fastapi import Request
from schulpilot import installation
from schulpilot.config import runtime_settings
from schulpilot.db import DB, Installation, engine, get_db
from schulpilot.main import app
from schulpilot.security import decrypt
from sqlalchemy.orm import Session as OrmSession
from test_admin_users import operator as operator_fixture


@pytest.fixture
def operator():
    yield from operator_fixture.__wrapped__()


@pytest.mark.parametrize("initial", [True, False])
def test_stale_loaded_installation_must_not_change_operator_approval(api, operator, initial):
    evidence = "Synthetic consent used only in this test"
    initial_values = {"real_data_approved": initial}
    if initial:
        initial_values["privacy_evidence"] = evidence
    approve = operator.put("/api/admin/installation/site", json=initial_values)
    assert approve.status_code == 200, approve.text
    with DB() as session:
        stale_row = session.get(Installation, 1)
        assert stale_row is not None and runtime_settings(session).real_data_approved is initial
        changed_values = {"real_data_approved": not initial}
        if not initial:
            changed_values["privacy_evidence"] = evidence
        revoke = operator.put("/api/admin/installation/site", json=changed_values)
        assert revoke.status_code == 200, revoke.text
        with DB() as check:
            latest_values = json.loads(decrypt(check.get(Installation, 1).encrypted_settings))
        installation.save_site(installation.SiteUpdate(operator_name="Synthetic operator"), "synthetic", session)
    with DB() as db:
        assert runtime_settings(db, fresh=True).real_data_approved is not initial
        final_values = json.loads(decrypt(db.get(Installation, 1).encrypted_settings))
        assert final_values.get("_tutor_real_data_consent_generation") == latest_values.get("_tutor_real_data_consent_generation")


@pytest.mark.parametrize("initial", [True, False])
def test_http_settings_interleaving_preserves_latest_approval(api, operator, monkeypatch, initial):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires real PostgreSQL request interleaving")
    evidence = "Synthetic consent used only in this test"
    initial_values = {"real_data_approved": initial}
    if initial:
        initial_values["privacy_evidence"] = evidence
    response = operator.put("/api/admin/installation/site", json=initial_values)
    assert response.status_code == 200, response.text

    # Model a request whose earlier dependency retains the same ORM row. This
    # uses the real HTTP routes and transactions; no production middleware or
    # data is changed, and no claim is made about current middleware retaining it.
    def loaded_request_db(request: Request):
        with DB() as db:
            if request.headers.get("X-Synthetic-Review") == "loaded":
                db.info["synthetic_review_retained_row"] = db.get(Installation, 1)
            yield db

    paused, resume = Event(), Event()
    original = installation.save_site

    def wait_before_save(data, actor, db):
        if data.operator_name == "Synthetic unrelated edit":
            paused.set()
            assert resume.wait(10)
        return original(data, actor, db)

    app.dependency_overrides[get_db] = loaded_request_db
    monkeypatch.setattr(installation, "save_site", wait_before_save)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            unrelated = pool.submit(operator.put, "/api/admin/installation/site",
                                    json={"operator_name": "Synthetic unrelated edit"},
                                    headers={"X-Synthetic-Review": "loaded"})
            assert paused.wait(8)
            change = {"real_data_approved": not initial}
            if not initial:
                change["privacy_evidence"] = evidence
            changed = operator.put("/api/admin/installation/site", json=change)
            assert changed.status_code == 200, changed.text
            with DB() as check:
                latest_values = json.loads(decrypt(check.get(Installation, 1).encrypted_settings))
            resume.set()
            saved = unrelated.result(12)
            assert saved.status_code == 200, saved.text
    finally:
        resume.set()
        app.dependency_overrides.pop(get_db, None)
    with DB() as db:
        assert runtime_settings(db, fresh=True).real_data_approved is not initial
        assert runtime_settings(db, fresh=True).operator_name == "Synthetic unrelated edit"
        final_values = json.loads(decrypt(db.get(Installation, 1).encrypted_settings))
        assert final_values.get("_tutor_real_data_consent_generation") == latest_values.get("_tutor_real_data_consent_generation")


@pytest.mark.parametrize("initial", ["manual", "automatic"])
def test_site_update_cannot_override_concurrent_material_review_cas(api, operator, monkeypatch, initial):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires real PostgreSQL request interleaving")
    current = operator.get("/api/admin/installation/material-review").json()
    if current["mode"] != initial:
        result = operator.put("/api/admin/installation/material-review",
                              json={"mode": initial, "expected_revision": current["revision"]})
        assert result.status_code == 200, result.text
        current = result.json()
    next_mode = "automatic" if initial == "manual" else "manual"
    paused, resume = Event(), Event()
    original = OrmSession.execute

    def pause_first_lock(db, statement, *args, **kwargs):
        if (getattr(statement, "is_update", False)
                and getattr(getattr(statement, "table", None), "name", None) == "installation"
                and not paused.is_set()):
            paused.set()
            assert resume.wait(10)
        return original(db, statement, *args, **kwargs)

    monkeypatch.setattr(OrmSession, "execute", pause_first_lock)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            unrelated = pool.submit(operator.put, "/api/admin/installation/site",
                                    json={"material_review_mode": initial,
                                          "operator_name": "Synthetic unrelated edit"})
            assert paused.wait(8)
            changed = operator.put("/api/admin/installation/material-review",
                                   json={"mode": next_mode, "expected_revision": current["revision"]})
            assert changed.status_code == 200, changed.text
            resume.set()
            saved = unrelated.result(12)
            assert saved.status_code == 409, saved.text
    finally:
        resume.set()
    final = operator.get("/api/admin/installation/material-review")
    assert final.status_code == 200 and final.json()["mode"] == next_mode
