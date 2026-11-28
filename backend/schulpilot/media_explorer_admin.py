"""Editorial decisions over existing public media candidates only.

This API does not import metadata, search external providers, or access family
or child data. A human decision is not evidence of a provider's availability.
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field, model_validator
from sqlalchemy import func, select, update

from .db import get_db, now
from .media_explorer_models import MediaEditorialReview, MediaResource
from .media_explorer_policy import METADATA_MAX_AGE, public_media_url
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
            if self.content_kind != "general" and not self.context:
                raise ValueError("Für diese Quelle ist eine altersgerechte Einordnung erforderlich.")
            if self.content_kind in ("propaganda", "sensitive") and not self.counterpoint:
                raise ValueError("Für diesen Inhalt ist eine Gegenperspektive erforderlich.")
        return self


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
