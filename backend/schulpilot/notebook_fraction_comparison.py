"""Source-bound, independently checked fraction comparison practice.

The AI can select only prepared graphic IDs and can add explanation/hints. It
cannot change the computed questions, answers, sources, or disclosure stages.
"""

import copy
import itertools
import re
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from . import learning_entry
from . import study_fraction_expansions as expansion
from .fraction_comparison_rule import comparison_signature, rule
from .fraction_comparison_rule import plan as plan_comparisons
from .math_tasks import _task, is_fraction_comparison_topic
from .package_prepared_graphics import Binding as PackageBinding
from .package_prepared_graphics import _digest, _fraction_bases, bind_candidates
from .subject_content import Graphic

RECIPE = "math.fraction.comparison"
VERSION = 1
REVISION = "notebook-fraction-comparison-1"
KEY = "notebook_comparison_plan"
HISTORY = "notebook_comparison_exclusions"
ERROR = "Der Bruchvergleich kann nicht sicher an Regel, Aufgabe und Grafik gebunden werden. Es wurde keine KI-Anfrage gesendet."
EXHAUSTED = "Für diese Regel gibt es gerade keine neuen passenden Vergleichsaufgaben. Es wurde keine KI-Anfrage gesendet."
CURRENT_ERROR = "Eine Vergleichsaufgabe wurde inzwischen bereits verwendet. Die neue Runde wurde nicht übernommen."
CORE = learning_entry.CORE


def _sources(payload):
    return expansion._sources(payload.get("visual_context") or {})


def eligible(payload):
    from .notebook_practice import requested_count

    context = payload.get("visual_context") or {}
    sources = _sources(payload)
    return (requested_count(payload) is not None and payload.get("required_subject") == "Mathematik"
        and context.get("required") is True and bool(sources)
        and not any(payload.get(key) for key in ("review", "study_block", "selected_groups", "homework_practice",
            "exam_preparation", "exam_review_practice"))
        and all(is_fraction_comparison_topic(source.get("topic")) for source in sources)
        and any(rule(source["content"]) for source in sources))


def add_reference(db, payload):
    import json

    from .visual_reference_models import VisualReference

    if not eligible(payload):
        return payload
    rows = json.loads((Path(__file__).with_name("reference") / "visual-v1.json").read_text())["references"]
    recipe = next(row for row in rows if row["id"] == RECIPE and row["version"] == VERSION)
    stored = db.get(VisualReference, (RECIPE, VERSION))
    if stored is None or stored.digest != _digest(recipe) or stored.recipe != recipe:
        return payload
    context = payload["visual_context"]
    ref = {"id": RECIPE, "version": VERSION, "digest": stored.digest, "kind": "fraction", "subject": "Mathematik"}
    return {**payload, "visual_context": {**context, "references": [*context["references"], ref]}}


def _signatures(prompts):
    if not isinstance(prompts, list):
        raise ValueError(ERROR)
    pairs = set()
    for item in prompts:
        if isinstance(item, str):
            prompt, options = item, []
        elif isinstance(item, dict) and isinstance(item.get("prompt"), str):
            prompt, options = item["prompt"], item.get("options")
        else:
            raise ValueError(ERROR)
        signature = comparison_signature(prompt)
        if signature and signature[0] == "compare":
            pairs.add(tuple(sorted(tuple(str(int(value)) for value in pair) for pair in signature[1])))
        elif (re.search(r"vergleich|gr(?:ö|oe|o)ss?er|kleiner", prompt.casefold())
                and re.search(r"\d\s*[/⁄∕]|\\(?:d?frac)\s*\{", prompt)):
            # A numerical legacy comparison that cannot be parsed cannot be
            # proved new merely by changing its wording.
            raise ValueError(EXHAUSTED)
        elif re.search(r"welch\w*\s+bruch[^.!?]{0,80}(?:gr(?:ö|oe|o)ss?er|kleiner)", prompt.casefold()):
            # Older choice tasks can keep the compared fractions in options.
            # This full option list is strictly local and never goes to AI.
            if not isinstance(options, list) or len(options) > 8 or any(not isinstance(option, str) for option in options):
                raise ValueError(EXHAUSTED)
            values = []
            for option in options:
                match = re.fullmatch(r"\s*(?:\(?[A-Ha-h]\)?[).:]?\s+)?(\d{1,4})\s*/\s*([1-9]\d{0,3})\s*", option)
                if match is None:
                    raise ValueError(EXHAUSTED)
                values.append((str(int(match[1])), str(int(match[2]))))
            if len(set(values)) < 2:
                raise ValueError(EXHAUSTED)
            pairs.update(tuple(sorted((a, b))) for a, b in itertools.combinations(set(values), 2))
    return sorted(pairs)


def with_history(payload, prompts):
    if not eligible(payload):
        return payload
    from .notebook_practice import requested_count

    slots = _slots(payload, requested_count(payload))
    if slots is None or not any(slot["role"] == "practice" for slot in slots):
        return payload  # Legacy/source-only entry retains its previous contract.
    signatures = _signatures(prompts)
    return {**payload, HISTORY: {"version": 1, "source_digest": _digest(_sources(payload)),
        "pairs": [[list(pair) for pair in signature] for signature in signatures]}}


def _history(payload):
    data = payload.get(HISTORY)
    if (not isinstance(data, dict) or set(data) != {"version", "source_digest", "pairs"}
            or type(data["version"]) is not int or data["version"] != 1
            or data["source_digest"] != _digest(_sources(payload)) or not isinstance(data["pairs"], list)):
        raise ValueError(ERROR)
    result = []
    for row in data["pairs"]:
        if (not isinstance(row, list) or len(row) != 2 or any(not isinstance(pair, list) or len(pair) != 2
                or any(not isinstance(value, str) or not re.fullmatch(r"\d{1,4}", value) for value in pair)
                or int(pair[1]) == 0 for pair in row)):
            raise ValueError(ERROR)
        result.append(f"Welcher Bruch ist größer: {row[0][0]}/{row[0][1]} oder {row[1][0]}/{row[1][1]}?")
    return result


def _slots(payload, count):
    entry = payload.get("learning_entry")
    if not entry:
        return [{"id": f"q{index + 1}", "role": "practice"} for index in range(count)]
    units = entry.get("units") or []
    if (len(units) != 1 or units[0].get("subject") != "Mathematik" or units[0].get("group_id") is not None
            or units[0].get("entry_mode") not in ("prerequisite_probe", "reuse_evidence")):
        return None
    return learning_entry._specs(units[0], count)


def prepare(payload):
    from .notebook_practice import requested_count

    if not eligible(payload):
        if KEY in payload or HISTORY in payload:
            raise ValueError(ERROR)
        return payload
    count = requested_count(payload)
    slots = _slots(payload, count)
    if slots is None or not any(slot["role"] == "practice" for slot in slots):
        # Existing source-only entry has no immutable probes to bind. Keep its
        # current generator contract; legacy all-probe rounds also retain their
        # reserved contract. Don't invent probe answers or references.
        if KEY in payload:
            raise ValueError(ERROR)
        return {key: value for key, value in payload.items() if key != HISTORY}
    context = payload["visual_context"]
    if not any(ref.get("id") == RECIPE and ref.get("version") == VERSION and ref.get("digest")
               for ref in context.get("references", [])):
        raise ValueError(ERROR)
    previous = _history(payload)
    sources = _sources(payload)
    selected = next(source for source in sources if rule(source["content"]))
    # Exclude values appearing in any selected page, not only the rule page.
    all_content = selected["content"] + "\n" + "\n".join(source["content"] for source in sources if source is not selected)
    practice = [slot for slot in slots if slot["role"] == "practice"]
    tasks = plan_comparisons(all_content, previous, len(practice), _digest([REVISION, context, slots, previous]))
    if len(tasks) != len(practice):
        raise ValueError(EXHAUSTED)
    for task, slot in zip(tasks, practice, strict=True):
        task["id"] = slot["id"]
    value = {"version": 1, "revision": REVISION, "context_digest": _digest(context),
        "exclusion_digest": _digest(payload[HISTORY]), "question_count": count,
        "tasks": tasks, "probes": [{key: copy.deepcopy(slot[key]) for key in CORE}
            for slot in slots if slot["role"] == "prior_check"]}
    if KEY in payload and payload[KEY] != value:
        raise ValueError(ERROR)
    return {**payload, KEY: value}


def _blocks(candidate):
    proof = candidate["proof"]
    return [Graphic.model_validate({"kind": "fraction", "title": title,
        "source_excerpt": proof["source_excerpt"], "labels": [], "numbers": pair,
        "connections": [], "marks": [], "unit": "", "variant": "", "disclosure": "solution"}).model_dump(mode="json")
        for title, pair in (("Erster Bruch", proof["left"]), ("Zweiter Bruch", proof["right"]),
            ("Erster Bruch gleichnamig", proof["expanded_left"]),
            ("Zweiter Bruch gleichnamig", proof["expanded_right"]))]


def _candidate(context, task):
    import math

    match = re.fullmatch(r"Welcher Bruch ist größer: ([0-9]+)/([0-9]+) oder ([0-9]+)/([0-9]+)\? Gib den größeren Bruch an\.",
        str(task.get("prompt", "")))
    if match is None:
        return None
    a, b, c, d = map(int, match.groups())
    if not (0 < a < b <= 12 and 0 < c < d <= 12 and b != d and math.lcm(b, d) <= 24
            and Fraction(a, b) != Fraction(c, d)):
        return None
    prompt, answer = _task("compare", (a, b, c, d), "apply")
    if (task.get("type") != "short" or task["prompt"] != prompt or task.get("answer") != answer
            or task.get("options") != [] or task.get("accepted") != []
            or not isinstance(task.get("id"), str) or not task["id"] or task.get("learning_goal_id") is not None):
        return None
    source = next((row for row in expansion._sources(context) if rule(row["content"])
        and ("source_excerpt" not in task or task["source_excerpt"] == rule(row["content"])["quotes"][0])), None)
    reference = next((row for row in context.get("references", []) if row.get("id") == RECIPE
        and row.get("version") == VERSION and row.get("subject") == "Mathematik" and row.get("digest")), None)
    if source is None or reference is None:
        return None
    source_rule, common = rule(source["content"]), math.lcm(b, d)
    quote = source_rule["quotes"][0]
    left, right = [a * (common // b), common], [c * (common // d), common]
    greater = ">" if left[0] > right[0] else "<"
    proof = {"version": 1, "left": [a, b], "right": [c, d], "expanded_left": left,
        "expanded_right": right, "common_denominator": common, "source_excerpt": quote, "source_rule": source_rule,
        "source_digest": _digest(source), "reference_digest": reference["digest"],
        "task": {key: copy.deepcopy(task[key]) for key in CORE}}
    row = {"subject": "Mathematik", "group_id": None, "kind": "fraction", "disclosure": "solution",
        "reference": {"id": RECIPE, "version": VERSION}, "source_refs": [source["ref"]],
        "text": (f"Der gemeinsame Nenner von {a}/{b} und {c}/{d} ist {common}. "
            f"Erweitert ergibt das {left[0]}/{common} {greater} {right[0]}/{common}. "
            f"Der größere Bruch ist {answer}."), "proof": proof}
    row["block"] = _blocks(row)[0]
    row["id"] = "fc_" + _digest({"revision": REVISION, "candidate": row})[:24]
    return row


def validate_step(raw, candidate):
    step = raw.model_dump(mode="json") if hasattr(raw, "model_dump") else raw
    expected = {"id": candidate["id"], "text": candidate["text"], "competence_id": None,
        "disclosure": "solution", "reference": candidate["reference"], "source_refs": candidate["source_refs"],
        "presentation": {"version": 1, "evidence_kind": "knowledge", "blocks": _blocks(candidate)}}
    if _digest(step) != _digest(expected):
        raise ValueError(ERROR)


def validate_question_step(raw, context, question):
    if question is None:
        raise ValueError(ERROR)
    candidate = _candidate(context, question)
    if candidate is None:
        raise ValueError(ERROR)
    validate_step(raw, candidate)


def _introductions(context, candidates, probes):
    reference = next((row for row in context.get("references", []) if row.get("id") == "math.fraction.part_whole"
        and row.get("version") == 1 and row.get("subject") == "Mathematik" and row.get("digest")), None)
    if reference is None:
        return []
    forbidden = {tuple(candidate["proof"][key]) for candidate in candidates
        for key in ("left", "right", "expanded_left", "expanded_right")}
    forbidden.update(tuple(value) for value in probes)
    result = []
    for source in expansion._sources(context):
        for base, text in _fraction_bases(source["content"]):
            if tuple(base["numbers"]) in forbidden:
                continue
            row = {"subject": "Mathematik", "group_id": None, "kind": "fraction", "disclosure": "given",
                "reference": {"id": reference["id"], "version": 1}, "source_refs": [source["ref"]],
                "text": "Vergleiche Brüche, indem du sie in gleich große Teile einteilst. " + text,
                "block": {**base, "disclosure": "given"}}
            row["id"] = "fc_" + _digest({"revision": REVISION, "candidate": row,
                "source_digest": _digest(source), "reference_digest": reference["digest"]})[:24]
            result.append(row)
            if len(result) >= 2:
                return result
    return result


@dataclass(frozen=True)
class Binding(PackageBinding):
    @property
    def rules(self):
        return ("\n" + REVISION + ": Übernimm alle Aufgabenkerne unverändert. Wähle pro Frage nur die "
            "zugehörige vorbereitete solution-ID. Einführung und Aufgabe bleiben getrennt; "
            "keine Zahlen, Lösungen, Quellen oder Aufdeckstufen ändern. Ergänze kurze Hinweise.")

    @property
    def context(self):
        return {"version": 1, "revision": REVISION, "candidates": [{key: copy.deepcopy(value)
            for key, value in row.items() if key != "block"} for row in self.candidates]}

    def question_bound(self, candidate, question):
        core = candidate.get("question_core") or (candidate.get("proof") or {}).get("task")
        return bool(core) and all(question.get(key) == value for key, value in core.items()) and question.get("learning_goal_id") is None

    def hydrate(self, data):
        result = super().hydrate({"units": [data]})["units"][0]
        choices = {candidate["id"]: candidate for candidate in self.candidates}
        for original, restored in zip(data["questions"], result["questions"], strict=True):
            step = original["explanation_steps"][0]
            selected = choices[step["presentation"]["blocks"][0]]
            if step.get("id") != selected["id"]:
                raise ValueError(ERROR)
            if selected.get("proof"):
                restored["explanation_steps"][0]["presentation"]["blocks"] = _blocks(selected)
                validate_step(restored["explanation_steps"][0], selected)
        intro = data["explanation_steps"][0]
        if intro.get("id") != intro["presentation"]["blocks"][0]:
            raise ValueError(ERROR)
        return result


def bind_schema(schema, payload):
    if KEY not in payload:
        return None
    from .notebook_fraction_expansions import _probe_candidates

    if prepare(payload) != payload:
        raise ValueError(ERROR)
    context, planned = payload["visual_context"], payload[KEY]
    candidates = [_candidate(context, task) for task in planned["tasks"]]
    if any(candidate is None for candidate in candidates):
        raise ValueError(ERROR)
    probes = _probe_candidates(payload, plan=planned, revision=REVISION)
    examples = {probe["id"]: probe for unit in (payload.get("learning_entry") or {}).get("units", [])
        for probe in unit.get("probes", [])}
    excluded = []
    for core in planned["probes"]:
        visual = examples[core["id"]]["visual_example"]
        excluded.append((visual["numerator"], visual["denominator"]))
        excluded.extend(base["numbers"] for base, _ in _fraction_bases(core["answer"]))
    introductions = _introductions(context, candidates, excluded)
    if not introductions:
        raise ValueError(ERROR)
    binding = Binding(tuple([*introductions, *probes, *candidates]))
    wrapper = {"$defs": schema["$defs"], "properties": {"units": {"items": copy.deepcopy(
        {key: value for key, value in schema.items() if key != "$defs"})}}}

    def question_binding(node, candidate):
        core = candidate.get("question_core") or candidate["proof"]["task"]
        props = node["properties"]
        for key in ("id", "type", "prompt", "answer"):
            allowed = props[key].get("enum", [props[key]["const"]] if "const" in props[key] else [])
            if allowed and core[key] not in allowed:
                return None
            props[key].update(type="string", enum=[core[key]])
        props["options"].update(minItems=0, maxItems=0)
        props["accepted"].update(minItems=0, maxItems=0)
        props["presentation"] = {"type": "null"}
        return node

    bind_candidates(wrapper, binding, question_binding=question_binding)
    for definition in wrapper["$defs"].values():
        props = definition.get("properties", {})
        ids = props.get("presentation", {}).get("properties", {}).get("blocks", {}).get("items", {}).get("enum", [])
        if len(ids) == 1 and ids[0] in {candidate["id"] for candidate in binding.candidates}:
            props["id"] = {"type": "string", "enum": ids}
            props["competence_id"] = {"type": "null"}
    body = wrapper["properties"]["units"]["items"]
    schema.clear()
    schema.update(body, **{"$defs": wrapper["$defs"]})
    return binding


def validate_output(payload, data):
    if KEY not in payload:
        return
    planned = prepare(payload)[KEY]
    cores = {row["id"]: {key: row[key] for key in CORE} for row in [*planned["probes"], *planned["tasks"]]}
    questions = data.get("questions", [])
    if (len(questions) != planned["question_count"] or {question["id"] for question in questions} != set(cores)
            or any(any(question.get(key) != value for key, value in cores[question["id"]].items()) for question in questions)):
        raise ValueError(ERROR)


def validate_history(payload, data, prompts):
    if KEY not in payload:
        return
    validate_output(payload, data)
    try:
        current = set(_signatures(prompts))
    except ValueError:
        raise ValueError(CURRENT_ERROR) from None
    from .coaching import fraction_task_signature

    for task in payload[KEY]["tasks"]:
        signature = fraction_task_signature(task["prompt"])
        if signature is None or signature[0] != "compare" or signature[1] in current:
            raise ValueError(CURRENT_ERROR)
