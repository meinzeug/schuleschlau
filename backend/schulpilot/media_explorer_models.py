"""Shared, editorially reviewed media records; never store learner data here.

A candidate is not a recommendation merely because metadata exists.  The
separate policy checks source freshness, educational placement and an actual
editorial content review before a record may be shown to a child.
"""
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    true,
)

from .db import Base, now, uid


class MediaResource(Base):
    __tablename__ = "media_resources"

    id = Column(String(32), primary_key=True, default=uid)
    provider = Column(String(24), nullable=False)
    provider_id = Column(String(128), nullable=False)
    title = Column(String(300), nullable=False)
    channel = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False)
    checked_region = Column(String(2), nullable=False)
    duration_seconds = Column(Integer)
    available = Column(Boolean, nullable=False, default=False)
    checked_at = Column(Integer, nullable=False)
    revision = Column(Integer, nullable=False, default=1)
    created = Column(Integer, nullable=False, default=lambda: int(now()))
    __table_args__ = (
        UniqueConstraint("provider", "provider_id", name="uq_media_provider_item"),
        CheckConstraint("revision >= 1", name="ck_media_resource_revision"),
        CheckConstraint("checked_at >= 0", name="ck_media_resource_check"),
        CheckConstraint("duration_seconds IS NULL OR duration_seconds >= 0", name="ck_media_duration"),
        Index("ix_media_resource_availability", "available", "checked_at"),
    )


class MediaCurriculumLink(Base):
    __tablename__ = "media_curriculum_links"

    resource_id = Column(ForeignKey("media_resources.id", ondelete="CASCADE"), primary_key=True)
    topic_id = Column(ForeignKey("curriculum_topics.id", ondelete="CASCADE"), primary_key=True)
    topic_digest = Column(String(64), nullable=False)
    level_kind = Column(String(16), nullable=False)
    min_level = Column(Integer, nullable=False)
    max_level = Column(Integer, nullable=False)
    # A removed link is a tombstone: its monotonically increasing version
    # prevents a stale editor from silently recreating an old assignment.
    revision = Column(Integer, nullable=False, default=1, server_default="1")
    active = Column(Boolean, nullable=False, default=True, server_default=true())
    __table_args__ = (
        CheckConstraint("min_level >= 1 AND max_level >= min_level", name="ck_media_level_range"),
        Index("ix_media_topic_level", "topic_id", "level_kind", "min_level", "max_level"),
    )


class MediaCurriculumLinkEvent(Base):
    """Immutable metadata-only record of an editorial mapping change."""
    __tablename__ = "media_curriculum_link_events"

    id = Column(String(32), primary_key=True, default=uid)
    resource_id = Column(ForeignKey("media_resources.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(ForeignKey("curriculum_topics.id", ondelete="CASCADE"), nullable=False)
    revision = Column(Integer, nullable=False)
    actor_id = Column(ForeignKey("users.id", ondelete="SET NULL"))
    action = Column(String(16), nullable=False)
    topic_digest = Column(String(64), nullable=False)
    min_level = Column(Integer, nullable=False)
    max_level = Column(Integer, nullable=False)
    created = Column(Integer, nullable=False, default=lambda: int(now()))
    __table_args__ = (
        UniqueConstraint("resource_id", "topic_id", "revision", name="uq_media_link_event_revision"),
        CheckConstraint("action IN ('inherited', 'created', 'updated', 'removed', 'restored')", name="ck_media_link_event_action"),
        Index("ix_media_link_event_history", "resource_id", "topic_id", "revision"),
    )


class MediaEditorialReview(Base):
    """Revision-bound editorial decision; older rows remain available for audit."""
    __tablename__ = "media_editorial_reviews"

    id = Column(String(32), primary_key=True, default=uid)
    resource_id = Column(ForeignKey("media_resources.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_revision = Column(Integer, nullable=False)
    review_number = Column(Integer, nullable=False)
    reviewer_id = Column(ForeignKey("users.id", ondelete="SET NULL"))
    decision = Column(String(16), nullable=False)
    evidence_scope = Column(String(16), nullable=False)
    content_kind = Column(String(24), nullable=False)
    min_age = Column(Integer, nullable=False)
    context = Column(Text, nullable=False, default="")
    counterpoint = Column(Text, nullable=False, default="")
    reviewed_at = Column(Integer, nullable=False, default=lambda: int(now()))
    __table_args__ = (
        CheckConstraint("resource_revision >= 1", name="ck_media_review_revision"),
        CheckConstraint("review_number >= 1", name="ck_media_review_number"),
        CheckConstraint("min_age >= 0 AND min_age <= 99", name="ck_media_review_age"),
        CheckConstraint("decision IN ('approved', 'rejected', 'blocked')", name="ck_media_review_decision"),
        CheckConstraint("evidence_scope IN ('metadata', 'content')", name="ck_media_review_scope"),
        CheckConstraint("content_kind IN ('general', 'historical_source', 'propaganda', 'sensitive')", name="ck_media_review_kind"),
        UniqueConstraint("resource_id", "review_number", name="uq_media_review_number"),
        Index("ix_media_review_latest", "resource_id", "review_number"),
    )
