"""Operator-reviewed beta access, without access to family learning data."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field, StrictInt
from sqlalchemy import and_, case, func, select

from .beta_models import BetaApplication
from .db import Family, Membership, Usage, User, get_db, now, uid
from .schemas import Strict
from .security import admin, audit, family_access, insert_ignore, lock_session_after_child, parent, rate_limit

router = APIRouter(tags=["Beta-Freigaben"])


class Decision(Strict):
    revision: StrictInt = Field(ge=1)
    decision: Literal["approve", "reject", "revoke"]


def application_for_family(db, family_id, *, lock=False):
    query = select(BetaApplication).where(BetaApplication.family_id == family_id)
    if lock:
        query = query.with_for_update()
    return db.scalar(query.execution_options(populate_existing=True))


def approved(db, family_id, *, lock=False):
    row = application_for_family(db, family_id, lock=lock)
    if not row or row.status != "approved":
        return False
    user = db.get(User, row.user_id, populate_existing=True)
    member = db.scalar(select(Membership).where(Membership.family_id == family_id,
        Membership.user_id == row.user_id, Membership.permission == "owner"))
    family = db.get(Family, family_id, populate_existing=True)
    return bool(user and user.role == "parent" and user.verified and not user.disabled
                and member and family and not family.synthetic)


def limit_ai_feature(db, family_id, key, limit, period):
    """Exempt only approved beta families from long-window AI quotas.

    Caller must already hold the corresponding Child lock. Short-term abuse,
    retry, idempotency and single-active-job protections remain separate.
    """
    if not approved(db, family_id, lock=True):
        rate_limit(db, key, limit, period, commit=False)


def projection(db, row):
    user = db.get(User, row.user_id)
    family = db.get(Family, row.family_id)
    usage = {"calls": 0, "known_usd_micros": 0, "unknown_calls": 0,
             "input_tokens": 0, "output_tokens": 0, "by_model": {}, "models_truncated": False}
    if row.approved_at is not None:
        conditions = [Usage.family_id == row.family_id, Usage.created >= row.approved_at,
                      Usage.route_snapshot["beta_unlimited"].as_boolean().is_(True)]
        if row.status == "revoked" and row.decided_at is not None:
            conditions.append(Usage.created <= row.decided_at)
        # Money is the provider's reported/reconciled amount, never an estimate.
        known = and_(Usage.cost_micros.is_not(None), Usage.cost_source.in_(("reported", "generation", "cancelled")))
        measures = (func.count(Usage.id), func.coalesce(func.sum(case((known, Usage.cost_micros), else_=0)), 0),
                    func.coalesce(func.sum(case((known, 0), else_=1)), 0),
                    func.coalesce(func.sum(Usage.input_tokens), 0), func.coalesce(func.sum(Usage.output_tokens), 0))
        totals = db.execute(select(*measures).where(*conditions)).one()
        for key, value in zip(("calls", "known_usd_micros", "unknown_calls", "input_tokens", "output_tokens"), totals):
            usage[key] = int(value)
        models = list(db.execute(select(Usage.model, *measures[:3]).where(*conditions)
                                 .group_by(Usage.model).order_by(Usage.model).limit(51)))
        usage["models_truncated"] = len(models) > 50
        usage["by_model"] = {model: {"calls": int(calls), "known_usd_micros": int(cost), "unknown_calls": int(unknown)}
                             for model, calls, cost, unknown in models[:50]}
    return {"id": row.id, "family_id": row.family_id, "family_name": family.name if family else "",
            "user_id": row.user_id, "display_name": user.display_name if user else "",
            "email": user.email if user else None, "email_verified": bool(user and user.verified),
            "status": row.status, "revision": row.revision, "created": row.created,
            "decided_at": row.decided_at, "approved_at": row.approved_at, "usage": usage}


@router.get("/families/{family_id}/beta-application")
def own_application(family_id: str, p=Depends(parent), db=Depends(get_db)):
    family, _ = family_access(db, p, family_id, owner=True)
    row = application_for_family(db, family.id)
    if not row:
        return {"status": "none"}
    return {"status": row.status, "revision": row.revision, "created": row.created}


@router.post("/families/{family_id}/beta-application", status_code=202)
def apply_existing(family_id: str, p=Depends(parent), db=Depends(get_db)):
    from .commerce import store

    family, _ = family_access(db, p, family_id, owner=True)
    if family.synthetic or not store(db)[0].beta_enabled:
        raise HTTPException(403, "Die Beta-Anmeldung ist derzeit geschlossen.")
    rate_limit(db, "beta-apply:" + p.user.id, 10, 60, commit=False)
    tick = int(now())
    insert_ignore(db, BetaApplication, {"id": uid(), "family_id": family.id, "user_id": p.user.id,
        "status": "pending", "revision": 1, "created": tick}, key="family_id")
    row = application_for_family(db, family.id, lock=True)
    if row.user_id != p.user.id:
        raise HTTPException(409, "Für diese Familie liegt bereits eine Beta-Anmeldung vor.")
    lock_session_after_child(db, p.user.id, p.session.id)
    if row.status in ("rejected", "revoked"):
        row.status, row.revision, row.decided_at, row.decided_by = "pending", row.revision + 1, None, None
        audit(db, p.user.id, "beta.reapplied", row.id)
    db.flush()
    value = {"status": row.status, "revision": row.revision, "created": row.created}
    db.commit()
    return value


@router.get("/admin/beta-applications")
def list_applications(status: Literal["pending", "approved", "rejected", "revoked", "all"] = "pending",
                      page: int = Query(default=1, ge=1, le=100000), p=Depends(admin), db=Depends(get_db)):
    query = select(BetaApplication)
    if status != "all":
        query = query.where(BetaApplication.status == status)
    rows = list(db.scalars(query.order_by(BetaApplication.created.desc(), BetaApplication.id.desc())
                           .offset((page - 1) * 50).limit(51)))
    return {"items": [projection(db, row) for row in rows[:50]], "page": page, "has_more": len(rows) > 50}


@router.post("/admin/beta-applications/{application_id}/decision")
def decide(application_id: str, data: Decision, p=Depends(admin), db=Depends(get_db)):
    rate_limit(db, "beta-decision:" + p.user.id, 60, 60, commit=False)
    row = db.scalar(select(BetaApplication).where(BetaApplication.id == application_id)
                    .with_for_update().execution_options(populate_existing=True))
    if not row:
        raise HTTPException(404, "Beta-Anmeldung nicht gefunden.")
    if row.revision != data.revision:
        raise HTTPException(409, "Die Beta-Anmeldung wurde geändert. Bitte neu laden.")
    user = db.get(User, row.user_id, populate_existing=True)
    member = db.scalar(select(Membership).where(Membership.family_id == row.family_id,
        Membership.user_id == row.user_id, Membership.permission == "owner"))
    family = db.get(Family, row.family_id, populate_existing=True)
    if data.decision == "approve":
        if row.status != "pending":
            raise HTTPException(409, "Nur offene Bewerbungen können freigegeben werden.")
        if not user or user.disabled or not user.verified or user.role != "parent" or not member or not family or family.synthetic:
            raise HTTPException(409, "Die Elternadresse muss bestätigt und das Familienkonto aktiv sein.")
        result = "approved"
    elif data.decision == "reject":
        if row.status != "pending":
            raise HTTPException(409, "Nur offene Bewerbungen können abgelehnt werden.")
        result = "rejected"
    else:
        if row.status != "approved":
            raise HTTPException(409, "Nur eine aktive Beta-Freigabe kann widerrufen werden.")
        result = "revoked"
    # Recheck the operator session before the revisioned mutation is committed.
    lock_session_after_child(db, p.user.id, p.session.id)
    tick = int(now())
    row.status, row.revision, row.decided_at, row.decided_by = result, row.revision + 1, tick, p.user.id
    if result == "approved" and row.approved_at is None:
        row.approved_at = tick
    audit(db, p.user.id, "beta." + result, row.id)
    db.flush()
    value = projection(db, row)
    db.commit()
    return value
