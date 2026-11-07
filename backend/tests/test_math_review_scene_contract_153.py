"""The model contract and canonical source checks for synthetic review scenes."""
import copy

import pytest
from schulpilot import providers, unit_reference_graphics
from schulpilot.graphic_schema import bind_coherent_graphics
from schulpilot.learning_scenes import validate as validate_scene
from schulpilot.package_prepared_graphics import _scene_bases
from schulpilot.schemas import PracticeUnitOutput
from schulpilot.subject_content import Graphic, bind_graphic_schema
from schulpilot.visual_references import _meaningful
from test_unit_reference_graphics_135 import branches

REFERENCE = {"id": "general.source_relation.phases", "version": 1,
             "subject": "Mathematik", "kind": "scene"}
SOURCE = "Ausgang → Ergebnis."


def make_schema(source=SOURCE):
    schema = providers.strict_schema(PracticeUnitOutput, preserve_limits=True)
    bind_graphic_schema(schema, ["Mathematik"])
    bind_coherent_graphics(schema)
    payload = {"review": True, "required_subject": "Mathematik",
        "material": {"subject": "Mathematik", "content": source},
        "visual_context": {"required": True, "references": [REFERENCE],
            "sources": [{"ref": "p1", "subject": "Mathematik", "group_id": None, "content": source}]}}
    return schema, payload


def deref(schema, node):
    return schema["$defs"][node["$ref"].rsplit("/", 1)[-1]] if "$ref" in node else node


def test_review_binds_relation_reference_to_two_phases_and_edges_without_altering_shared_scene():
    schema, payload = make_schema()
    previous_scene = copy.deepcopy(schema["$defs"]["SceneV1"])
    assert unit_reference_graphics.bind_schema(schema, payload)
    assert schema["$defs"]["SceneV1"] == previous_scene
    for step in branches(schema, schema["properties"]["explanation_steps"]["items"]):
        p = step["properties"]
        assert deref(schema, p["reference"])["properties"]["id"]["enum"] == [REFERENCE["id"]]
        panel = deref(schema, p["presentation"])
        graphic = deref(schema, panel["properties"]["blocks"]["items"])
        scene = deref(schema, graphic["properties"]["scene"])
        assert scene["properties"]["objects"]["minItems"] == 2
        assert scene["properties"]["steps"]["minItems"] == 2
        phase = deref(schema, scene["properties"]["steps"]["items"])
        assert phase["properties"]["edges"]["minItems"] == 1
    from test_graphic_native_transport import subset_record

    providers.prune_schema(schema)
    subset_record(schema)


def test_review_does_not_offer_relation_without_a_source_arrow():
    schema, payload = make_schema("Ausgang und Ergebnis.")
    with pytest.raises(ValueError, match="keine passende Referenz/Grafik"):
        unit_reference_graphics.bind_schema(schema, payload)


def test_relation_checks_still_reject_missing_or_fabricated_arrows():
    value = next(_scene_bases(SOURCE))[0]
    value["disclosure"] = "hint1"
    block = Graphic.model_validate(value)
    _meaningful(block, REFERENCE)
    validate_scene(block, {"prompt": ""}, [SOURCE])
    missing = copy.deepcopy(value)
    for phase in missing["scene"]["steps"]:
        phase["edges"] = []
    with pytest.raises(ValueError, match="belegte Beziehungen"):
        _meaningful(Graphic.model_validate(missing), REFERENCE)
    reversed_value = copy.deepcopy(value)
    reversed_value["scene"]["steps"][0]["edges"][0].update(start="o1", end="o0")
    with pytest.raises(ValueError):
        validate_scene(Graphic.model_validate(reversed_value), {"prompt": ""}, [SOURCE])
    with pytest.raises(ValueError):
        validate_scene(block, {"prompt": ""}, ["Ein anderer bestätigter Quelltext."])


def test_fraction_review_without_arrow_uses_existing_grounded_fraction_recipe(monkeypatch):
    from schulpilot.db import DB
    from schulpilot.visual_references import candidates
    from test_graphic_native_transport import subset_record
    from test_model_routing import policy
    from test_presentation_capability_paths import _config, _submitted, _transport
    from test_visual_references import SOURCE as FRACTION_SOURCE
    from test_visual_references import question, step

    with DB() as db:
        refs = candidates(db, "Mathematik", FRACTION_SOURCE)
    assert {"math.fraction.part_whole", REFERENCE["id"]} <= {r["id"] for r in refs}
    source = {"ref": "p1", "subject": "Mathematik", "group_id": None,
              "content": FRACTION_SOURCE, "material_id": "a" * 32, "revision": 1, "source_refs": []}
    visual_context = {"version": 1, "required": True, "reason": None, "references": refs, "sources": [source]}
    q1 = question()
    q2 = copy.deepcopy(q1)
    q1.update(id="q1", learning_goal_id="g1")
    q2.update(id="q2", learning_goal_id="g2", prompt="Wie schreibt man einen von zwei Teilen als Bruch?")
    value = {"subject": "Mathematik", "topic": "Brüche", "explanation": FRACTION_SOURCE,
             "explanation_steps": [step()], "questions": [q1, q2]}
    goals = [{"id": "g1", "label": "Brüche verstehen", "source_excerpt": FRACTION_SOURCE},
             {"id": "g2", "label": "Brüche schreiben", "source_excerpt": FRACTION_SOURCE}]
    payload = {"material": {"subject": "Mathematik", "topic": "Brüche", "content": FRACTION_SOURCE},
               "required_subject": "Mathematik", "review": True,
               "learning_goals": goals, "visual_context": visual_context}
    config = _config("openrouter")
    config.max_output_tokens, config.reserve_micros = 8000, 250000
    approved = policy()
    config._selected_route = {"reason": "material_or_new_teaching", "tier": "sol", "region": "standard",
        "route": {**approved["routes"]["sol"], "upstreams": ["fixture-upstream"]}, "budget": approved["budget"]}
    calls = _transport(monkeypatch, "openrouter", value)
    result = providers.request_provider(config, "unit", payload)
    assert [q["learning_goal_id"] for q in result.data["questions"]] == ["g1", "g2"]
    assert result.data["explanation_steps"][0]["presentation"]["blocks"][0]["numbers"] == [1, 2]
    assert len(calls) == 1
    _, schema, instructions = _submitted("openrouter", calls[0])
    assert "unit-reference-graphics-1" in instructions
    for owner in [schema, *branches(schema, schema["properties"]["questions"]["items"])]:
        for item in branches(schema, owner["properties"]["explanation_steps"]["items"]):
            ids = deref(schema, item["properties"]["reference"])["properties"]["id"]["enum"]
            assert REFERENCE["id"] not in ids
    subset_record(calls[0]["response_format"]["json_schema"]["schema"])
