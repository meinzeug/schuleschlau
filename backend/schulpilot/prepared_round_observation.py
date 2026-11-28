"""Conservative, private observation for an unopened automatically prepared round."""

from sqlalchemy import select

from .db import Attempt, Job
from .learning_evidence_marker import matches, snapshot


def may_have_changed(db, unit):
    """True only for an observed change; False includes unknown or legacy state.

    This best-effort read is not a mastery assessment or an atomic freshness
    guarantee. Caller must first authorise the family. Never expose the marker.
    """
    if (unit.status != "not_started" or unit.round_kind not in ("study_block", "study_recall")
            or not unit.school_day_id
            or db.scalar(select(Attempt.id).where(Attempt.unit_id == unit.id).limit(1))):
        return False
    jobs = list(db.scalars(select(Job).where(
        Job.child_id == unit.child_id, Job.kind == "study_block", Job.status == "completed",
        Job.result["unit_id"].as_string() == unit.id,
    ).limit(2)))
    if len(jobs) != 1 or (jobs[0].payload or {}).get("automatic_study_stage") is not True:
        return False
    observed = jobs[0].payload.get("automatic_evidence_observation")
    if not isinstance(observed, dict) or observed.get("consistency") != "best_effort":
        return False
    marker = observed.get("marker")
    if not matches(marker, marker):
        return False
    return not matches(marker, snapshot(db, unit.child_id, unit.subject, exclude_unit_id=unit.id))
