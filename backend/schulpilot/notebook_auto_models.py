"""Durable, account-bound intent to prepare one notebook practice round."""
from sqlalchemy import JSON, Column, ForeignKey, Index, Integer, String, UniqueConstraint

from .db import Base, now, uid


class NotebookAutoIntent(Base):
    __tablename__ = "notebook_auto_intents"
    id = Column(String(32), primary_key=True, default=uid)
    child_id = Column(ForeignKey("children.id", ondelete="CASCADE"), nullable=False)
    material_id = Column(ForeignKey("materials.id", ondelete="CASCADE"), nullable=False)
    revision = Column(Integer, nullable=False)
    user_id = Column(ForeignKey("users.id", ondelete="SET NULL"))
    session_id = Column(ForeignKey("sessions.id", ondelete="SET NULL"))
    family_id = Column(String(32), nullable=False)
    selection = Column(JSON, nullable=False)
    status = Column(String(16), nullable=False, default="pending", server_default="pending")
    job_id = Column(ForeignKey("jobs.id", ondelete="SET NULL"))
    created = Column(Integer, nullable=False, default=lambda: int(now()))
    __table_args__ = (UniqueConstraint("material_id", "revision", name="uq_notebook_auto_revision"),
                      Index("ix_notebook_auto_status_created", "status", "created", "id"))
