"""Conservative push permissions for an isolated restored database.

An old backup cannot prove that a parent has not withdrawn consent since it was
created. Call only after authenticating the current erasure journal, inside the
same transaction as the other restore reconciliation steps.
"""

from sqlalchemy import delete, inspect, select

from .db import Child, PushDevice


def clear_restored_push(db):
    """Require fresh consent and device registration after a restore."""
    if "preferences_revision" not in inspect(Child).columns:
        raise RuntimeError("Restore runtime lacks child preferences revision support")
    for child in db.scalars(select(Child).order_by(Child.id)):
        if not isinstance(child.preferences, dict):
            raise ValueError("Invalid restored child preferences")
        if child.preferences.get("push_consent", False) is not False:
            if child.preferences_revision >= 2147483647:
                raise ValueError("Restored child preferences revision exhausted")
            child.preferences = {**child.preferences, "push_consent": False}
            child.preferences_revision += 1
    db.execute(delete(PushDevice))
