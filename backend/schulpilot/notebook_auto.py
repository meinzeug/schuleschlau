"""One finite background preparation for a newly confirmed standalone page.

The originating session and exact safe source selection remain bound to the job.
Neither listing pages nor reopening a status page schedules paid work.
"""
import time

from fastapi import HTTPException
from sqlalchemy import and_, delete, or_, select, update

from .db import DB, Child, Job, LearningUnit, Material, RateBucket, Session, UnitSource, User
from .material_vocabulary import preview
from .notebook_auto_models import NotebookAutoIntent
from .notebook_practice import selection
from .providers import ProviderError
from .security import Principal, lock_session_after_child

_cursor = None


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


def _includes_source(payload, material):
    """Include non-primary pages of an existing multi-page job, too."""
    if not isinstance(payload, dict):
        return False
    if (payload.get("material_id") == material.id
            and type(payload.get("material_revision")) is int
            and payload.get("material_revision") == material.revision):
        return True
    refs = payload.get("sources")
    return isinstance(refs, list) and any(
        isinstance(ref, dict) and ref.get("id") == material.id
        and type(ref.get("revision")) is int and ref["revision"] == material.revision
        for ref in refs
    )


def lock_publication_session(db, job):
    """Serialize an auto-round publication with revocation, never the AI call.

    The worker already holds the child lock. Restrict this to a persisted
    automatic intent so older manual notebook jobs retain their contract.
    """
    payload = job.payload if isinstance(job.payload, dict) else {}
    material_id, revision = payload.get("material_id"), payload.get("material_revision")
    if not payload.get("notebook_practice") or not material_id or type(revision) is not int:
        return
    intent = db.scalar(select(NotebookAutoIntent).where(
        NotebookAutoIntent.material_id == material_id, NotebookAutoIntent.revision == revision,
        NotebookAutoIntent.child_id == job.child_id, NotebookAutoIntent.job_id == job.id,
    ))
    if not intent:
        return
    origin = payload.get("completion_origin")
    if (not isinstance(origin, dict) or not isinstance(origin.get("user_id"), str)
            or not isinstance(origin.get("session_id"), str)):
        raise ProviderError("Die Anmeldung für diese Runde ist nicht mehr gültig.")
    lock_session_after_child(db, origin["user_id"], origin["session_id"])


def _advance(db, intent_id):
    from .materials import JOB_RATE_LIMIT, JOB_RATE_SECONDS, enqueue
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
    # Jobs may contain this page as a secondary source. Check all the child's
    # retained unit payloads without loading the complete history into memory.
    # A multi-page failure must not silently become another paid auto request.
    previous = False
    for status, job_payload in db.execute(
        select(Job.status, Job.payload).where(Job.child_id == child.id, Job.kind == "unit")
        .execution_options(yield_per=100)
    ):
        if _includes_source(job_payload, material):
            if status in ("queued", "running"):
                return
            previous = True
    if previous:
        intent.status = "blocked"
        return
    if db.scalar(select(Job.id).where(Job.child_id == child.id, Job.status.in_(("queued", "running")))):
        return
    # Read-only advisory check: avoid writing the same exhausted bucket once
    # per worker tick. The atomic limiter in enqueue remains authoritative.
    tick = int(time.time()) // JOB_RATE_SECONDS
    bucket = db.get(RateBucket, f"job:{intent.user_id}:{tick}")
    if bucket and bucket.count >= JOB_RATE_LIMIT:
        return
    principal = Principal(db.get(User, intent.user_id), db.get(Session, intent.session_id))
    result = enqueue(db, principal, child, "unit", payload,
                     "notebook-auto:" + material.id + ":" + str(material.revision), commit=False)
    intent.job_id, intent.status = result["id"], "queued"


def advance_one():
    from .materials import JobRateLimitExceeded

    # The cursor is only a bounded scheduling hint. Each intent is still
    # checked and serialized afresh; wrap around after the last page.
    global _cursor
    with DB() as db:
        query = (select(NotebookAutoIntent.created, NotebookAutoIntent.id)
                 .where(NotebookAutoIntent.status.in_(("pending", "queued")))
                 .order_by(NotebookAutoIntent.created, NotebookAutoIntent.id).limit(100))
        if _cursor is not None:
            created, intent_id = _cursor
            query = query.where(or_(NotebookAutoIntent.created > created,
                                    and_(NotebookAutoIntent.created == created, NotebookAutoIntent.id > intent_id)))
        rows = list(db.execute(query))
        if not rows and _cursor is not None:
            _cursor = None
            return
        _cursor = tuple(rows[-1]) if len(rows) == 100 else None
    for _, intent_id in rows:
        try:
            with DB.begin() as db:
                _advance(db, intent_id)
        except JobRateLimitExceeded:
            # Transaction rolls back before a job/reservation exists. A later
            # window may reserve it once; this is never a provider retry.
            continue
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
