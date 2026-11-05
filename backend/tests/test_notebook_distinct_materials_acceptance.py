"""Distinct locally drawn material pages, never real pupils or external AI.

This exercises upload, authorization and GET effects, not OCR or visual UI.
"""
import hashlib
import io

from conftest import HEADERS, create_child
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont, ImageStat
from schulpilot.config import settings
from schulpilot.db import DB, Activity, Attempt, Job, LearningUnit, Mastery, Material, UnitSource, Usage
from schulpilot.main import app
from schulpilot.subject_registry import identity
from sqlalchemy import select
from test_admin_users import operator as _operator_fixture
from test_notebook_actions import kid, saved_round

admin_fixture = _operator_fixture

PAGES = [
    ("Arbeitsblatt", "AUFGABE 1: Zeichne drei gleich grosse Teile."),
    ("Hefter", "MERKSATZ: Der Nenner nennt die Anzahl der Teile."),
    ("Arbeitsheft", "UEBUNG: Markiere zwei der vier Kaestchen."),
    ("Buchseite", "BEISPIEL: Ein Ganzes besteht aus vier Vierteln."),
    ("Testseite", "KURZTEST: Wie viele Viertel ergeben ein Ganzes?"),
]


def artificial_page(title, text, index):
    image = Image.new("RGB", (1000, 1400), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=30)
    draw.rectangle((35, 35, 965, 1365), outline="#334455", width=3)
    draw.text((65, 65), "KUENSTLICHE TESTSEITE - KEINE KINDERDATEN", font=font, fill="#284d70")
    draw.text((65, 150), title.upper(), font=font, fill="black")
    draw.text((65, 240), text, font=font, fill="black")
    for n in range(index + 2):
        draw.rectangle((80 + n * 95, 360, 145 + n * 95, 425), outline="black", width=3)
    if index % 2:
        for y in range(520, 1100, 80):
            draw.line((65, y, 930, y), fill="#b0c6df", width=2)
    out = io.BytesIO()
    image.save(out, "JPEG", quality=88)
    return out.getvalue()


def inventory():
    """Snapshot values, not just row counts, including existing learning data."""
    with DB() as db:
        result = {}
        for model in (Material, LearningUnit, UnitSource, Attempt, Activity, Mastery, Job, Usage):
            rows = db.execute(select(model.__table__).order_by(*model.__table__.primary_key.columns)).mappings().all()
            result[model.__tablename__] = [dict(row) for row in rows]
        return result


def test_distinct_uploaded_materials_keep_private_data_and_existing_records_unchanged(api, household, admin_fixture):
    parent, child = household
    sibling = create_child(api, parent, "notebook-material-sibling")
    object.__setattr__(settings, "real_data_approved", True)
    object.__setattr__(settings, "privacy_evidence", "isolated synthetic material acceptance")
    ids = []
    for index, (title, text) in enumerate(PAGES):
        response = api.post(
            f"/api/children/{child['id']}/materials",
            files={"file": (f"synthetic-{index}.jpg", artificial_page(title, text, index), "image/jpeg")},
            headers={"Idempotency-Key": f"synthetic-notebook-{index:04}"},
        )
        assert response.status_code == 201, response.text
        ids.append(response.json()["id"])
    with DB.begin() as db:
        for material_id, (title, text) in zip(ids, PAGES, strict=True):
            material = db.get(Material, material_id)
            # Setup only: testing catalogue and authorization, not OCR or user confirmation.
            material.title = title
            material.subject = "Mathematik"
            material.subject_id = identity("mathematik")
            material.content = text
        db.add(Activity(child_id=child["id"], kind="synthetic", detail={"marker": "must stay unchanged"}))
        db.add(Mastery(child_id=child["id"], subject="Mathematik", topic="Brueche", independent=2,
                       next_review="2026-11-10", last_practiced="2026-11-01"))
        db.add(Usage(family_id=parent["families"][0]["id"], child_id=child["id"], job_id="synthetic",
                     provider="synthetic", model="synthetic", config_revision=1, function="unit",
                     status="completed", reserved_micros=0, cost_micros=0, bucket_ids=[]))
    saved_round(child, ids[0])
    before = inventory()
    image_hashes = set()
    with kid() as own, TestClient(app, headers=HEADERS) as guest, TestClient(app, headers=HEADERS) as other:
        login = other.post("/api/auth/login", json={"username": "notebook-material-sibling", "password": "secure-child-pass-123"})
        assert login.status_code == 200
        other.headers["Authorization"] = "Bearer " + login.json()["token"]
        route = f"/api/children/{child['id']}/materials"
        for sort in ("newest", "oldest"):
            listing = own.get(route, params={"subject_id": identity("mathematik"), "sort": sort})
            assert listing.status_code == 200, listing.text
            assert set(ids) <= {item["id"] for item in listing.json()["items"]}
            assert all("content" not in item and "path" not in item for item in listing.json()["items"])
        for material_id, (title, _) in zip(ids, PAGES, strict=True):
            result = own.get(route, params={"q": title})
            assert result.status_code == 200
            assert material_id in {item["id"] for item in result.json()["items"]}
            detail = own.get(f"/api/materials/{material_id}")
            assert detail.status_code == 200 and detail.json()["title"] == title
            revisions = own.get(f"/api/materials/{material_id}/revisions")
            assert revisions.status_code == 200
            image = own.get(f"/api/materials/{material_id}/image")
            assert image.status_code == 200 and image.headers["cache-control"] == "no-store"
            with Image.open(io.BytesIO(image.content)) as decoded:
                assert decoded.size == (1000, 1400)
                assert ImageStat.Stat(decoded.convert("L")).var[0] > 10
            image_hashes.add(hashlib.sha256(image.content).hexdigest())
            assert guest.get(f"/api/materials/{material_id}/image").status_code == 401
            assert other.get(f"/api/materials/{material_id}/image").status_code == 404
            assert admin_fixture.get(f"/api/materials/{material_id}/image").status_code in (403, 404)
            for suffix in ("", "/revisions"):
                assert guest.get(f"/api/materials/{material_id}{suffix}").status_code == 401
                assert other.get(f"/api/materials/{material_id}{suffix}").status_code == 404
                assert admin_fixture.get(f"/api/materials/{material_id}{suffix}").status_code in (403, 404)
        assert len(image_hashes) == len(PAGES)
        assert own.get(f"/api/children/{sibling['id']}/materials").status_code == 404
    assert inventory() == before
