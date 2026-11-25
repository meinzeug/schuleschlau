"""Bounded content-free receipts for two local, pre-job failure paths."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError

from .db import Child, LearningUnit, LocalProcessingFailure, get_db, now
from .security import child_access, lock_session_after_child, parent

router = APIRouter(tags=["Materialien und KI-Aufträge"])
log = logging.getLogger(__name__)
ALLOWED = {
    "upload": {"photo_invalid", "photo_too_large", "photo_unavailable"},
    "answer": {"question_missing"},
}
DAILY_LIMIT = 20


def record_failure(db, principal, child_id, phase, code, *, unit_id=None):
    """Best effort after a rejected action; never change its HTTP result.

    The original transaction is rolled back before creating an independent
    receipt. Unit -> Child -> Session matches the normal mutation lock order.
    The bounded receipt intentionally has no request payload, question id,
    filename, user input, image data, provider text or learning evidence.
    """
    if code not in ALLOWED.get(phase, set()) or (phase == "answer") != bool(unit_id):
        raise ValueError("Invalid local diagnostic category")
    user_id, session_id = principal.user.id, principal.session.id
    try:
        db.rollback()
        if unit_id:
            touched = db.execute(update(LearningUnit).where(
                LearningUnit.id == unit_id, LearningUnit.child_id == child_id
            ).values(status=LearningUnit.status)).rowcount
            if not touched:
                db.rollback()
                return None
        touched = db.execute(update(Child).where(Child.id == child_id).values(grade=Child.grade)).rowcount
        if not touched:
            db.rollback()
            return None
        lock_session_after_child(db, user_id, session_id)
        db.expire_all()
        child_access(db, principal, child_id, write=principal.user.role == "parent")
        stamp = int(now())
        total = db.scalar(select(func.count()).select_from(LocalProcessingFailure).where(
            LocalProcessingFailure.child_id == child_id, LocalProcessingFailure.phase == phase,
            LocalProcessingFailure.created > stamp - 86400))
        if total >= DAILY_LIMIT:
            db.rollback()
            return None
        receipt = LocalProcessingFailure(child_id=child_id, unit_id=unit_id, phase=phase, code=code, created=stamp)
        db.add(receipt)
        db.flush()
        identifier = receipt.id
        db.commit()
        return identifier
    except (HTTPException, SQLAlchemyError, RuntimeError) as error:
        try:
            db.rollback()
        except SQLAlchemyError:
            pass
        log.warning("local_processing_receipt_unavailable type=%s", type(error).__name__)
        return None


def failure_data(db, row):
    if row.code not in ALLOWED.get(row.phase, set()):
        return None
    unit = db.get(LearningUnit, row.unit_id) if row.unit_id else None
    if (row.phase == "answer" and (not unit or unit.child_id != row.child_id)) or (row.phase == "upload" and row.unit_id):
        return None
    return {"id": row.id, "phase": row.phase, "status": "failed", "code": row.code,
            "unit_id": row.unit_id, "created": row.created}


@router.get("/children/{child_id}/processing-errors")
def list_failures(child_id: str, limit: int = Query(20, ge=1, le=50), p=Depends(parent), db=Depends(get_db)):
    child_access(db, p, child_id)
    rows = db.scalars(select(LocalProcessingFailure).where(LocalProcessingFailure.child_id == child_id,
        LocalProcessingFailure.created >= int(now()) - 30 * 86400)
        .order_by(LocalProcessingFailure.created.desc(), LocalProcessingFailure.id.desc()).limit(limit))
    return {"errors": [value for row in rows if (value := failure_data(db, row)) is not None]}


@router.get("/processing-errors/{receipt_id}")
def get_failure(receipt_id: str, p=Depends(parent), db=Depends(get_db)):
    row = db.get(LocalProcessingFailure, receipt_id)
    if not row or row.created < int(now()) - 30 * 86400:
        raise HTTPException(404, "Verarbeitungsbeleg nicht gefunden.")
    child_access(db, p, row.child_id)
    data = failure_data(db, row)
    if data is None:
        raise HTTPException(404, "Verarbeitungsbeleg nicht gefunden.")
    return data
