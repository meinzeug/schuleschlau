"""Validated private package questions awaiting publication, scoped to one child.

Callers that make a publish/store decision must already hold the Child row lock.
This reader neither writes state nor sends prompts or answers to a provider.
"""
from sqlalchemy import select

from .db import Child, Job, SchoolDay, Usage
from .grades import subject_key
from .package_partitions import validated_parts


def unpublished_prompts(db, child_id, subject, *, ignore_job_ids=()):
    """Read every validated staged prompt of a subject; corrupt receipts fail closed."""
    ignored = set(ignore_job_ids)
    prompts = []
    child = db.get(Child, child_id, populate_existing=True)
    if child is None:
        raise ValueError('Das Kind für den Lernpaketverlauf ist nicht mehr vorhanden.')
    days = db.scalars(select(SchoolDay).where(SchoolDay.child_id == child_id)
        .order_by(SchoolDay.school_date, SchoolDay.id).execution_options(populate_existing=True))
    for day in days:
        state = day.preparation if day.preparation is not None else {}
        if not isinstance(state, dict):
            raise ValueError('Ein privater Lernpaketstand ist nicht prüfbar.')
        outputs = state.get('package_outputs')
        if outputs is None or outputs == {}:
            continue
        if not isinstance(outputs, dict):
            raise ValueError('Ein privater Teilrundenbeleg ist nicht prüfbar.')
        plan = state.get('package_plan')
        try:
            parts = validated_parts(state, plan, require_complete=False)
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError('Ein privater Teilrundenbeleg ist nicht prüfbar.') from error
        if plan.get('child_id') != child_id or plan.get('school_day_id') != day.id:
            raise ValueError('Ein privater Teilrundenbeleg gehört zu einer anderen Vorbereitung.')
        for part in parts:
            if subject_key(part['group']['subject']) != subject_key(subject):
                continue
            job = db.get(Job, part['job_id'])
            usage = db.scalar(select(Usage).where(Usage.job_id == part['job_id']))
            if (job is None or job.child_id != child_id or job.kind != 'package'
                    or job.status != 'completed' or not isinstance(job.payload, dict)
                    or job.payload.get('school_day_id') != day.id
                    or job.payload.get('package_plan_digest') != plan['digest']
                    or job.payload.get('package_partition') != part['index']
                    or usage is None or usage.child_id != child_id
                    or usage.status != 'completed' or usage.function != 'package'
                    or usage.family_id != child.family_id
                    or usage.provider != part['provider'] or usage.model != part['model']
                    or usage.config_revision != plan['config_revision']):
                raise ValueError('Ein privater Teilrundenbeleg ist nicht mehr gültig.')
            if part['job_id'] in ignored:
                continue
            for unit in part['output']['units']:
                for question in unit['questions']:
                    prompt = question.get('prompt')
                    if not isinstance(prompt, str) or not prompt.strip():
                        raise ValueError('Eine private Teilrundenfrage ist nicht prüfbar.')
                    prompts.append(prompt)
    return prompts
