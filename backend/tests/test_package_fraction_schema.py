"""Artificial contract/transport tests; no provider or learning record."""

import copy
import json

import pytest
from schulpilot import package_fraction_plan as planner
from schulpilot import package_fraction_schema as contract
from schulpilot.package_output_transport import bind as codec_for
from test_package_fraction_plan_groundwork import EXPAND, REDUCE, payload, slots


def object_schema(properties):
    return {
        "type": "object",
        "properties": json.loads(json.dumps(properties)),
        "required": list(properties),
        "additionalProperties": False,
    }


def contract_schema(selected):
    string = {"type": "string"}
    question = object_schema(
        {
            "id": string,
            "type": {"type": "string", "enum": ["short", "choice"]},
            "prompt": string,
            "answer": string,
            "options": {"type": "array", "items": string},
            "accepted": {"type": "array", "items": string},
            "explanation": string,
            "explanation_steps": {"type": "array", "items": string},
        }
    )
    branches = []
    for slot in selected:
        candidate = copy.deepcopy(question)
        candidate["properties"]["id"]["enum"] = [slot["id"]]
        if slot["role"] == "practice":
            candidate["properties"]["explanation_steps"]["items"] = {"$ref": "#/$defs/ExplanationStep"}
        branches.append(candidate)
    unit = object_schema(
        {
            "group_id": {"type": "string", "enum": ["g1"]},
            "subject": {"type": "string", "enum": ["Mathematik"]},
            "questions": {
                "type": "array",
                "minItems": len(selected),
                "maxItems": len(selected),
                "items": {"anyOf": branches},
            },
        }
    )
    schema = object_schema({"units": {"type": "array", "minItems": 1, "maxItems": 1, "items": {"anyOf": [unit]}}})
    schema["$defs"] = {
        "ExplanationStep": object_schema(
            {
                "id": string,
                "text": string,
                "competence_id": {"type": "null"},
                "disclosure": string,
                "reference": {"type": "object"},
                "source_refs": {"type": "array"},
                "presentation": {"type": "object"},
            }
        )
    }
    return schema


def data_for(plan):
    questions = []
    for row in plan["slots"]:
        if row["task"] is None:
            questions.append(
                {
                    "id": row["slot"]["id"],
                    "type": "short",
                    "prompt": "Was ist ein Anteil?",
                    "answer": "Ein Teil",
                    "options": [],
                    "accepted": [],
                    "explanation": "Denk an ein Ganzes.",
                    "explanation_steps": ["prior"],
                }
            )
            continue
        step = planner.solution_step(plan, row)
        step["presentation"]["blocks"] = [step["id"]]
        questions.append({**row["task"], "explanation": step["text"], "explanation_steps": [step]})
    return {"units": [{"group_id": "g1", "subject": "Mathematik", "questions": questions}]}


@pytest.mark.parametrize("content", [EXPAND, REDUCE])
@pytest.mark.parametrize(
    "roles", [("practice", "practice"), ("prior_check", "practice"), ("prior_check", "prior_check")]
)
def test_bound_schema_and_lossless_wire_preserve_diagnostic_slots(content, roles):
    request = payload(content)
    selected = slots(*roles)
    plan = planner.prepare(request, selected, [])
    original = contract_schema(selected)
    initial = copy.deepcopy(original)
    bound = contract.bind(original, request, selected, [], plan)
    assert original == initial
    wire = data_for(plan)
    codec = codec_for(bound)
    assert codec.decode(codec.encode(wire)) == wire
    hydrated = contract.hydrate(request, selected, [], plan, wire)
    assert wire == data_for(plan)
    for index, row in enumerate(plan["slots"]):
        if row["task"]:
            assert hydrated["units"][0]["questions"][index]["explanation_steps"] == [planner.solution_step(plan, row)]
        else:
            assert hydrated["units"][0]["questions"][index] == wire["units"][0]["questions"][index]


@pytest.mark.parametrize("change", ["answer", "prompt", "question_id", "step_id", "source", "disclosure"])
def test_wrong_planned_fields_or_graphic_id_fail_before_or_after_transport(change):
    request = payload()
    selected = slots("practice", "practice")
    plan = planner.prepare(request, selected, [])
    bound = contract.bind(contract_schema(selected), request, selected, [], plan)
    data = data_for(plan)
    question = data["units"][0]["questions"][0]
    step = question["explanation_steps"][0]
    if change == "answer":
        question["answer"] = "1/99"
    if change == "prompt":
        question["prompt"] += " verändert"
    if change == "question_id":
        question["id"] = "unknown"
    if change == "step_id":
        step["presentation"]["blocks"] = ["other"]
    if change == "source":
        step["source_refs"] = ["other"]
    if change == "disclosure":
        step["disclosure"] = "given"
    with pytest.raises(ValueError):
        codec_for(bound).encode(data)
    with pytest.raises(ValueError):
        contract.hydrate(request, selected, [], plan, data)


def test_incompatible_existing_constraint_never_gets_overwritten():
    request = payload()
    selected = slots("practice", "practice")
    plan = planner.prepare(request, selected, [])
    original = contract_schema(selected)
    original["properties"]["units"]["items"]["anyOf"][0]["properties"]["questions"]["items"]["anyOf"][0]["properties"][
        "answer"
    ]["enum"] = ["not the planned answer"]
    untouched = copy.deepcopy(original)
    with pytest.raises(ValueError):
        contract.bind(original, request, selected, [], plan)
    assert original == untouched


def test_existing_fixed_graphic_binding_is_never_overwritten():
    request = payload()
    selected = slots("practice", "practice")
    plan = planner.prepare(request, selected, [])
    original = contract_schema(selected)
    branch = original["properties"]["units"]["items"]["anyOf"][0]["properties"]["questions"]["items"]["anyOf"][0]
    branch["properties"]["explanation_steps"]["items"] = {"$ref": "#/$defs/AlreadyBoundStep"}
    with pytest.raises(ValueError, match="nicht mehr gültig"):
        contract.bind(original, request, selected, [], plan)


def test_hydrator_rejects_swapped_graphics_even_if_the_schema_were_bypassed():
    request = payload()
    selected = slots("practice", "practice")
    plan = planner.prepare(request, selected, [])
    wire = data_for(plan)
    first, second = wire["units"][0]["questions"]
    first["explanation_steps"][0]["presentation"]["blocks"] = second["explanation_steps"][0]["presentation"]["blocks"]
    with pytest.raises(ValueError, match="geplanten Lösungsschritt"):
        contract.hydrate(request, selected, [], plan, wire)


def test_hydrator_rejects_duplicate_question_slot_without_repair():
    request = payload()
    selected = slots("practice", "practice")
    plan = planner.prepare(request, selected, [])
    wire = data_for(plan)
    wire["units"][0]["questions"][1] = copy.deepcopy(wire["units"][0]["questions"][0])
    with pytest.raises(ValueError, match="genau einmal"):
        contract.hydrate(request, selected, [], plan, wire)


@pytest.mark.parametrize("mode", ["source_probe", "reuse_evidence"])
def test_actual_package_schema_accepts_bound_contract_and_keeps_prior_branches(household, mode):
    from schulpilot import learning_entry, providers, visual_references
    from schulpilot.db import DB
    from schulpilot.schemas import PackageOutput
    from schulpilot.subject_content import bind_graphic_schema
    from test_package_prepared_graphics import payload_for

    request = payload_for(EXPAND)
    request["learning_entry"] = {
        "units": [
            {
                "group_id": "g1",
                "subject": "Mathematik",
                "entry_mode": mode,
                "prefix": "synthetic",
                "probes": [],
                "allocation_version": 2,
            }
        ]
    }
    with DB() as db:
        request = planner.add_reference(db, request)
    selected = learning_entry._specs(request["learning_entry"]["units"][0], 2)
    plan = planner.prepare(request, selected, [])
    schema = providers.strict_schema(PackageOutput, preserve_limits=True)
    providers.prepare_package_schema(schema, request, partition=True)
    bind_graphic_schema(schema, ["Mathematik"])
    visual_references.bind_schema(schema, request)
    learning_entry.bind_entry_schema(schema, request)
    bound = contract.bind(schema, request, selected, [], plan)
    group = bound["properties"]["units"]["items"]["anyOf"][0]
    branches = group["properties"]["questions"]["items"]["anyOf"]
    for row in plan["slots"]:
        own = [b for b in branches if b["properties"]["id"]["enum"] == [row["slot"]["id"]]]
        assert own
        if row["task"]:
            assert all(b["properties"]["answer"]["enum"] == [row["task"]["answer"]] for b in own)
        else:
            assert any("enum" not in b["properties"]["answer"] for b in own)


@pytest.mark.parametrize("content", [EXPAND, REDUCE])
def test_real_package_codec_roundtrip_hydrates_only_bound_fraction_steps(household, content):
    from schulpilot import (
        learning_entry,
        package_part_output,
        package_prepared_graphics,
        package_transport,
        providers,
        visual_references,
    )
    from schulpilot.db import DB
    from schulpilot.schemas import PackageOutput
    from schulpilot.subject_content import bind_graphic_schema
    from test_package_prepared_graphics import payload_for

    request = payload_for(content)
    request["learning_entry"] = {
        "units": [
            {
                "group_id": "g1",
                "subject": "Mathematik",
                "entry_mode": "reuse_evidence",
                "prefix": "synthetic",
                "probes": [],
                "allocation_version": 2,
            }
        ]
    }
    with DB() as db:
        request["visual_context"]["references"] = visual_references.candidates(
            db, "Mathematik", content, package_prepared=True
        )
        request = planner.add_reference(db, request)
    selected = learning_entry._specs(request["learning_entry"]["units"][0], 2)
    plan = planner.prepare(request, selected, [])
    schema = providers.strict_schema(PackageOutput, preserve_limits=True)
    providers.prepare_package_schema(schema, request, partition=True)
    bind_graphic_schema(schema, ["Mathematik"])
    visual_references.bind_schema(schema, request)
    learning_entry.bind_entry_schema(schema, request)
    schema = contract.bind(schema, request, selected, [], plan)
    intro = next(
        r
        for r in package_prepared_graphics.compile_candidates(request)
        if r["kind"] == "fraction" and r["disclosure"] == "given"
    )
    intro_step = {
        "id": "e1",
        "text": intro["text"],
        "competence_id": None,
        "disclosure": "given",
        "reference": intro["reference"],
        "source_refs": intro["source_refs"],
        "presentation": {"version": 1, "evidence_kind": "knowledge", "blocks": [intro["block"]]},
    }
    questions = []
    for row in plan["slots"]:
        step = planner.solution_step(plan, row)
        step["presentation"]["blocks"] = [step["id"]]
        questions.append(
            {
                **row["task"],
                "hints": ["Denk an Zähler und Nenner."],
                "explanation": step["text"],
                "presentation": None,
                "field_group": None,
                "explanation_steps": [step],
            }
        )
    value = {
        "units": [
            {
                "group_id": "g1",
                "subject": "Mathematik",
                "topic": "Brüche",
                "explanation": intro["text"],
                "explanation_steps": [intro_step],
                "questions": questions,
            }
        ]
    }
    codec = codec_for(package_transport.schema_projection(schema))
    decoded = codec.decode(codec.encode(value))
    assert decoded == value
    restored = contract.hydrate(request, selected, [], plan, decoded)
    PackageOutput.model_validate(restored)
    assert all(len(q["explanation_steps"][0]["presentation"]["blocks"]) == 2 for q in restored["units"][0]["questions"])
    with pytest.raises(ValueError, match="Grafikschritt"):
        package_part_output.validate(restored)
    package_part_output.validate(restored, fraction_plan=plan)
    changed = copy.deepcopy(restored)
    changed["units"][0]["questions"][0]["explanation_steps"][0]["presentation"]["blocks"][1]["numbers"][0] += 1
    with pytest.raises(ValueError, match="Grafikschritt"):
        package_part_output.validate(changed, fraction_plan=plan)
    changed = copy.deepcopy(restored)
    changed["units"][0]["explanation_steps"][0]["presentation"]["blocks"] *= 2
    with pytest.raises(ValueError, match="Grafikschritt"):
        package_part_output.validate(changed, fraction_plan=plan)
    altered_plan = copy.deepcopy(plan)
    altered_plan["slots"][0]["task"]["answer"] = "1/99"
    with pytest.raises(ValueError, match="Grafikplan"):
        package_part_output.validate(restored, fraction_plan=altered_plan)
    protected_context = copy.deepcopy(request)
    protected_context["visual_context"]["package_fraction_plan"] = copy.deepcopy(plan)
    changed_proof = copy.deepcopy(restored)
    changed_proof["units"][0]["questions"][0]["explanation_steps"][0]["presentation"]["blocks"][1]["numbers"][0] += 1
    with DB() as db:
        visual_references.validate_output(db, restored, protected_context)
        with pytest.raises(ValueError):
            visual_references.validate_output(db, restored, request)
        with pytest.raises(ValueError):
            visual_references.validate_output(db, changed_proof, protected_context)


def test_actual_fixed_prerequisite_branches_are_left_byte_identical(household):
    from schulpilot import competences, learning_entry, providers, visual_references
    from schulpilot.db import DB
    from schulpilot.schemas import PackageOutput
    from schulpilot.subject_content import bind_graphic_schema
    from test_package_prepared_graphics import payload_for

    request = payload_for(EXPAND)
    probe = learning_entry._probe(competences.catalogue()["math.fractions.meaning"], "fraction-synthetic", set(), "1")
    entry = {
        "group_id": "g1",
        "subject": "Mathematik",
        "entry_mode": "prerequisite_probe",
        "prefix": "synthetic",
        "probes": [probe],
        "allocation_version": 2,
    }
    request["learning_entry"] = {
        "units": [entry],
        "references": [competences.resolve_reference(probe["reference_id"], competences.VERSION)],
    }
    with DB() as db:
        request = visual_references.with_foundation_context(db, request)
        request = planner.add_reference(db, request)
    selected = learning_entry._specs(entry, 2)
    plan = planner.prepare(request, selected, [])
    schema = providers.strict_schema(PackageOutput, preserve_limits=True)
    providers.prepare_package_schema(schema, request, partition=True)
    bind_graphic_schema(schema, ["Mathematik"])
    visual_references.bind_schema(schema, request)
    learning_entry.bind_entry_schema(schema, request)

    def questions(value):
        return value["properties"]["units"]["items"]["anyOf"][0]["properties"]["questions"]["items"]["anyOf"]

    prior_id = selected[0]["id"]
    original = [b for b in questions(schema) if b["properties"]["id"]["enum"] == [prior_id]]
    bound = contract.bind(schema, request, selected, [], plan)
    assert original and [b for b in questions(bound) if b["properties"]["id"]["enum"] == [prior_id]] == original
