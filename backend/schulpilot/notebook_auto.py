"""One finite background preparation for a newly confirmed standalone page.

The originating session and exact safe source selection remain bound to the job.
Neither listing pages nor reopening a status page schedules paid work.
"""
from fastapi import HTTPException
from sqlalchemy import delete, select, update

from .db import DB, Child, Job, LearningUnit, Material, Session, UnitSource, User
from .material_vocabulary import preview
from .notebook_auto_models import NotebookAutoIntent
from .notebook_practice import selection
from .providers import ProviderError
from .security import Principal


def arm(db, child, material, authority):
    """Persist an intent in the same transaction as a new source confirmation."""
    if (material.child_id != child.id or material.school_day_id is not None
            or material.purpose != "notebook" or not material.confirmed
            or material.synthetic or material.fixture_id
            or preview(material.subject, material.topic, material.content, material.source_blocks)):
        return
    db.flush()  # resolve known subject and persist the immutable source snapshot
    if db.scalar(select(NotebookAutoIntent.id).where(
            NotebookAutoIntent.material_id == material.id, NotebookAutoIntent.revision == material.revision)):
        return
    refs = [{"id": material.id, "revision": material.revision}]
    try:
        chosen = selection(db, child, material.id, refs, 3)
    except HTTPException:
        return  # unusable/uncertain sources remain available for parent review
    db.add(NotebookAutoIntent(child_id=child.id, material_id=material.id, revision=material.revision,
                              user_id=authority["user_id"], session_id=authority["session_id"],
                              family_id=authority["family_id"], selection=chosen))


def _advance(db, intent_id):
    from .materials import enqueue
    from .notebook_practice import guard
    from .study_authority import validate

    intent = db.get(NotebookAutoIntent, intent_id)
    if not intent:
        return
    # All writers and the standard provider reservation serialize per child.
    db.execute(update(Child).where(Child.id == intent.child_id).values(grade=Child.grade))
    db.refresh(intent)
    child = db.get(Child, intent.child_id, populate_existing=True)
    if not child:
        return
    if intent.status == "queued":
        job = db.get(Job, intent.job_id) if intent.job_id else None
        if not job or job.child_id != child.id or job.status in ("failed", "cancelled"):
            intent.status = "blocked"
        elif job.status == "completed":
            intent.status = "completed"
        return
    if intent.status != "pending":
        return
    authority = {"version": 1, "user_id": intent.user_id, "session_id": intent.session_id, "family_id": intent.family_id}
    validate(db, child, authority)
    material = db.get(Material, intent.material_id, populate_existing=True)
    if (not material or material.child_id != child.id or material.school_day_id is not None
            or material.revision != intent.revision or material.purpose != "notebook"
            or preview(material.subject, material.topic, material.content, material.source_blocks)):
        intent.status = "blocked"
        return
    payload = {"material_id": material.id, "assignment_id": None, "review_of": None,
               **intent.selection}
    guard(db, child, payload)
    # An existing round or a failed attempt is evidence, never a reason to
    # silently pay for a second provider call for the same source revision.
    existing_unit = db.scalar(select(UnitSource.unit_id).join(
        LearningUnit, LearningUnit.id == UnitSource.unit_id).where(
        LearningUnit.child_id == child.id, UnitSource.material_id == material.id,
        UnitSource.revision == material.revision).limit(1))
    if existing_unit:
        intent.status = "completed"
        return
    previous = list(db.scalars(select(Job).where(
        Job.child_id == child.id, Job.kind == "unit",
        Job.payload["material_id"].as_string() == material.id,
        Job.payload["material_revision"].as_integer() == material.revision)))
    if previous:
        intent.status = "blocked" if all(j.status not in ("queued", "running") for j in previous) else "pending"
        return
    if db.scalar(select(Job.id).where(Job.child_id == child.id, Job.status.in_(("queued", "running")))):
        return
    principal = Principal(db.get(User, intent.user_id), db.get(Session, intent.session_id))
    result = enqueue(db, principal, child, "unit", payload,
                     "notebook-auto:" + material.id + ":" + str(material.revision), commit=False)
    intent.job_id, intent.status = result["id"], "queued"


def advance_one():
    with DB() as db:
        ids = list(db.scalars(select(NotebookAutoIntent.id).where(
            NotebookAutoIntent.status.in_(("pending", "queued")))
            .order_by(NotebookAutoIntent.created, NotebookAutoIntent.id).limit(100)))
    for intent_id in ids:
        try:
            with DB.begin() as db:
                _advance(db, intent_id)
        except (ProviderError, HTTPException, ValueError, TypeError):
            # Reservation and intent update roll back together; never retry a
            # rejected reservation or provider failure automatically.
            with DB.begin() as db:
                intent = db.get(NotebookAutoIntent, intent_id)
                if intent:
                    db.execute(update(Child).where(Child.id == intent.child_id).values(grade=Child.grade))
                    db.refresh(intent)
                    if intent.status == "pending":
                        intent.status = "blocked"


def purge_expired(db, cutoff):
    """Remove terminal receipts after retention; preserve active idempotency."""
    db.execute(delete(NotebookAutoIntent).where(
        NotebookAutoIntent.created < cutoff,
        NotebookAutoIntent.status.in_(("blocked", "completed"))))
