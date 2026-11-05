"""Artificial multi-child acceptance against persisted facts; no provider requests."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from conftest import HEADERS, create_child, register
from fastapi.testclient import TestClient
from schulpilot import providers
from schulpilot.db import (
    DB,
    Activity,
    Assignment,
    Attempt,
    Child,
    Job,
    LearningUnit,
    Mastery,
    Material,
    SchoolGrade,
    Usage,
    now,
)
from schulpilot.learning import local_day
from schulpilot.main import app
from schulpilot.synthetic import sample_unit
from sqlalchemy import select


def stored_rows():
    """Compare whole domain rows: counts alone miss accidental updates.

    Sessions are deliberately excluded: authenticated GETs can update session
    activity independently of the child's learning records.
    """
    models = (Activity, Assignment, Attempt, Job, LearningUnit, Mastery, Material, SchoolGrade, Usage)
    with DB() as db:
        return {model.__tablename__: sorted(
            (dict(row) for row in db.execute(select(model.__table__)).mappings()),
            key=lambda row: str(row.get("id", "")),
        ) for model in models}


def seed(children):
    stamp = int(now())
    data = sample_unit()
    with DB.begin() as db:
        today = local_day(db.get(Child, children[0]["id"]))
        for index, child in enumerate(children):
            db.get(Child, child["id"]).preferences = {"weekdays": [(today.weekday() + index) % 7]}
            subject = ("Mathematik", "Biologie")[index]
            topic = ("Künstliche Brüche", "Künstliche Pflanzen")[index]
            unit = LearningUnit(child_id=child["id"], subject=subject, topic=topic,
                explanation=data["explanation"], questions=data["questions"],
                provider="synthetic", synthetic=True, status="paused", active_seconds=(180, 75)[index])
            db.add(unit)
            db.flush()
            db.add(Attempt(unit_id=unit.id, question_id="sum", answer="synthetisch",
                outcome="correct" if index else "incorrect", assisted=False, created=stamp - 86400))
            if index == 0:
                db.add(Attempt(unit_id=unit.id, question_id="sum", answer="synthetisch erneut",
                    outcome="correct", assisted=True, created=stamp - 30))
                db.add(Attempt(unit_id=unit.id, question_id="reduce", answer="synthetisch",
                    outcome="correct", assisted=False, created=stamp - 20))
                db.add(Activity(child_id=child["id"], unit_id=unit.id, kind="hint", detail={}, created=stamp - 40))
            db.add(Activity(child_id=child["id"], unit_id=unit.id, kind="active_time",
                detail={"seconds": (180, 75)[index]}, created=stamp))
            previous_noon = int(datetime.combine(today - timedelta(days=1), time(12), ZoneInfo("Europe/Berlin")).timestamp())
            db.add(Activity(child_id=child["id"], unit_id=unit.id, kind="active_time",
                detail={"seconds": 40}, created=previous_noon))
            db.add(Assignment(child_id=child["id"], subject=subject, topic=topic,
                kind="exam", mandatory=True, due=(today + timedelta(days=index + 1)).isoformat(),
                note=f"PRIVAT-NOTIZ-{index}"))
            db.add(SchoolGrade(child_id=child["id"], subject=subject, topic=topic,
                kind="test", scale="grade_1_6", value=index + 2, weight=1,
                assessed_on=today.isoformat(), note=f"PRIVAT-NOTE-{index}"))


def test_parent_reads_multiple_children_facts_without_creating_learning_or_provider_calls(api, household, mailbox, monkeypatch):
    parent, first = household
    second = create_child(api, parent, "another-synthetic-child")
    seed((first, second))
    calls = []
    monkeypatch.setattr(providers, "request_provider", lambda *args, **kwargs: calls.append((args, kwargs)))
    before = stored_rows()
    expected = [
        {"practiced_tasks": 2, "attempts": 3, "independent_tasks": 1, "assisted_tasks": 1,
         "hints_used": 1, "active_seconds_approx": 180},
        {"practiced_tasks": 1, "attempts": 1, "independent_tasks": 1, "assisted_tasks": 0,
         "hints_used": 0, "active_seconds_approx": 75},
    ]
    for index, child in enumerate((first, second)):
        base = f"/api/children/{child['id']}"
        for _ in range(2):
            progress = api.get(base + "/learning-progress")
            overview = api.get(base + "/overview", params={"compact": "true"})
            plan = api.get(base + "/learning-plan")
            grades = api.get(base + "/grades")
            assert all(response.status_code == 200 for response in (progress, overview, plan, grades))
            for key, value in expected[index].items():
                assert progress.json()["totals"][key] == value
                assert overview.json()["practice_summary"][key] == value
            assert overview.json()["plan"]["daily_active_seconds"] == (180, 75)[index]
            assert overview.json()["plan"]["free_day"] is bool(index)
            assert len(plan.json()["topics"]) == 1
            assert plan.json()["topics"][0]["mandatory"] is True
            with DB() as db:
                today = local_day(db.get(Child, child["id"]))
            assert plan.json()["topics"][0]["due"] == (today + timedelta(days=index + 1)).isoformat()
            assert len(grades.json()["items"]) == 1
            assert float(grades.json()["items"][0]["value"]) == index + 2
    assert stored_rows() == before
    assert calls == []

    # A child may see its own progress but never parent-only grade or plan data,
    # and may not read its sibling's learning facts.
    with TestClient(app, headers=HEADERS) as child_client:
        login = child_client.post("/api/auth/login", json={"username": "test-child", "password": "secure-child-pass-123"})
        assert login.status_code == 200
        child_client.headers["Authorization"] = "Bearer " + login.json()["token"]
        assert child_client.get(f"/api/children/{first['id']}/grades").status_code == 403
        assert child_client.get(f"/api/children/{first['id']}/learning-plan").status_code == 403
        assert child_client.get(f"/api/children/{second['id']}/learning-progress").status_code in (403, 404)
    with TestClient(app, headers=HEADERS) as foreign:
        register(foreign, mailbox, "foreign-parent@example.org")
        for suffix in ("overview?compact=true", "learning-progress", "learning-plan", "grades"):
            assert foreign.get(f"/api/children/{first['id']}/{suffix}").status_code in (403, 404)
    assert stored_rows() == before
    assert calls == []


def test_parent_multichild_local_flutter_browser(api, household, mailbox, monkeypatch, tmp_path):
    """Opt-in real Chrome check: localhost, isolated test DB, synthetic users only."""
    import json
    import os
    import socket
    import subprocess
    import threading
    import time as clock
    from dataclasses import replace
    from pathlib import Path

    import pytest
    import uvicorn
    from schulpilot import main
    from schulpilot.config import settings

    if os.environ.get("PARENT_MULTICHILD_BROWSER") != "1":
        pytest.skip("Run explicitly with a locally built Flutter release via WEB_DIR")
    if not settings.web_dir or not (Path(settings.web_dir) / "main.dart.js").is_file():
        pytest.fail("WEB_DIR must point to the locally built Flutter app before importing the server")
    parent, first = household
    second = create_child(api, parent, "browser-synthetic-child")
    seed((first, second))
    calls = []
    monkeypatch.setattr(providers, "request_provider", lambda *args, **kwargs: calls.append(True))
    before = stored_rows()
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
            clock.sleep(0.05)
        assert server.started
        result = subprocess.run(["node", "qa/parent_multichild_browser.mjs"],
            input=json.dumps({"base": f"http://127.0.0.1:{port}", "username": "parent@example.org",
                "password": "secure-parent-pass-123", "children": [first["id"], second["id"]],
                "screens": str(tmp_path)}), text=True, capture_output=True, timeout=180)
        assert result.returncode == 0, result.stderr[-3000:]
        assert stored_rows() == before
        assert calls == []
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        assert not thread.is_alive()
