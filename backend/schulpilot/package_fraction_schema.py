"""Private wire contract for planned package fraction questions.

The caller must independently check rights, source revisions, history and the
stored reference. This binder alone must not be used to dispatch a job.
"""
import copy
import re

from .package_fraction_plan import INVALID, solution_step, validate, validate_generated_output

SLOTS_MISMATCH = 'Die Antwort enthält nicht alle geplanten Bruchaufgaben genau einmal.'
STEP_MISMATCH = 'Die übertragene Bruchgrafik stimmt nicht mit dem geplanten Lösungsschritt überein.'
OUTPUT_MISMATCH = 'Die übertragene Bruchaufgabe stimmt nicht mit dem geprüften Plan überein.'


def _accepts(field, value):
    if not isinstance(field, dict) or any(key in field for key in ("$ref", "oneOf", "allOf", "not")):
        return False
    if "const" in field and field["const"] != value:
        return False
    if "enum" in field and value not in field["enum"]:
        return False
    if "anyOf" in field:
        return isinstance(field["anyOf"], list) and any(_accepts(branch, value) for branch in field["anyOf"])
    if isinstance(value, str):
        if field.get("type") != "string" or len(value) < field.get("minLength", 0) or len(value) > field.get("maxLength", 100000):
            return False
        if "pattern" in field:
            try:
                if not re.search(field["pattern"], value):
                    return False
            except (re.error, TypeError):
                return False
        return True
    if isinstance(value, list):
        return (field.get("type") == "array" and len(value) >= field.get("minItems", 0)
                and len(value) <= field.get("maxItems", 100000) and value == [])
    return False


def bind(schema, payload, slots, previous_prompts, plan):
    """Constrain practice branches; leave prior-check branches unchanged.

    Schema must already have server-assigned, singleton question IDs. The
    exact candidate ID replaces each practice step only inside that branch.
    No shared definition is modified and no caller-owned schema is changed.
    """
    validate(payload, slots, previous_prompts, plan)
    result = copy.deepcopy(schema)
    try:
        defs = result["$defs"]
        field = result["properties"]["units"]["items"]["anyOf"]
        if len(field) != 1:
            raise ValueError(INVALID)
        unit = field[0]
        props = unit["properties"]
        if props["group_id"].get("enum") != [plan["group_id"]] or props["subject"].get("enum") != ["Mathematik"]:
            raise ValueError(INVALID)
        branches = props["questions"]["items"]["anyOf"]
        if not isinstance(branches, list) or not branches:
            raise ValueError(INVALID)
        planned = {row["slot"]["id"]: row for row in plan["slots"] if row.get("task") is not None}
        expected = {row["slot"]["id"] for row in plan["slots"]}
        seen = set()
        retained = []
        for original in branches:
            branch = copy.deepcopy(original)
            values = branch["properties"]["id"].get("enum")
            if not isinstance(values, list) or len(values) != 1 or values[0] not in expected:
                raise ValueError(INVALID)
            ident = values[0]
            if ident not in planned:
                retained.append(branch)
                seen.add(ident)
                continue
            row = planned[ident]
            fields = branch["properties"]
            if not all(_accepts(fields.get(key), value) for key, value in row["task"].items()):
                continue
            # Never replace another binder's fixed graphic or incompatible
            # length. Only an untouched generic explanation slot is eligible.
            old_steps = fields.get("explanation_steps")
            if (not isinstance(old_steps, dict) or old_steps.get("type") != "array"
                    or old_steps.get("items") != {"$ref": "#/$defs/ExplanationStep"}
                    or old_steps.get("minItems", 0) > 1 or old_steps.get("maxItems", 100000) < 1
                    or any(k in old_steps for k in ("enum", "const", "contains", "prefixItems"))):
                raise ValueError(INVALID)
            for key, value in row["task"].items():
                fields[key] = ({**fields[key], "minItems": 0, "maxItems": 0} if isinstance(value, list)
                               else {**fields[key], "enum": [value]})
            step = solution_step(plan, row)
            if not _accepts(fields.get("explanation"), step["text"]):
                continue
            fields["explanation"] = {**fields["explanation"], "enum": [step["text"]]}
            candidate = step["id"]
            definition = copy.deepcopy(defs["ExplanationStep"])
            sf = definition["properties"]
            for key in ("id", "text", "disclosure"):
                sf[key] = {"type": "string", "enum": [step[key]]}
            sf["competence_id"] = {"type": "null"}
            sf["reference"] = {"type": "object", "properties": {
                "id": {"type": "string", "enum": [step["reference"]["id"]]},
                "version": {"type": "integer", "enum": [step["reference"]["version"]]}},
                "required": ["id", "version"], "additionalProperties": False}
            sf["source_refs"] = {"type": "array", "minItems": 1, "maxItems": 1,
                                 "items": {"type": "string", "enum": step["source_refs"]}}
            sf["presentation"] = {"type": "object", "properties": {
                "version": {"type": "integer", "enum": [1]},
                "evidence_kind": {"type": "string", "enum": ["knowledge"]},
                "blocks": {"type": "array", "minItems": 1, "maxItems": 1,
                           "items": {"type": "string", "enum": [candidate]}}},
                "required": ["version", "evidence_kind", "blocks"], "additionalProperties": False}
            name = "FractionPlan_" + candidate
            if name in defs and defs[name] != definition:
                raise ValueError(INVALID)
            defs[name] = definition
            fields["explanation_steps"] = {"type": "array", "minItems": 1, "maxItems": 1,
                                          "items": {"$ref": "#/$defs/" + name}}
            retained.append(branch)
            seen.add(ident)
        if seen != expected:
            raise ValueError(INVALID)
        props["questions"]["items"]["anyOf"] = retained
    except (KeyError, TypeError, IndexError):
        raise ValueError(INVALID) from None
    return result


def hydrate(payload, slots, previous_prompts, plan, wire):
    """Hydrate only exact planned IDs; original wire data is never modified."""
    validate(payload, slots, previous_prompts, plan)
    value = copy.deepcopy(wire)
    try:
        units = value["units"]
        if len(units) != 1 or not isinstance(units[0]["questions"], list):
            raise ValueError(INVALID)
        questions = units[0]['questions']
        actual_ids = [question.get('id') for question in questions if isinstance(question, dict)]
        expected_ids = [row['slot']['id'] for row in plan['slots']]
        if len(actual_ids) != len(questions) or len(set(actual_ids)) != len(actual_ids) or set(actual_ids) != set(expected_ids):
            raise ValueError(SLOTS_MISMATCH)
        candidates = {row["slot"]["id"]: row for row in plan["slots"] if row.get("task") is not None}
        for question in questions:
            row = candidates.get(question.get("id"))
            if row is None:
                continue
            expected = solution_step(plan, row)
            encoded = copy.deepcopy(expected)
            encoded["presentation"]["blocks"] = [expected["id"]]
            if question.get("explanation_steps") != [encoded]:
                raise ValueError(STEP_MISMATCH)
            question["explanation_steps"] = [expected]
        try:
            validate_generated_output(payload, slots, previous_prompts, plan, value)
        except ValueError:
            raise ValueError(OUTPUT_MISMATCH) from None
    except (KeyError, TypeError, IndexError, AttributeError):
        raise ValueError(INVALID) from None
    return value
