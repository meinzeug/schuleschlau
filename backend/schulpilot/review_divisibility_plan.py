"""Fixed, source-bound kgV and divisor-product review; never relabel goals."""
import copy
import re
from dataclasses import dataclass
from . import unit_multiples_common as multiples
from . import review_divisibility_product as product
from .fraction_practice_plan import INVALID, CURRENT_ERROR
from .package_prepared_graphics import Binding as BaseBinding, _digest, bind_candidates

KEY = 'review_divisibility_plan'
HISTORY = 'review_divisibility_history'
REVISION = 'review-divisibility-plan-1'
SOURCE_ERROR = 'Für die Teilbarkeitsaufgabe fehlt ein eindeutig bestätigtes Rechenbeispiel. Bitte prüfe die Heftseite. Es wurde keine KI-Anfrage gesendet.'


def supported(payload):
    if (payload.get('review') is not True or payload.get('practice_kind') != 'check'
            or payload.get('required_subject') != 'Mathematik' or payload.get('math_tasks')
            or (payload.get('visual_context') or {}).get('required') is not True):
        return False
    focus, goals = payload.get('focus_goal_ids'), payload.get('learning_goals')
    if (not isinstance(focus, list) or len(focus) != 2 or len(set(focus)) != 2
            or any(not isinstance(item, str) for item in focus)
            or not isinstance(goals, list) or any(not isinstance(g, dict) for g in goals)):
        return False
    indexed = {g.get('id'): g for g in goals}
    if len(indexed) != len(goals) or not set(focus) <= indexed.keys():
        return False
    labels = [indexed[key].get('label', '') for key in focus]
    if not all(isinstance(label, str) for label in labels):
        return False
    kgv = [i for i, label in enumerate(labels) if multiples._TOPIC.search(label)]
    divisibility = [i for i, label in enumerate(labels) if product.supports_label(label)]
    return len(kgv) == len(divisibility) == 1 and kgv[0] != divisibility[0]


def add_references(db, payload):
    from .visual_reference_models import VisualReference
    if not supported(payload):
        raise ValueError(INVALID)
    context = copy.deepcopy(payload['visual_context'])
    for module in (multiples, product):
        actual = module.public_recipe()
        row = db.get(VisualReference, (module.RECIPE, module.VERSION))
        if row is None or row.recipe != actual or row.digest != _digest(actual):
            raise ValueError(INVALID)
        ref = {'id': module.RECIPE, 'version': module.VERSION, 'digest': row.digest,
            'kind': 'scene', 'subject': 'Mathematik'}
        old = [item for item in context['references'] if item.get('id') == module.RECIPE]
        if old and (len(old) != 1 or type(old[0].get('version')) is not int or old[0] != ref):
            raise ValueError(INVALID)
        if not old:
            context['references'].append(ref)
    return {**payload, 'visual_context': context}


def with_history(payload, prompts):
    if not supported(payload) or not isinstance(prompts, list) or any(not isinstance(p, str) for p in prompts):
        raise ValueError(INVALID)
    return {**payload, HISTORY: {'version': 1, 'revision': REVISION,
        'context_digest': _digest(payload['visual_context']), 'prompts_digest': _digest(sorted(set(prompts))),
        'pairs': [list(pair) for pair in multiples._pool() if pair in multiples._pairs(prompts)
            or any(all(re.search(rf'(?<!\d){number}(?!\d)', text) for number in pair) for text in prompts)],
        'numbers': sorted({int(number) for prompt in prompts for number in re.findall(r'(?<!\d)\d{1,3}(?!\d)', prompt)})}}


def _plan(payload):
    from .providers import practice_tasks
    if not supported(payload):
        raise ValueError(INVALID)
    context, h = payload['visual_context'], payload.get(HISTORY)
    if (not isinstance(h, dict) or set(h) != {'version', 'revision', 'context_digest', 'prompts_digest', 'pairs', 'numbers'}
            or type(h['version']) is not int or h['version'] != 1 or h['revision'] != REVISION
            or h['context_digest'] != _digest(context) or not re.fullmatch(r'[a-f0-9]{64}', h['prompts_digest'])
            or not isinstance(h['pairs'], list) or any(not isinstance(pair, list) or tuple(pair) not in multiples._pool() for pair in h['pairs'])
            or not isinstance(h['numbers'], list) or any(type(n) is not int or not 0 <= n <= 999 for n in h['numbers'])):
        raise ValueError(INVALID)
    tasks = practice_tasks(payload)
    ktask = next((t for t in tasks if multiples._TOPIC.search(t['label'])), None)
    dtask = next((t for t in tasks if product.supports_label(t['label'])), None)
    rule = multiples._rule(context)
    if (not ktask or not dtask or not rule or ktask['id'] == dtask['id']
            or ktask['learning_goal_id'] == dtask['learning_goal_id']):
        raise ValueError(INVALID)
    # The saved learning goal quote must itself cite the source of this rule.
    rule_source = next((s for s in context['sources'] if s.get('ref') == rule['source_ref']), None)
    if not rule_source or not ktask['source_excerpt'] or ktask['source_excerpt'] not in rule_source['content']:
        raise ValueError(INVALID)
    compiled = product.compile_candidate(context, dtask)
    if compiled is None:
        raise ValueError(SOURCE_ERROR)
    dcore, dcandidate = compiled
    result = product._evidence(context, dtask)[-1]
    if result in h['numbers']:
        raise ValueError(INVALID)
    originals = {tuple(sorted(map(int, match.groups()))) for source in multiples._sources(context)
        for match in multiples._ANCHOR_PAIR.finditer(source['content'])}
    pool = [p for p in multiples._pool() if p not in {tuple(x) for x in h['pairs']} | originals and p != (2, 4)
        and multiples._arithmetic(p)[0] not in (2, 4, result, int(dcore['answer']))]
    if not pool:
        raise ValueError(INVALID)
    pair = sorted(pool, key=lambda p: _digest([REVISION, rule, h, p]))[0]
    kcore = {**multiples._core(ktask['id'], pair), 'learning_goal_id': ktask['learning_goal_id']}
    return {'version': 1, 'revision': REVISION, 'context_digest': _digest(context),
        'history_digest': _digest(h), 'rule': rule, 'intro': [2, 4],
        'tasks': [{'kind': 'kgv', 'task': ktask, 'core': kcore, 'pair': list(pair),
                'hints': [f'Schreibe die Vielfachen von {pair[0]} und {pair[1]} auf und vergleiche sie.']},
            {'kind': 'divisor', 'task': dtask, 'core': dcore, 'candidate_id': dcandidate['id'],
                'hints': [product.safe_hint(context, dtask)]}]}


def prepare(payload):
    plan = _plan(payload)
    if KEY in payload and payload[KEY] != plan:
        raise ValueError(INVALID)
    return {**payload, KEY: plan}


def _candidates(payload):
    if prepare(payload) != payload:
        raise ValueError(INVALID)
    plan, context = payload[KEY], payload['visual_context']
    intro = multiples._candidate(context, plan['rule'], tuple(plan['intro']))
    rows = [intro]
    for item in plan['tasks']:
        if item['kind'] == 'kgv':
            core = {k: v for k, v in item['core'].items() if k != 'learning_goal_id'}
            row = multiples._candidate(context, plan['rule'], tuple(item['pair']), question=core)
        else:
            generated = product.compile_candidate(context, item['task'])
            if generated is None or generated[0] != item['core'] or generated[1]['id'] != item['candidate_id']:
                raise ValueError(INVALID)
            row = generated[1]
        row['question_core'] = copy.deepcopy(item['core'])
        row['question_hints'] = copy.deepcopy(item['hints'])
        rows.append(row)
    return rows


@dataclass(frozen=True)
class Binding(BaseBinding):
    @property
    def rules(self):
        return ('\n' + REVISION + ': Übernimm die zwei festen Aufgabenkerne mit ihren Lernziel-IDs und die zugehörigen vorbereiteten Grafikschritte. '
            'Keine Aufgaben, Ziele, Zahlen oder Quellen ändern. Nur kurze Hinweise und Erklärungen ergänzen.')
    def offered(self, candidate):
        return True
    def hydrate(self, data):
        result = super().hydrate({'units': [data]})['units'][0]
        choices = {row['id']: row for row in self.candidates}
        for before, after in [(data, result), *zip(data['questions'], result['questions'], strict=True)]:
            row = choices[before['explanation_steps'][0]['presentation']['blocks'][0]]
            if after['explanation_steps'][0]['id'] != row['id']:
                raise ValueError(INVALID)
        return result


def bind_schema(schema, payload):
    if KEY not in payload:
        return None
    rows = _candidates(payload)
    binding = Binding(tuple(rows))
    bounds = schema['properties']['questions']
    if bounds.get('minItems') != 2 or bounds.get('maxItems') != 2:
        raise ValueError(INVALID)
    schema['properties']['explanation'].update(type='string', enum=[rows[0]['text']])
    wrapper = {'$defs': schema['$defs'], 'properties': {'units': {'items': copy.deepcopy({k: v for k, v in schema.items() if k != '$defs'})}}}
    def bind_question(node, candidate):
        core, props = candidate['question_core'], node['properties']
        if props['id'].get('enum') != [core['id']] or props['learning_goal_id'].get('enum') != [core['learning_goal_id']]:
            return None
        for key in ('id', 'type', 'prompt', 'answer'):
            allowed = props[key].get('enum', [props[key]['const']] if 'const' in props[key] else [])
            if allowed and core[key] not in allowed:
                return None
            props[key].update(type='string', enum=[core[key]])
        props['options'].update(minItems=0, maxItems=0)
        props['accepted'].update(minItems=0, maxItems=0)
        props['presentation'] = {'type': 'null'}
        if 'question_hints' in candidate:
            props['hints'].update(minItems=1, maxItems=1, items={'type': 'string', 'enum': candidate['question_hints']})
        return node
    bind_candidates(wrapper, binding, question_kinds=('scene',), question_binding=bind_question)
    choices = {row['id']: row for row in rows}
    for node in wrapper['$defs'].values():
        props = node.get('properties', {})
        ids = props.get('presentation', {}).get('properties', {}).get('blocks', {}).get('items', {}).get('enum', [])
        if len(ids) == 1 and ids[0] in choices:
            props['id'] = {'type': 'string', 'enum': ids}
            props['text'] = {'type': 'string', 'enum': [choices[ids[0]]['text']]}
            props['competence_id'] = {'type': 'null'}
    body = wrapper['properties']['units']['items']
    schema.clear()
    schema.update(body, **{'$defs': wrapper['$defs']})
    return binding


def validate_output(payload, data):
    if KEY not in payload:
        return
    rows = _candidates(payload)
    tasks = {item['core']['id']: item for item in payload[KEY]['tasks']}
    questions = data.get('questions')
    if (data.get('subject') != 'Mathematik' or data.get('explanation') != rows[0]['text']
            or not isinstance(questions, list) or len(questions) != 2
            or {q.get('id') for q in questions} != set(tasks) or len(data.get('explanation_steps') or []) != 1):
        raise ValueError(INVALID)
    multiples.validate_step(data['explanation_steps'][0], payload['visual_context'])
    for q in questions:
        item = tasks[q['id']]
        if any(q.get(k) != v for k, v in item['core'].items()) or len(q.get('explanation_steps') or []) != 1:
            raise ValueError(INVALID)
        if q.get('hints') != item['hints']:
            raise ValueError(INVALID)
        if item['kind'] == 'kgv':
            multiples.validate_step(q['explanation_steps'][0], payload['visual_context'], q)
        else:
            product.validate_step(q['explanation_steps'][0], payload['visual_context'], q, item['task'])


def validate_history(payload, data, prompts):
    try:
        validate_output(payload, data)
        current = prepare(with_history(payload, prompts))
        if current[KEY] != payload[KEY]:
            raise ValueError(CURRENT_ERROR)
    except ValueError:
        raise ValueError(CURRENT_ERROR) from None
