"""Curated media mappings never infer a child's data or constitute a review."""
from concurrent.futures import ThreadPoolExecutor

import pytest
from conftest import HEADERS
from fastapi.testclient import TestClient
from schulpilot.curriculum_models import CurriculumTopic
from schulpilot.db import DB, Activity, Audit, Job, Session, User, now
from schulpilot.main import app
from schulpilot.media_explorer_models import MediaCurriculumLink, MediaEditorialReview, MediaResource
from schulpilot.media_explorer_policy import select_for_topic
from schulpilot.security import digest
from sqlalchemy import func, select
from test_codex_models import operator as operator_fixture


@pytest.fixture
def operator():
    yield from operator_fixture.__wrapped__()


@pytest.fixture
def source():
    with DB.begin() as db:
        topic = next(row for row in db.scalars(select(CurriculumTopic).order_by(CurriculumTopic.id))
                     if row.data.get("grade_kind") in ("exact", "band") and row.data.get("grades"))
        grade = topic.data["grades"][0]
        medium = MediaResource(id="a" * 32, provider="youtube", provider_id="Abcdefgh_12",
            title="Künstliches Medium", channel="Testquelle", url="https://www.youtube.com/watch?v=Abcdefgh_12",
            checked_region=topic.state_code[:2], available=True, checked_at=int(now()), revision=1)
        db.add(medium)
        return {"id": topic.id, "digest": topic.digest, "grade": grade, "subject": topic.subject_id,
                "state": topic.state_code, "form": topic.school_form_id}


def endpoint(source):
    return "/api/admin/media-explorer/" + "a" * 32 + "/topics/" + source["id"]


def assignment(source, **override):
    return {"resource_revision": 1, "topic_digest": source["digest"],
            "min_level": source["grade"], "max_level": source["grade"], **override}


def test_explicit_mapping_is_idempotent_audited_and_does_not_approve(operator, source):
    url = endpoint(source)
    with DB() as db:
        jobs = db.scalar(select(func.count()).select_from(Job))
        activities = db.scalar(select(func.count()).select_from(Activity))
    preview = operator.get(url)
    assert preview.status_code == 200
    assert preview.json()["topic_digest"] == source["digest"]
    assert preview.json()["grades"] and preview.json()["assignment"] is None
    assert operator.post(url, json=assignment(source)).json()["created"] is True
    assert operator.post(url, json=assignment(source)).json()["created"] is False
    listing = operator.get("/api/admin/media-explorer/" + "a" * 32 + "/topics?limit=1")
    assert listing.status_code == 200 and listing.json()["items"][0]["topic_id"] == source["id"]
    assert listing.json()["next"] is None
    assert operator.get("/api/admin/media-explorer/" + "a" * 32 + "/topics?limit=51").status_code == 422
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(MediaCurriculumLink)) == 1
        assert db.scalar(select(func.count()).select_from(MediaEditorialReview)) == 0
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.action == "media.topic_assigned")) == 1
        assert db.scalar(select(func.count()).select_from(Job)) == jobs
        assert db.scalar(select(func.count()).select_from(Activity)) == activities
        assert select_for_topic(db, topic_id=source["id"], subject_id=source["subject"], state_code=source["state"],
                                school_form_id=source["form"], level_kind="klasse", level_number=source["grade"],
                                age=12) == []
    assert operator.get(url).json()["assignment"]["min_level"] == source["grade"]
    review_url = "/api/admin/media-explorer/" + "a" * 32 + "/decisions"
    review = {"resource_revision": 1, "previous_review": 0, "decision": "approved",
              "evidence_scope": "content", "content_kind": "general", "min_age": 10,
              "content_reviewed": True}
    assert operator.post(review_url, json=review).status_code == 200
    with DB() as db:
        assert [row["id"] for row in select_for_topic(
            db, topic_id=source["id"], subject_id=source["subject"], state_code=source["state"],
            school_form_id=source["form"], level_kind="klasse", level_number=source["grade"], age=12)] == ["a" * 32]
    review.update(previous_review=1, decision="blocked", evidence_scope="metadata", content_reviewed=False)
    assert operator.post(review_url, json=review).status_code == 200
    with DB() as db:
        assert select_for_topic(db, topic_id=source["id"], subject_id=source["subject"], state_code=source["state"],
                                school_form_id=source["form"], level_kind="klasse", level_number=source["grade"],
                                age=12) == []


@pytest.mark.parametrize("override,status", [
    ({"resource_revision": 2}, 409), ({"topic_digest": "b" * 64}, 409),
    ({"min_level": 13, "max_level": 1}, 422), ({"min_level": True}, 422),
    ({"topic_digest": "wrong"}, 422),
])
def test_invalid_or_stale_preview_never_links(operator, source, override, status):
    assert operator.post(endpoint(source), json=assignment(source, **override)).status_code == status
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(MediaCurriculumLink)) == 0


def test_grade_range_must_be_source_bound_and_existing_mapping_is_not_overwritten(operator, source):
    url = endpoint(source)
    assert operator.post(url, json=assignment(source)).status_code == 200
    other = 1 if source["grade"] != 1 else 13
    result = operator.post(url, json=assignment(source, min_level=other, max_level=other))
    assert result.status_code in (409, 422)
    with DB() as db:
        saved = db.get(MediaCurriculumLink, ("a" * 32, source["id"]))
        assert saved.min_level == saved.max_level == source["grade"]


def test_wrong_region_or_changed_topic_fails_closed(operator, source):
    with DB.begin() as db:
        db.get(MediaResource, "a" * 32).checked_region = "US"
    assert operator.post(endpoint(source), json=assignment(source)).status_code == 409
    with DB.begin() as db:
        db.get(MediaResource, "a" * 32).checked_region = source["state"][:2]
        db.get(CurriculumTopic, source["id"]).title = "Nicht belegter anderer Titel"
    assert operator.get(endpoint(source)).status_code == 409
    assert operator.post(endpoint(source), json=assignment(source)).status_code == 409


def test_admin_rights_and_origin_are_required(operator, source, api, household):
    url = endpoint(source)
    assert api.get(url).status_code == 403
    assert api.post(url, json=assignment(source)).status_code == 403
    login = api.post("/api/auth/login", json={"username": "test-child", "password": "secure-child-pass-123"})
    api.headers["Authorization"] = "Bearer " + login.json()["token"]
    assert api.get(url).status_code == 403
    assert api.post(url, json=assignment(source)).status_code == 403
    with TestClient(app) as anonymous:
        assert anonymous.get(url).status_code == 401
    with TestClient(app, headers={**HEADERS, "Authorization": "Bearer synthetic-catalog-session",
                                  "Origin": "https://evil.example"}) as cross_site:
        assert cross_site.post(url, json=assignment(source)).status_code == 403
    with DB.begin() as db:
        user = db.scalar(select(User).where(User.username == "catalog-operator"))
        db.scalar(select(Session).where(Session.user_id == user.id)).revoked = True
    assert operator.get(url).status_code == 401
    assert operator.post(url, json=assignment(source)).status_code == 401


def test_parallel_identical_mapping_is_idempotent(operator, source):
    with DB.begin() as db:
        editor = User(username="mapping-second-editor", display_name="Zweite Redaktion", role="admin", verified=True,
                      password_hash="synthetic-no-login")
        db.add(editor)
        db.flush()
        db.add(Session(user_id=editor.id, token_hash=digest("mapping-second-session"), device="test",
                       expires=int(now()) + 1000))

    def send(token):
        with TestClient(app, headers={**HEADERS, "Authorization": "Bearer " + token}) as client:
            response = client.post(endpoint(source), json=assignment(source))
            return response.status_code, response.json().get("created")

    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(send, ["synthetic-catalog-session", "mapping-second-session"]))
    assert sorted(result) == [(200, False), (200, True)]
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(MediaCurriculumLink)) == 1
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.action == "media.topic_assigned")) == 1
