"""A small, source-bound compiler for a literally written multiples sequence.

The parser accepts a whole, correct line, never a partial OCR fragment. The
source projection supplied by the caller already excludes uncertain blocks.
"""
import json
import re
from pathlib import Path

from . import package_prepared_graphics as prepared

REFERENCE = "math.multiples.verified_sequence"
REVISION = "multiples-sequence-1"
HISTORY = "multiples_sequence_history"

_LINE = re.compile(
    r"^[ \t]*(?:\\\([ \t]*)?V[ \t]*_[ \t]*\{[ \t]*([0-9]{1,2})[ \t]*\}"
    r"[ \t]*=[ \t]*(?:\\left[ \t]*)?\\?\{[ \t]*"
    r"([0-9]{1,3}(?:[ \t]*;[ \t]*[0-9]{1,3}){1,5})[ \t]*"
    r"(?:;?[ \t]*(?:\\ldots|\\dots|…|\.\.\.))?[ \t]*"
    r"(?:\\right[ \t]*)?\\?\}(?:[ \t]*\\\))?[ \t]*$"
)
_HEADING = re.compile(r"\bVielfach(?:e|en|es|er)?\b", re.IGNORECASE)
_WARNING = re.compile(r"\b(?:falsch|unsicher|unleserlich|durchgestrichen)\w*\b", re.IGNORECASE)


def evidence(content):
    """Return an exact source quote only for a verified initial sequence."""
    if not isinstance(content, str) or not _HEADING.search(content):
        return None
    for line in content.splitlines():
        match = _LINE.fullmatch(line)
        if not match or _WARNING.search(line):
            continue
        base = int(match.group(1))
        values = [int(value.strip()) for value in match.group(2).split(';')]
        if not 2 <= base <= 20 or values != [base * index for index in range(1, len(values) + 1)]:
            continue
        return {"quote": line.strip(), "base": base, "values": values}
    return None


def public_recipe():
    rows = json.loads((Path(__file__).with_name('reference') / 'visual-v1.json').read_text())['references']
    return next(row for row in rows if row['id'] == REFERENCE and row['version'] == 1)


def eligible_sources(payload):
    groups = payload.get('selected_groups') or []
    if (type(payload.get('package_partition')) is not int or len(groups) != 1
            or groups[0].get('subject') != 'Mathematik'):
        return []
    return [row for row in (payload.get('visual_context') or {}).get('sources', [])
            if row.get('subject') == 'Mathematik' and row.get('group_id') == groups[0].get('id')
            and not row.get('source_type') and row.get('factual_status') != 'blocked'
            and re.fullmatch(r'p[1-9][0-9]?', row.get('ref', ''))
            and re.fullmatch(r'[a-f0-9]{32}', row.get('material_id', ''))
            and type(row.get('revision')) is int and row['revision'] >= 1
            and evidence(row.get('content'))]


def add_reference(db, payload):
    from .visual_reference_models import VisualReference

    if not eligible_sources(payload):
        return payload
    recipe = public_recipe()
    row = db.get(VisualReference, (REFERENCE, 1))
    if row is None or row.recipe != recipe or row.digest != prepared._digest(recipe):
        return payload
    context = payload['visual_context']
    references = [*context.get('references', []), {'id': REFERENCE, 'version': 1,
        'digest': row.digest, 'kind': 'scene', 'subject': 'Mathematik'}]
    return {**payload, 'visual_context': {**context, 'references': references,
        'required': True, 'reason': None}}


def graphic(proof, factor=None):
    """Two checked phases, with solutions restricted to the solution stage."""
    base, quote = proof['base'], proof['quote']
    if factor is None:
        labels = [str(value) for value in proof['values'][:4]]
        captions = [f'Starte bei {base}.', f'Gehe immer {base} weiter.']
        stage = 'given'
    else:
        labels = [str(base), f'× {factor}', f'= {base * factor}']
        captions = [f'Zähle in {base}er-Schritten.', f'{factor} Schritte ergeben {base * factor}.']
        stage = 'solution'
    objects = [{'id': f'o{i}', 'label': label, 'shape': 'box', 'tone': 'accent'}
               for i, label in enumerate(labels)]
    positions = [{'object_id': row['id'], 'slot': i} for i, row in enumerate(objects)]
    phases = [{'caption': caption, 'source_excerpt': quote, 'placements': positions,
               'highlight': [objects[0 if i == 0 else -1]['id']], 'edges': []}
              for i, caption in enumerate(captions)]
    return {'kind': 'scene', 'title': 'Vielfache entdecken', 'disclosure': stage,
            'source_excerpt': quote, 'labels': labels, 'numbers': [], 'connections': [], 'marks': [],
            'unit': '', 'variant': '', 'text_probe': None, 'lab': None,
            'scene': {'version': 1, 'layout': 'row', 'objects': objects, 'steps': phases, 'transition_ms': 400}}


def core(base, factor, mode):
    value = base * factor
    if mode == 0:
        prompt, answer = f'Welche Zahl folgt auf {value - base} in der {base}er-Reihe?', value
    elif mode == 1:
        prompt, answer = f'Wie oft passt {base} in {value}?', factor
    elif mode == 2:
        prompt, answer = f'{base} · ? = {value}. Welche Zahl fehlt?', factor
    elif mode == 3:
        prompt, answer = f'Welche Zahl fehlt in der {base}er-Reihe: {value - base}, ?, {value + base}?', value
    else:
        prompt, answer = f'Wie viel ist {base} · {factor}?', value
    return {'type': 'short', 'prompt': prompt, 'answer': str(answer), 'options': [], 'accepted': []}


def _reference(context):
    digest = prepared._digest(public_recipe())
    return next((row for row in context.get('references', []) if row.get('id') == REFERENCE
        and type(row.get('version')) is int and row['version'] == 1 and row.get('digest') == digest
        and row.get('subject') == 'Mathematik' and row.get('kind') == 'scene'), None)


def visible_numbers(contents):
    return {int(number) for content in contents
            for number in re.findall(r'(?<!\d)[0-9]{1,3}(?!\d)', content)}


def compile_candidates(payload, *, count=2):
    from .learning_entry import _specs

    context = payload.get('visual_context') or {}
    reference = _reference(context)
    if not reference or not context.get('required'):
        return []
    groups = payload.get('selected_groups') or []
    sources = eligible_sources(payload)
    if not sources:
        return []
    group = groups[0]
    plan = next((item for item in (payload.get('learning_entry') or {}).get('units', [])
                 if item.get('subject') == 'Mathematik' and item.get('group_id') == group['id']), None)
    slots = (_specs(plan, count) if plan and plan['entry_mode'] != 'existing_contract'
             else [{'id': f'q{i + 1}'} for i in range(count)])
    # A fixed prerequisite must never be replaced with a newly invented task.
    if any(slot.get('type') for slot in slots):
        return []
    source = sources[0]
    proof = evidence(source['content'])
    excluded = {tuple(pair) for pair in payload.get(HISTORY, []) if isinstance(pair, list) and len(pair) == 2}
    # A different example elsewhere on the same selected source must not be
    # presented as a fresh independent exercise either. Conservatively treat
    # every literal source number as already visible, without guessing its role.
    visible = visible_numbers([row['content'] for row in sources])
    answers, factors = set(map(str, visible)), []
    for mode in range(len(slots)):
        factor = next((n for n in range(len(proof['values']) + 1, 50)
                       if (proof['base'], n) not in excluded and n not in factors
                       and proof['base'] * n not in visible
                       and core(proof['base'], n, mode)['answer'] not in answers), None)
        if factor is None:
            raise ValueError('Für diese Reihe fehlen ausreichend neue Aufgaben.')
        factors.append(factor)
        answers.add(core(proof['base'], factor, mode)['answer'])
    result = []
    for index, slot in enumerate([None, *slots]):
        factor = None if slot is None else factors[index - 1]
        block = graphic(proof, factor)
        text = (f"Bei Vielfachen gehst du immer {proof['base']} weiter." if factor is None
                else f"{factor} Schritte zu je {proof['base']} ergeben {proof['base'] * factor}.")
        row = {'subject': 'Mathematik', 'group_id': group['id'], 'kind': 'scene',
               'reference': {'id': REFERENCE, 'version': 1}, 'source_refs': [source['ref']],
               'disclosure': block['disclosure'], 'text': text, 'block': block}
        if slot is not None:
            row['question_core'] = {'id': slot['id'], **core(proof['base'], factor, index - 1),
                **({'learning_goal_id': slot['learning_goal_id']} if slot.get('learning_goal_id') else {})}
        row['id'] = 'ms_' + prepared._digest({'revision': REVISION, 'source': source,
            'candidate': row, 'plan': payload.get('package_plan_digest'),
            'partition': payload['package_partition'], 'reference': reference['digest']})[:24]
        result.append(row)
    return result


class Binding(prepared.Binding):
    @property
    def rules(self):
        return ('\nDie vorbereiteten Vielfachenaufgaben, Antworten, Texte und Grafik-IDs genau übernehmen. '
                'Jede Aufgaben-ID einmal verwenden. Hinweise dürfen die Antwort nicht verraten.')

    def offered(self, candidate):
        return True

    def hydrate(self, data):
        value = super().hydrate(data)
        questions = value['units'][0]['questions']
        expected = {row['question_core']['id'] for row in self.candidates if row.get('question_core')}
        if len(questions) != len(expected) or {q['id'] for q in questions} != expected:
            raise ValueError('Die geplanten Aufgaben müssen vollständig und verschieden sein.')
        if any(q['explanation'] != q['explanation_steps'][0]['text'] for q in questions):
            raise ValueError('Aufgabe und Erklärung stimmen nicht überein.')
        if any(q.get('hints') != ['Zähle in gleichen Schritten.'] for q in questions):
            raise ValueError('Der vorbereitete Hinweis darf die Lösung nicht verraten.')
        return value


def bind_schema(schema, payload):
    from .package_decimal_addition import question_binding

    candidates = compile_candidates(payload)
    if not candidates:
        return None
    def bind_question(node, candidate):
        node = question_binding(node, candidate)
        if node is not None:
            node['properties']['hints'] = {'type': 'array', 'minItems': 1, 'maxItems': 1,
                'items': {'type': 'string', 'enum': ['Zähle in gleichen Schritten.']}}
        return node

    return prepared.bind_candidates(schema, Binding(tuple(candidates)),
                                    question_kinds=('scene',), question_binding=bind_question)


def validate_step(step, sources, question):
    """Recompute the entire scene and task from the same eligible source."""
    if len(sources) != 1 or len(step.presentation.blocks) != 1:
        raise ValueError('Die Vielfachengrafik benötigt genau eine passende Quelle.')
    proof = evidence(sources[0])
    block = step.presentation.blocks[0].model_dump(mode='json')
    if not proof:
        raise ValueError('Die Vielfachenreihe ist nicht eindeutig belegt.')
    if question is None:
        expected = graphic(proof)
        text = f"Bei Vielfachen gehst du immer {proof['base']} weiter."
    else:
        labels = block.get('labels') or []
        match = re.fullmatch(r'× ([1-9][0-9]?)', labels[1]) if len(labels) == 3 else None
        if not match:
            raise ValueError('Die Vielfachengrafik hat ungültige Rechenschritte.')
        factor = int(match.group(1))
        if not len(proof['values']) < factor < 50:
            raise ValueError('Die neue Aufgabe ist kein zulässiges Folgebeispiel.')
        expected = graphic(proof, factor)
        text = f"{factor} Schritte zu je {proof['base']} ergeben {proof['base'] * factor}."
        if not any(all(question.get(k) == v for k, v in core(proof['base'], factor, mode).items())
                   for mode in range(5)):
            raise ValueError('Aufgabe und Vielfachengrafik stimmen nicht überein.')
        visible = visible_numbers(sources)
        if int(question['answer']) in visible or proof['base'] * factor in visible:
            raise ValueError('Das Originalbeispiel verrät bereits die Antwort.')
    if block != expected or step.disclosure != expected['disclosure'] or step.text != text:
        raise ValueError('Die Vielfachengrafik stimmt nicht mit dem belegten Rechenschritt überein.')


def prompt_pair(prompt):
    """Read only our own finite prompt forms, returning no private text."""
    patterns = (
        r'Welche Zahl folgt auf ([0-9]+) in der ([0-9]+)er-Reihe\?',
        r'Wie oft passt ([0-9]+) in ([0-9]+)\?',
        r'([0-9]+) · \? = ([0-9]+)\. Welche Zahl fehlt\?',
        r'Welche Zahl fehlt in der ([0-9]+)er-Reihe: ([0-9]+), \?, ([0-9]+)\?',
        r'Wie viel ist ([0-9]+) · ([0-9]+)\?',
    )
    for mode, pattern in enumerate(patterns):
        match = re.fullmatch(pattern, prompt or '')
        if not match:
            continue
        values = list(map(int, match.groups()))
        a, b = values[:2]
        if mode == 0:
            base, value = b, a + b
        elif mode == 3:
            base, left, right = values
            if right - left != 2 * base:
                return None
            value = left + base
        elif mode == 4:
            base, value = a, a * b
        else:
            base, value = a, b
        if not 2 <= base <= 20 or value % base or not 2 <= value // base < 50:
            return None
        return base, value // base
    return None


def history(db, child_id, *, ignore_job_ids=()):
    from sqlalchemy import select

    from .db import LearningUnit
    from .grades import subject_key
    from .package_question_history import unpublished_prompts_for_exclusion

    prompts = [question.get('prompt', '') for subject, questions in db.execute(
        select(LearningUnit.subject, LearningUnit.questions).where(LearningUnit.child_id == child_id))
        if subject_key(subject) == 'mathematik' for question in (questions or [])]
    prompts.extend(unpublished_prompts_for_exclusion(db, child_id, 'Mathematik', ignore_job_ids=ignore_job_ids))
    pairs = {prompt_pair(prompt) for prompt in prompts}
    # Previous provider-authored questions need not use our exact wording. If
    # both operands (or the base and product) are present, conservatively
    # exclude that exercise too; the private text never leaves this process.
    for prompt in prompts:
        numbers = {int(match) for match in re.findall(r'(?<!\w)[0-9]{1,4}(?!\w)', prompt or '')}
        for base in numbers & set(range(2, 21)):
            pairs.update((base, factor) for factor in range(2, 50)
                         if factor in numbers or base * factor in numbers)
    return [list(pair) for pair in sorted(pair for pair in pairs if pair is not None)]


def validate_history(db, child_id, data, *, ignore_job_ids=()):
    questions = [question for unit in data.get('units', []) for question in unit.get('questions', [])
                 if any((step.get('reference') or {}).get('id') == REFERENCE
                        for step in (question.get('explanation_steps') or []))]
    if not questions:
        return
    previous = {tuple(pair) for pair in history(db, child_id, ignore_job_ids=ignore_job_ids)}
    pairs = [prompt_pair(question.get('prompt')) for question in questions]
    if None in pairs or len(set(pairs)) != len(pairs) or any(pair in previous for pair in pairs):
        raise ValueError('Diese Zahlenaufgabe wurde inzwischen bereits vorbereitet. Bitte eine neue Runde anfordern.')
