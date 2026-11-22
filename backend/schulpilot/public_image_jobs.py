"""Explicit, separately reserved public-only illustrations for learning units."""
import copy
import re

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response
from sqlalchemy import select, text as sql_text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .db import DB, Child, Family, Job, LearningUnit, ProviderConfig, Session, Usage, User, get_db, now
from .learning_assets import actor, public_focus_for_unit, public_selection_for_unit
from .learning_asset_schemas import LearningAssetSpec
from .public_image_catalog import find_current, lookup_key, publish
from .public_image_contract import ImageContractError, public_prompt, request_resolved_image
from .public_image_models import PublicImageBuild
from .security import Principal, authenticated, child_access, rate_limit
from .subject_content import canonical_profile
from .visual_references import digest

router = APIRouter(tags=["Öffentliche Lernbilder"])
NOTICE = "Allgemeines KI-Bild · fachlich noch nicht geprüft"


def unit_spec(db, unit):
    """Resolve private unit title locally; the resulting selector is public."""
    child = db.get(Child, unit.child_id)
    if not child or type(child.grade) is not int or not 1 <= child.grade <= 13:
        return None
    topic, content = public_selection_for_unit(db, unit.subject, unit.topic)
    if topic is None:
        return None
    focus = public_focus_for_unit(unit.subject, unit.topic)
    if focus is not None:
        content = None  # A curated focus and a catalogue content are mutually exclusive.
    if (focus is None and content is None and canonical_profile(unit.subject) == "Biologie"
            and topic.id == "sofatutor:topic:5690" and re.search(r"\bbien(?:e|en)\b", unit.topic, re.I)):
        focus = "biology.honey_bee.general.v1"
    if content is None and focus is None:
        return None
    try:
        selector = LearningAssetSpec(subject=unit.subject, recipe_id="general.source_relation.phases", recipe_version=1,
            foundation_ids=[], catalog_topic_id=topic.id, catalog_content_id=content.id if content else None,
            public_focus_id=focus,
            level_band="primary" if child.grade <= 4 else "lower_secondary" if child.grade <= 10 else "upper_secondary")
        spec, _ = public_prompt(db, selector)
    except (ImageContractError, HTTPException, ValueError):
        return None
    return selector.model_dump(), spec


def route_available(db):
    from .model_routing import enabled, select_route
    from .providers import ProviderError, external_allowed

    config = db.get(ProviderConfig, 1)
    try:
        if (not config or config.provider != "openrouter" or not enabled(config)
                or (config.routing_policy or {}).get("region", "standard") not in ("standard", "eu")):
            return False
        route = select_route(config, "public_image")
        external_allowed(route, image_output=True, db=db)
        return True
    except (HTTPException, ProviderError, ValueError):
        return False


def state(db, spec, selector):
    image = find_current(db, selector)
    if image:
        from .public_image_review import review_view

        review = review_view(db, image)
        return {"status": "unavailable" if review['review_status'] == 'rejected' else "ready",
                "notice": NOTICE, **review}
    build = db.get(PublicImageBuild, lookup_key(spec))
    if not build or build.specification != spec:
        # A cached picture above remains available even when generation is
        # disabled. A mere status GET must not advertise an impossible start.
        return {"status": "missing" if route_available(db) else "unavailable", "notice": NOTICE}
    job = db.get(Job, build.job_id) if build.job_id else None
    status = (job.status if job and job.status in ("queued", "running", "failed") else
              "failed" if build.status != "ready" else "missing")
    rejected_image = find_current(db, selector, include_rejected=True)
    if rejected_image and status == 'missing':
        from .public_image_review import review_view

        if review_view(db, rejected_image)['review_status'] == 'rejected':
            retry = build.attempts < 2 and route_available(db)
            return {'status': 'missing' if retry else 'unavailable', 'notice': NOTICE,
                    'image_rejected': True, 'retry_allowed': retry, 'review_status': 'rejected'}
    return {"status": status, "notice": NOTICE,
            **({"retry_allowed": build.attempts < 2 and route_available(db)} if status == "failed" else {})}


@router.get("/units/{unit_id}/public-image")
def image_status(unit_id: str, p=Depends(authenticated), db=Depends(get_db)):
    from .learning import get_unit

    unit = get_unit(db, p, unit_id)
    resolved = unit_spec(db, unit)
    return state(db, resolved[1], resolved[0]) if resolved else {"status": "unavailable", "notice": NOTICE}


@router.get("/units/{unit_id}/public-image/file")
def image_file(unit_id: str, p=Depends(authenticated), db=Depends(get_db)):
    from .learning import get_unit

    unit = get_unit(db, p, unit_id)
    resolved = unit_spec(db, unit)
    row = find_current(db, resolved[0]) if resolved else None
    if row is None:
        raise HTTPException(404, "Für dieses Thema liegt noch kein Bild vor.")
    from .public_image_review import review_view

    if review_view(db, row)['review_status'] == 'rejected':
        raise HTTPException(404, "Dieses Bild ist nicht für die Anzeige verfügbar.")
    return Response(row.png, media_type="image/png", headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/units/{unit_id}/public-image", status_code=202)
def prepare(unit_id: str, key: str = Header(default="", alias="Idempotency-Key"),
            account: str = Header(default="", alias="X-Schulpilot-Account"),
            p=Depends(authenticated), db=Depends(get_db)):
    from .learning import get_unit
    from .providers import reserve

    actor(p, account)
    if not 16 <= len(key) <= 80 or not key.isascii():
        raise HTTPException(422, "Bitte einen eindeutigen Anfrageschlüssel verwenden.")
    unit = get_unit(db, p, unit_id, lock=True)
    child = child_access(db, p, unit.child_id, write=p.user.role == "parent")
    if unit.synthetic or db.get(Family, child.family_id).synthetic:
        raise HTTPException(409, "Die Demo startet keine zusätzliche Bilderzeugung.")
    db.execute(update(Child).where(Child.id == child.id).values(grade=Child.grade))
    child_access(db, p, child.id, write=p.user.role == "parent")
    config = db.get(ProviderConfig, 1)
    if not config or config.provider != "openrouter":
        raise HTTPException(503, "Für öffentliche Bilder ist noch kein passender Bildanbieter eingerichtet.")
    if (config.routing_policy or {}).get("region", "standard") not in ("standard", "eu"):
        raise HTTPException(503, "Die eingestellte Datenregion unterstützt diese Bildroute noch nicht.")
    resolved = unit_spec(db, unit)
    if not resolved:
        raise HTTPException(409, "Für dieses Thema ist noch kein passender öffentlicher Katalogeintrag vorhanden.")
    selector, spec = resolved
    if db.bind.dialect.name == "postgresql":
        db.execute(sql_text("SELECT pg_advisory_xact_lock(:key)"), {"key": int(digest([p.user.id, key])[:15], 16)})
    identity = "public-image:" + digest([p.user.id, key])
    previous = db.scalar(select(Job).where(Job.idempotency == identity))
    if previous:
        if previous.kind != "public_image" or previous.child_id != child.id or previous.payload.get("unit_id") != unit.id or previous.payload.get("lookup_key") != lookup_key(spec):
            raise HTTPException(409, "Dieser Anfrageschlüssel gehört zu einer anderen Auswahl.")
        return state(db, spec, selector)
    if find_current(db, selector):
        return state(db, spec, selector)
    insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
    cache_key = lookup_key(spec)
    db.execute(insert(PublicImageBuild).values(lookup_key=cache_key, specification=spec, status="claimed", attempts=0, updated=int(now()))
               .on_conflict_do_nothing(index_elements=["lookup_key"]))
    build = db.scalar(select(PublicImageBuild).where(PublicImageBuild.lookup_key == cache_key).with_for_update())
    if build.specification != spec:
        raise HTTPException(409, "Der öffentliche Themenstand wurde geändert.")
    current_job = db.get(Job, build.job_id) if build.job_id else None
    if current_job and current_job.status in ("queued", "running"):
        return {"status": current_job.status, "notice": NOTICE}
    if build.attempts >= 2:
        raise HTTPException(409, "Für dieses Thema konnte noch kein passendes Bild erstellt werden.")
    if db.scalar(select(Job.id).where(Job.child_id == child.id, Job.status.in_(["queued", "running"]))):
        raise HTTPException(409, "Für dieses Kind wird bereits ein Auftrag verarbeitet.")
    from .beta import approved as beta_approved

    if not beta_approved(db, child.family_id, lock=True):
        rate_limit(db, "public-image:" + p.user.id, 10, 3600, commit=False)
    job = Job(child_id=child.id, kind="public_image", idempotency=identity, payload={"unit_id": unit.id,
        "lookup_key": cache_key, "selector": selector, "user_id": p.user.id, "session_id": p.session.id,
        "family_id": child.family_id})
    db.add(job)
    db.flush()
    reserve(db, db.get(Family, child.family_id), child.id, job.id, "public_image")
    build.job_id, build.status, build.attempts, build.updated = job.id, "queued", build.attempts + 1, int(now())
    db.commit()
    return {"status": "queued", "notice": NOTICE}


def prepare_missing_unit_image(unit_job_id):
    """At most one reserved image after an explicitly requested incomplete unit.

    Reads on their own never generate. The originating session and family are
    checked again. A replay of this completion uses the same idempotency key;
    failed calls never automatically retry. The completed unit is untouched.
    """
    from .study_authority import validate
    from .visual_references import projection

    with DB() as db:
        original = db.get(Job, unit_job_id)
        if not original or original.kind != "unit" or original.status != "completed" or not isinstance(original.result, dict):
            return None
        config = db.get(ProviderConfig, 1)
        if (not config or config.provider != "openrouter" or not (config.routing_policy or {}).get("enabled")
                or "image" not in (config.routing_policy or {}).get("routes", {})):
            return None  # An unconfigured image route is not an attempted failure.
        unit = db.get(LearningUnit, original.result.get("unit_id"))
        child = db.get(Child, original.child_id)
        if not unit or not child or unit.child_id != child.id or unit.synthetic:
            return None
        visual = projection(db, unit)
        if visual.get("explanation_visual_status") != "incomplete" or visual.get("explanation_visual_reason") not in ("missing_steps", "invalid_graphic"):
            return None
        origin = original.payload.get("completion_origin")
        validate(db, child, origin)
        resolved = unit_spec(db, unit)
        if not resolved:
            return None
        principal = Principal(db.get(User, origin["user_id"]), db.get(Session, origin["session_id"]))
        result = prepare(unit.id, key="unit-image-" + original.id, account=principal.user.id, p=principal, db=db)
        return result["status"]


def authority(db, job):
    from .commerce import usage_terms
    from .learning import get_unit

    session = db.get(Session, job.payload["session_id"])
    user = db.get(User, job.payload["user_id"])
    if (not session or session.revoked or session.user_id != job.payload["user_id"] or session.expires <= now()
            or session.seen < now() - 7 * 86400 or not user or user.disabled or not user.verified):
        raise HTTPException(401, "Die Anmeldung wurde beendet.")
    principal = Principal(user, session)
    unit = get_unit(db, principal, job.payload["unit_id"])
    child = child_access(db, principal, unit.child_id, write=user.role == "parent")
    if child.id != job.child_id or child.family_id != job.payload["family_id"]:
        raise HTTPException(409, "Die Familienzuordnung wurde geändert.")
    usage_terms(db, db.get(Family, child.family_id), enforce=True)
    resolved = unit_spec(db, unit)
    if not resolved or resolved[0] != job.payload["selector"] or lookup_key(resolved[1]) != job.payload["lookup_key"]:
        raise HTTPException(409, "Das Thema oder die öffentliche Grundlage wurde geändert.")
    return child, unit, resolved


def process(job_id):
    from .config import settings
    from .model_routing import job_config, selection
    from .providers import Result, external_allowed, settle
    from .security import decrypt

    result, sent, receipt = None, False, None
    try:
        with DB() as db:
            job = db.get(Job, job_id)
            if not job or job.status != "running":
                return
            _, _, (selector, spec) = authority(db, job)
            build = db.get(PublicImageBuild, job.payload["lookup_key"])
            if not build or build.status != "queued" or build.job_id != job.id or build.specification != spec:
                raise ImageContractError("build_changed")
            config = job_config(db, job, "public_image")
            external_allowed(config, image_output=True, db=db)
            route = selection(config)
            if config.provider != "openrouter" or route.get("tier") != "image" or len(route["route"]["upstreams"]) != 1:
                raise ImageContractError("invalid_route")
            _, prompt = public_prompt(db, selector)
            token = settings.openrouter_api_key or (decrypt(config.encrypted_key) if config.encrypted_key else "")
            config_revision, model = config.revision, config.model
            upstream, region = route["route"]["upstreams"][0], route["region"]
        sent = True
        with httpx.Client(timeout=httpx.Timeout(145, connect=10), follow_redirects=False) as client:
            receipt = request_resolved_image(client, prompt, token=token, model=model, upstream=upstream, region=region)
        result = Result({}, **receipt.billing)
        with DB.begin() as db:
            job = db.get(Job, job_id)
            if not job:
                return
            db.execute(update(LearningUnit).where(LearningUnit.id == job.payload["unit_id"]).values(status=LearningUnit.status))
            db.execute(update(Child).where(Child.id == job.child_id).values(grade=Child.grade))
            db.expire_all()
            if job.status != "running":
                remember_late_receipt(db, job, result)
                return  # The reaper retained the unknown reservation; no result is published.
            _, _, (_, current_spec) = authority(db, job)
            build = db.scalar(select(PublicImageBuild).where(PublicImageBuild.lookup_key == job.payload["lookup_key"]).with_for_update())
            current = job_config(db, job, "public_image")
            external_allowed(current, image_output=True, db=db)
            if (not build or build.status != "queued" or build.job_id != job.id or current_spec != spec
                    or (current.revision, current.model) != (config_revision, model)):
                raise ImageContractError("build_changed")
            image = publish(db, selector, spec, receipt, model=model, upstream=upstream, region=region)
            build.status, build.image_key, build.updated = "ready", image.cache_key, int(now())
            settle(db, db.scalar(select(Usage).where(Usage.job_id == job.id)), result)
            job.status, job.finished, job.result = "completed", int(now()), {"public_image": True}
    except Exception as error:
        if isinstance(error, ImageContractError) and error.billing:
            result = Result({}, **error.billing)
        with DB.begin() as db:
            job = db.get(Job, job_id)
            if not job:
                return
            db.execute(update(LearningUnit).where(LearningUnit.id == job.payload["unit_id"]).values(status=LearningUnit.status))
            db.execute(update(Child).where(Child.id == job.child_id).values(grade=Child.grade))
            db.expire_all()
            if job.status != "running":
                remember_late_receipt(db, job, result)
                return
            build = db.scalar(select(PublicImageBuild).where(PublicImageBuild.lookup_key == job.payload["lookup_key"]).with_for_update())
            if build and build.job_id == job.id and build.status == "queued":
                build.status, build.updated = "failed", int(now())
            if result is None and not sent:
                result = Result({}, 0, 0, 0, cost_source="cancelled")
            settle(db, db.scalar(select(Usage).where(Usage.job_id == job.id)), result, failed=True)
            from .job_failures import failure_code

            category = getattr(error, "category", "")
            code = ("provider_unavailable" if category in ("provider_transport", "provider_http") else
                    "source_changed" if category in ("public_basis_changed", "build_changed") else
                    "invalid_output" if category.startswith(("image_", "response_")) else failure_code(error))
            job.status, job.finished, job.error_code = "failed", int(now()), code
            job.error = "Das Bild konnte nicht sicher erstellt werden."


def remember_late_receipt(db, job, result):
    """Keep a late generation ID for reconciliation, never publish the image."""
    from .ai_accounting import identifier, integer, micros

    raw = result.telemetry if result is not None and isinstance(result.telemetry, dict) else {}
    generation = identifier(raw.get("generation_id"))
    if not generation or job.kind not in ("public_image", "public_image_review"):
        return
    usage = db.scalar(select(Usage).where(Usage.job_id == job.id, Usage.child_id == job.child_id,
        Usage.family_id == job.payload.get("family_id"), Usage.provider == "openrouter")
        .with_for_update().execution_options(populate_existing=True))
    if not usage:
        return
    previous = usage.telemetry or {}
    if previous.get("generation_id") not in (None, generation):
        return
    closed = {"generation_id": generation, "late_discarded": True}
    for key in ("request_id", "upstream", "actual_model"):
        value = identifier(raw.get(key))
        if value is not None:
            closed[key] = value
    if micros(raw.get("billed_usd")) is not None:
        closed["billed_usd"] = str(raw["billed_usd"])
    for key, value in (("late_input_tokens", result.input_tokens), ("late_output_tokens", result.output_tokens),
                       ("late_cost_hint_micros", result.cost_micros)):
        value = integer(value)
        if value is not None:
            closed[key] = value
    usage.telemetry = {**previous, **closed}
