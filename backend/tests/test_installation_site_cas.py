"""Concurrent site edits use only artificial administrators and settings."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

import pytest
from schulpilot import installation
from schulpilot.db import DB, Installation, ProviderConfig, engine
from test_admin_users import operator as operator_fixture


@pytest.fixture
def operator():
    yield from operator_fixture.__wrapped__()


def current(operator):
    response = operator.get("/api/admin/installation")
    assert response.status_code == 200, response.text
    return response.json()


def test_legacy_admin_write_fails_closed_without_changing_settings_or_revision(api, operator):
    before = current(operator)
    response = operator.put("/api/admin/installation/site", json={"operator_name": "Synthetic stale"})
    assert response.status_code == 409
    after = current(operator)
    assert after["site_revision"] == before["site_revision"]
    assert after["site"]["operator_name"] == before["site"]["operator_name"]


def test_legacy_site_conflict_does_not_block_emergency_stop(api, operator):
    with DB.begin() as db:
        db.get(ProviderConfig, 1).emergency_stop = False
    stale = operator.put("/api/admin/installation/site", json={"operator_name": "Synthetic cached form"})
    assert stale.status_code == 409
    stop = operator.post("/api/admin/emergency-stop")
    assert stop.status_code == 200, stop.text
    with DB() as db:
        assert db.get(ProviderConfig, 1).emergency_stop is True


def test_stale_explicit_approval_cannot_undo_completed_revocation(api, operator):
    evidence = "Synthetic privacy evidence for isolated test"
    before = current(operator)
    approved = operator.put("/api/admin/installation/site", json={
        "expected_revision": before["site_revision"], "real_data_approved": True, "privacy_evidence": evidence,
    })
    assert approved.status_code == 200, approved.text
    old_revision = approved.json()["site_revision"]
    revoked = operator.put("/api/admin/installation/site", json={
        "expected_revision": old_revision, "real_data_approved": False,
    })
    assert revoked.status_code == 200, revoked.text
    stale = operator.put("/api/admin/installation/site", json={
        "expected_revision": old_revision, "real_data_approved": True, "privacy_evidence": evidence,
    })
    assert stale.status_code == 409
    after = current(operator)
    assert after["site"]["real_data_approved"] is False
    assert after["site_revision"] == revoked.json()["site_revision"]


def test_parallel_same_revision_has_exactly_one_winner(api, operator):
    before = current(operator)
    revision = before["site_revision"]
    ready = Barrier(2)

    def update(name):
        ready.wait(timeout=10)
        return operator.put("/api/admin/installation/site", json={
            "expected_revision": revision, "operator_name": name,
        })

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(update, ["Synthetic one", "Synthetic two"]))
    assert sorted(response.status_code for response in responses) == [200, 409]
    winner = next(response.json() for response in responses if response.status_code == 200)
    after = current(operator)
    assert after["site_revision"] == revision + 1 == winner["site_revision"]
    assert after["site"]["operator_name"] == winner["site"]["operator_name"]
    with DB() as db:
        assert db.get(Installation, 1).revision == after["site_revision"]


def test_settings_and_revision_come_from_same_snapshot_during_write(api, operator, monkeypatch):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires real PostgreSQL request interleaving")
    before = current(operator)
    paused, resume = Event(), Event()
    original = installation.runtime_settings

    def wait_before_read(db=None, *, fresh=False):
        if db is not None and not paused.is_set():
            paused.set()
            assert resume.wait(10)
        return original(db, fresh=fresh)

    monkeypatch.setattr(installation, "runtime_settings", wait_before_read)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(operator.get, "/api/admin/installation")
            assert paused.wait(8)
            changed = operator.put("/api/admin/installation/site", json={
                "expected_revision": before["site_revision"], "operator_name": "Synthetic other writer",
            })
            assert changed.status_code == 200, changed.text
            resume.set()
            captured = pending.result(12).json()
    finally:
        resume.set()
    assert captured["site_revision"] == before["site_revision"]
    assert captured["site"]["operator_name"] == before["site"]["operator_name"]
    assert current(operator)["site_revision"] == before["site_revision"] + 1


@pytest.mark.parametrize("revision", [0, -1, True, "1"])
def test_malformed_revisions_fail_without_updates(api, operator, revision):
    before = current(operator)
    response = operator.put("/api/admin/installation/site", json={
        "expected_revision": revision, "operator_name": "Synthetic stale",
    })
    assert response.status_code == 422
    assert current(operator)["site_revision"] == before["site_revision"]
