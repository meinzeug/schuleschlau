"""Bind ordinary source units to the same reviewed visual contracts as parts.

No package conversion, fixed exercise count, answer rewrite or output repair.
Also bind mathematical review units that do not have a more specific recipe.
"""

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
