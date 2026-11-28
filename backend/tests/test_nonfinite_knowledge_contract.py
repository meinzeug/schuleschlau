"""Synthetic reproduction of the source-bound timestamp contract gap."""
import copy
import math

import pytest
from conftest import HEADERS, create_child
from fastapi.testclient import TestClient
from schulpilot import competences
from schulpilot.competence_models import QuestionCompetence
from schulpilot.db import DB, Attempt, LearningUnit, Material, UnitSource
from schulpilot.main import app
from sqlalchemy import select
from test_adaptive_plan import fraction_profile as fraction_profile


@pytest.mark.parametrize("stamp", [float("inf"), float("-inf"), float("nan")], ids=["positive-infinity", "negative-infinity", "nan"])
def test_knowledge_read_preserves_original_evidence_even_on_error(fraction_profile, stamp):
    client, uid, _, _, _, _ = fraction_profile
    with DB.begin() as db:
        if math.isnan(stamp) and db.bind.dialect.name == "sqlite":
            pytest.skip("SQLite converts NaN to NULL, which Attempt.created disallows")
        attempt = Attempt(unit_id=uid, question_id="sum", answer="synthetic", outcome="correct", assisted=False,
                          evaluation={"attempt_number": 1}, created=stamp)
        db.add(attempt)
        db.flush()
        attempt_id = attempt.id
    client.get(f"/api/units/{uid}/learning-session/knowledge")
    with DB() as db:
        original = db.scalar(select(Attempt).where(Attempt.id == attempt_id))
        assert original.answer == "synthetic" and original.outcome == "correct" and not original.assisted
        assert original.evaluation == {"attempt_number": 1}
        assert math.isnan(original.created) if math.isnan(stamp) else original.created == stamp


@pytest.mark.parametrize("stamp", [float("inf"), float("-inf"), float("nan")], ids=["positive-infinity", "negative-infinity", "nan"])
def test_knowledge_must_not_promote_unknown_timestamp(fraction_profile, stamp):
    client, uid, _, _, _, _ = fraction_profile
    with DB.begin() as db:
        if math.isnan(stamp) and db.bind.dialect.name == "sqlite":
            pytest.skip("SQLite converts NaN to NULL, which Attempt.created disallows")
        attempt = Attempt(unit_id=uid, question_id="sum", answer="synthetic", outcome="correct", assisted=False,
                          evaluation={"attempt_number": 1}, created=stamp)
        db.add(attempt)
        db.flush()
        attempt_id = attempt.id
    response = client.get(f"/api/units/{uid}/learning-session/knowledge")
    with DB() as db:
        original = db.scalar(select(Attempt).where(Attempt.id == attempt_id))
        assert original.answer == "synthetic" and original.outcome == "correct" and not original.assisted
        assert math.isnan(original.created) if math.isnan(stamp) else original.created == stamp
    assert response.status_code == 200, response.text
    goals = response.json()["long_term"]
    assert any(goal["attempts"] for goal in goals)
    assert all(goal["independent"] == 0 and not goal["successful_check_dates"] for goal in goals)
    competencies = response.json()["competences"]
    assert any(item["attempts"] for item in competencies)
    assert all(item["independent"] == 0 and not item["successful_check_dates"] for item in competencies)


@pytest.mark.parametrize("assisted", [True, False])
def test_unknown_attempt_does_not_erase_other_question_or_recorded_help(fraction_profile, assisted):
    client, uid, _, _, _, _ = fraction_profile
    with DB.begin() as db:
        bad = Attempt(unit_id=uid, question_id="sum", answer="synthetic bad", outcome="correct", assisted=assisted,
                      evaluation={"attempt_number": 1}, created=float("inf"))
        retry = Attempt(unit_id=uid, question_id="sum", answer="synthetic retry", outcome="correct", assisted=False,
                        evaluation={"attempt_number": 2}, created=1700000000)
        good = Attempt(unit_id=uid, question_id="reduce", answer="synthetic good", outcome="correct", assisted=False,
                       evaluation={"attempt_number": 1}, created=1700000100)
        db.add_all([bad, retry, good])
        db.flush()
        bad_id = bad.id
    response = client.get(f"/api/units/{uid}/learning-session/knowledge")
    assert response.status_code == 200, response.text
    goals = {goal["label"]: goal for goal in response.json()["long_term"]}
    addition = goals["Brüche addieren"]
    assert addition["tasks"] == 1 and addition["attempts"] == 2 and addition["uncertain"] == 1
    assert addition["independent"] == 0 and addition["last_observation"] is None
    assert addition["review_due"] is None and not addition["successful_check_dates"]
    assert goals["Brüche kürzen"]["independent"] == 1
    with DB() as db:
        original = db.get(Attempt, bad_id)
        assert original.assisted is assisted and original.answer == "synthetic bad" and math.isinf(original.created)


def test_undated_exposure_prevents_same_question_being_new_recall(fraction_profile):
    client, uid, mid, _, _, child = fraction_profile
    with DB.begin() as db:
        root, source = db.get(LearningUnit, uid), db.get(Material, mid)
        db.add(Attempt(unit_id=uid, question_id="sum", answer="synthetic", outcome="incorrect", assisted=True,
                       created=float("inf")))
        check = LearningUnit(child_id=child["id"], material_id=mid, subject=root.subject, topic=root.topic,
                             explanation="Künstliche Wiederholung.", questions=[copy.deepcopy(root.questions[0])],
                             round_kind="spaced_review", provider="synthetic-fixture")
        db.add(check)
        db.flush()
        db.add(UnitSource(unit_id=check.id, material_id=mid, revision=source.revision))
        db.add(Attempt(unit_id=check.id, question_id="sum", answer="synthetic", outcome="correct", assisted=False,
                       created=1700000000))
    response = client.get(f"/api/units/{uid}/learning-session/knowledge")
    assert response.status_code == 200, response.text
    for key in ("long_term", "competences"):
        addition = next(item for item in response.json()[key] if item["attempts"] == 2)
        assert addition["independent"] == 1 and addition["uncertain"] == 1
        assert not addition["successful_check_dates"] and addition["confidence"] != "repeated_recall"


def test_unknown_difficulty_cannot_be_ordered_before_valid_recall_days(fraction_profile):
    client, uid, mid, _, _, child = fraction_profile
    with DB.begin() as db:
        root, source = db.get(LearningUnit, uid), db.get(Material, mid)
        db.add(Attempt(unit_id=uid, question_id="sum", answer="synthetic", outcome="incorrect", assisted=False,
                       created=float("-inf")))
        for index, (days, prompt) in enumerate(((9, "Berechne 2/5 + 1/10."),
                                                (5, "Berechne 1/4 + 1/6."),
                                                (1, "Berechne 1/3 + 1/12."))):
            check = LearningUnit(child_id=child["id"], material_id=mid, subject=root.subject, topic=root.topic,
                                 explanation="Künstliche Wiederholung.",
                                 questions=[dict(root.questions[0], prompt=prompt)], round_kind="spaced_review",
                                 provider="synthetic-fixture")
            db.add(check)
            db.flush()
            db.add(UnitSource(unit_id=check.id, material_id=mid, revision=source.revision))
            db.add(QuestionCompetence(unit_id=check.id, question_id="sum", child_id=child["id"],
                                      competence_id="math.fractions.add_unlike", catalog_version=competences.VERSION,
                                      role="recall", question_digest=competences.question_digest(check.questions[0]),
                                      source_refs=[competences.source_ref(db, source)], reference_ids=[]))
            db.add(Attempt(unit_id=check.id, question_id="sum", answer="synthetic", outcome="correct", assisted=False,
                           created=1701000000 - days * 86400))
    response = client.get(f"/api/units/{uid}/learning-session/knowledge")
    assert response.status_code == 200, response.text
    for key in ("long_term", "competences"):
        matching = [item for item in response.json()[key] if item["attempts"] == 4]
        assert matching, (key, [(item["id"], item["attempts"]) for item in response.json()[key]])
        addition = matching[0]
        assert addition["independent"] == 3 and addition["uncertain"] == 1
        assert len(addition["successful_check_dates"]) == 3
        assert addition["confidence"] != "repeated_recall" and addition["review_due"] is None
        assert addition["last_observation"] is None and addition["last_difficulty"] is None
        assert addition["last_independent_success"] is None


def test_unknown_timestamp_is_confined_to_its_child(fraction_profile, api):
    client, uid, mid, _, parent, _ = fraction_profile
    second = create_child(api, parent, username="synthetic-second-child")
    with DB.begin() as db:
        root, source = db.get(LearningUnit, uid), db.get(Material, mid)
        db.add(Attempt(unit_id=uid, question_id="sum", answer="synthetic", outcome="correct", assisted=False,
                       created=float("inf")))
        other_source = Material(child_id=second["id"], title="Künstliches Blatt", subject=source.subject,
                                topic=source.topic, content=source.content, status="confirmed", confirmed=True)
        db.add(other_source)
        db.flush()
        other = LearningUnit(child_id=second["id"], material_id=other_source.id, subject=root.subject, topic=root.topic,
                             explanation=root.explanation, questions=copy.deepcopy(root.questions),
                             provider="synthetic-fixture")
        db.add(other)
        db.flush()
        db.add(UnitSource(unit_id=other.id, material_id=other_source.id, revision=other_source.revision))
        db.add(Attempt(unit_id=other.id, question_id="sum", answer="synthetic", outcome="correct", assisted=False,
                       created=1700000000))
        other_id = other.id
    with TestClient(app, headers=HEADERS) as other_client:
        login = other_client.post("/api/auth/login", json={"username": "synthetic-second-child",
                                  "password": "secure-child-pass-123"})
        assert login.status_code == 200, login.text
        other_client.headers["Authorization"] = "Bearer " + login.json()["token"]
        assert other_client.get(f"/api/units/{uid}/learning-session/knowledge").status_code in (403, 404)
        assert client.get(f"/api/units/{other_id}/learning-session/knowledge").status_code in (403, 404)
        response = other_client.get(f"/api/units/{other_id}/learning-session/knowledge")
        assert response.status_code == 200, response.text
        for key in ("long_term", "competences"):
            addition = next(item for item in response.json()[key] if item["attempts"])
            assert addition["independent"] == 1 and addition["uncertain"] == 0
