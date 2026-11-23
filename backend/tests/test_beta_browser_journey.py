"""Opt-in, isolated browser journey through synthetic beta enrollment."""

import json
import os
import shutil
import socket
import subprocess
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest
import uvicorn
from fastapi import HTTPException
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from schulpilot import auth, families, main, providers
from schulpilot.beta_models import BetaApplication
from schulpilot.child_cost_models import ChildCostControl
from schulpilot.commerce import access, usage_terms
from schulpilot.config import settings
from schulpilot.db import (
    DB,
    Attempt,
    Child,
    Family,
    Job,
    LearningUnit,
    Material,
    ProviderConfig,
    StoreConfiguration,
    UnitSource,
    Usage,
    User,
    uid,
)
from schulpilot.main import app
from schulpilot.providers import Result, reserve, settle
from schulpilot.security import encrypt, password_hash
from schulpilot.synthetic import sample_unit
from sqlalchemy import select
from sqlalchemy.engine import make_url
from test_model_routing import setup_policy

ROOT = Path(__file__).resolve().parents[2]


def test_beta_browser_journey(monkeypatch, tmp_path):
    if os.environ.get("BETA_LOCAL_BROWSER") != "1":
        pytest.skip("Set BETA_LOCAL_BROWSER=1 for an isolated browser test")
    if (
        os.getenv("TEST_DATABASE_URL")
        or settings.environment != "test"
        or make_url(settings.database_url).get_backend_name() != "sqlite"
    ):
        pytest.fail("A fresh isolated SQLite database is required")
    if not settings.web_dir or not (Path(settings.web_dir) / "main.dart.js").is_file():
        pytest.fail("WEB_DIR must name a local Flutter web build")
    object.__setattr__(settings, "data_dir", tmp_path / "data")
    object.__setattr__(settings, "smtp_host", "smtp.example.invalid")
    object.__setattr__(settings, "smtp_from", "fixture@example.invalid")
    messages = []
    for module in (auth, families):
        monkeypatch.setattr(module, "require_mail", lambda: None)
        monkeypatch.setattr(
            module, "send_link", lambda email, subject, text, route, token: messages.append((route, token))
        )
    calls = []
    monkeypatch.setattr(providers, "request_provider", lambda *a, **k: calls.append(True))
    with DB.begin() as db:
        db.add(StoreConfiguration(id=1, encrypted_config=encrypt(json.dumps({"beta_enabled": True})), revision=1))
        db.add(
            User(
                username="synthetic-beta-operator",
                display_name="Synthetische Administration",
                role="admin",
                verified=True,
                password_hash=password_hash("Synthetic-Admin-Password-123!"),
            )
        )

    # Only this test process adds this endpoint, bound to the disposable loopback
    # server. Production never imports or installs a fixture mail endpoint.
    def fixture_mail():
        if len(messages) != 1 or messages[0][0] != "verify":
            return {"ready": False}
        return {"ready": True, "token": messages[0][1]}

    def fixture_unit(child_id: str):
        with DB.begin() as db:
            child = db.get(Child, child_id)
            if child is None or not db.scalar(
                select(BetaApplication).where(
                    BetaApplication.family_id == child.family_id, BetaApplication.status == "approved"
                )
            ):
                raise HTTPException(403)
            if db.scalar(select(LearningUnit).where(LearningUnit.child_id == child_id)):
                raise HTTPException(409)
            material = Material(
                child_id=child_id,
                title="Künstlicher Bruchtest",
                status="ready",
                subject="Mathematik",
                topic="Brüche",
                content="Ein Ganzes besteht aus vier Vierteln. 1/4 + 1/4 = 2/4.",
                confirmed=True,
                synthetic=True,
            )
            db.add(material)
            db.flush()
            unit = LearningUnit(
                child_id=child_id, material_id=material.id, provider="synthetic", synthetic=True, **sample_unit()
            )
            db.add(unit)
            db.flush()
            db.add(UnitSource(unit_id=unit.id, material_id=material.id, revision=material.revision))
            return {"id": unit.id}

    route = APIRoute("/__fixture/beta-mail", fixture_mail, methods=["GET"], include_in_schema=False)
    unit_route = APIRoute("/__fixture/beta-unit", fixture_unit, methods=["POST"], include_in_schema=False)
    app.router.routes.insert(0, route)
    app.router.routes.insert(0, unit_route)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    port = sock.getsockname()[1]
    monkeypatch.setattr(main, "settings", replace(settings, public_url=f"http://127.0.0.1:{port}"))
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="off"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if server.started:
                break
            time.sleep(0.05)
        assert server.started
        node = shutil.which("node")
        assert node
        result = subprocess.run(
            [node, "qa/beta_local_browser.mjs"],
            input=json.dumps({"base": f"http://127.0.0.1:{port}", "screens": str(tmp_path)}),
            text=True,
            capture_output=True,
            timeout=240,
            env={
                "PATH": str(Path(node).parent) + ":/usr/bin:/bin",
                "LANG": "C.UTF-8",
                "TMPDIR": os.environ.get("TMPDIR", "/tmp"),
            },
        )
        assert result.returncode == 0, result.stderr[-4000:]
        assert json.loads(result.stdout)["approved"] is True
        assert calls == []
        with DB() as db:
            rows = list(db.scalars(select(BetaApplication)))
            assert len(rows) == 1 and rows[0].status == "approved" and rows[0].revision == 2
            assert db.get(User, rows[0].user_id).verified
            application_id, family_id = rows[0].id, rows[0].family_id
            child = db.scalar(select(Child).where(Child.family_id == family_id))
            assert child is not None
            child_id = child.id
            assert not list(db.scalars(select(Job)))
            assert not list(db.scalars(select(Usage)))
            attempts = list(db.scalars(select(Attempt)))
            assert len(attempts) == 1 and attempts[0].outcome == "correct"
        # Artificial provider policy and billing only: no external provider call.
        # Test a zero personal/global budget, known/unknown costs and a real
        # revision-bound revoke on the application created by the browser.
        setup_policy(family_id)
        with DB.begin() as db:
            db.get(ProviderConfig, 1).global_limit_micros = 0
            db.add(
                ChildCostControl(
                    child_id=child_id,
                    enabled=True,
                    revision=1,
                    timezone="Europe/Berlin",
                    daily_limit_eur_micros=0,
                    monthly_limit_eur_micros=0,
                )
            )
        with DB.begin() as db:
            family = db.get(Family, family_id)
            assert access(db, family)["unlimited"] is True
            known = reserve(db, family, child_id, uid(), "unit")
            assert known.route_snapshot["child_cost_control"]["beta_unlimited"] is True
            settle(db, known, Result({}, 30, 40, 1234, cost_source="reported"))
        with DB.begin() as db:
            unknown = reserve(db, db.get(Family, family_id), child_id, uid(), "unit")
            settle(db, unknown, None, failed=True)
        with TestClient(app, headers={"X-Schulpilot-Request": "1", "X-Client-Platform": "native"}) as operator:
            login = operator.post(
                "/api/auth/login",
                json={"username": "synthetic-beta-operator", "password": "Synthetic-Admin-Password-123!"},
            )
            assert login.status_code == 200
            operator.headers["Authorization"] = "Bearer " + login.json()["token"]
            items = operator.get("/api/admin/beta-applications?status=approved").json()["items"]
            item = next(row for row in items if row["id"] == application_id)
            assert (item["usage"]["calls"], item["usage"]["known_usd_micros"], item["usage"]["unknown_calls"]) == (
                2,
                1234,
                1,
            )
            response = operator.post(
                f"/api/admin/beta-applications/{application_id}/decision", json={"revision": 2, "decision": "revoke"}
            )
            assert response.status_code == 200 and response.json()["status"] == "revoked"
        with DB() as db:
            with pytest.raises(HTTPException):
                usage_terms(db, db.get(Family, family_id), enforce=True)
            assert len(list(db.scalars(select(Usage)))) == 2
        with TestClient(app, headers={"X-Schulpilot-Request": "1", "X-Client-Platform": "native"}) as parent:
            login = parent.post(
                "/api/auth/login",
                json={"username": "beta-browser@example.org", "password": "Synthetic-Parent-Password-123!"},
            )
            assert login.status_code == 200
            parent.headers["Authorization"] = "Bearer " + login.json()["token"]
            application = parent.post(f"/api/families/{family_id}/beta-application")
            assert application.status_code == 202 and application.json()["status"] == "pending"
        with DB() as db:
            with pytest.raises(HTTPException):
                usage_terms(db, db.get(Family, family_id), enforce=True)
        with TestClient(app, headers={"X-Schulpilot-Request": "1", "X-Client-Platform": "native"}) as operator:
            login = operator.post(
                "/api/auth/login",
                json={"username": "synthetic-beta-operator", "password": "Synthetic-Admin-Password-123!"},
            )
            assert login.status_code == 200
            operator.headers["Authorization"] = "Bearer " + login.json()["token"]
            response = operator.post(
                f"/api/admin/beta-applications/{application_id}/decision", json={"revision": 4, "decision": "approve"}
            )
            assert response.status_code == 200
            usage = response.json()["usage"]
            assert (usage["calls"], usage["known_usd_micros"], usage["unknown_calls"]) == (2, 1234, 1)
        with DB() as db:
            assert access(db, db.get(Family, family_id))["unlimited"] is True
            assert len(list(db.scalars(select(Usage)))) == 2
            assert len(list(db.scalars(select(Attempt)))) == 1
        assert calls == []
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        app.router.routes.remove(route)
        app.router.routes.remove(unit_route)
        assert not thread.is_alive()


def test_beta_browser_rejects_external_database_before_import():
    env = {
        **os.environ,
        "PYTHONPATH": "backend/tests:backend",
        "BETA_LOCAL_BROWSER": "1",
        "TEST_DATABASE_URL": "postgresql+psycopg://fixture@127.0.0.1/schulpilot_test",
    }
    result = subprocess.run(
        [__import__("sys").executable, "-c", "import conftest"], env=env, capture_output=True, text=True, timeout=10
    )
    assert result.returncode != 0
    assert "require an automatically isolated SQLite database" in result.stderr
