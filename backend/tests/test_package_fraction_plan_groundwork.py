"""Pure planning only: this does not test or enable a package provider path."""

import copy
from fractions import Fraction

import pytest
from schulpilot import package_fraction_plan as planner

EXPAND = "Beim Erweitern multipliziert man Zähler und Nenner mit derselben Zahl. Beispiel: 1/2 = 2/4."
REDUCE = "Beim Kürzen teilt man Zähler und Nenner durch dieselbe Zahl. Beispiel: 2/4 = 1/2."
OCR_EXPAND = "Brüche erweitern\n\nZähler und Nenner mit derselben Zahl multiplizieren.\n\n2/3 = 4/6."
OCR_REDUCE = "Brüche kürzen\n\nZähler und Nenner durch dieselbe Zahl teilen.\n\n3/9 = 1/3."


def payload(content=EXPAND):
    return {
        "package_partition": 0,
        "package_plan_digest": "a" * 64,
        "selected_groups": [{"id": "g1", "subject": "Mathematik"}],
        "visual_context": {
            "required": True,
            "references": [
                {"id": "math.fraction.expansion", "version": 1, "subject": "Mathematik", "digest": "a" * 64},
                {"id": "math.fraction.reduction", "version": 1, "subject": "Mathematik", "digest": "b" * 64},
            ],
            "sources": [
                {
                    "ref": "p1",
                    "group_id": "g1",
                    "material_id": "1" * 32,
                    "revision": 1,
                    "subject": "Mathematik",
                    "content": content,
                }
            ],
        },
    }


def slots(*roles):
    return [{"id": f"q{i + 1}", "role": role} for i, role in enumerate(roles)]


@pytest.mark.parametrize(
    "content",
    [
        "Brüche kürzen\n\nBeim Kürzen teilt man Zähler und Nenner\ndurch dieselbe Zahl. Beispiel: 2/4 = 1/2.",
        "Beim Kürzen werden Zähler und Nenner\ndurch die gleiche Zahl geteilt.",
    ],
)
def test_wrapped_literal_reduction_rule_is_planned_without_changing_its_source(content):
    value = planner.prepare(payload(content), slots("practice"), [])
    assert value["operation"] == "reduce"
    assert "\n" in value["source_excerpt"] and value["source_excerpt"] in content


@pytest.mark.parametrize(
    "content",
    [
        "Beim Kürzen teilt man Zähler und Nenner\n\ndurch dieselbe Zahl.",
        "Beim Kürzen teilt man Zähler und Nenner\nnicht durch dieselbe Zahl.",
        "Falsches Beispiel beim Kürzen: Man teilt Zähler und Nenner\ndurch dieselbe Zahl.",
        "Beim Kürzen teilt man Zähler und Nenner\ndurch dieselbe Zahl. Heute nur durch 2.",
        "Beim Kürzen teilt man Zähler und Nenner\nbeim Vergleich durch dieselbe Zahl.",
    ],
)
def test_wrapped_reduction_never_joins_unrelated_or_restricted_claims(content):
    assert planner.prepare(payload(content), slots("practice"), []) is None


@pytest.mark.parametrize(("content", "method"), [(EXPAND, "expand"), (REDUCE, "reduce")])
@pytest.mark.parametrize("count", [0, 1, 2])
def test_exact_calculation_and_no_duplicate_values(content, method, count):
    items = slots(*(["practice"] * count), *(["prior_check"] * (2 - count)))
    value = planner.prepare(payload(content), items, ["Beispiel 1/3"])
    assert value["operation"] == method
    actual = [s for s in value["slots"] if s["task"]]
    assert len(actual) == count
    seen = {"1/2", "1/3"}
    for item in actual:
        n, d = item["input"]
        a, b = item["output"]
        k = item["factor_or_divisor"]
        assert (a, b) == ((n * k, d * k) if method == "expand" else (n // k, d // k))
        assert Fraction(n, d) == Fraction(a, b)
        assert str(Fraction(n, d)) not in seen
        assert item["task"]["answer"] == f"{a}/{b}"
        assert ("Faktor" if method == "expand" else "Teiler") + f" {k}" in item["task"]["prompt"]
        seen.add(str(Fraction(n, d)))


def test_fixed_and_open_prior_checks_are_never_rewritten():
    fixed = {"id": "prior", "role": "prior_check", "type": "choice", "prompt": "Original"}
    free = {"id": "next", "role": "practice"}
    value = planner.prepare(payload(), [fixed, free], [])
    assert value["slots"][0] == {"slot": fixed, "task": None}
    assert value["slots"][1]["task"]["id"] == "next"


def test_unknown_rules_cross_group_and_unmapped_goals_do_not_create_a_plan():
    assert planner.prepare(payload("Thema Brüche, 1/2."), slots("practice"), []) is None
    assert (
        planner.prepare(
            payload(EXPAND + "\n" + REDUCE), [{"id": "q1", "role": "practice", "learning_goal_id": "unmapped"}], []
        )
        is None
    )
    p = payload()
    p["visual_context"]["sources"][0]["group_id"] = "other"
    assert planner.prepare(p, slots("practice"), []) is None
    p = payload()
    p["visual_context"]["sources"][0]["source_type"] = "curated_foundation"
    assert planner.prepare(p, slots("practice"), []) is None
    p = payload()
    p["selected_groups"][0]["subject"] = "Biologie"
    assert planner.prepare(p, slots("practice"), []) is None


def test_mixed_explicit_rules_rotate_without_claiming_mastery_or_repeating_values():
    request = payload(EXPAND + "\n" + REDUCE)
    chosen = slots("prior_check", "practice")
    first = planner.prepare(request, chosen, [])
    assert first["operation"] in ("expand", "reduce")
    assert first["revision"] == planner.MIXED_REVISION
    assert first["slots"][0] == {"slot": chosen[0], "task": None}
    prior = [first["slots"][1]["task"]["prompt"]]
    following = planner.prepare(request, chosen, prior)
    assert following["operation"] != first["operation"]
    assert Fraction(*following["slots"][1]["input"]) != Fraction(*first["slots"][1]["input"])
    planner.validate(request, chosen, first["excluded_values"], first)
    planner.validate(request, chosen, following["excluded_values"], following)
    for plan in (first, following):
        row = plan["slots"][1]
        factor = row["factor_or_divisor"]
        assert ("Faktor" if plan["operation"] == "expand" else "Teiler") + f" {factor}" in row["task"]["prompt"]
        assert Fraction(*row["input"]) == Fraction(*row["output"])


def test_mixed_explicit_rules_prefer_the_less_often_offered_procedure():
    request = payload(EXPAND + "\n" + REDUCE)
    chosen = slots("practice", "practice")
    counts = {"expand": 4, "reduce": 1}
    plan = planner.prepare(request, chosen, [], operation_counts=counts)
    assert plan["operation"] == "reduce" and plan["mixed_operation_counts"] == counts
    assert all("Teiler" in row["task"]["prompt"] for row in plan["slots"])
    planner.validate(request, chosen, plan["excluded_values"], plan, operation_counts=counts)
    with pytest.raises(ValueError, match="nicht mehr gültig"):
        planner.validate(request, chosen, plan["excluded_values"], plan, operation_counts={"expand": 4, "reduce": 2})


def test_operation_history_counts_only_own_distinct_offered_questions(api, household):
    from conftest import create_child
    from schulpilot.db import DB, LearningUnit

    parent, child = household
    other = create_child(api, parent, username="fraction-operation-sibling")
    with DB.begin() as db:
        db.add(
            LearningUnit(
                child_id=child["id"],
                subject="Mathematik",
                topic="Künstlich",
                explanation="",
                provider="synthetic-test",
                questions=[
                    {"prompt": "Erweitere 1/3 mit dem Faktor 2."},
                    {"prompt": "Erweitere 1/3 mit dem Faktor 2."},
                    {"prompt": "Kürze 4/6 durch den Teiler 2."},
                ],
            )
        )
        db.add(
            LearningUnit(
                child_id=other["id"],
                subject="Mathematik",
                topic="Künstlich",
                explanation="",
                provider="synthetic-test",
                questions=[{"prompt": "Kürze 6/9 durch den Teiler 3."}],
            )
        )
        db.flush()
        assert planner.operation_history(db, child["id"]) == {"expand": 1, "reduce": 1}


def test_literal_ocr_heading_and_rule_are_bound_even_when_two_sources_are_combined():
    request = payload(OCR_REDUCE)
    request["visual_context"]["sources"].append(
        {**request["visual_context"]["sources"][0], "ref": "p2", "material_id": "2" * 32, "content": OCR_EXPAND}
    )
    chosen = slots("prior_check", "practice")
    value = planner.prepare(request, chosen, [])
    assert value is not None
    assert value["source_excerpt"] in (OCR_REDUCE.split("\n\n3/9")[0], OCR_EXPAND.split("\n\n2/3")[0])
    assert value["slots"][1]["task"] is not None
    planner.validate(request, chosen, value["excluded_values"], value)


@pytest.mark.parametrize(
    "content",
    [
        "Brüche kürzen\n\nHeute keine Regel.\n\nZähler und Nenner durch dieselbe Zahl teilen.",
        "Brüche kürzen und erweitern\n\nZähler und Nenner durch dieselbe Zahl teilen.",
        "Brüche kürzen\n\nZähler und Nenner durch dieselbe Zahl teilen. Das ist falsch.",
        "Brüche kürzen\n\nZähler und Nenner durch dieselbe Zahl teilen.\n\nHeute nur durch 2.",
        "Brüche erweitern\n\nZähler und Nenner mit derselben Zahl multiplizieren.\n\nNur mit dem Faktor 2.",
        "Falsches Beispiel:\n\nBrüche kürzen\n\nZähler und Nenner durch dieselbe Zahl teilen.",
        "Brüche kürzen\n\nZähler und Nenner durch dieselbe Zahl teilen.\n\nDiese Regel ist falsch.",
    ],
)
def test_heading_rule_does_not_bridge_unrelated_or_restricted_text(content):
    from schulpilot.math_tasks import _procedure_quote

    label = "Brüche erweitern" if "erweitern" in content and "kürzen" not in content else "Brüche kürzen"
    assert _procedure_quote([{"content": content}], label) is None


def test_equivalent_historical_values_and_unknown_questions_are_conservative():
    assert planner.history_exclusions(["Erweitere 2/4 mit 3", r"Kürze \\frac{3}{6}"]) == ["1/2"]
    with pytest.raises(ValueError, match="nicht sicher"):
        planner.prepare(payload(), slots("practice"), ["Erweitere den abgebildeten Bruch."])
    with pytest.raises(ValueError, match="nicht sicher"):
        planner.prepare(payload(), slots("practice"), ["Nenne den Nenner in der Abbildung."])
    for ambiguous in ("Wandle 2 1/2 um.", "Wandle 2 ½ um.", r"Wandle 2 \frac{1}{2} um."):
        with pytest.raises(ValueError, match="nicht sicher"):
            planner.prepare(payload(), slots("practice"), [ambiguous])
        with pytest.raises(ValueError, match="nicht sicher"):
            planner.prepare(payload(EXPAND + "\n" + ambiguous), slots("practice"), [])
    old = [f"{a}/{b}" for a, b, _, _, _ in planner._pool("expand")]
    with pytest.raises(ValueError, match="keine ausreichend"):
        planner.prepare(payload(), slots("practice"), old)


def test_part_whole_question_answer_key_excludes_exact_fraction_without_attempts():
    question = {
        'type': 'short',
        'prompt': 'In einer Schachtel liegen 10 Stifte. 4 sind rot. Welcher Bruch ist rot? Schreibe Zähler/Nenner.',
        'answer': '4/10',
    }
    assert planner.history_exclusions([planner._history_question_prompt(question)]) == ['2/5']
    assert question['prompt'].endswith('Zähler/Nenner.')  # persisted question stays untouched


@pytest.mark.parametrize('changes', [
    {'type': 'choice'},
    {'presentation': {'type': 'fraction_grid'}},
    {'answer': '2/5'},  # does not match the two numbers in the question
    {'answer': '4/10 oder 2/5'},
    {'prompt': 'Die Grafik zeigt 10 Kreise, 4 rot. Welcher Bruch? Schreibe Zähler/Nenner.'},
    {'prompt': 'Es gibt 10 und 4 sowie 2. Welcher Bruch? Schreibe Zähler/Nenner.'},
    {'prompt': 'Vergleiche 10 und 4. Welcher Bruch? Schreibe Zähler/Nenner.'},
    {'prompt': 'Aus 10,4 und 4. Welcher Bruch? Schreibe Zähler/Nenner.'},
])
def test_part_whole_history_rejects_ambiguous_or_unrelated_answer_keys(changes):
    question = {'type': 'short', 'prompt': 'Von 10 sind 4 rot. Welcher Bruch? Schreibe Zähler/Nenner.', 'answer': '4/10'}
    question.update(changes)
    with pytest.raises(ValueError, match='nicht sicher'):
        planner.history_exclusions([planner._history_question_prompt(question)])


def test_digest_binds_source_revision_and_finite_task_plan():
    initial = planner.prepare(payload(), slots("practice"), [])
    assert initial["revision"] == planner.REVISION
    planner.validate(payload(), slots("practice"), [], initial)
    changed = copy.deepcopy(payload())
    changed["visual_context"]["sources"][0]["revision"] += 1
    revised = planner.prepare(changed, slots("practice"), [])
    assert revised["source_digest"] != initial["source_digest"]
    assert revised["digest"] != initial["digest"]
    assert planner.prepare(payload(), slots("practice"), []) == initial
    changed_ref = copy.deepcopy(payload())
    changed_ref["visual_context"]["references"][0]["digest"] = "c" * 64
    with pytest.raises(ValueError, match="nicht mehr gültig"):
        planner.validate(changed_ref, slots("practice"), [], initial)
    with pytest.raises(ValueError, match="nicht mehr gültig"):
        planner.validate(changed, slots("practice"), [], initial)
    forged = copy.deepcopy(initial)
    forged["slots"][0]["task"]["answer"] = "1/99"
    with pytest.raises(ValueError, match="nicht mehr gültig"):
        planner.validate(payload(), slots("practice"), [], forged)
    with pytest.raises(ValueError, match="nicht mehr gültig"):
        planner.validate(payload(), slots("practice"), [initial["slots"][0]["task"]["prompt"]], initial)


def test_private_history_excludes_only_own_sources_questions_and_active_plan(api, household):
    from conftest import create_child
    from schulpilot.db import DB, Job, LearningUnit, Material

    parent, first = household
    second = create_child(api, parent, username="fraction-history-other")
    pending = planner.prepare(payload(), slots("practice"), ["1/3", "3/8"])
    task = pending["slots"][0]["task"]
    with DB.begin() as db:
        db.add(
            LearningUnit(
                child_id=first["id"],
                subject="Mathematik",
                topic="Brüche",
                explanation="",
                provider="synthetic-test",
                questions=[
                    {"prompt": "Erweitere 2/6 mit 2."},
                    {"type": "short", "prompt": "Von 10 sind 4 rot. Welcher Bruch? Schreibe Zähler/Nenner.", "answer": "4/10"},
                ],
            )
        )
        db.add(
            LearningUnit(
                child_id=second["id"],
                subject="Mathematik",
                topic="Brüche",
                explanation="",
                provider="synthetic-test",
                questions=[{"prompt": "Erweitere 2/10 mit 2."}],
            )
        )
        db.add(
            Material(
                child_id=first["id"], title="Synthetic", subject="Mathematik", content="Beispiel 3/8", confirmed=True
            )
        )
        db.add(
            Material(
                child_id=first["id"],
                title="Not confirmed",
                subject="Mathematik",
                content="Beispiel 1/7",
                confirmed=False,
            )
        )
        job = Job(
            child_id=first["id"],
            kind="package",
            status="running",
            idempotency="synthetic-fraction-plan",
            payload={"package_fraction_plan": pending},
        )
        db.add(job)
        db.flush()
        job_id = job.id
        found = planner.history(db, first["id"])
        assert "1/3" in found and "3/8" in found and "2/5" in found and str(Fraction(*pending["slots"][0]["input"])) in found
        assert "1/5" not in found and "1/7" not in found
        assert str(Fraction(*pending["slots"][0]["input"])) not in planner.history(
            db, first["id"], ignore_job_ids={job_id}
        )
        assert task["prompt"] not in found


def test_unplanned_concurrent_package_blocks_history_until_accounted_for(household):
    from schulpilot.db import DB, Job

    _, child = household
    with DB.begin() as db:
        other = Job(
            child_id=child["id"], kind="package", status="running", idempotency="synthetic-old-concurrent", payload={}
        )
        db.add(other)
        db.flush()
        with pytest.raises(ValueError, match="nicht sicher"):
            planner.history(db, child["id"])
        assert planner.history(db, child["id"], ignore_job_ids={other.id}) == []


def test_history_refreshes_cached_pending_plan_after_other_transaction(household):
    from schulpilot.db import DB, Job

    _, child = household
    initial = planner.prepare(payload(), slots("practice"), [])
    later = planner.prepare(payload(), slots("practice"), [initial["slots"][0]["task"]["prompt"]])
    with DB.begin() as db:
        if db.bind.dialect.name != "postgresql":
            pytest.skip("Concurrent refresh requires isolated PostgreSQL")
        job = Job(
            child_id=child["id"],
            kind="package",
            status="running",
            idempotency="synthetic-fraction-stale",
            payload={"package_fraction_plan": initial},
        )
        db.add(job)
        db.flush()
        job_id = job.id
    with DB() as stale:
        cached = stale.get(Job, job_id)
        assert cached.payload["package_fraction_plan"] == initial
        with DB.begin() as fresh:
            fresh.get(Job, job_id).payload = {"package_fraction_plan": later}
        assert planner.history(stale, child["id"]) == [str(Fraction(*later["slots"][0]["input"]))]
        assert cached.payload["package_fraction_plan"] == later


@pytest.mark.parametrize(
    "tamper", ["answer", "prompt", "factor", "goal", "numbers", "disclosure", "duplicate", "fixed"]
)
def test_bound_task_and_graphics_tampering_is_rejected(tamper):
    fixed = {
        "id": "prior",
        "role": "prior_check",
        "type": "choice",
        "prompt": "Original?",
        "answer": "A",
        "options": ["A", "B"],
        "accepted": [],
    }
    free = {"id": "next", "role": "practice", "learning_goal_id": "goal1"}
    chosen = [fixed, free]
    plan = planner.prepare(payload(), chosen, [])
    row = plan["slots"][1]
    questions = [{**fixed}, {**row["task"], "hints": ["Versuche es."]}]
    graphics = {"next": planner.graphic_blocks(plan, row)}
    planner.validate_bound_tasks(payload(), chosen, [], plan, questions, graphics)
    if tamper == "answer":
        questions[1]["answer"] = "1/99"
    if tamper == "prompt":
        questions[1]["prompt"] += " verändert"
    if tamper == "goal":
        questions[1]["learning_goal_id"] = "goal2"
    if tamper == "fixed":
        questions[0]["answer"] = "B"
    if tamper == "duplicate":
        questions[0]["id"] = "next"
    if tamper == "numbers":
        graphics["next"][1]["numbers"][0] += 1
    if tamper == "disclosure":
        graphics["next"][0]["disclosure"] = "given"
    if tamper == "factor":
        plan["slots"][1]["factor_or_divisor"] += 1
    with pytest.raises(ValueError, match="nicht mehr gültig"):
        planner.validate_bound_tasks(payload(), chosen, [], plan, questions, graphics)


def test_unpublished_part_is_only_a_child_scoped_exclusion(household):
    from schulpilot.db import DB, Child
    from test_package_question_history import sibling_for, staged

    _, child = household
    with DB.begin() as db:
        own = db.get(Child, child["id"])
        sibling = sibling_for(db, own)
        _, job = staged(
            db, own, day_date="2026-11-01", first="Erweitere 2/3 mit dem Faktor 4.", second="Was heißt cat auf Deutsch?"
        )
        staged(
            db, sibling, day_date="2026-11-02", first="Was heißt cat auf Deutsch?", second="Was heißt dog auf Deutsch?"
        )
        assert set(planner.history(db, own.id)) == {"2/3"}
        assert planner.history(db, own.id, ignore_job_ids={job.id}) == []


def test_stored_visual_recipe_digest_must_be_authentic(household):
    from schulpilot.db import DB
    from schulpilot.visual_reference_models import VisualReference
    from schulpilot.visual_references import candidates

    context = payload()
    with DB() as db:
        reference = db.get(VisualReference, ("math.fraction.expansion", 1))
        assert reference is not None
        context["visual_context"]["references"][0]["digest"] = reference.digest
        plan = planner.prepare(context, slots("practice"), [])
        planner.validate_reference(db, plan)
        altered = copy.deepcopy(plan)
        altered["reference"]["digest"] = "f" * 64
        with pytest.raises(ValueError, match="nicht mehr gültig"):
            planner.validate_reference(db, altered)
        reduction_context = payload(REDUCE)
        recipe = db.get(VisualReference, ("math.fraction.reduction", 1))
        assert recipe is not None
        reduction_context["visual_context"]["references"][1]["digest"] = recipe.digest
        reduction = planner.prepare(reduction_context, slots("practice"), [])
        planner.validate_reference(db, reduction)
        assert not any(
            ref["id"] == "math.fraction.reduction"
            for ref in candidates(db, "Mathematik", REDUCE, package_prepared=True)
        )
        forged_reduction = copy.deepcopy(reduction)
        forged_reduction["reference"]["digest"] = "f" * 64
        with pytest.raises(ValueError, match="nicht mehr gültig"):
            planner.validate_reference(db, forged_reduction)


def test_private_history_plan_never_leaves_via_package_transport():
    from schulpilot.package_transport import payload_projection

    request = payload()
    plan = planner.prepare(request, slots("practice"), ["1/3"])
    request["package_fraction_plan"] = copy.deepcopy(plan)
    request["visual_context"]["package_fraction_plan"] = copy.deepcopy(plan)
    projected = payload_projection(request)
    assert "package_fraction_plan" not in projected
    assert "package_fraction_plan" not in projected["visual_context"]
    assert request["package_fraction_plan"] == plan


@pytest.mark.parametrize(
    ("content", "reference"), [(EXPAND, "math.fraction.expansion"), (REDUCE, "math.fraction.reduction")]
)
def test_only_exact_stored_recipe_for_confirmed_group_is_added(household, content, reference):
    from schulpilot.db import DB
    from schulpilot.visual_reference_models import VisualReference

    request = payload(content)
    request["visual_context"]["references"] = []
    with DB() as db:
        result = planner.add_reference(db, request)
        actual = result["visual_context"]["references"]
        stored = db.get(VisualReference, (reference, 1))
        assert actual == [
            {"id": reference, "version": 1, "digest": stored.digest, "kind": "fraction", "subject": "Mathematik"}
        ]
        assert request["visual_context"]["references"] == []
        assert planner.add_reference(db, result) == result
        planned = planner.prepare(result, slots("practice"), [])
        planner.validate_reference(db, planned)
        wrong = copy.deepcopy(result)
        wrong["visual_context"]["references"][0]["digest"] = "f" * 64
        with pytest.raises(ValueError, match="nicht mehr gültig"):
            planner.add_reference(db, wrong)
        other_group = copy.deepcopy(request)
        other_group["visual_context"]["sources"][0]["group_id"] = "other"
        assert planner.add_reference(db, other_group) == other_group
        mixed = payload(EXPAND + "\n" + REDUCE)
        mixed["visual_context"]["references"] = []
        enriched = planner.add_reference(db, mixed)
        assert {item["id"] for item in enriched["visual_context"]["references"]} == {
            "math.fraction.expansion",
            "math.fraction.reduction",
        }
        assert planner.add_reference(db, enriched) == enriched
        planner.validate_reference(db, planner.prepare(enriched, slots("practice"), []))


@pytest.mark.parametrize("content", [EXPAND, REDUCE])
@pytest.mark.parametrize(
    "change", ["none", "answer", "first_model", "second_model", "reference", "source", "step_text", "disclosure"]
)
def test_generated_output_binds_the_actual_two_models_and_task(content, change):
    request = payload(content)
    selected = slots("practice", "practice")
    plan = planner.prepare(request, selected, [])
    questions = []
    for row in plan["slots"]:
        step = planner.solution_step(plan, row)
        questions.append({**row["task"], "explanation": step["text"], "explanation_steps": [step]})
    output = {"units": [{"group_id": "g1", "subject": "Mathematik", "questions": questions}]}
    question = questions[0]
    step = question["explanation_steps"][0]
    if change == "answer":
        question["answer"] = "1/99"
    if change == "first_model":
        step["presentation"]["blocks"][0]["numbers"][0] += 1
    if change == "second_model":
        step["presentation"]["blocks"][1]["numbers"][1] += 1
    if change == "reference":
        step["reference"]["id"] = "different"
    if change == "source":
        step["source_refs"] = ["foreign"]
    if change == "step_text":
        step["text"] += " Veränderung."
    if change == "disclosure":
        step["disclosure"] = "given"
    if change == "none":
        planner.validate_generated_output(request, selected, [], plan, output)
    else:
        with pytest.raises(ValueError, match="nicht mehr gültig"):
            planner.validate_generated_output(request, selected, [], plan, output)


@pytest.mark.parametrize("prior_kind", ["open", "fixed"])
@pytest.mark.parametrize("practice_count", [0, 1])
def test_generated_output_retains_prior_questions(prior_kind, practice_count):
    prior = {"id": "prior", "role": "prior_check"}
    if prior_kind == "fixed":
        prior.update(type="choice", prompt="Was ist ein Zähler?", answer="Oben", options=["Oben", "Unten"], accepted=[])
    selected = [prior, {"id": "other", "role": "practice" if practice_count else "prior_check"}]
    request = payload()
    plan = planner.prepare(request, selected, [])
    prior_result = (
        {**prior}
        if prior_kind == "fixed"
        else {"id": "prior", "type": "short", "prompt": "Was ist ein Bruch?", "answer": "Ein Anteil"}
    )
    questions = [prior_result]
    row = plan["slots"][1]
    if row["task"]:
        step = planner.solution_step(plan, row)
        questions.append({**row["task"], "explanation": step["text"], "explanation_steps": [step]})
    else:
        questions.append({"id": "other", "type": "short", "prompt": "Was ist ein Nenner?", "answer": "Unten"})
    output = {"units": [{"group_id": "g1", "subject": "Mathematik", "questions": questions}]}
    planner.validate_generated_output(request, selected, [], plan, output)
    if prior_kind == "fixed":
        questions[0]["answer"] = "Unten"
        with pytest.raises(ValueError, match="nicht mehr gültig"):
            planner.validate_generated_output(request, selected, [], plan, output)
