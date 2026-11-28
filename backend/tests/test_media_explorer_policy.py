"""Shared media never becomes a recommendation on metadata alone."""
from types import SimpleNamespace

import pytest
from schulpilot.curriculum import fingerprint
from schulpilot.curriculum_models import CurriculumTopic
from schulpilot.db import DB, Activity, Job, Subject, User
from schulpilot.media_explorer_models import MediaCurriculumLink, MediaEditorialReview, MediaResource
from schulpilot.media_explorer_policy import METADATA_MAX_AGE, eligible, public_media_url, select_for_topic
from sqlalchemy import func, select


@pytest.fixture
def example():
    resource = SimpleNamespace(id="media", provider="youtube", provider_id="Abcdefgh_12",
        url="https://www.youtube.com/watch?v=Abcdefgh_12", available=True, checked_region="DE",
        checked_at=1_000_000, revision=1)
    data = {"id": "topic", "document_id": "source", "title": "Brüche", "grade_kind": "band", "grades": [5, 6]}
    topic = SimpleNamespace(id="topic", digest=fingerprint(data), state_code="DE-ST",
                            school_form_id="de-st.sekundarschule", document_id="source", title="Brüche", data=data)
    link = SimpleNamespace(resource_id="media", topic_id="topic", topic_digest=topic.digest,
        level_kind="klasse", min_level=5, max_level=6)
    review = SimpleNamespace(resource_id="media", resource_revision=1, decision="approved", evidence_scope="content",
        reviewer_id="editor", reviewed_at=1_000_000, min_age=10, content_kind="general", context="", counterpoint="")
    reviewer = SimpleNamespace(id="editor", role="admin", verified=True, disabled=False)
    profile = dict(state_code="DE-ST", school_form_id="de-st.sekundarschule", level_kind="klasse", level_number=6,
        age=12, current_time=1_000_001)
    return resource, link, topic, review, reviewer, profile


def accepted(example):
    return eligible(*example[:5], **example[5])


def test_canonical_url_excludes_redirects_credentials_and_unrelated_video():
    vid = "Abcdefgh_12"
    assert public_media_url("youtube", vid, f"https://www.youtube.com/watch?v={vid}")
    for url in (f"https://youtube.com/watch?v={vid}", f"http://www.youtube.com/watch?v={vid}",
                f"https://www.youtube.com@evil.example/watch?v={vid}",
                f"https://www.youtube.com/watch?v={vid}&next=https://evil.example",
                "https://www.youtube.com/watch?v=Qbcdefgh_12"):
        assert not public_media_url("youtube", vid, url)
    assert not public_media_url("other", vid, f"https://www.youtube.com/watch?v={vid}")
    assert not public_media_url("youtube", "../bad", "https://www.youtube.com/watch?v=../bad")


@pytest.mark.parametrize("index,field,value", [
    (0, "available", False), (0, "revision", 2), (0, "checked_at", 1_000_002), (0, "checked_region", "AT"),
    (1, "topic_digest", "b" * 64), (1, "resource_id", "other"), (1, "level_kind", "lernjahr"),
    (2, "state_code", "DE-BY"), (2, "school_form_id", "de-st.gymnasium"),
    (2, "data", {"grade_kind": "phase", "grades": []}),
    (2, "data", {"grade_kind": "band", "grades": [5, 6, 7]}),
    (3, "decision", "blocked"), (3, "evidence_scope", "metadata"), (3, "reviewer_id", None),
    (3, "reviewed_at", 1_000_002), (3, "content_kind", "unknown"),
    (4, "role", "parent"), (4, "verified", False), (4, "disabled", True),
])
def test_unknown_stale_or_unreviewed_inputs_never_become_recommendations(example, index, field, value):
    assert accepted(example)
    setattr(example[index], field, value)
    assert not accepted(example)


def test_age_level_and_retention_must_be_explicit(example):
    assert accepted(example)
    for key, value in (("age", None), ("age", 9), ("age", True), ("level_number", None),
                       ("level_number", 7), ("level_kind", "lernjahr"),
                       ("current_time", 1_000_000 + METADATA_MAX_AGE)):
        bad = dict(example[5], **{key: value})
        assert not eligible(*example[:5], **bad)


@pytest.mark.parametrize("kind", ["historical_source", "propaganda", "sensitive"])
def test_historical_and_sensitive_context_cannot_be_omitted(example, kind):
    review = example[3]
    review.content_kind = kind
    assert not accepted(example)
    review.context = "Zeitgenössische Quelle: Aussagen müssen eingeordnet werden."
    if kind == "historical_source":
        assert accepted(example)
    else:
        assert not accepted(example)
        review.counterpoint = "Vergleiche eine unabhängige historische Einordnung."
        assert accepted(example)


def test_shared_tables_have_no_family_or_child_reference():
    for table in (MediaResource.__table__, MediaCurriculumLink.__table__, MediaEditorialReview.__table__):
        assert "child_id" not in table.c and "family_id" not in table.c
        assert all(fk.column.table.name not in {"children", "families", "materials", "learning_units", "attempts"}
                   for fk in table.foreign_keys)


def test_db_selection_is_read_only_and_latest_block_wins(api, monkeypatch):
    monkeypatch.setattr("schulpilot.media_explorer_policy.now", lambda: 1001)
    with DB.begin() as db:
        topic = next(row for row in db.scalars(select(CurriculumTopic).order_by(CurriculumTopic.id))
                     if row.data.get("grade_kind") in ("exact", "band") and row.data.get("grades"))
        assert topic is not None
        grade = topic.data["grades"][0]
        subject = db.get(Subject, topic.subject_id)
        assert subject.owner_family_id is None
        editor = User(id="e" * 32, username="artificial-editor", display_name="Test", role="admin",
                      verified=True, disabled=False, password_hash="test")
        other_editor = User(id="f" * 32, username="artificial-editor-two", display_name="Test", role="admin",
                            verified=True, disabled=False, password_hash="test")
        media = MediaResource(id="m" * 32, provider="youtube", provider_id="Abcdefgh_12", title="Testinhalt",
                              channel="Testquelle", url="https://www.youtube.com/watch?v=Abcdefgh_12",
                              available=True, checked_region=topic.state_code[:2], checked_at=1000, revision=1, created=1000)
        db.add_all([editor, other_editor, media])
        db.flush()
        db.add(MediaCurriculumLink(resource_id=media.id, topic_id=topic.id, topic_digest=topic.digest,
                                   level_kind="klasse", min_level=grade, max_level=grade))
        db.add(MediaEditorialReview(id="r" * 32, resource_id=media.id, resource_revision=1, review_number=1,
            reviewer_id=editor.id, decision="approved", evidence_scope="content", content_kind="general",
            min_age=10, context="", counterpoint="", reviewed_at=1000))
        topic_id, subject_id, state_code, school_form = topic.id, subject.id, topic.state_code, topic.school_form_id
    args = dict(topic_id=topic_id, subject_id=subject_id, state_code=state_code, school_form_id=school_form,
                level_kind="klasse", level_number=grade, age=12)
    with DB() as db:
        before = (db.scalar(select(func.count()).select_from(Job)), db.scalar(select(func.count()).select_from(Activity)))
        rows = select_for_topic(db, **args)
        assert len(rows) == 1 and rows[0]["review_scope"] == "content"
        assert before == (db.scalar(select(func.count()).select_from(Job)), db.scalar(select(func.count()).select_from(Activity)))
    with DB.begin() as db:
        db.add(MediaEditorialReview(id="s" * 32, resource_id="m" * 32, resource_revision=1, review_number=2,
            reviewer_id="f" * 32, decision="blocked", evidence_scope="metadata", content_kind="general",
            min_age=10, context="", counterpoint="", reviewed_at=1000))
    with DB() as db:
        assert select_for_topic(db, **args) == []
    # Deleting an editor preserves their historical decision but removes its
    # human binding. The block by the other editor is unaffected.
    with DB.begin() as db:
        db.delete(db.get(User, "e" * 32))
    with DB() as db:
        assert db.get(MediaEditorialReview, "r" * 32).reviewer_id is None
        assert select_for_topic(db, **args) == []
