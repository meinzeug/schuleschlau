"""Private groundwork for exact fraction practice in initial package parts.

This module is deliberately not connected to the worker or provider. A plan is
not a learning record and does not authorize or fabricate a generated unit.
"""
import copy
import math
import re
from fractions import Fraction

from .math_tasks import _procedure_quote
from .package_prepared_graphics import _digest
from .study_fraction_expansions import _sources

REVISION = 'package-fraction-plan-1'
EXHAUSTED = 'Für diese Regel sind keine ausreichend verschiedenen neuen Brüche verfügbar.'
UNCLEAR = 'Frühere Bruchaufgaben können nicht sicher auf Wiederholungen geprüft werden.'
INVALID = 'Der Bruchplan oder seine Quellen sind nicht mehr gültig.'
_LITERAL = re.compile(r'(?<![\w/.,+−-])([0-9]{1,3})\s*(?:/|durch)\s*([1-9][0-9]{0,2})(?![\w/]|[.,][0-9])', re.I)
_LATEX = re.compile(r'\\(?:d?frac)\s*\{\s*([0-9]{1,3})\s*\}\s*\{\s*([1-9][0-9]{0,2})\s*\}')
_MIXED = re.compile(r'(?<![\w/])\d+\s+(?:\d+\s*/\s*\d+|\\(?:d?frac)\s*\{)')
_VULGAR = re.compile(r'[¼½¾⅐⅑⅒⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞]')
_METHOD = re.compile(r'\b(?:br(?:ü|ue|u)ch\w*|zähler|zaehler|nenner|'
                     r'erweiter(?:e|n|t|st|ung)|kürz(?:e|en|t|st|ung)|kuerz(?:e|en|t|st|ung))\b', re.I)


def values(text):
    """Parse literal fractions to exact values, including LaTeX notation."""
    if not isinstance(text, str):
        raise ValueError(INVALID)
    if _MIXED.search(text) or _VULGAR.search(text):
        raise ValueError(UNCLEAR)
    return {str(Fraction(int(m[1]), int(m[2]))) for pattern in (_LITERAL, _LATEX) for m in pattern.finditer(text)}


def history_exclusions(prompts):
    """Keep only numeric exclusions; ambiguous historical operations fail closed."""
    result = set()
    for prompt in prompts:
        if not isinstance(prompt, str):
            raise ValueError(INVALID)
        found = values(prompt)
        if _METHOD.search(prompt) and not found:
            raise ValueError(UNCLEAR)
        result.update(found)
    return sorted(result)


def history(db, child_id, *, ignore_job_ids=()):
    """Read only this child's numerical exclusions; caller must lock Child.

    Saved answers are never read. A pending private plan can only exclude a
    value, never prove mastery. This helper alone does not reserve or publish.
    """
    from sqlalchemy import select
    from .db import Job, LearningUnit, Material
    from .grades import subject_key
    from .package_question_history import unpublished_prompts_for_exclusion

    found = set()
    prompts = []
    for subject, questions in db.execute(select(LearningUnit.subject, LearningUnit.questions)
                                         .where(LearningUnit.child_id == child_id)):
        if subject_key(subject) != 'mathematik':
            continue
        if not isinstance(questions, list):
            raise ValueError(INVALID)
        for question in questions:
            if not isinstance(question, dict) or not isinstance(question.get('prompt'), str):
                raise ValueError(INVALID)
            prompts.append(question['prompt'])
    prompts.extend(unpublished_prompts_for_exclusion(db, child_id, 'Mathematik', ignore_job_ids=ignore_job_ids))
    found.update(history_exclusions(prompts))
    for subject, content in db.execute(select(Material.subject, Material.content)
            .where(Material.child_id == child_id, Material.confirmed.is_(True))):
        if subject_key(subject) == 'mathematik':
            found.update(values(content))
    ignored = set(ignore_job_ids)
    for job in db.scalars(select(Job).where(Job.child_id == child_id, Job.kind == 'package',
                                             Job.status.in_(['queued', 'running']))):
        if job.id in ignored:
            continue
        plan = job.payload.get('package_fraction_plan') if isinstance(job.payload, dict) else None
        if plan is None:
            # An old/concurrent package could still publish any fraction.
            # Without a persisted plan, its intended task cannot be excluded.
            raise ValueError(UNCLEAR)
        if (not isinstance(plan, dict) or plan.get('revision') != REVISION
                or plan.get('digest') != _digest({k: v for k, v in plan.items() if k != 'digest'})
                or not isinstance(plan.get('slots'), list)):
            raise ValueError(INVALID)
        for row in plan['slots']:
            if not isinstance(row, dict):
                raise ValueError(INVALID)
            task = row.get('task')
            if task is not None:
                if not isinstance(task, dict) or not isinstance(task.get('prompt'), str):
                    raise ValueError(INVALID)
                found.update(history_exclusions([task['prompt']]))
    return sorted(found)


def _pool(operation):
    """One canonical value per entry, with a bounded factor or divisor."""
    for denominator in range(2, 13):
        for numerator in range(1, denominator):
            if math.gcd(numerator, denominator) != 1:
                continue
            for factor in range(2, 5):
                if denominator * factor > 24:
                    continue
                if operation == 'expand':
                    yield numerator, denominator, factor, numerator * factor, denominator * factor
                else:
                    yield numerator * factor, denominator * factor, factor, numerator, denominator


def _core(ident, operation, row):
    n, d, factor, out_n, out_d = row
    if operation == 'expand':
        prompt = f'Erweitere den Bruch {n}/{d} mit dem Faktor {factor}. Gib den fertigen Bruch an.'
    else:
        prompt = f'Kürze den Bruch {n}/{d} durch den Teiler {factor}. Gib den fertigen Bruch an.'
    return {'id': ident, 'type': 'short', 'prompt': prompt, 'answer': f'{out_n}/{out_d}',
            'options': [], 'accepted': []}


def prepare(payload, slots, previous_prompts):
    """Plan only original, explicitly taught one-operation practice slots.

    Fixed diagnostic questions and open prior checks are returned unchanged.
    The output is a private test artifact until schema/worker/publication and
    concurrent history binding have been implemented and verified.
    """
    groups, context = payload.get('selected_groups'), payload.get('visual_context') or {}
    if (type(payload.get('package_partition')) is not int or not isinstance(groups, list)
            or len(groups) != 1 or not isinstance(groups[0], dict)
            or groups[0].get('subject') != 'Mathematik' or not isinstance(context, dict)
            or not context.get('required')):
        return None
    group = groups[0].get('id')
    if (not isinstance(group, str) or not group or not isinstance(slots, list) or not 1 <= len(slots) <= 5
            or not isinstance(payload.get('package_plan_digest'), str)
            or not re.fullmatch(r'[a-f0-9]{64}', payload['package_plan_digest'])):
        raise ValueError(INVALID)
    if any(not isinstance(s, dict) or not isinstance(s.get('id'), str) or not s['id'] for s in slots):
        raise ValueError(INVALID)
    if len({s['id'] for s in slots}) != len(slots):
        raise ValueError(INVALID)
    sources = _sources(context, group_id=group)
    if not sources:
        return None
    rule = {name: _procedure_quote(sources, label) for name, label in
            (('expand', 'Brüche erweitern'), ('reduce', 'Brüche kürzen'))}
    eligible = [(name, quote) for name, quote in rule.items() if quote]
    # A mixed page has two different eligible procedures; a topic title alone
    # cannot determine which one the child has actually selected.
    if len(eligible) != 1:
        return None
    operation, quote = eligible[0]
    source = next((s for s in sources if quote in s['content']), None)
    if source is None:
        raise ValueError(INVALID)
    recipe_id = {'expand': 'math.fraction.expansion', 'reduce': 'math.fraction.reduction'}[operation]
    references = context.get('references', [])
    if not isinstance(references, list):
        raise ValueError(INVALID)
    selected_refs = [r for r in references if isinstance(r, dict) and r.get('id') == recipe_id
                     and type(r.get('version')) is int and r['version'] == 1 and r.get('subject') == 'Mathematik'
                     and isinstance(r.get('digest'), str) and re.fullmatch(r'[a-f0-9]{64}', r['digest'])]
    if len(selected_refs) != 1:
        return None
    excluded = set(history_exclusions(previous_prompts))
    for row in sources:
        excluded.update(values(row['content']))
    free = [s for s in slots if s.get('role') == 'practice' and 'type' not in s]
    choices, seen = [], set(excluded)
    for row in _pool(operation) if free else ():
        n, d = row[:2]
        key = str(Fraction(n, d))
        if key in seen:
            continue
        seen.add(key)
        choices.append(row)
        if len(choices) == len(free):
            break
    if len(choices) < len(free):
        raise ValueError(EXHAUSTED)
    selected = iter(choices)
    planned = []
    for slot in slots:
        if slot not in free:
            planned.append({'slot': copy.deepcopy(slot), 'task': None})
            continue
        row = next(selected)
        task = _core(slot['id'], operation, row)
        if 'learning_goal_id' in slot:
            if not isinstance(slot['learning_goal_id'], str) or not slot['learning_goal_id']:
                raise ValueError(INVALID)
            task['learning_goal_id'] = slot['learning_goal_id']
        planned.append({'slot': copy.deepcopy(slot), 'task': task,
                        'input': list(row[:2]), 'factor_or_divisor': row[2], 'output': list(row[3:])})
    value = {'version': 1, 'revision': REVISION, 'operation': operation, 'group_id': group,
             'partition': payload['package_partition'], 'package_plan_digest': payload.get('package_plan_digest'),
             'source_ref': source['ref'], 'source_digest': _digest(source), 'source_excerpt': quote,
             'reference': {'id': recipe_id, 'version': 1, 'digest': selected_refs[0]['digest']},
             'excluded_values': sorted(excluded), 'slots': planned}
    return {**value, 'digest': _digest(value)}


def validate(payload, slots, previous_prompts, saved):
    """Recompute against current authoritative inputs; never repair a plan."""
    if not isinstance(saved, dict) or saved.get('digest') != _digest({k: v for k, v in saved.items() if k != 'digest'}):
        raise ValueError(INVALID)
    if prepare(payload, slots, previous_prompts) != saved:
        raise ValueError(INVALID)


def validate_reference(db, saved):
    """Authenticate the exact recipe against the immutable stored version."""
    from .visual_reference_models import VisualReference

    if not isinstance(saved, dict) or not isinstance(saved.get('reference'), dict):
        raise ValueError(INVALID)
    ref = saved['reference']
    expected = {'expand': 'math.fraction.expansion', 'reduce': 'math.fraction.reduction'}.get(saved.get('operation'))
    if ref.get('id') != expected or type(ref.get('version')) is not int or ref['version'] != 1:
        raise ValueError(INVALID)
    stored = db.get(VisualReference, (ref['id'], ref['version']), populate_existing=True)
    if (stored is None or not isinstance(stored.recipe, dict) or stored.digest != ref.get('digest')
            or _digest(stored.recipe) != stored.digest or 'Mathematik' not in stored.recipe.get('subjects', [])
            or stored.recipe.get('kind') != 'fraction' or stored.recipe.get('id') != expected
            or stored.recipe.get('version') != 1 or stored.recipe.get('scope') != 'unit_composition_only'):
        raise ValueError(INVALID)


def graphic_blocks(plan, row):
    """Return two exact fraction models for a locally planned solution."""
    from .subject_content import Graphic

    if row not in plan['slots'] or not isinstance(row.get('task'), dict):
        raise ValueError(INVALID)
    blocks = []
    for title, numbers in (('Vor dem Rechenschritt', row['input']), ('Nach dem Rechenschritt', row['output'])):
        blocks.append(Graphic.model_validate({'kind': 'fraction', 'title': title,
            'source_excerpt': plan['source_excerpt'], 'labels': [], 'numbers': numbers,
            'connections': [], 'marks': [], 'unit': '', 'variant': '', 'disclosure': 'solution'}).model_dump(mode='json'))
    return blocks


def validate_bound_tasks(payload, slots, previous_prompts, saved, questions, graphics):
    """Check planned core and graphics without changing a provider response.

    This isolated proof helper is not a substitute for source authorization,
    provider schemas, database locking or publication-time history checks.
    """
    validate(payload, slots, previous_prompts, saved)
    if not isinstance(questions, list) or len(questions) != len(slots) or not isinstance(graphics, dict):
        raise ValueError(INVALID)
    if any(not isinstance(q, dict) or not isinstance(q.get('id'), str) for q in questions):
        raise ValueError(INVALID)
    actual = {q['id']: q for q in questions}
    if len(actual) != len(questions) or set(actual) != {s['id'] for s in slots}:
        raise ValueError(INVALID)
    planned_ids = {row['slot']['id'] for row in saved['slots'] if row.get('task') is not None}
    if set(graphics) != planned_ids:
        raise ValueError(INVALID)
    for row in saved['slots']:
        ident, task = row['slot']['id'], row.get('task')
        # Any pre-existing diagnostic core is immutable. Open prior checks
        # have no fixed answer and are deliberately not fabricated here.
        fixed = task or {k: row['slot'][k] for k in ('id', 'type', 'prompt', 'answer', 'options', 'accepted', 'learning_goal_id')
                         if k in row['slot']}
        if any(actual[ident].get(key) != value for key, value in fixed.items()):
            raise ValueError(INVALID)
        if task is not None and graphics[ident] != graphic_blocks(saved, row):
            raise ValueError(INVALID)
