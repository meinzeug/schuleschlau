"""Metadata-only beta application, separate from learning content."""
from sqlalchemy import Column, ForeignKey, Integer, String

from .db import Base, now, uid


class BetaApplication(Base):
    __tablename__ = "beta_applications"
    id = Column(String(32), primary_key=True, default=uid)
    family_id = Column(ForeignKey("families.id", ondelete="CASCADE"), nullable=False, unique=True)
    user_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(16), nullable=False, default="pending")
    revision = Column(Integer, nullable=False, default=1)
    created = Column(Integer, nullable=False, default=lambda: int(now()))
    approved_at = Column(Integer)
    decided_at = Column(Integer)
    decided_by = Column(ForeignKey("users.id", ondelete="SET NULL"))
