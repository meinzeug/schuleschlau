"""Private provider binding for a previously reserved fraction plan.

This adapter does not reserve jobs or provide authorization. It is only
selected for a server-supplied plan; the worker and publication guards remain
required before any use in live package generation.
"""
import copy
from dataclasses import dataclass

from . import package_fraction_plan as fractions
from . import package_fraction_schema as contract


@dataclass(frozen=True)
class Binding:
    payload: dict
    plan: dict
    slots: list
    standard: object

    @property
    def context(self):
        candidates = []
        for row in self.plan['slots']:
            if row.get('task') is None:
                continue
            step = fractions.solution_step(self.plan, row)
            candidates.append({'id': step['id'], 'question': copy.deepcopy(row['task']),
                               'text': step['text'], 'reference': step['reference'],
                               'source_refs': step['source_refs'], 'disclosure': 'solution'})
        return {'version': 1, 'revision': 'package-fraction-wire-1',
                'candidates': [*self.standard.context['candidates'], *candidates]}

    @property
    def rules(self):
        return (self.standard.rules + '\npackage-fraction-wire-1: Die geplanten Bruchfragen sind fest an jeweils eine '
                'Grafik-ID, Antwort, Quelle und solution-Text gebunden. Alle Felder unverändert '
                'übernehmen; presentation.blocks enthält ausschließlich die zugehörige ID. '
                'Vorwissen und Einführung behalten ihre vorhandenen Grafikverträge. '
                'Ergänze nur kurze Hinweise, die die Lösung nicht verraten.')

    def hydrate(self, data):
        ids = {row['slot']['id'] for row in self.plan['slots'] if row.get('task') is not None}
        standard = self.standard.hydrate(data, skip_question_ids=ids)
        return contract.hydrate(self.payload, self.slots, self.plan['excluded_values'], self.plan, standard)


def bind(schema, payload):
    plan = payload.get('package_fraction_plan')
    visual = payload.get('visual_context')
    if not isinstance(plan, dict) or not isinstance(visual, dict) or visual.get('package_fraction_plan') != plan:
        raise ValueError(fractions.INVALID)
    slots = [row['slot'] for row in plan['slots']]
    result = contract.bind(schema, payload, slots, plan['excluded_values'], plan)
    schema.clear()
    schema.update(result)
    # Keep introduction and unplanned diagnostic slots on the compact,
    # independently checked graphic-ID contract. Inline graphics exceed the
    # upstream structured-output nesting limit for these package branches.
    from .package_prepared_graphics import bind_schema as bind_prepared_graphics

    ids = {row['slot']['id'] for row in plan['slots'] if row.get('task') is not None}
    # These specialised recipes require the complete two-graphic proof. They
    # are never valid as a generic introduction or single-image prior probe.
    references = visual.get('references')
    if not isinstance(references, list) or any(not isinstance(row, dict) for row in references):
        raise ValueError(fractions.INVALID)
    standard_payload = {**payload, 'visual_context': {**visual, 'references': [
        reference for reference in references
        if reference.get('id') not in ('math.fraction.expansion', 'math.fraction.reduction')]}}
    standard = bind_prepared_graphics(schema, standard_payload, skip_question_ids=ids)
    if standard is None:
        raise ValueError('Der Teilauftrag hat keine passende Referenz/Grafik für seine Aufdeckstufe.')
    return Binding(copy.deepcopy(payload), copy.deepcopy(plan), copy.deepcopy(slots), standard)
