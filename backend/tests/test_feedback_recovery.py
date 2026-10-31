"""Explicit, child-scoped recovery of unread legacy feedback markers."""

import pytest
from conftest import HEADERS, create_child
from fastapi.testclient import TestClient
from schulpilot.db import DB, Activity, Attempt, Job, LearningMemory, LearningUnit, Material, UnitSource, Usage
from schulpilot.learning_controller import source_state
from schulpilot.main import app
from sqlalchemy import func, select

pytest_plugins = ("test_guided_feedback",)


@pytest.mark.parametrize("invalid", [None, "legacy", [], ["bad"], 0, {"attempt_id": []}, {"attempt_id": {}}])
def test_recovery_ignores_broken_legacy_marker_details_without_losing_them(guided, invalid):
    kid, _, child_id, uid, questions = guided
    first, second = "1" * 32, "2" * 32
    with DB.begin() as db:
        for index, attempt_id in enumerate((first, second)):
            db.add(Attempt(id=attempt_id, unit_id=uid, question_id=questions[index]["id"], answer="synthetic",
                           outcome="incorrect", assisted=False, created=101,
                           evaluation={"attempt_number": 1}))
            db.add(Activity(child_id=child_id, unit_id=uid, kind="feedback_pending", detail={"attempt_id": attempt_id}))
        db.add_all([
            Activity(child_id=child_id, unit_id=uid, kind="feedback_pending", detail=invalid),
            Activity(child_id=child_id, unit_id=uid, kind="feedback_seen", detail=invalid),
            Activity(child_id=child_id, unit_id=uid, kind="feedback_exposure", detail=invalid),
        ])
    detail = kid.get(f"/api/units/{uid}")
    assert detail.status_code == 200
    assert detail.json()["feedback_recovery_available"] is True
    listed = kid.get(f"/api/units/{uid}/feedback/recovery")
    assert listed.status_code == 200
    assert {item["attempt_id"] for item in listed.json()["items"]} == {first, second}
    result = kid.post(f"/api/units/{uid}/feedback/recovery/acknowledge", json={"attempt_id": second})
    assert result.status_code == 200, result.text
    assert [item["attempt_id"] for item in kid.get(f"/api/units/{uid}/feedback/recovery").json()["items"]] == [first]
    with DB() as db:
        events = list(db.scalars(select(Activity).where(Activity.unit_id == uid)))
        assert sum(e.kind == "feedback_pending" and e.detail == invalid for e in events) == 1
        assert sum(e.kind == "feedback_seen" and e.detail == invalid for e in events) == 1
        assert sum(e.kind == "feedback_exposure" and e.detail == invalid for e in events) == 1
        assert sum(e.kind == "feedback_seen" and e.detail == {"attempt_id": second} for e in events) == 1
    # A corrupt older exposure record must not prevent recording an actual
    # disclosure when the currently displayed answer needs it.
    from schulpilot.learning import record_feedback_exposure

    with DB.begin() as db:
        record_feedback_exposure(db, db.get(LearningUnit, uid), db.get(Attempt, second), "visual")
    with DB() as db:
        exposures = list(db.scalars(select(Activity).where(Activity.unit_id == uid, Activity.kind == "feedback_exposure")))
        assert sum(e.detail == invalid for e in exposures) == 1
        assert sum(e.detail == {"attempt_id": second, "question_id": questions[1]["id"], "surface": "visual"}
                   for e in exposures) == 1


def test_recovery_unblocks_a_visible_legacy_tie_without_changing_the_old_contract(guided):
    kid, _, child_id, uid, questions = guided
    with DB.begin() as db:
        db.add_all([
            Attempt(id="e" * 32, unit_id=uid, question_id=questions[0]["id"], answer="first",
                    outcome="incorrect", assisted=False, created=100, evaluation={"attempt_number": 1}),
            Attempt(id="0" * 32, unit_id=uid, question_id=questions[0]["id"], answer="second",
                    outcome="incorrect", assisted=True, created=101, evaluation={"attempt_number": 2}),
            Attempt(id="f" * 32, unit_id=uid, question_id=questions[1]["id"], answer="other",
                    outcome="incorrect", assisted=False, created=101, evaluation={"attempt_number": 1}),
            Activity(child_id=child_id, unit_id=uid, kind="feedback_pending", detail={"attempt_id": "0" * 32}),
        ])
    detail = kid.get(f"/api/units/{uid}").json()
    assert detail["pending_feedback"]["attempt_id"] == "0" * 32
    assert detail["feedback_recovery_available"] is True
    # Older clients still encounter their documented 409; the new path does
    # not silently redefine that acknowledgement as chronological proof.
    assert kid.post(f"/api/units/{uid}/feedback/acknowledge", json={"attempt_id": "0" * 32}).status_code == 409
    listed = kid.get(f"/api/units/{uid}/feedback/recovery").json()["items"]
    assert [item["attempt_id"] for item in listed] == ["0" * 32]
    assert kid.post(f"/api/units/{uid}/feedback/recovery/acknowledge", json={"attempt_id": "0" * 32}).status_code == 200
    assert kid.get(f"/api/units/{uid}").json()["pending_feedback"] is None
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Attempt).where(Attempt.unit_id == uid)) == 3
        assert db.scalar(select(func.count()).select_from(Activity).where(Activity.kind == "feedback_seen")) == 1


def test_unordered_markers_can_be_reviewed_individually_without_new_evidence(guided, monkeypatch):
    kid, _, child_id, uid, questions = guided
    ids = ["0" * 32, "f" * 32]
    with DB.begin() as db:
        for index, attempt_id in enumerate(ids):
            db.add(Attempt(id=attempt_id, unit_id=uid, question_id=questions[index]["id"], answer="synthetic",
                           outcome="incorrect", assisted=False, created=101,
                           evaluation={"attempt_number": 1, "reason": "Do not reveal a solution here"}))
            db.add(Activity(child_id=child_id, unit_id=uid, kind="feedback_pending", detail={"attempt_id": attempt_id}))
    monkeypatch.setattr("schulpilot.providers.request_provider", lambda *a, **kw: (_ for _ in ()).throw(
        AssertionError("Recovery must not invoke the provider")))
    detail = kid.get(f"/api/units/{uid}").json()
    assert detail["supports_feedback_recovery"] and detail["feedback_recovery_available"]
    recovery = kid.get(f"/api/units/{uid}/feedback/recovery").json()
    assert {item["attempt_id"] for item in recovery["items"]} == set(ids)
    assert all("explanation" not in item and "reason" not in item for item in recovery["items"])
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Activity).where(Activity.kind == "feedback_seen")) == 0
    for attempt_id in ids:
        ack = kid.post(f"/api/units/{uid}/feedback/recovery/acknowledge", json={"attempt_id": attempt_id})
        assert ack.status_code == 200, ack.text
        assert kid.post(f"/api/units/{uid}/feedback/recovery/acknowledge", json={"attempt_id": attempt_id}).status_code == 200
    assert kid.get(f"/api/units/{uid}/feedback/recovery").json()["items"] == []
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Attempt).where(Attempt.unit_id == uid)) == 2
        assert db.scalar(select(func.count()).select_from(Activity).where(Activity.kind == "feedback_pending")) == 2
        assert db.scalar(select(func.count()).select_from(Activity).where(Activity.kind == "feedback_seen")) == 2
        assert db.scalar(select(func.count()).select_from(Job)) == 0
        assert db.scalar(select(func.count()).select_from(Usage)) == 0


def test_recovery_requires_own_child_and_exact_unit(guided, household):
    kid, parent, child_id, uid, questions = guided
    user, _ = household
    other = create_child(parent, user, username="other-child")
    attempt_id = "1" * 32
    with DB.begin() as db:
        db.add(Attempt(id=attempt_id, unit_id=uid, question_id=questions[0]["id"], answer="synthetic",
                       outcome="incorrect", assisted=False, created=101, evaluation={"attempt_number": 1}))
        db.add(Activity(child_id=child_id, unit_id=uid, kind="feedback_pending", detail={"attempt_id": attempt_id}))
        wrong_unit = LearningUnit(child_id=child_id, questions=questions, subject="Mathematik", topic="Test",
                                  explanation="Test", provider="fixture", synthetic=True)
        db.add(wrong_unit)
        db.flush()
        other_unit_id = wrong_unit.id
    assert kid.post(f"/api/units/{other_unit_id}/feedback/recovery/acknowledge", json={"attempt_id": attempt_id}).status_code == 404
    assert kid.post(f"/api/units/{uid}/feedback/recovery/acknowledge", json={"attempt_id": "2" * 32}).status_code == 404
    assert parent.get(f"/api/units/{uid}/feedback/recovery").status_code == 403
    with TestClient(app, headers=HEADERS) as sibling:
        login = sibling.post("/api/auth/login", json={"username": "other-child", "password": "secure-child-pass-123"})
        sibling.headers["Authorization"] = "Bearer " + login.json()["token"]
        assert other["id"] != child_id
        assert sibling.get(f"/api/units/{uid}/feedback/recovery").status_code in (403, 404)
        assert sibling.post(f"/api/units/{uid}/feedback/recovery/acknowledge", json={"attempt_id": attempt_id}).status_code in (403, 404)


def test_recovery_pages_unread_markers_without_changing_them(guided):
    kid, _, child_id, uid, questions = guided
    ids = [f"{index + 1:032x}" for index in range(23)]
    with DB.begin() as db:
        for index, attempt_id in enumerate(ids):
            db.add(Attempt(id=attempt_id, unit_id=uid, question_id=questions[index % len(questions)]["id"],
                           answer="synthetic", outcome="incorrect", assisted=False,
                           created=200 - index, evaluation={"attempt_number": 1}))
            db.add(Activity(child_id=child_id, unit_id=uid, kind="feedback_pending", detail={"attempt_id": attempt_id}))
    cursor = None
    returned = []
    page_sizes = []
    while True:
        response = kid.get(f"/api/units/{uid}/feedback/recovery", params={"after": cursor} if cursor else None)
        assert response.status_code == 200
        page = response.json()
        returned.extend(item["attempt_id"] for item in page["items"])
        page_sizes.append(len(page["items"]))
        cursor = page["next_after"]
        if cursor is None:
            break
    # Stable traversal only; the intentionally reversed timestamps demonstrate
    # that the ordering does not claim when answers were submitted.
    assert returned == ids
    assert page_sizes == [10, 10, 3]
    assert kid.get(f"/api/units/{uid}/feedback/recovery", params={"after": "bad"}).status_code == 422
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Activity).where(Activity.kind == "feedback_seen")) == 0


def test_two_devices_acknowledge_one_marker_only_once(guided):
    from concurrent.futures import ThreadPoolExecutor

    kid, _, child_id, uid, questions = guided
    first, second = "1" * 32, "2" * 32
    with DB.begin() as db:
        for index, attempt_id in enumerate((first, second)):
            db.add(Attempt(id=attempt_id, unit_id=uid, question_id=questions[index]["id"], answer="synthetic",
                           outcome="incorrect", assisted=False, created=101,
                           evaluation={"attempt_number": 1}))
            db.add(Activity(child_id=child_id, unit_id=uid, kind="feedback_pending", detail={"attempt_id": attempt_id}))
    authorization = kid.headers["Authorization"]

    def acknowledge(_):
        with TestClient(app, headers={**HEADERS, "Authorization": authorization}) as device:
            return device.post(f"/api/units/{uid}/feedback/recovery/acknowledge", json={"attempt_id": first}).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(acknowledge, range(2))) == [200, 200]
    assert [item["attempt_id"] for item in kid.get(f"/api/units/{uid}/feedback/recovery").json()["items"]] == [second]
    with DB() as db:
        seen = list(db.scalars(select(Activity).where(Activity.unit_id == uid, Activity.kind == "feedback_seen")))
        assert [e.detail["attempt_id"] for e in seen] == [first]


def test_recovery_of_final_marker_finishes_deferred_round_without_provider_job(guided, monkeypatch):
    from schulpilot import coaching
    from schulpilot.synthetic import CONTENT

    kid, _, child_id, uid, questions = guided
    assert len(questions) >= 2
    ids = [f"{index + 1:032x}" for index in range(len(questions))]
    with DB.begin() as db:
        unit = db.get(LearningUnit, uid)
        material = Material(child_id=child_id, title="Künstliche Testseite", status="confirmed", confirmed=True,
                            synthetic=True, subject="Mathematik", topic="Brüche", content=CONTENT)
        db.add(material)
        db.flush()
        unit.material_id = material.id
        db.add(UnitSource(unit_id=uid, material_id=material.id, revision=material.revision))
        for index, q in enumerate(questions):
            db.add(Attempt(id=ids[index], unit_id=uid, question_id=q["id"], answer="synthetic",
                           outcome="incorrect" if index == 0 else "correct", assisted=False,
                           created=101 + index, evaluation={"attempt_number": 1}))
            db.add(Activity(child_id=child_id, unit_id=uid, kind="feedback_pending", detail={"attempt_id": ids[index]}))
        db.flush()
        signature, valid, _ = source_state(db, unit)
        assert valid
        db.add(LearningMemory(unit_id=uid, child_id=child_id, source_signature=signature,
                              working={"instructional_deferrals": {"source_signature": signature,
                                                                  "question_ids": [questions[0]["id"]]}}, decision={}))
    review_requests = []
    original_schedule = coaching.schedule

    def track_review(unit_id, **kwargs):
        review_requests.append((unit_id, kwargs))
        return original_schedule(unit_id, **kwargs)

    monkeypatch.setattr("schulpilot.coaching.schedule", track_review)
    # Deliberately acknowledge the timestamp-latest response first: an older
    # unread marker must still remain reachable and prevent final completion.
    for index, attempt_id in enumerate(reversed(ids)):
        result = kid.post(f"/api/units/{uid}/feedback/recovery/acknowledge", json={"attempt_id": attempt_id})
        assert result.status_code == 200, result.text
        if index == 0:
            assert result.json()["completed"] is False
            assert kid.get(f"/api/units/{uid}").json()["status"] == "active"
            assert {item["attempt_id"] for item in kid.get(f"/api/units/{uid}/feedback/recovery").json()["items"]} == set(ids[:-1])
    assert result.json()["completed"] is True
    detail = kid.get(f"/api/units/{uid}").json()
    assert detail["status"] == "completed" and detail["pending_feedback"] is None
    assert not review_requests
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Attempt).where(Attempt.unit_id == uid)) == len(ids)
        assert db.scalar(select(func.count()).select_from(Job)) == 0
        assert db.scalar(select(func.count()).select_from(Usage)) == 0
    # The existing review endpoint remains available by deliberate action.
    review = kid.post(f"/api/units/{uid}/coaching")
    assert review.status_code == 200, review.text
    assert review.json()["status"] == "ready"
    assert review_requests == [(uid, {})]
