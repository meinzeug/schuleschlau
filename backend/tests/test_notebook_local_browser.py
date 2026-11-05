"""Opt-in end-to-end notebook exercise: isolated SQLite, browser, no worker."""

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
from conftest import HEADERS, create_child, register
from fastapi.testclient import TestClient
from schulpilot import main, providers
from schulpilot.config import settings
from schulpilot.db import DB, Attempt, Job, LearningUnit, Material, UnitSource, Usage, now
from schulpilot.main import app
from schulpilot.subject_registry import identity
from schulpilot.synthetic import sample_unit
from sqlalchemy import select
from sqlalchemy.engine import make_url
from test_providers import configured

ROOT = Path(__file__).resolve().parents[2]
NAMES = ("arbeitsblatt", "hefter", "arbeitsheft", "buchseite", "klassenarbeit")


def test_notebook_local_browser(api, household, mailbox, monkeypatch, tmp_path):
    if os.environ.get("NOTEBOOK_LOCAL_BROWSER") != "1":
        pytest.skip("Set NOTEBOOK_LOCAL_BROWSER=1 for the isolated browser test")
    if settings.environment != "test" or make_url(settings.database_url).get_backend_name() != "sqlite":
        pytest.fail("This test requires the dedicated pytest SQLite database")
    if not settings.web_dir or not (Path(settings.web_dir) / "main.dart.js").is_file():
        pytest.fail("WEB_DIR must point to a locally built Flutter web app")
    # Uploads and recordings are kept under pytest's own disposable directory.
    object.__setattr__(settings, "data_dir", tmp_path / "data")
    parent, first = household
    second = create_child(api, parent, "notebook-browser-second")
    third = create_child(api, parent, "notebook-browser-third")
    configured(parent["families"][0]["id"])
    calls = []
    monkeypatch.setattr(providers, "request_provider", lambda *args, **kwargs: calls.append(True))
    pages = []
    for child in (first, second):
        own = []
        for name in NAMES:
            response = api.post(
                f"/api/children/{child['id']}/materials",
                files={
                    "file": (
                        name + ".jpg",
                        (ROOT / "testdata/notebook_synthetic" / (name + ".jpg")).read_bytes(),
                        "image/jpeg",
                    )
                },
            )
            assert response.status_code == 201, response.text
            material_id = response.json()["id"]
            # No OCR is invoked: the artificial transcript is explicitly set up
            # as a review candidate, then confirmed through the actual API.
            with DB.begin() as db:
                material = db.get(Material, material_id)
                material.status = "review"
                material.title = "Künstliche " + name
            confirmed = api.put(
                f"/api/materials/{material_id}/confirm",
                json={
                    "subject": "Mathematik",
                    "topic": "Künstliche " + name,
                    "content": "Künstlicher Teststoff: Ein Ganzes besteht aus vier Vierteln.",
                    "homework": [],
                    "uncertainties_resolved": True,
                },
            )
            assert confirmed.status_code == 200, confirmed.text
            own.append(
                {
                    "id": material_id,
                    "revision": confirmed.json()["revision"],
                    "subject_id": confirmed.json()["subject_id"],
                }
            )
        pages.append(own)
    # One artificial unconfirmed page, belonging only to the third child.
    response = api.post(
        f"/api/children/{third['id']}/materials",
        files={
            "file": ("test.jpg", (ROOT / "testdata/notebook_synthetic/arbeitsblatt.jpg").read_bytes(), "image/jpeg")
        },
    )
    assert response.status_code == 201, response.text
    unconfirmed_id = response.json()["id"]
    with DB.begin() as db:
        material = db.get(Material, unconfirmed_id)
        material.status = "review"
        material.title = "Künstliche ungeprüfte Seite"
        material.subject = "Mathematik"
        material.subject_id = identity("mathematik")
        unit = LearningUnit(
            child_id=first["id"],
            material_id=pages[0][0]["id"],
            status="completed",
            completed=int(now()),
            provider="synthetic",
            synthetic=True,
            **sample_unit(),
        )
        db.add(unit)
        db.flush()
        for source in pages[0]:
            db.add(UnitSource(unit_id=unit.id, material_id=source["id"], revision=source["revision"]))
        db.add(Attempt(unit_id=unit.id, question_id="sum", answer="künstlich", outcome="correct", assisted=False))
    with TestClient(app, headers=HEADERS) as outsider:
        foreign_parent = register(outsider, mailbox, "foreign-notebook-browser@example.org")
        create_child(outsider, foreign_parent, "foreign-notebook-browser")
        login = outsider.post(
            "/api/auth/login", json={"username": "foreign-notebook-browser", "password": "secure-child-pass-123"}
        )
        assert login.status_code == 200
        outsider.headers["Authorization"] = "Bearer " + login.json()["token"]
        assert outsider.get(f"/api/materials/{pages[0][0]['id']}/image").status_code in (403, 404)
    with DB() as db:
        assert not list(db.scalars(select(Job))) and not list(db.scalars(select(Usage)))
        assert len(list(db.scalars(select(Attempt)))) == 1
    # Exercise the same parent reads before the browser; never print data or
    # SQL parameters if this artificial fixture exposes an application error.
    import traceback

    from schulpilot import families, learning
    from schulpilot.db import Session, User
    from schulpilot.security import Principal

    with DB() as db:
        user = db.get(User, parent["id"])
        session = db.scalar(select(Session).where(Session.user_id == user.id))
        principal = Principal(user=user, session=session)
        for name, call in (
            ("family_detail", lambda: families.family_detail(parent["families"][0]["id"], principal, db)),
            ("child_overview", lambda: learning.overview(first["id"], principal, db, capabilities=None)),
        ):
            try:
                call()
            except Exception as exc:
                frames = [(Path(f.filename).name, f.lineno, f.name) for f in traceback.extract_tb(exc.__traceback__)]
                pytest.fail(f"Synthetic {name} raised {type(exc).__name__}; frames={frames}")
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
        config = {
            "base": f"http://127.0.0.1:{port}",
            "parent": "parent@example.org",
            "parent_password": "secure-parent-pass-123",
            "child_password": "secure-child-pass-123",
            "children": [first["id"], second["id"], third["id"]],
            "pages": pages,
            "unconfirmed_id": unconfirmed_id,
            "subject_id": identity("mathematik"),
            "screens": str(tmp_path),
        }
        node = shutil.which("node")
        assert node is not None
        result = subprocess.run(
            [node, "qa/notebook_local_browser.mjs"],
            input=json.dumps(config),
            text=True,
            capture_output=True,
            timeout=240,
            env={"PATH": str(Path(node).parent) + ":/usr/bin:/bin", "LANG": "C.UTF-8"},
        )
        assert result.returncode == 0, result.stderr[-4000:]
        assert calls == []
        with DB() as db:
            jobs = list(db.scalars(select(Job)))
            assert len(jobs) == 2 and all(j.status == "queued" and j.attempts == 0 and j.result is None for j in jobs)
            assert len(list(db.scalars(select(Usage)))) == 2
            assert len(list(db.scalars(select(Attempt)))) == 1
            assert db.get(Material, unconfirmed_id) is None
            for job in jobs:
                index = [first["id"], second["id"]].index(job.child_id)
                expected = {p["id"]: p["revision"] for p in pages[index]}
                sources = job.payload["sources"]
                assert len(sources) == index + 1
                assert all(expected.get(row["id"]) == row["revision"] for row in sources)
            assert all(db.get(Material, p["id"]) is not None for group in pages for p in group)
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        assert not thread.is_alive()


def test_notebook_browser_rejects_external_database_before_import():
    import sys

    environment = {
        **os.environ,
        "PYTHONPATH": "backend/tests:backend",
        "NOTEBOOK_LOCAL_BROWSER": "1",
        "TEST_DATABASE_URL": "postgresql+psycopg://fixture@127.0.0.1/schulpilot_test",
    }
    result = subprocess.run(
        [sys.executable, "-c", "import conftest"], env=environment, text=True, capture_output=True, timeout=10
    )
    assert result.returncode != 0
    assert "require an automatically isolated SQLite database" in result.stderr
