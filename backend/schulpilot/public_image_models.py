"""Immutable catalogue illustrations built solely from public selectors."""
from sqlalchemy import JSON, Column, ForeignKey, Integer, LargeBinary, String

from .db import Base, now


class PublicImage(Base):
    __tablename__ = "public_images"
    cache_key = Column(String(64), primary_key=True)
    lookup_key = Column(String(64), nullable=False, index=True)
    specification = Column(JSON, nullable=False)
    format_version = Column(String(40), nullable=False)
    model = Column(String(160), nullable=False)
    upstream = Column(String(100), nullable=False)
    region = Column(String(20), nullable=False)
    png = Column(LargeBinary, nullable=False)
    png_sha256 = Column(String(64), nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    factual_status = Column(String(24), nullable=False, default="unassessed")
    created = Column(Integer, nullable=False, default=lambda: int(now()))


class PublicImageBuild(Base):
    __tablename__ = "public_image_builds"
    lookup_key = Column(String(64), primary_key=True)
    specification = Column(JSON, nullable=False)
    status = Column(String(24), nullable=False)
    job_id = Column(ForeignKey("jobs.id", ondelete="SET NULL"))
    image_key = Column(ForeignKey("public_images.cache_key", ondelete="SET NULL"))
    attempts = Column(Integer, nullable=False, default=0)
    updated = Column(Integer, nullable=False, default=lambda: int(now()))


class PublicImageReview(Base):
    """One versioned machine opinion, never a human-reviewed certificate."""
    __tablename__ = "public_image_reviews"
    image_key = Column(ForeignKey("public_images.cache_key", ondelete="CASCADE"), primary_key=True)
    job_id = Column(ForeignKey("jobs.id", ondelete="SET NULL"), unique=True)
    status = Column(String(24), nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    image_sha256 = Column(String(64), nullable=False)
    specification_digest = Column(String(64), nullable=False)
    review_version = Column(String(40), nullable=False)
    reviewer_model = Column(String(160))
    reviewer_upstream = Column(String(100))
    reference_available = Column(Integer, nullable=False, default=0)
    assessment = Column(JSON)
    updated = Column(Integer, nullable=False, default=lambda: int(now()))
