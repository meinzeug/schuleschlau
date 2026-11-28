"""Editorial decisions over existing public media candidates only.

This API does not import metadata, search external providers, or access family
or child data. A human decision is not evidence of a provider's availability.
"""
import hashlib
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field, model_validator
from sqlalchemy import func, select, update

from .curriculum_models import CurriculumTopic
from .db import get_db, now
from .media_explorer_models import MediaCurriculumLink, MediaEditorialReview, MediaResource
from .media_explorer_policy import METADATA_MAX_AGE, public_media_url
from .media_youtube_metadata import curated_query
from .operator_incidents import reauthorize
from .schemas import Strict
from .security import admin, audit, rate_limit

router = APIRouter(tags=["Medienredaktion"])


class EditorialDecision(Strict):
    resource_revision: int = Field(ge=1, strict=True)
    previous_review: int = Field(ge=0, strict=True)
    decision: Literal["approved", "rejected", "blocked"]
    evidence_scope: Literal["metadata", "content"]
    content_kind: Literal["general", "historical_source", "propaganda", "sensitive"]
    min_age: int = Field(ge=0, le=99, strict=True)
    context: str = Field(default="", max_length=2000)
    counterpoint: str = Field(default="", max_length=2000)
    content_reviewed: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def validate_decision(self):
        if self.decision == "approved":
            if self.evidence_scope != "content" or not self.content_reviewed:
                raise ValueError("Für eine Freigabe muss der Inhalt tatsächlich geprüft und bestätigt sein.")
            if self.content_kind != "general" and not self.context.strip():
                raise ValueError("Für diese Quelle ist eine altersgerechte Einordnung erforderlich.")
            if self.content_kind in ("propaganda", "sensitive") and not self.counterpoint.strip():
                raise ValueError("Für diesen Inhalt ist eine Gegenperspektive erforderlich.")
        return self


class TopicAssignment(Strict):
    resource_revision: int = Field(ge=1, strict=True)
    topic_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    min_level: int = Field(ge=1, le=13, strict=True)
    max_level: int = Field(ge=1, le=13, strict=True)


def _topic_assignment_source(db, topic_id):
    """A link may only use an intact, public, grade-bound curriculum source."""
    topic = db.get(CurriculumTopic, topic_id, populate_existing=True)
    if topic is None:
        raise HTTPException(404, "Lehrplanthema nicht gefunden.")
    try:
        curated_query(db, topic.id)
    except ValueError:
        raise HTTPException(409, "Der Lehrplanbeleg ist nicht mehr gültig.") from None
    data = topic.data
    grades = data.get("grades")
    if (data.get("grade_kind") not in ("exact", "band") or not isinstance(grades, list)
            or not grades or any(type(grade) is not int or not 1 <= grade <= 13 for grade in grades)):
        raise HTTPException(409, "Für dieses Thema ist keine passende Klassenstufe belegt.")
    return topic, sorted(set(grades))


def _review_data(review):
    if not review:
        return None
    return {key: getattr(review, key) for key in (
        "resource_revision", "review_number", "decision", "evidence_scope", "content_kind",
        "min_age", "context", "counterpoint", "reviewed_at",
    )}


def _resource_data(row, review):
    return {
        "id": row.id, "provider": row.provider, "title": row.title, "channel": row.channel,
        "url": row.url if public_media_url(row.provider, row.provider_id, row.url) else None,
        "available": row.available, "checked_region": row.checked_region,
        "checked_at": row.checked_at, "duration_seconds": row.duration_seconds,
        "revision": row.revision, "review": _review_data(review),
    }


def _latest_review(db, resource_id):
    return db.scalar(select(MediaEditorialReview).where(MediaEditorialReview.resource_id == resource_id)
                     .order_by(MediaEditorialReview.review_number.desc()).limit(1))


@router.get("/admin/media-explorer")
def list_candidates(after: str = Query("", max_length=32), limit: int = Query(30, ge=1, le=50),
                    p=Depends(admin), db=Depends(get_db)):
    # Bounded keyset: no page walks or child-specific data in the shared index.
    rows = list(db.scalars(select(MediaResource).where(MediaResource.id > after)
                           .order_by(MediaResource.id).limit(limit + 1)))
    page = rows[:limit]
    if not page:
        return {"items": [], "next": None}
    ids = [row.id for row in page]
    latest = (select(MediaEditorialReview.resource_id, func.max(MediaEditorialReview.review_number).label("number"))
              .where(MediaEditorialReview.resource_id.in_(ids))
              .group_by(MediaEditorialReview.resource_id).subquery())
    reviews = {row.resource_id: row for row in db.scalars(
        select(MediaEditorialReview).join(latest, (MediaEditorialReview.resource_id == latest.c.resource_id)
                                         & (MediaEditorialReview.review_number == latest.c.number))
    )}
    return {"items": [_resource_data(row, reviews.get(row.id)) for row in page],
            "next": page[-1].id if len(rows) > limit else None}


@router.get("/admin/media-explorer/{resource_id}")
def get_candidate(resource_id: str, p=Depends(admin), db=Depends(get_db)):
    row = db.get(MediaResource, resource_id)
    if not row:
        raise HTTPException(404, "Medium nicht gefunden.")
    return _resource_data(row, _latest_review(db, row.id))


@router.get("/admin/media-explorer/{resource_id}/topics/{topic_id}")
def assignment_preview(resource_id: str, topic_id: str, p=Depends(admin), db=Depends(get_db)):
    """Inspect only public curriculum information; this does not fetch media."""
    resource = db.get(MediaResource, resource_id)
    if resource is None:
        raise HTTPException(404, "Medium nicht gefunden.")
    topic, grades = _topic_assignment_source(db, topic_id)
    existing = db.get(MediaCurriculumLink, (resource_id, topic_id))
    return {"resource_revision": resource.revision, "topic_id": topic.id, "topic_digest": topic.digest,
            "title": topic.title, "subject_id": topic.subject_id, "state_code": topic.state_code,
            "school_form_id": topic.school_form_id, "grades": grades,
            "region_matches": resource.checked_region == topic.state_code[:2],
            "assignment": None if existing is None else {"topic_digest": existing.topic_digest,
                "level_kind": existing.level_kind, "min_level": existing.min_level, "max_level": existing.max_level}}


@router.get("/admin/media-explorer/{resource_id}/topics")
def list_assignments(resource_id: str, after: str = Query("", max_length=140),
                     limit: int = Query(30, ge=1, le=50), p=Depends(admin), db=Depends(get_db)):
    """Bounded list of existing public mappings, without any learner lookup."""
    resource = db.get(MediaResource, resource_id)
    if resource is None:
        raise HTTPException(404, "Medium nicht gefunden.")
    rows = list(db.scalars(select(MediaCurriculumLink).where(MediaCurriculumLink.resource_id == resource_id,
        MediaCurriculumLink.topic_id > after).order_by(MediaCurriculumLink.topic_id).limit(limit + 1)))
    page = rows[:limit]
    return {"resource_revision": resource.revision,
            "items": [{"topic_id": row.topic_id, "topic_digest": row.topic_digest, "level_kind": row.level_kind,
                       "min_level": row.min_level, "max_level": row.max_level} for row in page],
            "next": page[-1].topic_id if len(rows) > limit else None}


@router.post("/admin/media-explorer/{resource_id}/topics/{topic_id}")
def assign_topic(resource_id: str, topic_id: str, data: TopicAssignment, p=Depends(admin), db=Depends(get_db)):
    """Create one immutable curriculum mapping; it never approves a resource."""
    reauthorize(db, p, lock=True)
    if p.session.user_id != p.user.id:
        raise HTTPException(401, "Bitte erneut anmelden.")
    rate_limit(db, "media-topic:" + p.user.id, 120, 60, commit=False)
    # Serialize assignments and editorial decisions in the same resource order.
    claimed = db.execute(update(MediaResource).where(MediaResource.id == resource_id,
        MediaResource.revision == data.resource_revision).values(revision=MediaResource.revision))
    if claimed.rowcount != 1:
        raise HTTPException(409, "Das Medium wurde geändert oder ist nicht mehr vorhanden. Bitte neu laden.")
    resource = db.get(MediaResource, resource_id, populate_existing=True)
    topic_claimed = db.execute(update(CurriculumTopic).where(CurriculumTopic.id == topic_id,
        CurriculumTopic.digest == data.topic_digest).values(digest=CurriculumTopic.digest))
    if topic_claimed.rowcount != 1:
        raise HTTPException(409, "Das Lehrplanthema wurde geändert oder ist nicht mehr vorhanden. Bitte neu laden.")
    topic, grades = _topic_assignment_source(db, topic_id)
    if resource.checked_region != topic.state_code[:2]:
        raise HTTPException(409, "Die geprüfte Medienregion passt nicht zum Lehrplan.")
    if data.min_level > data.max_level or not set(range(data.min_level, data.max_level + 1)).issubset(grades):
        raise HTTPException(422, "Der Klassenbereich muss im Lehrplanbeleg enthalten sein.")
    existing = db.get(MediaCurriculumLink, (resource_id, topic_id))
    if existing:
        if (existing.topic_digest, existing.level_kind, existing.min_level, existing.max_level) != (
                topic.digest, "klasse", data.min_level, data.max_level):
            raise HTTPException(409, "Für dieses Medium und Thema besteht bereits eine andere Zuordnung.")
        return {"created": False, "topic_id": topic.id, "resource_revision": resource.revision}
    db.add(MediaCurriculumLink(resource_id=resource.id, topic_id=topic.id, topic_digest=topic.digest,
                               level_kind="klasse", min_level=data.min_level, max_level=data.max_level))
    topic_hash = hashlib.sha256(topic.id.encode("utf-8")).hexdigest()[:32]
    audit(db, p.user.id, "media.topic_assigned", resource.id + ":" + topic_hash)
    db.flush()
    result = {"created": True, "topic_id": topic.id, "resource_revision": resource.revision}
    db.commit()
    return result


@router.post("/admin/media-explorer/{resource_id}/decisions")
def decide(resource_id: str, data: EditorialDecision, p=Depends(admin), db=Depends(get_db)):
    # Lock the same admin identity and session used for authentication. Then
    # serialize all decisions for one resource, including on SQLite where
    # FOR UPDATE is ignored. The revision remains the provider's revision.
    reauthorize(db, p, lock=True)
    if p.session.user_id != p.user.id:
        raise HTTPException(401, "Bitte erneut anmelden.")
    rate_limit(db, "media-editor:" + p.user.id, 120, 60, commit=False)
    claimed = db.execute(update(MediaResource).where(MediaResource.id == resource_id,
        MediaResource.revision == data.resource_revision).values(revision=MediaResource.revision))
    if claimed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Das Medium wurde geändert oder ist nicht mehr vorhanden. Bitte neu laden.")
    resource = db.get(MediaResource, resource_id, populate_existing=True)
    current = _latest_review(db, resource_id)
    if (current.review_number if current else 0) != data.previous_review:
        raise HTTPException(409, "Die redaktionelle Prüfung wurde geändert. Bitte neu laden.")
    if data.decision == "approved":
        timestamp = int(now())
        if (not resource.available or not public_media_url(resource.provider, resource.provider_id, resource.url)
                or resource.checked_at > timestamp or timestamp - resource.checked_at >= METADATA_MAX_AGE):
            raise HTTPException(409, "Das Medium ist nicht aktuell verfügbar. Bitte zuerst die Quelle prüfen.")
    row = MediaEditorialReview(resource_id=resource.id, resource_revision=resource.revision,
        review_number=data.previous_review + 1, reviewer_id=p.user.id, decision=data.decision,
        evidence_scope=data.evidence_scope, content_kind=data.content_kind, min_age=data.min_age,
        context=data.context, counterpoint=data.counterpoint)
    db.add(row)
    audit(db, p.user.id, "media.editorial_" + data.decision, resource.id + ":" + str(row.review_number))
    db.flush()
    result = _resource_data(resource, row)
    db.commit()
    return result
