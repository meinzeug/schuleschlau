"""Explicit revision-bound editorial corrections with synthetic public media."""
from concurrent.futures import ThreadPoolExecutor

import pytest
import test_media_explorer_topic_assignment as shared
from conftest import HEADERS
from fastapi.testclient import TestClient
from schulpilot.curriculum_models import CurriculumTopic
from schulpilot.db import DB, Audit, Session, User, now
from schulpilot.main import app
from schulpilot.media_explorer_models import (
    MediaCurriculumLink,
    MediaCurriculumLinkEvent,
    MediaEditorialReview,
    MediaResource,
)
from schulpilot.media_explorer_policy import select_for_topic
from schulpilot.security import digest
from sqlalchemy import func, select
from test_media_explorer_topic_assignment import assignment, endpoint


@pytest.fixture
def operator():
    yield from shared.operator.__wrapped__()


@pytest.fixture
def source():
    return shared.source.__wrapped__()


def select_resource(source):
    with DB() as db:
        return select_for_topic(db, topic_id=source["id"], subject_id=source["subject"], state_code=source["state"],
            school_form_id=source["form"], level_kind="klasse", level_number=source["grade"], age=12)


def setup_approved(operator, source):
    result = operator.post(endpoint(source), json=assignment(source))
    assert result.status_code == 200 and result.json()["assignment_revision"] == 1
    review = {"resource_revision": 1, "previous_review": 0, "decision": "approved",
              "evidence_scope": "content", "content_kind": "general", "min_age": 10, "content_reviewed": True}
    assert operator.post("/api/admin/media-explorer/" + "a" * 32 + "/decisions", json=review).status_code == 200
    assert [row["id"] for row in select_resource(source)] == ["a" * 32]


def test_remove_restore_keeps_editorial_evidence_and_rejects_stale_or_implicit_restore(operator, source):
    setup_approved(operator, source)
    url = endpoint(source)
    remove = {"resource_revision": 1, "assignment_revision": 1}
    response = operator.post(url + "/remove", json=remove)
    assert response.json() == {"changed": True, "active": False, "assignment_revision": 2}
    assert operator.post(url + "/remove", json={"resource_revision": 1, "assignment_revision": 2}).json() == {
        "changed": False, "active": False, "assignment_revision": 2}
    assert select_resource(source) == []
    assert operator.post(url, json=assignment(source)).status_code == 409
    assert operator.post(url + "/change", json=assignment(source, assignment_revision=1)).status_code == 409
    assert operator.post(url + "/change", json=assignment(source, assignment_revision=2)).json() == {
        "changed": True, "active": True, "assignment_revision": 3}
    assert [row["id"] for row in select_resource(source)] == ["a" * 32]
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(MediaEditorialReview)) == 1
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.action == "media.topic_removed")) == 1
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.action == "media.topic_restored")) == 1
    first = operator.get(url + "/history?limit=2").json()
    assert [row["action"] for row in first["items"]] == ["created", "removed"]
    assert first["next"] == 2 and first["current_revision"] == 3
    second = operator.get(url + "/history?after=2").json()
    assert [row["action"] for row in second["items"]] == ["restored"] and second["next"] is None


def test_correct_grade_keeps_old_revision_and_does_not_widen_source(operator, source):
    with DB.begin() as db:
        rows = db.scalars(select(CurriculumTopic).order_by(CurriculumTopic.id))
        topic = next(row for row in rows if row.data.get("grade_kind") in ("exact", "band")
                     and len(set(row.data.get("grades", []))) > 1)
        grades = sorted(set(topic.data["grades"]))
        source.update(id=topic.id, digest=topic.digest, grade=grades[0], subject=topic.subject_id,
                      state=topic.state_code, form=topic.school_form_id)
        db.get(MediaResource, "a" * 32).checked_region = topic.state_code[:2]
    setup_approved(operator, source)
    url = endpoint(source)
    response = operator.post(url + "/change", json=assignment(source, assignment_revision=1,
                                                               min_level=grades[1], max_level=grades[1]))
    assert response.status_code == 200 and response.json()["assignment_revision"] == 2
    assert select_resource(source) == []
    history = operator.get(url + "/history").json()["items"]
    assert [(row["action"], row["min_level"], row["max_level"]) for row in history] == [
        ("created", grades[0], grades[0]), ("updated", grades[1], grades[1])]
    assert operator.post(url + "/change", json=assignment(source, assignment_revision=1)).status_code == 409


def test_pre_migration_mapping_snapshot_is_attributed_as_inherited_not_invented(operator, source):
    with DB.begin() as db:
        db.add(MediaCurriculumLink(resource_id="a" * 32, topic_id=source["id"], topic_digest=source["digest"],
                                   level_kind="klasse", min_level=source["grade"], max_level=source["grade"]))
    url = endpoint(source)
    assert operator.get(url + "/history").json()["items"] == []
    assert operator.post(url + "/remove", json={"resource_revision": 1, "assignment_revision": 1}).status_code == 200
    history = operator.get(url + "/history").json()["items"]
    assert [event["action"] for event in history] == ["inherited", "removed"]
    assert history[0]["actor_id"] is None and history[1]["actor_id"] is not None


def test_removal_works_for_corrupted_source_but_restore_does_not(operator, source):
    setup_approved(operator, source)
    with DB.begin() as db:
        db.get(CurriculumTopic, source["id"]).title = "Ungültige Änderung"
    url = endpoint(source)
    assert operator.post(url + "/remove", json={"resource_revision": 1, "assignment_revision": 1}).status_code == 200
    assert operator.post(url + "/change", json=assignment(source, assignment_revision=2)).status_code == 409
    assert select_resource(source) == []


def test_restoring_a_mapping_does_not_override_a_later_editorial_block(operator, source):
    setup_approved(operator, source)
    url = endpoint(source)
    assert operator.post(url + "/remove", json={"resource_revision": 1, "assignment_revision": 1}).status_code == 200
    block = {"resource_revision": 1, "previous_review": 1, "decision": "blocked",
             "evidence_scope": "metadata", "content_kind": "general", "min_age": 10, "content_reviewed": False}
    assert operator.post("/api/admin/media-explorer/" + "a" * 32 + "/decisions", json=block).status_code == 200
    assert operator.post(url + "/change", json=assignment(source, assignment_revision=2)).status_code == 200
    assert select_resource(source) == []
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(MediaEditorialReview)) == 2


def test_parallel_removals_cannot_both_claim_same_revision(operator, source):
    setup_approved(operator, source)
    with DB.begin() as db:
        editor = User(username="revision-editor", display_name="Andere Redaktion", role="admin", verified=True,
                      password_hash="synthetic-no-login")
        db.add(editor)
        db.flush()
        db.add(Session(user_id=editor.id, token_hash=digest("revision-editor-session"), device="test",
                       expires=int(now()) + 1000))

    def remove(token):
        with TestClient(app, headers={**HEADERS, "Authorization": "Bearer " + token}) as client:
            return client.post(endpoint(source) + "/remove", json={"resource_revision": 1,
                               "assignment_revision": 1}).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(remove, ["synthetic-catalog-session", "revision-editor-session"])) == [200, 409]
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(MediaCurriculumLinkEvent)) == 2
        assert db.get(MediaCurriculumLink, ("a" * 32, source["id"])).revision == 2


def test_assignment_mutations_and_history_require_admin_and_same_origin(operator, source, api, household):
    setup_approved(operator, source)
    url = endpoint(source)
    assert api.get(url + "/history").status_code == 403
    assert api.post(url + "/remove", json={"resource_revision": 1, "assignment_revision": 1}).status_code == 403
    login = api.post("/api/auth/login", json={"username": "test-child", "password": "secure-child-pass-123"})
    assert login.status_code == 200
    api.headers["Authorization"] = "Bearer " + login.json()["token"]
    assert api.get(url + "/history").status_code == 403
    assert api.post(url + "/change", json=assignment(source, assignment_revision=1)).status_code == 403
    with TestClient(app, headers={**HEADERS, "Authorization": "Bearer synthetic-catalog-session",
                                  "Origin": "https://evil.example"}) as client:
        assert client.post(url + "/remove", json={"resource_revision": 1, "assignment_revision": 1}).status_code == 403
    assert [row["id"] for row in select_resource(source)] == ["a" * 32]
    with DB.begin() as db:
        admin = db.scalar(select(User).where(User.username == "catalog-operator"))
        db.scalar(select(Session).where(Session.user_id == admin.id)).revoked = True
    assert operator.get(url + "/history").status_code == 401
    assert operator.post(url + "/remove", json={"resource_revision": 1, "assignment_revision": 1}).status_code == 401
