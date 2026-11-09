"""Bind ordinary source units to the same reviewed visual contracts as parts.

No package conversion, fixed exercise count, answer rewrite or output repair.
Also bind mathematical review units that do not have a more specific recipe.
"""

import copy
from dataclasses import dataclass

from .package_part_output import _bind_references
from .subject_content import PROFILES


def bind_text_only(schema):
    """Close all graphic slots while preserving the task and answer schemas."""
    def walk(node):
        if not isinstance(node, dict):
            return
        props = node.get("properties", {})
        if "explanation_steps" in props:
            props["explanation_steps"] = {"type": "null"}
        if "prompt" in props and "hints" in props and "presentation" in props:
            props["presentation"] = {"type": "null"}
        for key in ("properties", "$defs"):
            for child in node.get(key, {}).values():
                walk(child)
        for key in ("items", "additionalProperties"):
            walk(node.get(key))
        for key in ("anyOf", "oneOf", "allOf"):
            for child in node.get(key, []):
                walk(child)
    walk(schema)


def unique_text_question_ids(value):
    """Resolve duplicate transient IDs, without changing question content.

    Only the ordinary, non-entry, text-only unit caller may use this. The
    resulting question array still undergoes the complete canonical schema,
    answer, source and novelty validation before anything is persisted.
    """
    if not isinstance(value, dict) or not isinstance(value.get("questions"), list):
        return value, 0
    questions = value["questions"]
    if any(not isinstance(row, dict) or not isinstance(row.get("id"), str) for row in questions):
        return value, 0
    ids = [row["id"] for row in questions]
    if len(ids) == len(set(ids)):
        return value, 0
    result = copy.deepcopy(value)
    used, seen, changed = set(ids), set(), 0
    for index, row in enumerate(result["questions"], 1):
        if row["id"] in seen:
            candidate = f"auto_q{index}"
            while candidate in used:
                candidate += "x"
            row["id"] = candidate
            used.add(candidate)
            changed += 1
        else:
            seen.add(row["id"])
    return result, changed


@dataclass(frozen=True)
class EntrySlots:
    ids: tuple[str, ...]

    def decode(self, value):
        if not isinstance(value, dict) or not isinstance(value.get("questions"), dict):
            raise ValueError("Ungültige Aufgabenplätze im Lernstart.")
        slots = value["questions"]
        keys = [f"v{index}" for index in range(len(self.ids))]
        if set(slots) != set(keys):
            raise ValueError("Ungültige Aufgabenplätze im Lernstart.")
        questions = [slots[key] for key in keys]
        if any(not isinstance(row, dict) or row.get("id") != expected
               for row, expected in zip(questions, self.ids, strict=True)):
            raise ValueError("Ein Aufgabenplatz gehört nicht zum vorgegebenen Lernstart.")
        return {**value, "questions": questions}


def bind_text_entry_slots(schema, payload):
    """Bind each existing entry ID to its own output slot, without rewriting it."""
    from .learning_entry import _specs

    entry = payload.get("learning_entry")
    if not isinstance(entry, dict) or len(entry.get("units", [])) != 1:
        return None
    plan = entry["units"][0]
    if plan.get("group_id") is not None or plan.get("entry_mode") == "existing_contract":
        return None
    questions = schema.get("properties", {}).get("questions", {})
    count = questions.get("minItems")
    branches = questions.get("items", {}).get("anyOf")
    if type(count) is not int or count != questions.get("maxItems") or not 2 <= count <= 5 or not isinstance(branches, list):
        raise ValueError("Der Lernstart hat keine eindeutig gebundenen Aufgabenplätze.")
    ids = tuple(spec["id"] for spec in _specs(plan, count))
    if len(set(ids)) != count:
        raise ValueError("Der Lernstart hat keine eindeutig gebundenen Aufgabenplätze.")
    slots = {}
    for index, identifier in enumerate(ids):
        selected = [copy.deepcopy(branch) for branch in branches
                    if branch.get("properties", {}).get("id", {}).get("enum") == [identifier]]
        if not selected:
            raise ValueError("Der Lernstart hat keine eindeutig gebundenen Aufgabenplätze.")
        slots[f"v{index}"] = selected[0] if len(selected) == 1 else {"anyOf": selected}
    schema["properties"]["questions"] = {"type": "object", "properties": slots,
        "required": list(slots), "additionalProperties": False}
    return EntrySlots(ids)

RULES = """
unit-reference-graphics-1: reference.id/version und Grafiktyp bilden im Schema
einen gemeinsamen Zweig. Wähle ausschließlich einen vollständig passenden Zweig
für das bestätigte Fach und die gebundene Aufdeckstufe. Quellenreferenzen gehören
zu demselben Fach. Eine bloße Wortliste belegt keine gerichtete Beziehung oder
zeitliche Folge: verwende den angebotenen Originalvergleich, keine erfundene Szene.
Übernimm seine Beschriftungen vollständig und wörtlich aus dem zitierten Beleg.
Die Aufgabe ist bereits durch ihren Prompt verständlich. presentation=null;
ihre Grafik steht ausschließlich im gebundenen explanation_steps-Schritt.
Aufgabenanzahl, feste Vorwissensfragen, Antworten und alle Quellenprüfungen bleiben
unverändert. Erstelle weiterhin kurze verständliche Erklärtexte zur gewählten Grafik.
Für general.source_relation.phases: mindestens zwei Phasen mit je mindestens einem
gerichteten Pfeil aus dem wörtlichen Quellenbeleg; die Phasen unterscheiden sich
sichtbar durch Markierungen oder belegte Beziehungen. Niemals Pfeile erfinden.
"""


def bind_schema(schema, payload):
    context = payload.get("visual_context") or {}
    subject = payload.get("required_subject") or (payload.get("material") or {}).get("subject")
    tasks = payload.get("practice_tasks")
    # Explicit coach follow-ups have two server-bound task/goal pairs. Keep the
    # ordinary review contract unchanged for every other kind of review.
    coach_practice = (payload.get("review") is True and isinstance(tasks, list) and len(tasks) == 2
                      and all(isinstance(task, dict) and isinstance(task.get("id"), str)
                              and isinstance(task.get("learning_goal_id"), str) for task in tasks))
    math_review = payload.get("review") is True and subject == "Mathematik"
    if (not context.get("required") or not isinstance(subject, str) or subject not in PROFILES
            or (subject == "Mathematik" and not math_review) or payload.get("selected_groups")
            or (payload.get("review") and not (coach_practice or math_review))
            or any(payload.get(key) for key in ("homework_practice",
                "exam_preparation", "exam_review_practice"))):
        return False
    _bind_references(schema, payload, unit_subject=subject)
    return True
