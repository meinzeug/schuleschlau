"""Private provider binding for a previously reserved fraction plan.

This adapter does not reserve jobs or provide authorization. It is only
selected for a server-supplied plan; the worker and publication guards remain
required before any use in live package generation.
"""
import copy
from dataclasses import dataclass

from . import package_fraction_plan as fractions, package_fraction_schema as contract


@dataclass(frozen=True)
class Binding:
    payload: dict
    plan: dict
    slots: list

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
        return {'version': 1, 'revision': 'package-fraction-wire-1', 'candidates': candidates}

    @property
    def rules(self):
        return ('\npackage-fraction-wire-1: Die geplanten Bruchfragen sind fest an jeweils eine '
                'Grafik-ID, Antwort, Quelle und solution-Text gebunden. Alle Felder unverändert '
                'übernehmen; presentation.blocks enthält ausschließlich die zugehörige ID. '
                'Vorwissen und Einführung behalten ihre vorhandenen Grafikverträge. '
                'Ergänze nur kurze Hinweise, die die Lösung nicht verraten.')

    def hydrate(self, data):
        return contract.hydrate(self.payload, self.slots, self.plan['excluded_values'], self.plan, data)


def bind(schema, payload):
    plan = payload.get('package_fraction_plan')
    visual = payload.get('visual_context')
    if not isinstance(plan, dict) or not isinstance(visual, dict) or visual.get('package_fraction_plan') != plan:
        raise ValueError(fractions.INVALID)
    slots = [row['slot'] for row in plan['slots']]
    result = contract.bind(schema, payload, slots, plan['excluded_values'], plan)
    schema.clear()
    schema.update(result)
    return Binding(copy.deepcopy(payload), copy.deepcopy(plan), copy.deepcopy(slots))
