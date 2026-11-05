"""Private package questions used only as conservative novelty exclusions.

Callers that make a publish/store decision must already hold the Child row lock.
This reader neither writes state nor sends prompts or answers to a provider.
"""
import logging

from sqlalchemy import select

from .db import Child, Job, SchoolDay, Usage, now
from .grades import subject_key
from .package_partitions import validated_parts

log = logging.getLogger(__name__)


def unpublished_prompts_for_exclusion(db, child_id, subject, *, ignore_job_ids=()):
    """Read only negative exclusions, never authority or proof of learning.

    An old deliberately inactive preparation may have legitimately lost its
    30-day Job/90-day Usage. A structurally bound receipt from such a day can
    only suppress a repeat; it cannot establish authorship or publication rights.
    """
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
            cutoff30, cutoff90 = int(now()) - 30 * 86400, int(now()) - 90 * 86400
            inactive = state.get('status') in ('postponed', 'saved')
            missing_job_expired = (job is None and inactive and day.created < cutoff30
                and (usage.created < cutoff30 if usage is not None else day.created < cutoff90))
            missing_usage_expired = (usage is None and inactive and day.created < cutoff90
                and (job.created < cutoff90 if job is not None else missing_job_expired))
            if not missing_job_expired and (job is None or job.child_id != child_id or job.kind != 'package'
                    or job.status != 'completed' or not isinstance(job.payload, dict)
                    or job.payload.get('school_day_id') != day.id
                    or job.payload.get('package_plan_digest') != plan['digest']
                    or job.payload.get('package_partition') != part['index']):
                raise ValueError('Ein privater Teilrundenbeleg ist nicht mehr gültig.')
            if ((usage is None and not missing_usage_expired) or (usage is not None and (usage.child_id != child_id
                    or usage.status != 'completed' or usage.function != 'package'
                    or usage.family_id != child.family_id
                    or usage.provider != part['provider'] or usage.model != part['model']
                    or usage.config_revision != plan['config_revision']))):
                raise ValueError('Ein privater Teilrundenbeleg ist nicht mehr gültig.')
            if missing_job_expired or missing_usage_expired:
                # Closed diagnostic only: never log identifiers or content.
                log.warning('expired_unverified_package_receipt_used_only_for_exclusion')
            if part['job_id'] in ignored:
                continue
            for unit in part['output']['units']:
                for question in unit['questions']:
                    prompt = question.get('prompt')
                    if not isinstance(prompt, str) or not prompt.strip():
                        raise ValueError('Eine private Teilrundenfrage ist nicht prüfbar.')
                    prompts.append(prompt)
    return prompts
