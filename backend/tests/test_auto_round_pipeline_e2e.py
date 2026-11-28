"""Isolated upload-to-prepared-round checks with synthetic images and transport.

No network/model provider is contacted and no learning interaction is simulated.
"""

import copy
from concurrent.futures import ThreadPoolExecutor

import test_material_auto_review as review_tests
import test_notebook_practice as notebook_tests
from conftest import HEADERS
from fastapi.testclient import TestClient
from schulpilot import notebook_auto, worker
from schulpilot.db import DB, Activity, Attempt, Job, LearningUnit, Material, UnitSource, Usage, engine
from schulpilot.main import app
from schulpilot.notebook_auto_models import NotebookAutoIntent
from schulpilot.providers import Result
from sqlalchemy import func, select

pytest_plugins = ["test_material_auto_review"]


def test_confirmed_upload_prepares_one_round_without_get_side_effects(pipeline, monkeypatch):
    pipeline["outputs"][:] = [review_tests.reading(notebook_tests.CONTENT, topic="Brüche")]
    page = review_tests.upload(pipeline)
    review_tests.first(pipeline, page)
    review_tests.check(pipeline)
    assert len(pipeline["calls"]) == 2  # first transcription and independent check
    with DB() as db:
        material = db.get(Material, page["id"])
        intent = db.scalar(select(NotebookAutoIntent).where(NotebookAutoIntent.material_id == material.id))
        assert material.confirmed and intent and intent.status == "pending"
        revision = material.revision
        assert intent.revision == revision
        before_attempts = db.scalar(select(func.count()).select_from(Attempt))
        before_activity = db.scalar(select(func.count()).select_from(Activity).where(Activity.kind.in_(("unit_started", "unit_completed", "hint", "introduction_read", "explanation"))))

    # GET/reload and competing worker ticks must not allocate two round jobs.
    for _ in range(3):
        assert pipeline["api"].get(f"/api/materials/{page['id']}").status_code == 200
    if engine.dialect.name == "postgresql":
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: notebook_auto.advance_one(), range(2)))
    else:
        notebook_auto.advance_one()
        notebook_auto.advance_one()
    with DB() as db:
        intent = db.scalar(select(NotebookAutoIntent).where(NotebookAutoIntent.material_id == page["id"]))
        assert intent.status == "queued"
        jid = intent.job_id
        jobs = list(db.scalars(select(Job).where(Job.child_id == pipeline["child"]["id"], Job.kind == "unit")))
        assert [job.id for job in jobs] == [jid]
        assert db.scalar(select(func.count()).select_from(Usage).where(Usage.job_id == jid)) == 1

    calls = []
    def provider(_config, function, payload, *_args, **_kwargs):
        assert function == "unit"
        calls.append(copy.deepcopy(payload))
        return Result(notebook_tests.output(3), 100, 100, 200, cost_source="reported")

    monkeypatch.setattr(worker, "request_provider", provider)
    with DB() as db:
        assert worker.claim(db) == jid
    worker.process(jid)
    with DB() as db:
        job = db.get(Job, jid)
        assert job.status == "completed", job.error
        unit_id = job.result["unit_id"]
        unit = db.get(LearningUnit, unit_id)
        assert unit.status == "not_started" and unit.active_seconds == 0
        sources = list(db.scalars(select(UnitSource).where(UnitSource.unit_id == unit_id)))
        assert [(x.material_id, x.revision) for x in sources] == [(page["id"], revision)]
        assert db.scalar(select(func.count()).select_from(Attempt)) == before_attempts
        assert db.scalar(select(func.count()).select_from(Activity).where(Activity.kind.in_(("unit_started", "unit_completed", "hint", "introduction_read", "explanation")))) == before_activity
    assert len(calls) == 1

    # The owner sees the finished unit after reload; this is a read, not a start.
    with TestClient(app, headers=HEADERS) as child:
        login = child.post("/api/auth/login", json={"username": "test-child", "password": "secure-child-pass-123"})
        assert login.status_code == 200, login.text
        child.headers["Authorization"] = "Bearer " + login.json()["token"]
        for _ in range(3):
            assert child.get(f"/api/units/{unit_id}").status_code == 200
            assert pipeline["api"].get(f"/api/jobs/{jid}").status_code == 200
            notebook_auto.advance_one()
            worker.process(jid)
    with DB() as db:
        intent = db.scalar(select(NotebookAutoIntent).where(NotebookAutoIntent.material_id == page["id"]))
        assert intent.status == "completed"
        assert db.scalar(select(func.count()).select_from(Job).where(Job.child_id == pipeline["child"]["id"], Job.kind == "unit")) == 1
        assert db.scalar(select(func.count()).select_from(Usage).where(Usage.job_id == jid)) == 1
        assert db.scalar(select(func.count()).select_from(LearningUnit).where(LearningUnit.child_id == pipeline["child"]["id"])) == 1
        assert db.scalar(select(func.count()).select_from(Attempt)) == before_attempts
        assert db.scalar(select(func.count()).select_from(Activity).where(Activity.kind.in_(("unit_started", "unit_completed", "hint", "introduction_read", "explanation")))) == before_activity
        assert db.get(LearningUnit, unit_id).active_seconds == 0
    assert len(calls) == 1


def test_upload_round_provider_failure_does_not_automatically_retry(pipeline, monkeypatch):
    from schulpilot.providers import ProviderError

    pipeline["outputs"][:] = [review_tests.reading(notebook_tests.CONTENT, topic="Brüche")]
    page = review_tests.upload(pipeline)
    review_tests.first(pipeline, page)
    review_tests.check(pipeline)
    notebook_auto.advance_one()
    with DB() as db:
        intent = db.scalar(select(NotebookAutoIntent).where(NotebookAutoIntent.material_id == page["id"]))
        jid = intent.job_id
        assert intent.status == "queued"
    calls = []

    def failing(_config, function, _payload, *_args, **_kwargs):
        assert function == "unit"
        calls.append(function)
        raise ProviderError("Synthetischer Fehler")

    monkeypatch.setattr(worker, "request_provider", failing)
    with DB() as db:
        assert worker.claim(db) == jid
    worker.process(jid)
    for _ in range(4):
        assert pipeline["api"].get(f"/api/jobs/{jid}").status_code == 200
        assert pipeline["api"].get(f"/api/materials/{page['id']}").status_code == 200
        notebook_auto.advance_one()
        worker.process(jid)
    with DB() as db:
        assert db.get(Job, jid).status == "failed"
        intent = db.scalar(select(NotebookAutoIntent).where(NotebookAutoIntent.material_id == page["id"]))
        assert intent.status == "blocked"
        assert db.scalar(select(func.count()).select_from(Job).where(Job.child_id == pipeline["child"]["id"], Job.kind == "unit")) == 1
        assert db.scalar(select(func.count()).select_from(Usage).where(Usage.job_id == jid)) == 1
        assert db.scalar(select(func.count()).select_from(LearningUnit).where(LearningUnit.child_id == pipeline["child"]["id"])) == 0
        assert db.scalar(select(func.count()).select_from(Attempt)) == 0
    assert calls == ["unit"]
