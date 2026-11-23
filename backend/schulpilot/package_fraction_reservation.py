"""Private transaction for planned fraction package parts.

The package worker reserves plans before dispatch and validates them again
after the provider call and before publication. Callers own transactions.
"""
import copy
from fractions import Fraction

from sqlalchemy import select, update

from . import package_fraction_plan as fractions
from .db import Child, Job

INVALID = 'Die Vorbereitung des Bruchplans ist nicht mehr gültig.'


def purge_source_plans(db, child_id, material_ids):
    """Forget private source excerpts from job plans before source erasure.

    The child/source owner remains responsible for locks, journal and deleting
    units. Corrupt source lists cannot establish ownership, so their unusable
    plans are scrubbed conservatively even during global journal replay.
    """
    ids = set(material_ids)
    if not ids:
        return set()
    affected_days = set()
    query = select(Job).where(Job.kind == 'package')
    if child_id is not None:
        query = query.where(Job.child_id == child_id)
    for job in db.scalars(query):
        if not isinstance(job.payload, dict) or 'package_fraction_plan' not in job.payload:
            continue
        sources = job.payload.get('package_partition_sources')
        invalid = (not isinstance(sources, list) or any(not isinstance(row, dict) or not isinstance(row.get('id'), str)
                                                        for row in sources))
        if invalid or any(row['id'] in ids for row in sources):
            if isinstance(job.payload.get('school_day_id'), str):
                affected_days.add(job.payload['school_day_id'])
            job.payload = {key: value for key, value in job.payload.items() if key != 'package_fraction_plan'}
    return affected_days


def _checked_payload(db, job, payload, pages):
    from .learning_entry import _specs, guard_entry_context
    from .source_lineage import learning_source

    data = job.payload
    groups = data.get('groups')
    selected = payload.get('selected_groups') if isinstance(payload, dict) else None
    if (not isinstance(groups, list) or len(groups) != 1 or not isinstance(groups[0], dict)
            or not isinstance(selected, list) or len(selected) != 1 or not isinstance(selected[0], dict)
            or selected[0].get('id') != groups[0].get('id')
            or selected[0].get('subject') != groups[0].get('subject')
            or selected[0].get('estimated_minutes') != groups[0].get('estimated_minutes')
            or payload.get('package_partition') != data.get('package_partition')
            or payload.get('package_plan_digest') != data.get('package_plan_digest')):
        raise ValueError(INVALID)
    group = groups[0]
    material_ids = group.get('material_ids')
    if not isinstance(material_ids, list) or not material_ids or len(set(material_ids)) != len(material_ids):
        raise ValueError(INVALID)
    page_map = {page.id: page for page in pages if page.id in material_ids}
    if set(page_map) != set(material_ids) or any(page.child_id != job.child_id for page in page_map.values()):
        raise ValueError(INVALID)
    visual = payload.get('visual_context')
    if not isinstance(visual, dict) or not isinstance(visual.get('sources'), list):
        raise ValueError(INVALID)
    original = [row for row in visual['sources'] if isinstance(row, dict) and not row.get('source_type')]
    if len(original) != len(page_map) or len({row.get('material_id') for row in original}) != len(page_map):
        raise ValueError(INVALID)
    ordered_pages = [page for page in pages if page.id in page_map]
    if [row.get('material_id') for row in original] != [page.id for page in ordered_pages]:
        raise ValueError(INVALID)
    for index, row in enumerate(original, start=1):
        page = page_map.get(row.get('material_id'))
        if (page is None or row.get('ref') != f'p{index}' or row.get('group_id') != group['id']
                or row.get('revision') != page.revision):
            raise ValueError(INVALID)
        safe = learning_source(db, page, revision=page.revision)
        if (row.get('subject') != page.subject or row.get('topic') != page.topic
                or any(row.get(key) != safe.get(key) for key in ('content', 'source_refs', 'factual_status'))):
            raise ValueError(INVALID)
    child = db.get(Child, job.child_id, populate_existing=True)
    guard_entry_context(db, child, payload, list(page_map.values()))
    entry = payload.get('learning_entry')
    if not isinstance(entry, dict) or not isinstance(entry.get('units'), list) or len(entry['units']) != 1:
        return None
    target = entry['units'][0]
    if (not isinstance(target, dict) or target.get('group_id') != group['id']
            or target.get('subject') != group['subject'] or target.get('entry_mode') == 'existing_contract'):
        return None
    return _specs(target, 2)


def prepare(db, job_id, payload, *, require_existing=False):
    """Lock Child, recheck authority and reserve one source-bound private plan.

    Must be called in a clean, fresh transaction; returns the augmented request.
    A failed check does not alter a saved receipt or authorize provider calls.
    """
    from .model_routing import job_config
    from .school_day import validate_package_sources
    from .school_preparation import validate_job
    from .worker import validate_submission_authority

    if db.new or db.dirty or db.deleted:
        raise ValueError(INVALID)
    db.expire_all()
    child_id = db.scalar(select(Job.child_id).where(Job.id == job_id))
    if child_id is None or not db.execute(update(Child).where(Child.id == child_id).values(grade=Child.grade)).rowcount:
        raise ValueError(INVALID)
    job = db.get(Job, job_id, populate_existing=True)
    if (job is None or job.child_id != child_id or job.kind != 'package' or job.status != 'running'
            or not isinstance(job.payload, dict) or not job.payload.get('preparation_id')
            or type(job.payload.get('package_partition')) is not int):
        raise ValueError(INVALID)
    validate_job(db, job)
    validate_submission_authority(db, job)
    job_config(db, job)
    _, pages = validate_package_sources(db, job)
    slots = _checked_payload(db, job, payload, pages)
    if slots is None:
        return payload
    enriched = fractions.add_reference(db, payload)
    # A missing or ambiguous explicit rule is ineligible, not an invented task.
    provisional = fractions.prepare(enriched, slots, [])
    if provisional is None:
        return payload
    prior = fractions.history(db, child_id, ignore_job_ids={job.id})
    counts = (fractions.operation_history(db, child_id, ignore_job_ids={job.id})
              if provisional.get('mixed_rule') else None)
    saved = job.payload.get('package_fraction_plan')
    if saved is None:
        if require_existing:
            raise ValueError(INVALID)
        saved = fractions.prepare(enriched, slots, prior, operation_counts=counts)
        fractions.validate_reference(db, saved)
        job.payload = {**job.payload, 'package_fraction_plan': copy.deepcopy(saved)}
        db.flush()
    else:
        fractions.validate(enriched, slots, saved.get('excluded_values', []), saved, operation_counts=counts)
        fractions.validate_reference(db, saved)
        used = {str(Fraction(*row['input'])) for row in saved['slots'] if row.get('task') is not None}
        if used.intersection(prior):
            raise ValueError(fractions.UNCLEAR)
    return {**enriched, 'package_fraction_plan': copy.deepcopy(saved)}


def validate_result(db, job_id, payload, output):
    """Recheck the persisted plan, authority and actual output under Child lock.

    This is not the publication guard and it cannot reserve a missing plan.
    """
    expected = payload.get('package_fraction_plan') if isinstance(payload, dict) else None
    if not isinstance(expected, dict):
        raise ValueError(INVALID)
    checked = prepare(db, job_id, payload, require_existing=True)
    if checked.get('package_fraction_plan') != expected:
        raise ValueError(INVALID)
    slots = [row['slot'] for row in expected['slots']]
    fractions.validate_generated_output(checked, slots, expected['excluded_values'], expected, output)


def validate_publication(db, job, child, context, output, pages):
    """Recheck a finished private receipt while the caller holds Child lock.

    Legacy receipts without a plan retain their existing validation. A plan in
    only one of the two independent private records is never accepted.
    """
    if not isinstance(job.payload, dict) or not isinstance(context, dict):
        raise ValueError(INVALID)
    plan = job.payload.get('package_fraction_plan')
    visual = context.get('visual_context')
    visual_plan = visual.get('package_fraction_plan') if isinstance(visual, dict) else None
    if plan is None and visual_plan is None:
        return None
    if (not isinstance(plan, dict) or visual_plan != plan or job.kind != 'package'
            or job.status != 'completed' or job.child_id != child.id):
        raise ValueError(INVALID)
    groups = job.payload.get('groups')
    if not isinstance(groups, list) or len(groups) != 1 or not isinstance(groups[0], dict):
        raise ValueError(INVALID)
    group = groups[0]
    payload = {'visual_context': visual, 'learning_entry': context.get('learning_entry'),
               'package_partition': job.payload.get('package_partition'),
               'package_plan_digest': job.payload.get('package_plan_digest'),
               'selected_groups': [{'id': group.get('id'), 'subject': group.get('subject'),
                                    'estimated_minutes': group.get('estimated_minutes')}]}
    slots = _checked_payload(db, job, payload, pages)
    if slots is None:
        raise ValueError(INVALID)
    prior = fractions.history(db, child.id, ignore_job_ids={job.id})
    counts = (fractions.operation_history(db, child.id, ignore_job_ids={job.id})
              if plan.get('mixed_rule') else None)
    fractions.validate(payload, slots, plan.get('excluded_values', []), plan, operation_counts=counts)
    fractions.validate_reference(db, plan)
    used = {str(Fraction(*row['input'])) for row in plan['slots'] if row.get('task') is not None}
    if used.intersection(prior):
        raise ValueError(fractions.UNCLEAR)
    fractions.validate_generated_output(payload, slots, plan['excluded_values'], plan, output)
    return plan
