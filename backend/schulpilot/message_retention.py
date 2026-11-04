"""Apply the same message retention rule to live and restored databases."""

from sqlalchemy import delete

from .db import Message

RETENTION_SECONDS = 365 * 86400


def purge_expired(db, current):
    """Remove expired messages without turning the cutoff itself into a deletion."""
    if type(current) is not int or current < 0:
        raise ValueError("Invalid retention time")
    return db.execute(delete(Message).where(Message.created < current - RETENTION_SECONDS)).rowcount
