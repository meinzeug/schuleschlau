"""Child-owned, source-bound round deferrals are not learning evidence."""
from sqlalchemy import select

from .db import LearningMemory


def candidates(db, child_id):
    """Fetch only memories which contain a possible active deferral."""
    rows = db.scalars(select(LearningMemory).where(LearningMemory.child_id == child_id,
        LearningMemory.working["round_deferral"].as_string().is_not(None)))
    return {row.unit_id: row for row in rows}


def is_deferred(db, unit, memory=None):
    from .learning_controller import source_state

    memory = memory if memory is not None else db.get(LearningMemory, unit.id)
    value = (memory.working or {}).get("round_deferral") if memory else None
    if (not isinstance(value, dict) or value.get("version") != 1
            or value.get("reason") != "already_done" or unit.status == "completed"
            or type(value.get("plan_revision")) is not int or value["plan_revision"] != memory.plan_revision):
        return False
    signature, valid, _ = source_state(db, unit)
    return valid and value.get("source_signature") == signature
