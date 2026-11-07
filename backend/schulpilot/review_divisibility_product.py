"""A bounded review visualization of a literal confirmed factor example.

This is deliberately not a divisibility-rule generator. An OCR transcription is
not proof of photographic accuracy. The caller must use an explicitly confirmed
source and preserve its revision, exact task evidence and history.
"""
import copy
import json
import re
from pathlib import Path

from .package_prepared_graphics import _digest
from .subject_content import Graphic
from .visual_reference_schemas import ExplanationStep

RECIPE = 'math.divisibility.verified_product'
VERSION = 1
REVISION = 'review-divisibility-product-1'
ERROR = 'Die Teilbarkeitsaufgabe ist nicht eindeutig an das bestätigte Beispiel gebunden.'
PRODUCT = re.compile(r'(?<![\w.,/\-])([2-5])\s*(?:·|⋅|×|\*|\\cdot)\s*([2-6])\s*=\s*([0-9]{1,2})(?![\w.,/])(?!(?:\s*[+\-−×⋅·*/=:]))')
WARNING = re.compile(r'\b(?:nicht|kein\w*|falsch\w*|durchgestrichen\w*|unsicher\w*|unleserlich\w*)\b', re.I)


def public_recipe():
    rows = json.loads((Path(__file__).with_name('reference') / 'visual-v1.json').read_text())['references']
    return next(r for r in rows if r['id'] == RECIPE and r['version'] == VERSION)


def _reference(context):
    digest = _digest(public_recipe())
    return next((r for r in context.get('references', []) if r.get('id') == RECIPE and
        type(r.get('version')) is int and r['version'] == VERSION and r.get('subject') == 'Mathematik'
        and r.get('kind') == 'scene' and r.get('digest') == digest), None)


def supports_label(value):
    if not isinstance(value, str):
        return False
    label = ' '.join(value.split()).rstrip('.!?')
    return re.fullmatch(r'(?:Teilbarkeit|Teiler|Einen Teiler (?:einer Zahl )?bestimmen)', label, re.I) is not None


def _core(task, a, b, result):
    return {'id': task['id'], 'learning_goal_id': task['learning_goal_id'], 'type': 'short',
        'prompt': f'{a} · ? = {result}. Welcher Teiler von {result} fehlt?',
        'answer': str(b), 'options': [], 'accepted': []}


def _evidence(context, task):
    if (not isinstance(task, dict) or not re.fullmatch(r'q[1-9][0-9]*', task.get('id', ''))
            or not re.fullmatch(r'g[1-9][0-9]*', task.get('learning_goal_id', ''))
            or not supports_label(task.get('label'))):
        return None
    quote = task.get('source_excerpt')
    if not isinstance(quote, str) or not quote.strip() or len(quote) > 500 or WARNING.search(quote):
        return None
    matches = list(PRODUCT.finditer(quote))
    if len(matches) != 1:
        return None
    a, b, result = map(int, matches[0].groups())
    if a * b != result or result > 24:
        return None
    # Ambiguous occurrences across sources are not a reliable citation.
    sources = [s for s in context.get('sources', []) if not s.get('source_type')
        and s.get('subject') == 'Mathematik' and s.get('group_id') is None
        and s.get('factual_status') != 'blocked'
        and re.fullmatch(r'p[1-9][0-9]?', s.get('ref', ''))
        and re.fullmatch(r'[a-f0-9]{32}', s.get('material_id', ''))
        and type(s.get('revision')) is int and s['revision'] >= 1
        and isinstance(s.get('content'), str) and quote in s['content']]
    if len(sources) != 1:
        return None
    # A fragment may omit a correction or strikeout in the same source line.
    lines = [line for line in sources[0]['content'].splitlines() if quote in line]
    if len(lines) != 1 or WARNING.search(lines[0]) or any(mark in lines[0] for mark in ('~~', '<s>', '</s>', '̶')):
        return None
    return sources[0], quote, a, b, result


def safe_hint(context, task):
    evidence = _evidence(context, task)
    if evidence is None:
        raise ValueError(ERROR)
    _, _, a, _, result = evidence
    return f'Zähle in {a}er-Schritten bis {result}. Wie viele Schritte sind es?'


def _graphic(quote, a, b, result):
    ids = [f'group{i}' for i in range(1, a + 1)]
    labels = [' '.join(['●'] * b) for _ in ids]
    objects = [{'id': i, 'label': label, 'shape': 'box', 'tone': 'accent'} for i, label in zip(ids, labels, strict=True)]
    placements = [{'object_id': i, 'slot': n} for n, i in enumerate(ids)]
    block = {'kind': 'scene', 'title': 'Gleich große Gruppen', 'disclosure': 'solution', 'source_excerpt': quote,
        'labels': labels, 'numbers': [], 'connections': [], 'marks': [], 'unit': '', 'variant': '', 'text_probe': None, 'lab': None,
        'scene': {'version': 1, 'layout': 'row', 'objects': objects, 'transition_ms': 300, 'steps': [
            {'caption': f'Eine Gruppe enthält {b} Punkte.', 'source_excerpt': quote, 'placements': placements, 'highlight': [ids[0]], 'edges': []},
            {'caption': f'{a} Gruppen mit je {b} Punkten ergeben {result}.', 'source_excerpt': quote, 'placements': placements, 'highlight': ids, 'edges': []}]}}
    return Graphic.model_validate(block).model_dump(mode='json')


def compile_candidate(context, task, history=()):
    """Return (fixed question, visual candidate) or None if the source is insufficient."""
    if not isinstance(history, (list, tuple)) or any(not isinstance(s, str) for s in history):
        raise ValueError(ERROR)
    evidence = _evidence(context, task)
    if evidence is None or _reference(context) is None:
        return None
    source, quote, a, b, result = evidence
    if any(re.search(rf'(?<!\d){result}(?!\d)', s) for s in history):
        return None
    question = _core(task, a, b, result)
    row = {'subject': 'Mathematik', 'group_id': None, 'kind': 'scene', 'disclosure': 'solution',
        'reference': {'id': RECIPE, 'version': VERSION}, 'source_refs': [source['ref']],
        'text': f'{a} Gruppen mit je {b} Punkten ergeben {result}. {a} · {b} = {result}. {a} und {b} sind Teiler von {result}.',
        'block': _graphic(quote, a, b, result),
        'proof': {'version': 1, 'revision': REVISION, 'source_digest': _digest(source),
            'task': {key: copy.deepcopy(task[key]) for key in ('id', 'learning_goal_id', 'source_excerpt')}, 'question': copy.deepcopy(question), 'reference_digest': _reference(context)['digest']}}
    row['id'] = 'dv_' + _digest([REVISION, _digest(context), row])[:24]
    return question, row


def step_for(candidate):
    return {'id': candidate['id'], 'text': candidate['text'], 'competence_id': None,
        'disclosure': 'solution', 'reference': candidate['reference'], 'source_refs': candidate['source_refs'],
        'presentation': {'version': 1, 'evidence_kind': 'knowledge', 'blocks': [candidate['block']]}}


def validate_step(raw, context, question, task, history=()):
    candidate = compile_candidate(context, task, history)
    if candidate is None or question is None or any(question.get(k) != v for k, v in candidate[0].items()):
        raise ValueError(ERROR)
    step = ExplanationStep.model_validate(raw).model_dump(mode='json')
    if _digest(step) != _digest(step_for(candidate[1])):
        raise ValueError(ERROR)
