"""The same expiry rule for private conversations in live and restored data."""

from sqlalchemy import delete

from .db import ParentLearningReview, SchulbuddyTurn, TutorTurn

RETENTION_SECONDS = 365 * 86400


def purge_expired(db, current):
    """Apply the existing strict 365-day cutoff within the caller's transaction."""
    if type(current) is not int or current < 0:
        raise ValueError("Invalid retention time")
    return {
        model.__tablename__: db.execute(delete(model).where(model.created < current - RETENTION_SECONDS)).rowcount
        for model in (TutorTurn, SchulbuddyTurn, ParentLearningReview)
    }
