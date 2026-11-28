"""Opt-in isolated real-provider check of automatic notebook preparation.

Only the fixed artificial picture below is submitted. The ordinary upload,
reservation, worker, automatic countercheck and automatic round paths run
against the pytest-only SQLite database. This is not a browser or live-site
test. Default test runs skip this module before reading any key or making calls.
"""

import io
import json
import os
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont
from schulpilot import material_review, notebook_auto, worker
from schulpilot.config import settings
from schulpilot.db import DB, Attempt, Family, Job, LearningUnit, Material, ProviderConfig, UnitSource, Usage, engine
from schulpilot.notebook_auto_models import NotebookAutoIntent
from sqlalchemy import func, select
from test_material_auto_review import mode

pytestmark = pytest.mark.skipif(
    os.getenv("SCHOOLSCHLAU_ISOLATED_REAL_AI") != "1",
    reason="Explicit opt-in required for isolated paid-provider integration",
)


def artificial_page(lines=None):
    image = Image.new("RGB", (1600, 1100), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("DejaVuSans.ttf", 42)
    for n, line in enumerate(lines or (
        "KÜNSTLICHER TEST – KEINE KINDERDATEN",
        "Mathematik: Brüche und ganze Zahlen",
        "Multipliziere den Zähler mit der ganzen Zahl.",
        "Der Nenner bleibt zunächst unverändert.",
        "3/8 mal 12 = 36/8 = 9/2",
        "2/3 mal 4 = 8/3",
    )):
        draw.text((65, 75 + 145 * n), line, font=font, fill="black")
    target = io.BytesIO()
    image.save(target, "JPEG", quality=94)
    return target.getvalue()


def artificial_addition_page():
    """Same fixed picture as the separate real 390px-browser observation."""
    return artificial_page((
        "KÜNSTLICHER TEST – KEINE KINDERDATEN",
        "Mathematik: Brüche mit gleichem Nenner addieren",
        "Bei gleichen Nennern addiere ich die Zähler.",
        "Der Nenner bleibt unverändert.",
        "1/4 + 2/4 = 3/4",
        "2/7 + 3/7 = 5/7",
    ))


def test_fixed_photo_to_automatic_round_with_real_provider(api, household):
    from conftest import _EXPECTED_TEST_DATABASE_URL, require_test_database

    require_test_database(engine, settings, _EXPECTED_TEST_DATABASE_URL)
    assert engine.dialect.name == "sqlite"
    route_path = Path(os.environ["SCHOOLSCHLAU_ISOLATED_ROUTE"])
    key_path = Path(os.environ["SCHOOLSCHLAU_ISOLATED_KEY"])
    assert route_path.is_file() and key_path.is_file()
    route = json.loads(route_path.read_text())
    assert route["provider"] == "openrouter" and route["privacy_approved"]
    assert route["routing_policy"]["enabled"] and route["production_block_reason"] == ""
    key = key_path.read_text().strip()
    assert key
    # pytest's isolated clean_database fixture restores settings after the test.
    object.__setattr__(settings, "openrouter_api_key", key)
    object.__setattr__(settings, "real_data_approved", True)
    object.__setattr__(settings, "privacy_evidence", "Explicitly approved fixed artificial test only")
    mode("automatic")
    parent, child = household
    with DB.begin() as db:
        config = db.get(ProviderConfig, 1)
        for name, value in route.items():
            setattr(config, name, value)
        config.emergency_stop = False
        config.encrypted_key = None
        family = db.get(Family, parent["families"][0]["id"])
        family.call_limit = 5
        family.budget_micros = 20_000_000
    response = api.post(f"/api/children/{child['id']}/materials", files={
        "file": ("artificial-fractions.jpg", artificial_page(), "image/jpeg"),
    }, headers={"Idempotency-Key": "isolated-real-auto-round-photo-v1"})
    assert response.status_code == 201
    material_id = response.json()["id"]
    first = api.post(f"/api/materials/{material_id}/extract", headers={
        "Idempotency-Key": "isolated-real-auto-round-ocr-v1"})
    assert first.status_code == 202
    first_job = first.json()["id"]
    with DB() as db:
        assert worker.claim(db) == first_job
    worker.process(first_job)
    with DB() as db:
        first_row = db.get(Job, first_job)
        assert first_row.status == "completed", "Initial OCR failed; no retry"
    material_review.advance_one()
    with DB() as db:
        check_job = worker.claim(db)
        assert check_job and db.get(Job, check_job).payload.get(material_review.KEY)
    worker.process(check_job)
    with DB() as db:
        assert db.get(Job, check_job).status == "completed", "Countercheck failed; no retry"
        material = db.get(Material, material_id)
        assert material.confirmed, "Artificial photo still needs review; no false success"
        intent = db.scalar(select(NotebookAutoIntent).where(NotebookAutoIntent.material_id == material_id))
        assert intent and intent.status == "pending"
    notebook_auto.advance_one()
    with DB() as db:
        intent = db.scalar(select(NotebookAutoIntent).where(NotebookAutoIntent.material_id == material_id))
        assert intent.status == "queued", "Automatic preparation could not reserve a job"
        unit_job = intent.job_id
        assert worker.claim(db) == unit_job
    worker.process(unit_job)
    with DB() as db:
        job = db.get(Job, unit_job)
        assert job.status == "completed", "Actual round generation failed; no retry"
        unit = db.get(LearningUnit, job.result["unit_id"])
        assert unit.status == "not_started" and unit.active_seconds == 0
        assert db.scalar(select(UnitSource).where(UnitSource.unit_id == unit.id,
                         UnitSource.material_id == material_id))
        assert db.scalar(select(func.count()).select_from(Attempt).where(Attempt.unit_id == unit.id)) == 0
        records = list(db.scalars(select(Usage).where(Usage.child_id == child["id"])))
        assert len(records) == 3 and {r.function for r in records} == {"extract", "unit"}
        assert len([r for r in records if r.function == "extract"]) == 2
        print(json.dumps({"real_provider": True, "automatic_round": True,
            "provider_models": sorted({r.model for r in records}),
            "known_cost_micros_usd": sum(r.cost_micros or 0 for r in records),
            "unknown_costs": sum(r.cost_micros is None for r in records),
            "exercise_count": len(unit.questions), "browser_checked": False}))
