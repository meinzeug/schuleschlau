"""Immutable catalogue illustrations built solely from public selectors."""
from sqlalchemy import JSON, Column, Integer, LargeBinary, String

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
