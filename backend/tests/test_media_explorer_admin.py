"""Synthetic editorial decisions; no media fetches or learner contents."""
from concurrent.futures import ThreadPoolExecutor

import pytest
from conftest import HEADERS
from fastapi.testclient import TestClient
from schulpilot.curriculum_models import CurriculumTopic
from schulpilot.db import DB, Audit, Job, Session, Subject, User, now
from schulpilot.main import app
from schulpilot.media_explorer_models import MediaCurriculumLink, MediaEditorialReview, MediaResource
from schulpilot.media_explorer_policy import select_for_topic
from schulpilot.security import digest
from sqlalchemy import func, select
from test_codex_models import operator as operator_fixture

MEDIA_ID = "a" * 32
PATH = "/api/admin/media-explorer/" + MEDIA_ID


@pytest.fixture
def operator():
    yield from operator_fixture.__wrapped__()


@pytest.fixture
def candidate():
    with DB.begin() as db:
        db.add(MediaResource(id=MEDIA_ID, provider="youtube", provider_id="Abcdefgh_12", title="Künstliches Medium",
            channel="Testquelle", url="https://www.youtube.com/watch?v=Abcdefgh_12", checked_region="DE",
            available=True, checked_at=int(now()), revision=1))
    return MEDIA_ID


def decision(**changes):
    return {"resource_revision": 1, "previous_review": 0, "decision": "approved",
            "evidence_scope": "content", "content_kind": "general", "min_age": 10,
            "content_reviewed": True, **changes}


def test_review_is_revision_bound_audited_and_read_only_on_get(operator, candidate):
    with DB() as db:
        before_jobs = db.scalar(select(func.count()).select_from(Job))
        before_audit = db.scalar(select(func.count()).select_from(Audit))
    assert operator.get(PATH).json()["review"] is None
    assert operator.get("/api/admin/media-explorer").json()["items"][0]["id"] == candidate
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Job)) == before_jobs
        assert db.scalar(select(func.count()).select_from(Audit)) == before_audit
    result = operator.post(PATH + "/decisions", json=decision())
    assert result.status_code == 200, result.text
    assert result.json()["review"]["review_number"] == 1
    assert result.json()["review"]["evidence_scope"] == "content"
    assert operator.post(PATH + "/decisions", json=decision()).status_code == 409
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(MediaEditorialReview)) == 1
        audit = db.scalar(select(Audit).where(Audit.action == "media.editorial_approved"))
        assert audit and audit.target == candidate + ":1"
        assert db.scalar(select(func.count()).select_from(Job)) == before_jobs
    result = operator.post(PATH + "/decisions", json=decision(previous_review=1, decision="blocked",
                                                                evidence_scope="metadata", content_reviewed=False))
    assert result.status_code == 200
    assert operator.get(PATH).json()["review"]["decision"] == "blocked"


@pytest.mark.parametrize("override", [
    {"content_reviewed": False}, {"evidence_scope": "metadata"},
    {"content_kind": "historical_source"}, {"content_kind": "propaganda", "context": "Einordnung"},
    {"content_kind": "sensitive", "context": "Einordnung"}, {"min_age": True},
])
def test_cannot_approve_without_explicit_content_evidence_or_context(operator, candidate, override):
    assert operator.post(PATH + "/decisions", json=decision(**override)).status_code == 422
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(MediaEditorialReview)) == 0


def test_sensitive_content_needs_context_and_counterpoint(operator, candidate):
    value = decision(content_kind="propaganda", context="Historische Einordnung", counterpoint="Andere Quelle")
    assert operator.post(PATH + "/decisions", json=value).status_code == 200


def test_admin_list_is_bounded_and_uses_stable_cursor(operator, candidate):
    with DB.begin() as db:
        db.add(MediaResource(id="b" * 32, provider="youtube", provider_id="Abcdefgh_13", title="Anderes Medium",
            channel="Testquelle", url="https://www.youtube.com/watch?v=Abcdefgh_13", checked_region="DE",
            available=True, checked_at=int(now()), revision=1))
    first = operator.get("/api/admin/media-explorer?limit=1").json()
    assert [row["id"] for row in first["items"]] == [candidate] and first["next"] == candidate
    second = operator.get("/api/admin/media-explorer", params={"limit": 1, "after": first["next"]}).json()
    assert [row["id"] for row in second["items"]] == ["b" * 32] and second["next"] is None
    assert operator.get("/api/admin/media-explorer?limit=51").status_code == 422


@pytest.mark.parametrize("field,value", [("available", False), ("checked_at", 0),
                                         ("url", "https://evil.example"), ("revision", 2)])
def test_stale_or_invalid_media_cannot_be_approved_but_may_be_blocked(operator, candidate, field, value):
    with DB.begin() as db:
        setattr(db.get(MediaResource, candidate), field, value)
    assert operator.post(PATH + "/decisions", json=decision()).status_code == 409
    assert operator.post(PATH + "/decisions", json=decision(resource_revision=2 if field == "revision" else 1,
        decision="blocked", evidence_scope="metadata", content_reviewed=False)).status_code == 200


def test_parent_child_anonymous_and_cross_site_cannot_administer(operator, candidate, api, household):
    assert api.get(PATH).status_code == 403
    assert api.post(PATH + "/decisions", json=decision()).status_code == 403
    login = api.post("/api/auth/login", json={"username": "test-child", "password": "secure-child-pass-123"})
    assert login.status_code == 200
    api.headers["Authorization"] = "Bearer " + login.json()["token"]
    assert api.get(PATH).status_code == 403
    assert api.post(PATH + "/decisions", json=decision()).status_code == 403
    with TestClient(app) as anonymous:
        assert anonymous.get(PATH).status_code == 401
    with TestClient(app, headers={"Authorization": "Bearer synthetic-catalog-session"}) as no_header:
        assert no_header.post(PATH + "/decisions", json=decision()).status_code == 403
    with TestClient(app, headers={**HEADERS, "Authorization": "Bearer synthetic-catalog-session",
                                  "Origin": "https://evil.example"}) as cross_site:
        assert cross_site.post(PATH + "/decisions", json=decision()).status_code == 403
    with DB.begin() as db:
        user = db.scalar(select(User).where(User.username == "catalog-operator"))
        db.scalar(select(Session).where(Session.user_id == user.id)).revoked = True
    assert operator.post(PATH + "/decisions", json=decision()).status_code == 401


def test_later_block_immediately_removes_a_previously_approved_resource(operator, candidate):
    with DB.begin() as db:
        topic = next(row for row in db.scalars(select(CurriculumTopic).order_by(CurriculumTopic.id))
                     if row.data.get("grade_kind") in ("exact", "band") and row.data.get("grades"))
        grade = topic.data["grades"][0]
        assert db.get(Subject, topic.subject_id).owner_family_id is None
        db.get(MediaResource, candidate).checked_region = topic.state_code[:2]
        db.add(MediaCurriculumLink(resource_id=candidate, topic_id=topic.id, topic_digest=topic.digest,
                                   level_kind="klasse", min_level=grade, max_level=grade))
        args = dict(topic_id=topic.id, subject_id=topic.subject_id, state_code=topic.state_code,
                    school_form_id=topic.school_form_id, level_kind="klasse", level_number=grade, age=12)
    assert operator.post(PATH + "/decisions", json=decision()).status_code == 200
    with DB() as db:
        assert [row["id"] for row in select_for_topic(db, **args)] == [candidate]
    assert operator.post(PATH + "/decisions", json=decision(previous_review=1, decision="blocked",
        evidence_scope="metadata", content_reviewed=False)).status_code == 200
    with DB() as db:
        assert select_for_topic(db, **args) == []


def test_parallel_decisions_cannot_both_use_the_same_previous_review(operator, candidate):
    with DB.begin() as db:
        other = User(username="second-editor", display_name="Zweite Redaktion", role="admin", verified=True,
                     password_hash="synthetic-no-login")
        db.add(other)
        db.flush()
        db.add(Session(user_id=other.id, token_hash=digest("other-synthetic-session"), device="test",
                       expires=int(now()) + 1000))
    def send(token):
        with TestClient(app, headers={**HEADERS, "Authorization": "Bearer " + token}) as client:
            return client.post(PATH + "/decisions", json=decision()).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(send, ["synthetic-catalog-session", "other-synthetic-session"])) == [200, 409]
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(MediaEditorialReview)) == 1
