"""Synthetic divisor-set proofs and narrowly scoped evaluation; no provider calls."""

import copy

import pytest
from schulpilot import answer_evaluation as answers
from schulpilot import review_divisibility_plan as plan
from schulpilot import review_divisor_set as divset
from schulpilot import visual_references
from schulpilot.package_prepared_graphics import _digest
from test_review_divisibility_plan import RULE, original, wire
from test_review_fraction_compositions_142 import RecipeLookup

SET = "T_18 = {1, 2, 3, 6, 9, 18}"


@pytest.fixture(autouse=True)
def clean_database():
    # This suite uses only in-memory fixtures and immutable recipe lookups.
    yield


def context(quote=SET):
    recipe = divset.public_recipe()
    return {
        "sources": [
            {
                "ref": "p1",
                "subject": "Mathematik",
                "group_id": None,
                "material_id": "a" * 32,
                "revision": 1,
                "content": "Teiler\n" + quote,
                "source_refs": [],
                "factual_status": "not_assessed",
            }
        ],
        "references": [
            {"id": recipe["id"], "version": 1, "subject": "Mathematik", "kind": "scene", "digest": _digest(recipe)}
        ],
    }


def task(quote=SET):
    return {
        "id": "q2",
        "learning_goal_id": "g2",
        "label": "Die Teiler von 18 vollständig angeben",
        "source_excerpt": quote,
    }


def generated():
    source = original()
    source["visual_context"]["sources"][0]["content"] = RULE + "\n" + SET
    source["material"]["content"] = RULE + "\n" + SET
    source["learning_goals"][1] = task() | {"id": "g2"}
    source["learning_goals"][1].pop("learning_goal_id")
    body = plan.prepare(plan.with_history(plan.add_references(RecipeLookup(), source), []))
    binding, response = wire(body)
    return body, binding.hydrate(response)


def test_complete_set_is_bound_to_goal_and_solution_only():
    ctx = context()
    question, scene = divset.compile_candidate(ctx, task())
    assert question["learning_goal_id"] == "g2"
    assert question["answer"] == "1, 2, 3, 6, 9, 18"
    assert scene["block"]["disclosure"] == "solution"
    assert len(scene["block"]["scene"]["objects"]) == 6
    assert len(scene["block"]["scene"]["steps"]) == 2
    divset.validate_step(divset.step_for(scene), ctx, question, task())
    assert divset.compile_candidate(ctx, task(), ["Nenne Teiler von 18"]) is None
    assert divset.compile_candidate(ctx, task(), ["Nenne Teiler von achtzehn"]) is None
    for mutation in ("question", "scene", "disclosure", "revision", "goal"):
        q, step, changed = copy.deepcopy(question), copy.deepcopy(divset.step_for(scene)), copy.deepcopy(ctx)
        if mutation == "question":
            q["answer"] = "1, 2"
        if mutation == "scene":
            step["presentation"]["blocks"][0]["scene"]["objects"][0]["label"] = "99"
        if mutation == "disclosure":
            step["disclosure"] = "given"
        if mutation == "revision":
            changed["sources"][0]["revision"] = 2
        if mutation == "goal":
            q["learning_goal_id"] = "g1"
        with pytest.raises(ValueError):
            divset.validate_step(step, changed, q, task())


@pytest.mark.parametrize(
    "quote",
    [
        "T_18 = {1, 2, 3, 6, 9}",
        "T_18 = {1, 2, 3, 6, 9, 17, 18}",
        "T_18 = {1, 2, 3, 6, 9, 9, 18}",
        "T_18 = {2, 1, 3, 6, 9, 18}",
        "T_18 = {1, 2, 3, 6, 9, 18} falsch",
        "T_18 = {1, 2, 3, 6, 9, 18} ~~",
        "T_18 = {1, 2, 3, 6, 9, 18} und T_9 = {1, 3, 9}",
        "T_18 = {1, 2, 3, 6, 9, 18} ∪ {99}",
        "T_18 = {1, 2, 3, 6, 9, 18} = {99}",
        "T_18 = {1, 2, 3, 6, 9, 18} + 1",
        "T_20 = {1, 2, 4, 5, 10, 20}",
        "T_18 = {1 2 3 6 9 18}",
        "T_18 = {, 1, 2, 3, 6, 9, 18}",
        "T_18 = {1,, 2, 3, 6, 9, 18}",
    ],
)
def test_rejects_incomplete_conflicting_or_ambiguous_source(quote):
    assert divset.compile_candidate(context(quote), task(quote)) is None


def test_two_goal_transport_and_solutions_are_bound():
    body, data = generated()
    plan.validate_output(body, data)
    visual_references.validate_output(RecipeLookup(), data, body)
    assert [q["learning_goal_id"] for q in data["questions"]] == ["g1", "g2"]
    target = data["questions"][1]
    assert target["hints"] == ["Teile die Zahl durch mögliche Teiler. Wo bleibt kein Rest?"]
    assert target["explanation_steps"][0]["disclosure"] == "solution"
    for change in ("source", "answer", "scene", "goal", "hint", "history"):
        altered, changed = copy.deepcopy(body), copy.deepcopy(data)
        if change == "source":
            altered["visual_context"]["sources"][0]["revision"] += 1
        if change == "answer":
            changed["questions"][1]["answer"] = "1, 18"
        if change == "scene":
            changed["questions"][1]["explanation_steps"][0]["presentation"]["blocks"][0]["scene"]["objects"][0][
                "label"
            ] = "99"
        if change == "goal":
            changed["questions"][1]["learning_goal_id"] = "g1"
        if change == "hint":
            changed["questions"][1]["hints"] = ["Schau auf die fertige Menge."]
        with pytest.raises(ValueError):
            if change == "history":
                plan.validate_history(altered, changed, ["Nenne alle Teiler von 18."])
            else:
                plan.validate_output(altered, changed)


@pytest.mark.parametrize(
    ("given", "outcome"),
    [
        ("18, 9, 6, 3, 2, 1", "correct"),
        ("{1;2;3;6;9;18}", "correct"),
        ("1, 2, 3, 6, 9", "incorrect"),
        ("1, 2, 3, 6, 9, 18, 19", "incorrect"),
        ("1, 2, 3, 6, 9, 18, 18", "incorrect"),
        ("1, 2, 3, vielleicht 6, 9, 18", "uncertain"),
        ("", "uncertain"),
        ("1 2 3 6 9 18", "uncertain"),
    ],
)
def test_set_answer_is_order_independent_and_strict(given, outcome):
    _, data = generated()
    assert answers.evaluate(data["questions"][1], given)["outcome"] == outcome


def test_other_tasks_and_forged_key_are_not_reinterpreted():
    _, data = generated()
    question = data["questions"][1]
    forged = copy.deepcopy(question)
    forged["answer"] = "1, 2"
    assert answers.evaluate(forged, "1, 2")["outcome"] == "uncertain"
    other = copy.deepcopy(question)
    other["explanation_steps"] = []
    assert answers.verified_divisor_set(other, "18, 9, 6, 3, 2, 1") is None
    other = copy.deepcopy(question)
    other["prompt"] = "Nenne die Elemente der Menge."
    assert answers.verified_divisor_set(other, "18, 9, 6, 3, 2, 1") is None


def test_spelled_out_history_is_excluded():
    source = original()
    source["visual_context"]["sources"][0]["content"] = RULE + "\n" + SET
    source["material"]["content"] = RULE + "\n" + SET
    source["learning_goals"][1] = {"id": "g2", "label": "Die Teiler von 18 vollständig angeben", "source_excerpt": SET}
    source = plan.add_references(RecipeLookup(), source)
    with pytest.raises(ValueError):
        plan.prepare(plan.with_history(source, ["Welche Teiler hat achtzehn?"]))
    assert {12, 21, 118} <= plan._written_numbers(["zwölf, ein und zwanzig und einhundertachtzehn"])


def test_mock_provider_transport_enforces_both_goals_and_graphics(monkeypatch):
    import json

    import httpx
    from schulpilot import db as storage
    from schulpilot import providers
    from schulpilot.config import settings
    from test_review_fraction_compositions_142 import config

    source = original()
    source["visual_context"]["sources"][0]["content"] = RULE + "\n" + SET
    source["material"]["content"] = RULE + "\n" + SET
    source["learning_goals"][1] = {"id": "g2", "label": "Die Teiler von 18 vollständig angeben", "source_excerpt": SET}
    body = plan.prepare(plan.with_history(plan.add_references(RecipeLookup(), source), []))
    _, response = wire(body)
    calls, client = [], httpx.Client

    def handler(request):
        calls.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(response)}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 500, "cost": 0.001},
            },
        )

    monkeypatch.setattr(storage, "DB", RecipeLookup)
    from dataclasses import replace

    synthetic_settings = replace(settings, real_data_approved=True, privacy_evidence="Synthetic fixture")
    monkeypatch.setattr(providers, "runtime_settings", lambda: synthetic_settings)
    monkeypatch.setattr(providers.httpx, "Client", lambda **kwargs: client(transport=httpx.MockTransport(handler)))
    result = providers.request_provider(config(), "unit", body)
    assert len(calls) == 1
    assert [q["learning_goal_id"] for q in result.data["questions"]] == ["g1", "g2"]
    plan.validate_output(body, result.data)
    visual_references.validate_output(RecipeLookup(), result.data, body)
    from test_graphic_native_transport import subset_record

    subset_record(calls[0]["response_format"]["json_schema"]["schema"])


@pytest.mark.parametrize("suffix", [" ∪ {99}", " + 1", " = {99}", " \\cup {99}"])
def test_short_goal_quote_cannot_hide_source_expression_continuation(suffix):
    ctx = context()
    ctx["sources"][0]["content"] += suffix
    assert divset.compile_candidate(ctx, task()) is None


@pytest.mark.parametrize("prefix", ["A ∪ ", "2 + ", "3 × ", "A \\cap ", "A ⊆ ", "A ≠ "])
def test_short_goal_quote_cannot_hide_source_expression_prefix(prefix):
    ctx = context()
    ctx["sources"][0]["content"] = "Teiler\n" + prefix + SET
    assert divset.compile_candidate(ctx, task()) is None


@pytest.mark.parametrize("suffix", [" ⊆ {99}", " ≠ {99}", " ∈ {99}"])
def test_unicode_operator_after_source_set_is_rejected(suffix):
    ctx = context()
    ctx["sources"][0]["content"] += suffix
    assert divset.compile_candidate(ctx, task()) is None


def test_public_projection_never_exposes_solution_or_private_quote_early():
    import json

    _, candidate = divset.compile_candidate(context(), task())
    step = divset.step_for(candidate)
    for hints in range(4):
        assert visual_references.public_steps([step], closed=False, hints=hints) == []
        view = visual_references.public_presentation(step["presentation"], closed=False, hints=hints)
        assert view["blocks"] == []
        assert SET not in json.dumps(view, ensure_ascii=False)
    disclosed = visual_references.public_steps([step], closed=True, hints=3)
    assert len(disclosed) == 1
    assert len(disclosed[0]["presentation"]["blocks"]) == 1
    assert SET not in json.dumps(disclosed, ensure_ascii=False)
    assert "source_excerpt" not in json.dumps(disclosed, ensure_ascii=False)
