"""Separately reserved, source-bound Vision review of a public image.

The result is an AI opinion, not a factual or human certification. Provider
errors and unavailable routes never produce an approval or an implicit retry.
"""
import copy

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .db import DB, Child, Family, Job, LearningUnit, ProviderConfig, Usage, get_db, now
from .public_image_catalog import find_current, lookup_key
from .public_image_models import PublicImage, PublicImageReview
from .public_image_review_contract import REVIEW_VERSION, public_review_input, request_review
from .security import authenticated, child_access
from .visual_references import digest

router = APIRouter(tags=['Öffentliche Bildprüfung'])


def review_view(db, image):
    from .public_image_review_contract import ImageReviewOutput

    row = db.get(PublicImageReview, image.cache_key)
    if (not row or row.image_sha256 != image.png_sha256 or row.specification_digest != digest(image.specification)
            or row.review_version != REVIEW_VERSION):
        return {'review_status': 'unavailable', 'review_reference_available': False,
                'review_request_allowed': review_route_available(db, image)}
    status = row.status
    if status == 'pending':
        job = db.get(Job, row.job_id) if row.job_id else None
        if not job or job.status not in ('queued', 'running'):
            status = 'unavailable'
    if status in ('approved', 'rejected', 'uncertain'):
        try:
            assessment = ImageReviewOutput.model_validate(row.assessment)
            expected = {'approved': 'consistent', 'rejected': 'incorrect', 'uncertain': 'uncertain'}[status]
            if (assessment.verdict != expected or not row.reviewer_model or not row.reviewer_upstream
                    or row.reviewer_model == image.model):
                status = 'unavailable'
        except (ValueError, TypeError):
            status = 'unavailable'
    retry = status in ('unavailable', 'uncertain') and row.attempts < 2 and review_route_available(db, image)
    return {'review_status': status, 'review_reference_available': bool(row.reference_available),
            'review_request_allowed': retry}


def review_route_available(db, image):
    from .model_routing import enabled, select_route
    from .providers import ProviderError, external_allowed

    config = db.get(ProviderConfig, 1)
    try:
        if not config or not enabled(config):
            return False
        route = select_route(config, 'public_image_review')
        if route.provider != 'openrouter' or not route.image_capable or route.model == image.model:
            return False
        external_allowed(route, image=True, db=db)
        return True
    except (HTTPException, ProviderError, ValueError):
        return False


def queue(db, unit, child, user, session, image, selector, spec, *, explicit=False, request_key=None):
    """Reserve exactly one review; caller owns a dedicated transaction."""
    from types import SimpleNamespace

    from .model_routing import enabled, select_route
    from .providers import reserve
    from .public_image_jobs import authority as image_authority

    # Unit and Child are already locked by both callers. Capture only
    # server-derived identities, then re-read session/family/source after any
    # contended advisory/provider lock; stale ORM identity-map values do not
    # constitute authorization.
    authority_snapshot = SimpleNamespace(child_id=child.id, payload={
        'unit_id': unit.id, 'family_id': child.family_id, 'user_id': user.id,
        'session_id': session.id, 'selector': selector, 'lookup_key': lookup_key(spec)})
    from .security import lock_session_after_child

    lock_session_after_child(db, authority_snapshot.payload['user_id'], authority_snapshot.payload['session_id'])

    def recheck():
        db.expire_all()
        fresh_child, fresh_unit, (fresh_selector, fresh_spec) = image_authority(db, authority_snapshot)
        if fresh_selector != selector or fresh_spec != spec or fresh_child.id != authority_snapshot.child_id:
            raise HTTPException(409, 'Die öffentliche Grundlage oder der Zugang wurde geändert.')
        return fresh_child, fresh_unit

    identity = ('public-review:' + digest([user.id, request_key]) if explicit else
                'public-review-auto:' + digest([image.cache_key, REVIEW_VERSION]))
    if explicit:
        if not isinstance(request_key, str) or not 16 <= len(request_key) <= 80 or not request_key.isascii():
            raise HTTPException(422, 'Bitte einen eindeutigen Anfrageschlüssel verwenden.')
        if db.bind.dialect.name == 'postgresql':
            from sqlalchemy import text
            db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': int(digest([user.id, request_key])[:15], 16)})
        previous = db.scalar(select(Job).where(Job.idempotency == identity))
        if previous:
            if previous.kind != 'public_image_review' or previous.child_id != child.id or previous.payload.get('image_key') != image.cache_key:
                raise HTTPException(409, 'Dieser Anfrageschlüssel gehört zu einer anderen Auswahl.')
            recheck()
            return review_view(db, image)
    config = db.scalar(select(ProviderConfig).where(ProviderConfig.id == 1).with_for_update())
    child, unit = recheck()
    if not config or not enabled(config):
        raise HTTPException(503, 'Die Bildprüfung ist momentan nicht verfügbar.')
    route = select_route(config, 'public_image_review')
    if route.provider != 'openrouter' or not route.image_capable or route.model == image.model:
        raise HTTPException(503, 'Für die Bildprüfung fehlt eine unabhängige Bildroute.')
    spec2, public_input = public_review_input(db, selector, image)
    if spec2 != spec:
        raise HTTPException(409, 'Das öffentliche Thema wurde geändert.')
    insert = pg_insert if db.bind.dialect.name == 'postgresql' else sqlite_insert
    values = {'image_key': image.cache_key, 'status': 'unavailable', 'attempts': 0,
              'image_sha256': image.png_sha256, 'specification_digest': digest(spec),
              'review_version': REVIEW_VERSION, 'reference_available': int(public_input['reference_available']),
              'updated': int(now())}
    db.execute(insert(PublicImageReview).values(**values).on_conflict_do_nothing(index_elements=['image_key']))
    review = db.scalar(select(PublicImageReview).where(PublicImageReview.image_key == image.cache_key).with_for_update())
    if (review.image_sha256 != image.png_sha256 or review.specification_digest != digest(spec)
            or review.review_version != REVIEW_VERSION):
        raise HTTPException(409, 'Das Bild oder die Prüfgrundlage wurde geändert.')
    if review.status == 'pending':
        pending_job = db.get(Job, review.job_id) if review.job_id else None
        if not pending_job or pending_job.status not in ('queued', 'running'):
            review.status = 'unavailable'
    if review.status in ('pending', 'approved', 'rejected') or (review.status == 'uncertain' and not explicit):
        return review_view(db, image)
    if review.attempts and not explicit:
        return review_view(db, image)
    if review.attempts >= 2:
        raise HTTPException(409, 'Für dieses Bild ist keine weitere automatische Prüfung verfügbar.')
    if db.scalar(select(Job.id).where(Job.child_id == child.id, Job.status.in_(['queued', 'running']))):
        raise HTTPException(409, 'Für dieses Kind wird bereits ein Auftrag verarbeitet.')
    job = Job(child_id=child.id, kind='public_image_review', idempotency=identity,
              payload={'review_unit_id': unit.id, 'family_id': child.family_id, 'user_id': user.id,
                       'session_id': session.id, 'selector': selector, 'lookup_key': lookup_key(spec),
                       'image_key': image.cache_key, 'image_sha256': image.png_sha256,
                       'specification_digest': digest(spec), 'review_version': REVIEW_VERSION})
    db.add(job)
    db.flush()
    reserve(db, db.get(Family, child.family_id), child.id, job.id, 'public_image_review')
    review.job_id, review.status, review.attempts, review.updated = job.id, 'pending', review.attempts + 1, int(now())
    db.flush()
    return review_view(db, image)


@router.post('/units/{unit_id}/public-image/review', status_code=202)
def review_existing(unit_id: str, account: str = Header(default='', alias='X-Schulpilot-Account'),
                    key: str = Header(default='', alias='Idempotency-Key'),
                    p=Depends(authenticated), db=Depends(get_db)):
    from .learning import get_unit
    from .learning_assets import actor
    from .public_image_jobs import unit_spec

    actor(p, account)
    unit = get_unit(db, p, unit_id, lock=True)
    child = child_access(db, p, unit.child_id, write=p.user.role == 'parent')
    db.execute(update(Child).where(Child.id == child.id).values(grade=Child.grade))
    child_access(db, p, unit.child_id, write=p.user.role == 'parent')
    resolved = unit_spec(db, unit)
    image = find_current(db, resolved[0]) if resolved else None
    if not image:
        raise HTTPException(404, 'Für dieses Thema liegt noch kein Bild vor.')
    value = queue(db, unit, child, p.user, p.session, image, *resolved, explicit=True, request_key=key)
    db.commit()
    return value


def enqueue_after_image(job_id):
    """Best effort after the creator job commits; no retry on failure."""
    from .public_image_jobs import authority

    with DB.begin() as db:
        job = db.get(Job, job_id)
        if not job or job.kind != 'public_image' or job.status != 'completed':
            return
        db.execute(update(LearningUnit).where(LearningUnit.id == job.payload['unit_id']).values(status=LearningUnit.status))
        db.execute(update(Child).where(Child.id == job.child_id).values(grade=Child.grade))
        db.expire_all()
        child, unit, (selector, spec) = authority(db, job)
        image = find_current(db, selector)
        if not image:
            return
        from .db import Session, User
        queue(db, unit, child, db.get(User, job.payload['user_id']), db.get(Session, job.payload['session_id']),
              image, selector, spec)


def backfill_one():
    """Mark and attempt at most one old image; never infer authority from it.

    A persisted unavailable marker also prevents an inactive/revoked session
    or failed reservation from triggering an automatic retry loop. The normal
    authenticated explicit action remains possible later.
    """
    import logging

    from .public_image_models import PublicImageBuild

    with DB.begin() as db:
        query = (select(PublicImage, PublicImageBuild, Job)
            .join(PublicImageBuild, PublicImageBuild.image_key == PublicImage.cache_key)
            .join(Job, Job.id == PublicImageBuild.job_id)
            .outerjoin(PublicImageReview, PublicImageReview.image_key == PublicImage.cache_key)
            .where(Job.kind == 'public_image', Job.status == 'completed', PublicImageReview.image_key.is_(None))
            .order_by(PublicImage.created, PublicImage.cache_key).limit(1))
        if db.bind.dialect.name == 'postgresql':
            query = query.with_for_update(of=PublicImage, skip_locked=True)
        match = db.execute(query).first()
        if not match:
            return False
        image, build, creator = match
        specification = image.specification if isinstance(image.specification, dict) else {}
        insert = pg_insert if db.bind.dialect.name == 'postgresql' else sqlite_insert
        inserted = db.execute(insert(PublicImageReview).values(
            image_key=image.cache_key, status='unavailable', attempts=0,
            image_sha256=image.png_sha256, specification_digest=digest(specification),
            review_version=REVIEW_VERSION,
            reference_available=int(bool((specification.get('public_focus') or {}).get('content'))),
            updated=int(now())).on_conflict_do_nothing(index_elements=['image_key'])).rowcount
        creator_id = creator.id if inserted else None
    if creator_id:
        try:
            enqueue_after_image(creator_id)
        except Exception as error:
            logging.getLogger('schulpilot.worker').warning('public_image_review_backfill_unavailable type=%s', type(error).__name__)
    return True


def authority(db, job):
    from types import SimpleNamespace

    from .public_image_jobs import authority as image_authority

    proxy = SimpleNamespace(payload={**job.payload, 'unit_id': job.payload['review_unit_id']}, child_id=job.child_id)
    child, unit, (selector, spec) = image_authority(db, proxy)
    image = db.get(PublicImage, job.payload['image_key'])
    actual, public_input = public_review_input(db, selector, image)
    if (actual != spec or digest(spec) != job.payload['specification_digest']
            or image.png_sha256 != job.payload['image_sha256'] or job.payload['review_version'] != REVIEW_VERSION):
        raise HTTPException(409, 'Bild oder öffentliche Grundlage wurden geändert.')
    return child, unit, selector, spec, image, public_input


def process(job_id):
    from .config import settings
    from .model_routing import job_config, selection
    from .providers import ProviderError, Result, external_allowed, settle
    from .security import decrypt

    result, sent = None, False
    try:
        with DB() as db:
            job = db.get(Job, job_id)
            if not job or job.status != 'running':
                return
            _, _, _, spec, image, public_input = authority(db, job)
            row = db.get(PublicImageReview, image.cache_key)
            if not row or row.status != 'pending' or row.job_id != job.id:
                raise HTTPException(409, 'Der Prüfauftrag wurde geändert.')
            config = job_config(db, job, 'public_image_review')
            external_allowed(config, image=True, db=db)
            route = selection(config)
            if not route or config.model == image.model:
                raise HTTPException(409, 'Die Bildprüfroute ist nicht unabhängig.')
            token = settings.openrouter_api_key or (decrypt(config.encrypted_key) if config.encrypted_key else '')
            revision, model = config.revision, config.model
            # Detached image instance contains only the public sanitized PNG.
            db.expunge(image)
        sent = True
        with httpx.Client(timeout=httpx.Timeout(145, connect=10), follow_redirects=False) as client:
            result = request_review(client, config, image, public_input, token=token, route=route)
        with DB.begin() as db:
            job = db.get(Job, job_id)
            if not job:
                return
            if job.status != 'running':
                from .public_image_jobs import remember_late_receipt

                remember_late_receipt(db, job, result)
                return
            db.execute(update(LearningUnit).where(LearningUnit.id == job.payload['review_unit_id']).values(status=LearningUnit.status))
            db.execute(update(Child).where(Child.id == job.child_id).values(grade=Child.grade))
            from .security import lock_session_after_child

            lock_session_after_child(db, job.payload['user_id'], job.payload['session_id'])
            db.expire_all()
            _, _, _, current_spec, current_image, public_input = authority(db, job)
            row = db.scalar(select(PublicImageReview).where(PublicImageReview.image_key == current_image.cache_key).with_for_update())
            current = job_config(db, job, 'public_image_review')
            external_allowed(current, image=True, db=db)
            if (not row or row.status != 'pending' or row.job_id != job.id or current_spec != spec
                    or (current.revision, current.model) != (revision, model)):
                raise HTTPException(409, 'Die Bildprüfung ist nicht mehr aktuell.')
            verdict = result.data['verdict']
            row.status = {'consistent': 'approved', 'incorrect': 'rejected', 'uncertain': 'uncertain'}[verdict]
            row.reviewer_model, row.reviewer_upstream = model, route['route']['upstreams'][0]
            row.reference_available, row.assessment, row.updated = int(public_input['reference_available']), copy.deepcopy(result.data), int(now())
            settle(db, db.scalar(select(Usage).where(Usage.job_id == job.id)), result)
            job.status, job.finished, job.result = 'completed', int(now()), {'review_status': row.status}
    except Exception as error:
        if isinstance(error, ProviderError) and error.billing_result is not None:
            result = error.billing_result
        with DB.begin() as db:
            job = db.get(Job, job_id)
            if not job:
                return
            if job.status != 'running':
                from .public_image_jobs import remember_late_receipt

                remember_late_receipt(db, job, result)
                return
            db.execute(update(LearningUnit).where(LearningUnit.id == job.payload['review_unit_id']).values(status=LearningUnit.status))
            db.execute(update(Child).where(Child.id == job.child_id).values(grade=Child.grade))
            db.expire_all()
            row = db.scalar(select(PublicImageReview).where(PublicImageReview.image_key == job.payload['image_key']).with_for_update())
            if row and row.job_id == job.id and row.status == 'pending':
                row.status, row.updated = 'unavailable', int(now())
            if result is None and not sent:
                result = Result({}, 0, 0, 0, cost_source='cancelled')
            settle(db, db.scalar(select(Usage).where(Usage.job_id == job.id)), result, failed=True)
            from .job_failures import failure_code

            job.error_code = failure_code(error)
            job.status, job.finished, job.error = 'failed', int(now()), 'Die Bildprüfung konnte nicht abgeschlossen werden.'
