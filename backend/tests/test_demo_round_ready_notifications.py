"""Only fixed in-process demo units may exercise the real ready-notice path.

No external model, real children, provider payload, or FCM transport is used.
"""

import uuid

import pytest
from conftest import HEADERS
from fastapi.testclient import TestClient
from schulpilot import notifications as notifications
from schulpilot import ready_notifications as ready
from schulpilot import worker
from schulpilot.db import (
    DB,
    Attempt,
    Child,
    Family,
    Job,
    LearningUnit,
    Material,
    Message,
    PushDelivery,
    PushDevice,
    PushTestGrant,
    Session,
    UnitSource,
    now,
)
from schulpilot.main import app
from schulpilot.synthetic import CONTENT
from sqlalchemy import func, select
from test_notifications import device, enable


def make_demo(api, *, parent_grant=True, child_grant=True):
    demo = api.post("/api/demo").json()
    api.headers["Authorization"] = "Bearer " + demo["token"]
    with DB.begin() as db:
        child = db.get(Child, demo["child_id"])
        child.preferences = {"push_consent": True, "quiet_start": 0, "quiet_end": 0}
        if parent_grant:
            db.add(PushTestGrant(user_id=demo["user"]["id"], expires=int(now()) + 3600))
        if child_grant:
            db.add(PushTestGrant(user_id=child.user_id, expires=int(now()) + 3600))
    result = api.put(
        "/api/materials/" + demo["material_id"] + "/confirm",
        json={
            "subject": "Mathematik",
            "topic": "Brüche",
            "content": CONTENT,
            "homework": [],
            "uncertainties_resolved": True,
        },
    )
    assert result.status_code == 200, result.text
    result = api.post(
        "/api/children/" + demo["child_id"] + "/units",
        json={"material_id": demo["material_id"]},
        headers={"Idempotency-Key": uuid.uuid4().hex},
    )
    assert result.status_code == 202, result.text
    job_id = result.json()["id"]
    with DB() as db:
        assert worker.claim(db) == job_id
    worker.process(job_id)
    with DB() as db:
        job = db.get(Job, job_id)
        assert job.status == "completed"
        child = db.get(Child, demo["child_id"])
        unit = db.get(LearningUnit, job.result["unit_id"])
        assert unit.synthetic and unit.provider == "synthetic" and unit.model == "fixed-fractions-v1"
        if parent_grant and child_grant:
            from schulpilot.source_lineage import learning_source

            assert ready.authority(db, job, child)
            refs = list(db.scalars(select(UnitSource).where(UnitSource.unit_id == unit.id)))
            assert len(refs) == 1 and refs[0].material_id == unit.material_id
            assert unit.assignment_id is None and unit.review_of is None and unit.school_day_id is None
            src = db.get(Material, demo["material_id"])
            assert src.synthetic and src.confirmed and src.revision == refs[0].revision
            assert learning_source(db, src)["content"], learning_source(db, src)
            from schulpilot.visual_reference_models import UnitVisualSnapshot
            from schulpilot.visual_references import projection

            if db.get(UnitVisualSnapshot, unit.id) is not None:
                assert projection(db, unit)["explanation_visual_status"] == "ready", projection(db, unit)
            assert ready.valid_unit(db, unit, child), (
                unit.round_kind,
                unit.material_id,
                unit.school_day_id,
                db.get(Material, demo["material_id"]).path,
                db.get(Material, demo["material_id"]).fixture_id,
                learning_source(db, db.get(Material, demo["material_id"])),
                list(db.scalars(select(UnitSource).where(UnitSource.unit_id == unit.id))),
            )
            assert ready.valid_job_unit(db, job, unit, child), job.payload
        return demo, job_id, unit.id, child.user_id


def child_client(demo):
    client = TestClient(app, headers=HEADERS)
    client.__enter__()
    login = client.post(
        "/api/auth/login",
        json={"username": demo["credentials"]["child_username"], "password": demo["credentials"]["child_password"]},
    )
    assert login.status_code == 200
    client.headers["Authorization"] = "Bearer " + login.json()["token"]
    return client


def test_granted_demo_round_emits_one_real_bound_receipt_and_neutral_push(api, tmp_path, monkeypatch):
    enable(tmp_path)
    demo, job_id, unit_id, _ = make_demo(api)
    client = child_client(demo)
    sent = []
    monkeypatch.setattr(notifications, "send_fcm", lambda *args, **kwargs: sent.append((args, kwargs)))
    try:
        event = next(x for x in client.get("/api/notifications/inbox").json()["items"] if x["kind"] == "round_ready")
        assert event["route"] == "/unit/" + unit_id
        dev = device(client)
        with DB.begin() as db:
            notifications.prepare(db)
            notifications.prepare(db)
        assert notifications.deliver_one(DB)
        assert not notifications.deliver_one(DB)
        assert len(sent) == 1 and sent[0][1] == {"unit_path": "/unit/" + unit_id}
        assert CONTENT not in str(sent)
        with DB() as db:
            assert db.scalar(select(func.count()).select_from(Message).where(Message.kind == ready.KIND)) == 1
            rows = list(db.scalars(select(PushDelivery)))
            assert len(rows) == 1 and rows[0].status == "accepted" and rows[0].device_id == dev["id"]
            assert db.get(Job, job_id).result == {"unit_id": unit_id}
            assert db.get(LearningUnit, unit_id).status == "not_started"
            assert db.scalar(select(func.count()).select_from(Attempt)) == 0
    finally:
        client.__exit__(None, None, None)


@pytest.mark.parametrize("parent_grant,child_grant", [(False, True), (True, False), (False, False)])
def test_demo_notice_requires_both_requester_and_child_grants_at_creation(api, parent_grant, child_grant):
    _, job_id, _, _ = make_demo(api, parent_grant=parent_grant, child_grant=child_grant)
    with DB.begin() as db:
        assert not ready.remember(db, db.get(Job, job_id))
        assert db.scalar(select(func.count()).select_from(Message).where(Message.kind == ready.KIND)) == 0


@pytest.mark.parametrize(
    "change",
    [
        "child_grant",
        "parent_grant",
        "parent_session",
        "child_session",
        "source_revision",
        "source_unconfirmed",
        "child_consent",
        "device_category",
        "child_quiet",
        "device_quiet",
        "unit_started",
        "family_expired",
    ],
)
def test_demo_push_rechecks_grants_authority_and_device_before_send(api, tmp_path, monkeypatch, change):
    enable(tmp_path)
    demo, job_id, unit_id, child_user_id = make_demo(api)
    client = child_client(demo)
    try:
        dev_id = device(client)["id"]
        with DB.begin() as db:
            notifications.prepare(db)
            assert db.scalar(select(func.count()).select_from(PushDelivery)) == 1
        with DB.begin() as db:
            child = db.get(Child, demo["child_id"])
            dev = db.get(PushDevice, dev_id)
            job = db.get(Job, job_id)
            if change in ("child_grant", "parent_grant"):
                user_id = child_user_id if change == "child_grant" else demo["user"]["id"]
                db.delete(db.get(PushTestGrant, user_id))
            elif change == "parent_session":
                db.get(Session, job.payload[ready.ORIGIN]["session_id"]).revoked = True
            elif change == "child_session":
                db.get(Session, dev.session_id).revoked = True
            elif change == "source_revision":
                db.get(Material, demo["material_id"]).revision += 1
            elif change == "source_unconfirmed":
                db.get(Material, demo["material_id"]).confirmed = False
            elif change == "child_consent":
                child.preferences = {**child.preferences, "push_consent": False}
            elif change == "device_category":
                dev.reminders = False
            elif change in ("child_quiet", "device_quiet"):
                from datetime import datetime, timezone

                hour = datetime.fromtimestamp(now(), timezone.utc).hour
                if change == "child_quiet":
                    child.preferences = {
                        **child.preferences,
                        "timezone": "UTC",
                        "quiet_start": hour,
                        "quiet_end": (hour + 1) % 24,
                    }
                else:
                    dev.timezone, dev.quiet_start, dev.quiet_end = "UTC", hour, (hour + 1) % 24
            elif change == "unit_started":
                db.get(LearningUnit, unit_id).status = "active"
            else:
                db.get(Family, child.family_id).expires = int(now()) - 1
        sent = []
        monkeypatch.setattr(notifications, "send_fcm", lambda *a, **kw: sent.append((a, kw)))
        assert notifications.deliver_one(DB)
        assert not sent
        with DB() as db:
            assert db.scalar(select(PushDelivery)).status == "suppressed"
    finally:
        client.__exit__(None, None, None)


@pytest.mark.parametrize(
    "change",
    [
        "unit_provider",
        "unit_model",
        "unit_label",
        "family_label",
        "source_label",
        "source_fixture",
        "source_photo",
        "extra_source",
        "job_source",
        "job_kind",
        "unit_review",
        "unit_assignment",
        "unit_day",
        "unit_round_kind",
    ],
)
def test_demo_event_never_guesses_origin_or_source(api, change):
    demo, job_id, unit_id, _ = make_demo(api)
    with DB() as db:
        child = db.get(Child, demo["child_id"])
        unit, job, source = db.get(LearningUnit, unit_id), db.get(Job, job_id), db.get(Material, demo["material_id"])
        if change == "unit_provider":
            unit.provider = "openrouter"
        elif change == "unit_model":
            unit.model = "unapproved"
        elif change == "unit_label":
            unit.synthetic = False
        elif change == "family_label":
            db.get(Family, child.family_id).synthetic = False
        elif change == "source_label":
            source.synthetic = False
        elif change == "source_fixture":
            source.fixture_id = "fractions-v1"
        elif change == "source_photo":
            source.path = "synthetic.jpg"
        elif change == "extra_source":
            extra = Material(
                child_id=child.id,
                title="Another synthetic source",
                confirmed=True,
                synthetic=True,
                content=CONTENT,
                subject="Mathematik",
                topic="Brüche",
                status="confirmed",
            )
            db.add(extra)
            db.flush()
            db.add(UnitSource(unit_id=unit.id, material_id=extra.id, revision=extra.revision))
            db.flush()
        elif change == "job_source":
            job.payload = {**job.payload, "material_id": "a" * 32}
        elif change == "job_kind":
            job.kind = "coach_practice"
        elif change == "unit_review":
            unit.review_of = "a" * 32
        elif change == "unit_assignment":
            unit.assignment_id = "a" * 32
        elif change == "unit_day":
            unit.school_day_id = "a" * 32
        else:
            unit.round_kind = "spaced_review"
        # Inspect without committing fabricated foreign-key references.
        with db.no_autoflush:
            assert ready.events_for_child(db, child, int(now())) == []
        db.rollback()


@pytest.mark.parametrize("variant", [0, 1, 2])
def test_demo_visual_is_a_labelled_example_and_never_replaces_answers(variant):
    from schulpilot.synthetic import sample_unit, with_demo_visuals
    from schulpilot.visual_references import public_steps

    data = sample_unit(variant)
    payload = {
        "visual_context": {
            "required": True,
            "sources": [{"ref": "p1", "subject": "Mathematik", "group_id": None, "content": CONTENT}],
            "references": [{"id": "math.fraction.part_whole", "version": 1, "subject": "Mathematik"}],
        }
    }
    result = with_demo_visuals(data, payload)
    assert "explanation_steps" not in data
    assert [q["answer"] for q in data["questions"]] == [q["answer"] for q in result["questions"]]
    for step in [*result["explanation_steps"], *(q["explanation_steps"][0] for q in result["questions"])]:
        assert "Beispiel aus dem Demoheft" in step["text"]
        assert "Beispiel aus dem Demoheft" in step["presentation"]["blocks"][0]["title"]
        assert step["presentation"]["blocks"][0]["numbers"] == [2, 4]
    for question in result["questions"]:
        assert question["explanation_steps"][0]["disclosure"] == "solution"
        assert public_steps(question["explanation_steps"], closed=False, hints=3) == []
    missing = {"visual_context": {**payload["visual_context"], "sources": []}}
    assert with_demo_visuals(data, missing) == data


def test_demo_grant_never_overrides_production_push_stop(api, tmp_path, monkeypatch):
    from schulpilot.config import settings

    enable(tmp_path)
    demo, _, _, _ = make_demo(api)
    client = child_client(demo)
    try:
        device(client)
        # The grant is present but ordinary completion notices are production
        # traffic and must not switch to the special direct-test sender.
        object.__setattr__(settings, "push_approved", False)
        with DB.begin() as db:
            notifications.prepare(db)
            assert db.scalar(select(func.count()).select_from(PushDelivery)) == 0
        assert not notifications.deliver_one(DB)
    finally:
        client.__exit__(None, None, None)


def test_revoking_production_push_after_queue_prevents_fcm_send(api, tmp_path, monkeypatch):
    from schulpilot.config import settings

    enable(tmp_path)
    demo, _, _, _ = make_demo(api)
    client = child_client(demo)
    try:
        device(client)
        with DB.begin() as db:
            notifications.prepare(db)
            assert db.scalar(select(func.count()).select_from(PushDelivery)) == 1
        object.__setattr__(settings, "push_approved", False)

        def network_forbidden(*args, **kwargs):
            raise AssertionError("provider network must not be reached after revocation")

        monkeypatch.setattr(notifications.httpx, "Client", network_forbidden)
        assert notifications.deliver_one(DB)
        with DB() as db:
            delivery = db.scalar(select(PushDelivery))
            assert delivery.status == "failed" and delivery.error_code == "NOT_CONFIGURED"
    finally:
        client.__exit__(None, None, None)
