"""Reproducible month simulation: artificial family, local clock and fake provider.

This runs real API/worker/storage paths. It does not measure real OCR, a
provider, background push delivery, teaching quality or sustained study time.
"""

import copy
import hashlib
import io
import json
import socket
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from conftest import HEADERS
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from schulpilot import (
    coaching,
    learning,
    learning_entry,
    material_review,
    package_part_output,
    school_day,
    security,
    worker,
)
from schulpilot import db as database
from schulpilot.db import (
    DB,
    Attempt,
    Child,
    Family,
    Job,
    LearningUnit,
    Material,
    SchoolDay,
    UnitCoaching,
    UnitSource,
    Usage,
)
from schulpilot.main import app
from schulpilot.providers import Result, validate_factual_package
from schulpilot.schemas import PackageOutput
from schulpilot.school_preparation import _advance, advance_one
from schulpilot.visual_references import validate_output as validate_visuals
from sqlalchemy import event, func, select
from test_material_auto_review import pipeline as pipeline  # noqa: F401
from test_material_auto_review import reading

CASES = json.loads((Path(__file__).parents[2] / "testdata/learning_scenes_v1.json").read_text())["cases"][:2]


def image_for(day_number, case):
    img = Image.new("RGB", (900, 600), "white")
    painter = ImageDraw.Draw(img)
    painter.text((30, 30), f"KUENSTLICHE TESTSEITE {day_number}", fill="black")
    painter.text((30, 100), case["source"].replace("→", "->"), fill="black")
    data = io.BytesIO()
    img.save(data, "JPEG", quality=90)
    return data.getvalue()


def package_output(payload, case):
    group = payload["selected_groups"][0]
    ref = next(item["ref"] for item in payload["visual_context"]["sources"] if item["group_id"] == group["id"])

    def step(disclosure):
        presentation = copy.deepcopy(case["question"]["presentation"])
        for block in presentation["blocks"]:
            block["disclosure"] = disclosure
            block["scene"]["steps"] = block["scene"]["steps"][:2]
        return {"id": "e1", "text": case["source"], "competence_id": None, "disclosure": disclosure,
                "reference": {"id": "general.source_relation.phases", "version": 1}, "source_refs": [ref],
                "presentation": presentation}

    entry = payload.get("learning_entry", {}).get("units", [])
    ids = [item["id"] for item in learning_entry._specs(entry[0], 2)] if entry else ["q1", "q2"]
    first = {**copy.deepcopy(case["question"]), "id": ids[0], "presentation": None,
             "explanation_steps": [step("solution")]}
    prior, answer = (("Kondensation", "Niederschlag") if case["subject"] == "Geographie" else ("Handel", "Stadt"))
    second = {**copy.deepcopy(first), "id": ids[1],
              "prompt": f"Welcher Begriff folgt in der Quelle auf {prior}?", "answer": answer}
    value = {"units": [{"group_id": group["id"], "subject": group["subject"], "topic": "Künstliche Themenfolge",
                        "explanation": case["source"], "explanation_steps": [step("given")],
                        "questions": [first, second]}]}
    value = PackageOutput.model_validate(value).model_dump(mode="json")
    package_part_output.validate(value)
    validate_factual_package(value, payload, allow_matching=True)
    learning_entry.validate_entry_output(payload, value)
    with DB() as db:
        validate_visuals(db, value, payload)
    return value


def school_dates():
    dates = []
    day = date(2026, 9, 1)
    while len(dates) < 30:
        # Weekends and two deliberately missed days produce no compulsory backlog.
        if day.weekday() < 5 and day not in (date(2026, 9, 11), date(2026, 9, 21)):
            dates.append(day)
        day += timedelta(days=1)
    return dates


def run_one():
    advance_one()
    with DB() as db:
        job_id = worker.claim(db)
    assert job_id
    worker.process(job_id)
    return job_id


def test_thirty_individual_synthetic_school_days(pipeline, monkeypatch, tmp_path, request):
    child = pipeline["child"]
    clock = {"date": school_dates()[0], "case": CASES[0]}

    def no_network(*_args, **_kwargs):
        raise AssertionError("The artificial month test cannot access the network")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "getaddrinfo", no_network)

    def test_now():
        return datetime.combine(clock["date"], datetime.min.time(), timezone.utc).timestamp() + 12 * 3600

    class TestDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            current = datetime.fromtimestamp(test_now(), tz or timezone.utc)
            return current if tz else current.replace(tzinfo=None)

    # Patch already imported domain clocks; later imports receive database.now.
    # Everything remains inside the isolated test process.
    original_now = database.now
    for name, module in list(sys.modules.items()):
        if name.startswith("schulpilot.") and getattr(module, "now", None) is original_now:
            monkeypatch.setattr(module, "now", test_now)
    # Attempt.created stores the original function as a SQLAlchemy default.
    def stamp_attempt(_mapper, _connection, attempt):
        if attempt.created is None:
            attempt.created = test_now()

    event.listen(Attempt, "before_insert", stamp_attempt)
    request.addfinalizer(lambda: event.remove(Attempt, "before_insert", stamp_attempt))
    monkeypatch.setattr(learning, "datetime", TestDateTime)
    monkeypatch.setattr(school_day, "local_day", lambda _: clock["date"])
    monkeypatch.setattr(learning, "local_day", lambda _: clock["date"])
    # Rate windows progress with the isolated test date, never the host clock.
    monkeypatch.setattr(security, "time", SimpleNamespace(time=test_now))
    with DB.begin() as db:
        db.get(Child, child["id"]).preferences = {"weekdays": list(range(5)), "daily_minutes": 30,
            "weekly_minutes": 150, "session_minutes": 10, "quiet_start": 0, "quiet_end": 0}
        family = db.get(Family, pipeline["parent"]["families"][0]["id"])
        family.call_limit, family.budget_micros = 500, 50_000_000

    provider_calls = []
    coach_calls = []

    def provider(config, function, payload, image_bytes=None, *, synthetic_fixture=False):
        provider_calls.append(function)
        if function == "extract":
            assert image_bytes
            return Result(reading(clock["case"]["source"], subject=clock["case"]["subject"], topic="Künstliche Themenfolge"),
                          12, 30, 17, cost_source="reported")
        assert function == "package"
        return Result(package_output(payload, clock["case"]), 20, 50, 23, cost_source="reported")

    monkeypatch.setattr(worker, "request_provider", provider)
    monkeypatch.setattr(material_review, "request_provider", provider)

    def coach_provider(config, function, payload):
        assert function == "coach"
        coach_calls.append(function)
        with DB() as db:
            item = db.scalar(select(UnitCoaching).where(UnitCoaching.status == "pending"))
            data = coaching.synthetic_report(db, db.get(LearningUnit, item.unit_id), payload["next_action"])
        unknown = len(coach_calls) == 7
        return Result(data, 12, 30, None if unknown else 0, cost_source="unknown" if unknown else "reported")

    monkeypatch.setattr(coaching, "request_provider", coach_provider)
    records = []
    with TestClient(app, headers=HEADERS) as kid, TestClient(app, headers=HEADERS) as second:
        for number, current in enumerate(school_dates(), start=1):
            if current in (date(2026, 9, 14), date(2026, 9, 22)):
                gap = date(2026, 9, 11) if current.day == 14 else date(2026, 9, 21)
                clock["date"] = gap
                if gap.day == 11:
                    with DB.begin() as db:
                        profile = db.get(Child, child["id"])
                        profile.preferences = {**profile.preferences, "pause_until": gap.isoformat()}
                with DB() as db:
                    before = db.scalar(select(func.count()).select_from(Job))
                absent = kid.get(f"/api/children/{child['id']}/school-day/today")
                assert absent.status_code == 200 and absent.json()["day"] is None
                with DB() as db:
                    assert db.scalar(select(func.count()).select_from(Job)) == before
                if gap.day == 11:
                    with DB.begin() as db:
                        profile = db.get(Child, child["id"])
                        profile.preferences = {**profile.preferences, "pause_until": None}
            clock["date"] = current
            clock["case"] = CASES[(number - 1) % len(CASES)]
            for client in (kid, second):
                login = client.post("/api/auth/login", json={"username": "test-child", "password": "secure-child-pass-123"})
                assert login.status_code == 200, login.text
                client.headers["Authorization"] = "Bearer " + login.json()["token"]
                client.headers["X-Schulpilot-Capabilities"] = "visual-v1,learning-entry-v1"
            day = kid.post(f"/api/children/{child['id']}/school-day/today")
            assert day.status_code == 201, day.text
            day_id = day.json()["id"]
            photo = image_for(number, clock["case"])
            page = kid.post(f"/api/children/{child['id']}/materials?school_day_id={day_id}",
                files={"file": ("artificial.jpg", photo, "image/jpeg")},
                headers={"Idempotency-Key": f"month-upload-{number:04d}-key"})
            assert page.status_code == 201, page.text
            page_id = page.json()["id"]
            if number == 2:
                duplicate = kid.post(f"/api/children/{child['id']}/materials?school_day_id={day_id}",
                    files={"file": ("artificial.jpg", photo, "image/jpeg")},
                    headers={"Idempotency-Key": f"month-upload-{number:04d}-key"})
                assert duplicate.status_code == 201 and duplicate.json()["id"] == page_id
            submitted = kid.post(f"/api/school-days/{day_id}/prepare", headers={
                "Idempotency-Key": f"month-prepare-{number:04d}-key",
                "X-Schulpilot-Capabilities": "visual-v1,learning-entry-v1"})
            assert submitted.status_code == 202, submitted.text
            jobs = [run_one(), run_one(), run_one()]
            with DB.begin() as db:
                _advance(db, db.get(SchoolDay, day_id))
            with DB() as db:
                day_row = db.get(SchoolDay, day_id)
                page_row = db.get(Material, page_id)
                unit = db.scalar(select(LearningUnit).where(LearningUnit.school_day_id == day_id))
                assert day_row.preparation["status"] == "ready", day_row.preparation
                assert page_row.confirmed and unit and db.get(UnitSource, (unit.id, page_id)).revision == page_row.revision
                assert all(db.get(Job, job_id).status == "completed" for job_id in jobs)
                usages = [db.scalar(select(Usage).where(Usage.job_id == job_id)) for job_id in jobs]
                assert all(u and u.status == "completed" for u in usages)
                assert all(datetime.fromtimestamp(db.get(Job, job_id).created, timezone.utc).date() == current
                           for job_id in jobs)
                assert all(datetime.fromtimestamp(u.created, timezone.utc).date() == current for u in usages)
                assert datetime.fromtimestamp(page_row.created, timezone.utc).date() == current
                unit_id = unit.id
                questions = [(q["id"], q["answer"]) for q in unit.questions]
                planned_parts = len(day_row.preparation["package_plan"]["parts"])
                job_count = db.scalar(select(func.count()).select_from(Job))
            # Device switch and read-only reconnect never start a new job.
            assert second.get(f"/api/school-days/{day_id}").status_code == 200
            assert second.get(f"/api/units/{unit_id}").status_code == 200
            with DB() as db:
                assert db.scalar(select(func.count()).select_from(Job)) == job_count
            started = kid.post(f"/api/units/{unit_id}/start")
            assert started.status_code == 200, started.text
            if number % 2 == 0:
                assert kid.post(f"/api/units/{unit_id}/questions/{questions[0][0]}/hint").status_code == 200
            for index, (question_id, answer) in enumerate(questions):
                # An unknown free-text answer must remain uncertain rather
                # than being presented as a wrong or successful answer.
                if number % 5 == 0 and index == 1:
                    answer = "Das weiß ich noch nicht."
                answer_response = kid.post(f"/api/units/{unit_id}/questions/{question_id}/answer", json={"answer": answer})
                assert answer_response.status_code == 200, answer_response.text
            with DB() as db:
                coach_id = worker.claim(db)
                assert coach_id and db.get(Job, coach_id).kind == "coach"
            worker.process(coach_id)
            with DB() as db:
                saved = db.get(LearningUnit, unit_id)
                attempts = list(db.scalars(select(Attempt).where(Attempt.unit_id == unit_id)))
                assert saved.status == "completed" and len(attempts) == len(questions)
                assert all(datetime.fromtimestamp(a.created, timezone.utc).date() == current for a in attempts)
                first = next(a for a in attempts if a.question_id == questions[0][0])
                assert first.assisted == (number % 2 == 0)
                if number % 5 == 0:
                    assert next(a for a in attempts if a.question_id == questions[1][0]).outcome == "uncertain"
                assert db.get(Job, coach_id).status == "completed"
                coach_usage = db.scalar(select(Usage).where(Usage.job_id == coach_id))
                assert coach_usage and coach_usage.status == "completed"
                assert (coach_usage.cost_micros is None) == (number == 7)
                assert datetime.fromtimestamp(db.get(Job, coach_id).created, timezone.utc).date() == current
                assert datetime.fromtimestamp(coach_usage.created, timezone.utc).date() == current
                pending = list(db.scalars(select(Job).where(Job.child_id == child["id"], Job.status.in_(("queued", "running")))))
                assert not pending, [(job.kind, job.status) for job in pending]
                records.append({"date": current.isoformat(), "page": page_id, "revision": page_row.revision,
                    "day": day_id, "unit": unit_id, "subject": page_row.subject, "planned_parts": planned_parts,
                    "jobs": [{"id": job_id, "kind": db.get(Job, job_id).kind,
                              "status": db.get(Job, job_id).status, "error": db.get(Job, job_id).error_code,
                              "created": db.get(Job, job_id).created,
                              "cost_micros": usage.cost_micros, "cost_source": usage.cost_source}
                             for job_id, usage in zip([*jobs, coach_id], [*usages, coach_usage], strict=True)],
                    "attempts": [{"question": a.question_id, "outcome": a.outcome, "assisted": a.assisted}
                                 for a in attempts]})
    assert len(records) == 30 and len({r["date"] for r in records}) == 30
    assert len({r["page"] for r in records}) == len({r["unit"] for r in records}) == 30
    assert provider_calls == ["extract", "extract", "package"] * 30
    assert coach_calls == ["coach"] * 30
    with DB() as db:
        assert not db.scalar(select(func.count()).select_from(SchoolDay).where(SchoolDay.child_id == child["id"],
            SchoolDay.school_date.in_(("2026-09-11", "2026-09-21"))))
    (tmp_path / "thirty-school-days.json").write_text(json.dumps({
        "test_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "database": database.engine.dialect.name,
        "clock": "isolated domain timestamps, learning date and rate windows; global provider month uses host date",
        "transport": "synthetic fixture; no external OCR, model or push",
        "days": records,
    }, ensure_ascii=False, indent=2))
