"""Synthetic upload replays and automatic round reservation; no network calls."""

import copy
import io
import threading
from concurrent.futures import ThreadPoolExecutor

import test_material_auto_review as review_tests
import test_notebook_practice as notebook_tests
from fastapi.testclient import TestClient
from PIL import Image
from schulpilot import main, materials, notebook_auto, worker
from schulpilot.db import DB, Attempt, Job, LearningUnit, Material, UnitSource, Usage
from schulpilot.notebook_auto_models import NotebookAutoIntent
from schulpilot.providers import Result
from sqlalchemy import func, select
from test_school_day import image_bytes

pytest_plugins = ["test_material_auto_review"]


def test_concurrent_same_key_upload_produces_one_source_and_one_automatic_round(pipeline, monkeypatch):
    # Two slots emulate two API processes: the actual slots are process-local,
    # so database serialization must still protect an overlapping upload.
    monkeypatch.setattr(main, "_PHOTO_REQUEST_SLOT", threading.BoundedSemaphore(2))
    monkeypatch.setattr(materials, "_SYNC_PHOTO_SLOT", threading.BoundedSemaphore(2))
    original = materials.normalize_photo
    barrier = threading.Barrier(2)

    def synchronized_normalize(raw):
        result = original(raw)
        barrier.wait(timeout=30)
        return result

    monkeypatch.setattr(materials, "normalize_photo", synchronized_normalize)
    pipeline["outputs"][:] = [review_tests.reading(notebook_tests.CONTENT, topic="Brüche")]
    child_id = pipeline["child"]["id"]
    url = f"/api/children/{child_id}/materials"
    headers = dict(pipeline["api"].headers)
    headers["Idempotency-Key"] = "artificial-concurrent-upload-0001"
    image = image_bytes()

    def submit(_):
        with TestClient(main.app, headers=headers) as client:
            return client.post(url, files={"file": ("synthetic.jpg", image, "image/jpeg")})

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(submit, range(2)))
    assert [response.status_code for response in responses] == [201, 201], [r.text for r in responses]
    assert responses[0].json()["id"] == responses[1].json()["id"]
    page = responses[0].json()
    monkeypatch.setattr(materials, "normalize_photo", original)

    # Same key cannot be reused for a different image.
    different = io.BytesIO()
    Image.new("RGB", (80, 60), "black").save(different, "JPEG")
    conflict = pipeline["api"].post(url, headers={"Idempotency-Key": headers["Idempotency-Key"]},
                                    files={"file": ("different.jpg", different.getvalue(), "image/jpeg")})
    assert conflict.status_code == 409
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Material).where(Material.child_id == child_id)) == 1

    review_tests.first(pipeline, page)
    review_tests.check(pipeline)
    assert len(pipeline["calls"]) == 2
    notebook_auto.advance_one()
    with DB() as db:
        intent = db.scalar(select(NotebookAutoIntent).where(NotebookAutoIntent.material_id == page["id"]))
        assert intent.status == "queued"
        jid = intent.job_id
        revision = intent.revision
    calls = []

    def provider(_config, function, payload, *_args, **_kwargs):
        assert function == "unit"
        calls.append(copy.deepcopy(payload))
        return Result(notebook_tests.output(3), 100, 100, 200, cost_source="reported")

    monkeypatch.setattr(worker, "request_provider", provider)
    with DB() as db:
        assert worker.claim(db) == jid
    worker.process(jid)
    notebook_auto.advance_one()
    notebook_auto.advance_one()
    with DB() as db:
        job = db.get(Job, jid)
        assert job.status == "completed", job.error
        unit = db.get(LearningUnit, job.result["unit_id"])
        assert unit.status == "not_started" and unit.active_seconds == 0
        assert db.scalar(select(func.count()).select_from(NotebookAutoIntent).where(
            NotebookAutoIntent.material_id == page["id"])) == 1
        assert db.scalar(select(func.count()).select_from(Job).where(Job.child_id == child_id, Job.kind == "unit")) == 1
        assert db.scalar(select(func.count()).select_from(Usage).where(Usage.job_id == jid)) == 1
        assert db.scalar(select(func.count()).select_from(LearningUnit).where(LearningUnit.child_id == child_id)) == 1
        assert db.scalar(select(func.count()).select_from(Attempt)) == 0
        assert [(s.material_id, s.revision) for s in db.scalars(select(UnitSource).where(
            UnitSource.unit_id == unit.id))] == [(page["id"], revision)]
    assert len(calls) == 1
