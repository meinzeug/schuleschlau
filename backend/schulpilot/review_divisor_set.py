"""A closed, source-bound divisor-set exercise; no inferred transcription."""
import copy
import json
import re
import unicodedata
from pathlib import Path

from .package_prepared_graphics import _digest
from .review_divisibility_product import WARNING
from .review_number_words import written_numbers
from .subject_content import Graphic
from .visual_reference_schemas import ExplanationStep

RECIPE = 'math.divisibility.verified_set'
VERSION = 1
REVISION = 'review-divisor-set-1'
ERROR = 'Die Teileraufgabe ist nicht eindeutig an die bestätigte Teilermenge gebunden.'
LABEL = re.compile(r'Die Teiler von ([1-9][0-9]{0,2}) vollständig angeben[.!?]?', re.I)
SET = re.compile(r'(?<!\w)T\s*(?:_\s*)?(?:\{\s*)?([1-9][0-9]{0,2})(?:\s*\})?\s*=\s*(?:\\left\s*)?\\?\{\s*([0-9]{1,3}(?:\s*[,;]\s*[0-9]{1,3}){1,11})\s*(?:\\right\s*)?\\?\}(?!\s*(?:[∪∩+−\-*/×·=:]|\\(?:cup|cap|cdot|times)))', re.I)


def supports_label(value):
    return isinstance(value, str) and LABEL.fullmatch(' '.join(value.split())) is not None


def public_recipe():
    rows = json.loads((Path(__file__).with_name('reference') / 'visual-v1.json').read_text())['references']
    return next(row for row in rows if row['id'] == RECIPE and row['version'] == VERSION)


def _reference(context):
    expected = _digest(public_recipe())
    return next((row for row in context.get('references', []) if row.get('id') == RECIPE
        and type(row.get('version')) is int and row['version'] == VERSION
        and row.get('subject') == 'Mathematik' and row.get('kind') == 'scene'
        and row.get('digest') == expected), None)


def _evidence(context, task):
    if (not isinstance(task, dict) or not re.fullmatch(r'q[1-9][0-9]*', task.get('id', ''))
            or not re.fullmatch(r'g[1-9][0-9]*', task.get('learning_goal_id', ''))
            or not supports_label(task.get('label'))):
        return None
    label = LABEL.fullmatch(' '.join(task['label'].split()))
    quote = task.get('source_excerpt')
    if not isinstance(quote, str) or not quote.strip() or len(quote) > 500 or WARNING.search(quote):
        return None
    matches = list(SET.finditer(unicodedata.normalize('NFKC', quote)))
    if len(matches) != 1:
        return None
    number = int(matches[0][1])
    values = [int(v) for v in re.findall(r'\d+', matches[0][2])]
    if (number != int(label[1]) or not 2 <= number <= 120 or not 2 <= len(values) <= 12
            or values != sorted(set(values)) or values != [n for n in range(1, number + 1) if number % n == 0]):
        return None
    sources = [source for source in context.get('sources', []) if not source.get('source_type')
        and source.get('subject') == 'Mathematik' and source.get('group_id') is None
        and source.get('factual_status') != 'blocked'
        and re.fullmatch(r'p[1-9][0-9]?', source.get('ref', ''))
        and re.fullmatch(r'[a-f0-9]{32}', source.get('material_id', ''))
        and type(source.get('revision')) is int and source['revision'] >= 1
        and isinstance(source.get('content'), str) and quote in source['content']]
    if len(sources) != 1:
        return None
    content = sources[0]['content']
    if content.count(quote) != 1:
        return None
    normalized_content = unicodedata.normalize('NFKC', content)
    normalized_quote = unicodedata.normalize('NFKC', quote)
    if normalized_content.count(normalized_quote) != 1:
        return None
    absolute_start = normalized_content.index(normalized_quote) + matches[0].start()
    absolute_end = normalized_content.index(normalized_quote) + matches[0].end()
    before = normalized_content[normalized_content.rfind('\n', 0, absolute_start) + 1:absolute_start].rstrip()
    end_line = normalized_content.find('\n', absolute_end)
    after = normalized_content[absolute_end:end_line if end_line >= 0 else len(normalized_content)].lstrip()
    if (before and (unicodedata.category(before[-1]) == 'Sm' or before[-1] in '-/^*'
                    or re.search(r'\\[A-Za-z]+$', before))):
        return None
    if (after and (unicodedata.category(after[0]) == 'Sm' or after[0] in '-/^*'
                   or re.match(r'\\[A-Za-z]+', after))):
        return None
    if not any(match.start() == absolute_start and match.end() == absolute_end
               for match in SET.finditer(normalized_content)):
        return None
    start = content.index(quote)
    begin = content.rfind('\n', 0, start) + 1
    end = content.find('\n', start + len(quote))
    lines = content[begin:end if end >= 0 else len(content)]
    if WARNING.search(lines) or any(mark in lines for mark in ('~~', '<s>', '</s>', '̶')):
        return None
    return sources[0], quote, number, values


def _graphic(quote, number, values):
    ids = [f'divisor{i}' for i in range(1, len(values) + 1)]
    labels = [str(value) for value in values]
    objects = [{'id': i, 'label': value, 'shape': 'circle', 'tone': 'accent'}
               for i, value in zip(ids, labels, strict=True)]
    placements = [{'object_id': i, 'slot': index} for index, i in enumerate(ids)]
    block = {'kind': 'scene', 'title': 'Alle Teiler', 'disclosure': 'solution', 'source_excerpt': quote,
        'labels': labels, 'numbers': [], 'connections': [], 'marks': [], 'unit': '', 'variant': '', 'text_probe': None, 'lab': None,
        'scene': {'version': 1, 'layout': 'grid', 'objects': objects, 'transition_ms': 300, 'steps': [
            {'caption': f'Diese Zahlen teilen {number} ohne Rest.', 'source_excerpt': quote,
             'placements': placements, 'highlight': ids[:1], 'edges': []},
            {'caption': f'Alle angezeigten Zahlen sind Teiler von {number}.', 'source_excerpt': quote,
             'placements': placements, 'highlight': ids, 'edges': []}]}}
    return Graphic.model_validate(block).model_dump(mode='json')


def compile_candidate(context, task, history=()):
    if not isinstance(history, (list, tuple)) or any(not isinstance(p, str) for p in history):
        raise ValueError(ERROR)
    evidence = _evidence(context, task)
    if evidence is None or _reference(context) is None:
        return None
    source, quote, number, values = evidence
    if number in written_numbers(history) or any(re.search(rf'(?<!\d){number}(?!\d)', p) for p in history):
        return None
    question = {'id': task['id'], 'learning_goal_id': task['learning_goal_id'], 'type': 'short',
        'prompt': f'Nenne alle positiven Teiler von {number}. Trenne sie durch Kommas.',
        'answer': ', '.join(map(str, values)), 'options': [], 'accepted': []}
    row = {'subject': 'Mathematik', 'group_id': None, 'kind': 'scene', 'disclosure': 'solution',
        'reference': {'id': RECIPE, 'version': VERSION}, 'source_refs': [source['ref']],
        'text': f'Alle gezeigten Zahlen teilen {number} ohne Rest.',
        'block': _graphic(quote, number, values),
        'proof': {'version': 1, 'revision': REVISION, 'source_digest': _digest(source),
            'task': {key: copy.deepcopy(task[key]) for key in ('id', 'learning_goal_id', 'source_excerpt')},
            'question': copy.deepcopy(question), 'reference_digest': _reference(context)['digest']}}
    row['id'] = 'ds_' + _digest([REVISION, _digest(context), row])[:24]
    return question, row


def step_for(candidate):
    return {'id': candidate['id'], 'text': candidate['text'], 'competence_id': None,
        'disclosure': 'solution', 'reference': candidate['reference'], 'source_refs': candidate['source_refs'],
        'presentation': {'version': 1, 'evidence_kind': 'knowledge', 'blocks': [candidate['block']]}}


def validate_step(raw, context, question, task, history=()):
    candidate = compile_candidate(context, task, history)
    if candidate is None or question is None or any(question.get(k) != v for k, v in candidate[0].items()):
        raise ValueError(ERROR)
    if _digest(ExplanationStep.model_validate(raw).model_dump(mode='json')) != _digest(step_for(candidate[1])):
        raise ValueError(ERROR)
