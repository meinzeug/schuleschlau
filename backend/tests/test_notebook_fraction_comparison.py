"""Artificial, source-bound notebook comparisons through the real provider contract."""

import copy
import re

import pytest
from schulpilot import competences, learning_entry, providers, schemas, subject_content, visual_references, worker
from schulpilot import notebook_fraction_comparison as comparison
from schulpilot.competence_models import CompetenceDefinition, QuestionCompetence
from schulpilot.db import DB, Attempt, Child, Job, LearningUnit, Material, UnitSource, Usage
from schulpilot.graphic_schema import bind_coherent_graphics
from schulpilot.subject_registry import identity
from schulpilot.visual_reference_models import UnitVisualSnapshot
from sqlalchemy import select
from test_graphic_native_transport import subset_record
from test_notebook_fraction_expansions import http_mock
from test_notebook_practice import notebook as notebook
from test_notebook_practice import post
from test_presentation_capability_paths import _config

RULE = ("1. Schritt: Finde das kleinste gemeinsame Vielfache (kgV) von den Nennern!\n"
    "2. Schritt: Erweitere beide Brüche auf den gleichen Nenner!\n"
    "3. Schritt: Vergleiche die Zähler!")
CONTENT = "Brüche vergleichen: Ein Ganzes wird in gleich große Teile geteilt.\n" + RULE + "\nBeispiele: 1/4, 2/5, 3/7."
NUMBERED = ("Brüche vergleichen: Ein Ganzes wird in gleich große Teile geteilt.\n\n"
    "1. Schritt: Finde das kgV von den Nennern!\n\nBeispiel: kgV(2;3)=6.\n\n"
    "2. Schritt: Erweitere beide Brüche auf den „kgV-Nenner“.\n\n"
    "3. Schritt: Vergleiche die Zähler!\n\nBeispiele: 1/4, 2/5, 3/7.")
TOPIC = "Ungleichnamige Brüche gleichnamig machen und vergleichen"


def prepared(household, *, count=2, entry=True, content=CONTENT):
    with DB.begin() as db:
        child = db.get(Child, household[1]["id"])
        page = Material(child_id=child.id, title="Künstliche Vergleichsseite", subject="Mathematik",
            subject_id=identity("mathematik"), topic=TOPIC, content=content, confirmed=True, status="confirmed")
        db.add(page)
        db.flush()
        payload = {"required_subject": "Mathematik", "grade": 6,
            "notebook_practice": {"version": 1, "question_count": count},
            "material": {"subject": page.subject, "topic": page.topic, "content": page.content}, "previous_prompts": []}
        payload = visual_references.with_visual_context(db, child, payload, [page])
        payload = learning_entry.with_learning_entry(db, child, payload, [page], enabled=entry)
        payload = visual_references.with_foundation_context(db, payload)
        payload = comparison.with_history(payload, [])
        identifier = page.id
    return identifier, comparison.prepare(payload)


def binding_and_wire(payload):
    schema = providers.strict_schema(schemas.UnitOutput, preserve_limits=True)
    subject_content.bind_graphic_schema(schema, ["Mathematik"])
    bind_coherent_graphics(schema)
    providers.indexed_choice_schema(schema, bounded_matches=True)
    visual_references.bind_schema(schema, payload)
    learning_entry.bind_entry_schema(schema, payload)
    binding = comparison.bind_schema(schema, payload)
    assert binding is not None

    def step(row):
        return {"id": row["id"], "text": row["text"], "competence_id": None, "disclosure": row["disclosure"],
            "reference": copy.deepcopy(row["reference"]), "source_refs": copy.deepcopy(row["source_refs"]),
            "presentation": {"version": 1, "evidence_kind": "knowledge", "blocks": [row["id"]]}}

    intro = next(row for row in binding.candidates if row["disclosure"] == "given")
    questions = []
    for core in [*payload[comparison.KEY]["probes"], *payload[comparison.KEY]["tasks"]]:
        candidate = next(row for row in binding.candidates if (row.get("question_core") or row.get("proof", {}).get("task", {})).get("id") == core["id"])
        question = {key: copy.deepcopy(core[key]) for key in comparison.CORE}
        question.update(hints=["Mach die Nenner gleich."], explanation="Vergleiche die gleich großen Teile.",
            explanation_steps=[step(candidate)], presentation=None, field_group=None)
        questions.append(question)
    return binding, {"subject": "Mathematik", "topic": TOPIC, "explanation": intro["text"],
        "explanation_steps": [step(intro)], "questions": questions}


@pytest.mark.parametrize("count,entry", [(2, True), (3, True), (5, True), (2, False), (5, False)])
def test_real_provider_transport_keeps_checked_questions_and_closed_graphics(household, monkeypatch, count, entry):
    page_id, payload = prepared(household, count=count, entry=entry)
    binding, wire = binding_and_wire(payload)
    calls = []
    http_mock(monkeypatch, wire, calls)
    config = _config("openrouter")
    config.max_output_tokens, config.reserve_micros = 8000, 250000
    config.input_per_million_micros, config.output_per_million_micros = 2000000, 10000000
    result = providers.request_provider(config, "unit", payload)
    assert len(calls) == 1 and result.cost_micros == 1000
    subset_record(calls[0]["response_format"]["json_schema"]["schema"])
    assert len(result.data["questions"]) == count
    assert comparison.HISTORY not in calls[0]["messages"][-1]["content"]
    assert any("Welcher Bruch ist größer" in q["prompt"] for q in result.data["questions"])
    for task in payload[comparison.KEY]["tasks"]:
        question = next(q for q in result.data["questions"] if q["id"] == task["id"])
        assert all(question[key] == task[key] for key in comparison.CORE)
        blocks = question["explanation_steps"][0]["presentation"]["blocks"]
        assert len(blocks) == 4 and all(row["disclosure"] == "solution" for row in blocks)
        candidate = next(row for row in binding.candidates if row.get("proof", {}).get("task", {}).get("id") == task["id"])
        assert [subject_content.Graphic.model_validate(row).model_dump(mode="json") for row in blocks] == comparison._blocks(candidate)
    with DB.begin() as db:
        visual_references.validate_output(db, result.data, payload)
        unit = LearningUnit(child_id=household[1]["id"], material_id=page_id, subject="Mathematik", topic=TOPIC,
            explanation=result.data["explanation"], questions=result.data["questions"], provider="synthetic")
        db.add(unit)
        db.flush()
        db.add(UnitSource(unit_id=unit.id, material_id=page_id, revision=1))
        visual_references.remember(db, unit, result.data, payload)
        db.flush()
        snapshot = db.get(UnitVisualSnapshot, unit.id)
        assert snapshot.status == "ready", snapshot.reason
        for task in payload[comparison.KEY]["tasks"]:
            question = next(q for q in unit.questions if q["id"] == task["id"])
            assert visual_references.question_projection(db, unit, question, closed=False, hints=3) == []
            assert len(visual_references.question_projection(db, unit, question, closed=True, hints=0)) == 1


def test_missing_rule_never_activates_planner(household):
    _, payload = prepared(household, entry=False, content="Brüche vergleichen: 1/4 > 1/8.")
    assert comparison.KEY not in payload and not comparison.eligible(payload)


def test_source_only_legacy_entry_does_not_get_a_new_comparison_history_gate(household):
    _, payload = prepared(household, entry=True)
    clean = {key: value for key, value in payload.items() if key not in (comparison.KEY, comparison.HISTORY)}
    entry = clean["learning_entry"]["units"][0]
    entry.update(entry_mode="source_probe", probes=[])
    assert comparison.eligible(clean)
    result = comparison.with_history(clean, ["Welcher Bruch ist größer?"])
    assert comparison.HISTORY not in result and comparison.KEY not in comparison.prepare(result)


@pytest.mark.parametrize("part", ["answer", "prompt", "source", "visual", "phase"])
def test_changed_comparison_or_graphic_is_rejected(household, part):
    _, payload = prepared(household, entry=False)
    binding, wire = binding_and_wire(payload)
    changed = copy.deepcopy(wire)
    q = changed["questions"][0]
    if part == "answer":
        q["answer"] = "1/999"
    elif part == "prompt":
        q["prompt"] += " Andere Aufgabe."
    elif part == "source":
        q["explanation_steps"][0]["source_refs"] = ["r99"]
    elif part == "visual":
        q["explanation_steps"][0]["presentation"]["blocks"] = ["invented"]
    else:
        q["explanation_steps"][0]["disclosure"] = "given"
    with pytest.raises(ValueError):
        binding.hydrate(changed)


def test_newly_used_question_is_rejected_before_publication(household):
    _, payload = prepared(household, entry=False)
    binding, wire = binding_and_wire(payload)
    data = binding.hydrate(wire)
    with pytest.raises(ValueError, match="inzwischen bereits verwendet"):
        comparison.validate_history(payload, data, [payload[comparison.KEY]["tasks"][0]["prompt"]])


@pytest.mark.parametrize("old", [
    "Welcher Bruch ist größer?",
    r"Vergleiche \frac{1}{2} und \frac{3}{4}.",
])
def test_ambiguous_old_comparison_is_not_silently_reused(household, old):
    _, payload = prepared(household, entry=False)
    clean = {key: value for key, value in payload.items() if key not in (comparison.KEY, comparison.HISTORY)}
    with pytest.raises(ValueError, match="keine neuen passenden Vergleichsaufgaben"):
        comparison.with_history(clean, [old])


def test_legacy_choice_options_are_checked_locally_without_answers_or_provider_payload(household):
    _, payload = prepared(household, entry=False)
    clean = {key: value for key, value in payload.items() if key not in (comparison.KEY, comparison.HISTORY)}
    old = {"prompt": "Welcher Bruch ist größer?", "options": ["A) 1/2", "B) 3/4", "C) 2/5"],
        "answer": "PRIVATE_NOT_NEEDED"}
    planned = comparison.prepare(comparison.with_history(clean, [old]))
    pairs = planned[comparison.HISTORY]["pairs"]
    assert len(pairs) == 3
    assert "PRIVATE_NOT_NEEDED" not in str(planned)
    for task in planned[comparison.KEY]["tasks"]:
        values = {tuple(map(str, task["comparison"][key])) for key in ("left", "right")}
        assert values != {("1", "2"), ("3", "4")}
        assert values != {("1", "2"), ("2", "5")}
        assert values != {("2", "5"), ("3", "4")}


@pytest.mark.parametrize("fault", ["revision", "content", "reference", "task", "history"])
def test_changed_source_reference_or_plan_is_rejected_before_provider(household, monkeypatch, fault):
    _, payload = prepared(household, entry=False)
    changed = copy.deepcopy(payload)
    if fault == "revision":
        changed["visual_context"]["sources"][0]["revision"] += 1
    elif fault == "content":
        changed["visual_context"]["sources"][0]["content"] += "\nNeue Quellenfassung."
    elif fault == "reference":
        next(ref for ref in changed["visual_context"]["references"] if ref["id"] == comparison.RECIPE)["digest"] = "0" * 64
    elif fault == "task":
        changed[comparison.KEY]["tasks"][0]["answer"] = "1/999"
    else:
        changed[comparison.HISTORY]["source_digest"] = "0" * 64
    monkeypatch.setattr(providers.httpx, "Client", lambda **kw: pytest.fail("No HTTP call is allowed"))
    with pytest.raises(providers.ProviderError) as error:
        providers.request_provider(_config("openrouter"), "unit", changed)
    assert error.value.billing_result.cost_source == "cancelled"


def test_introduction_does_not_disclose_planned_fractions(household):
    _, payload = prepared(household, entry=True)
    binding, _ = binding_and_wire(payload)
    candidates = [row for row in binding.candidates if row.get("proof")]
    forbidden = {tuple(candidate["proof"][key]) for candidate in candidates
        for key in ("left", "right", "expanded_left", "expanded_right")}
    for intro in (row for row in binding.candidates if row["disclosure"] == "given"):
        assert tuple(int(value) for value in intro["block"]["numbers"]) not in forbidden


def test_rule_cannot_be_assembled_across_separately_excluded_text_blocks(household):
    split = "Finde das kgV der Nenner.\n\nErweitere beide Brüche auf den gleichen Nenner.\n\nVergleiche die Zähler."
    _, payload = prepared(household, entry=False, content=split)
    assert not comparison.eligible(payload) and comparison.KEY not in payload


def test_numbered_safe_blocks_keep_three_separate_rule_quotes_in_graphic_proof(household):
    _, payload = prepared(household, entry=False, content=NUMBERED)
    binding, wire = binding_and_wire(payload)
    candidate = next(row for row in binding.candidates if row.get("proof"))
    proof = candidate["proof"]
    assert proof["source_rule"]["kind"] == "numbered_safe_blocks"
    assert len(proof["source_rule"]["quotes"]) == 3
    assert all(quote in NUMBERED for quote in proof["source_rule"]["quotes"])
    comparison.validate_output(payload, binding.hydrate(wire))


@pytest.mark.parametrize("mode", ["independent", "after_wrong", "hint"])
def test_actual_notebook_worker_uses_one_source_one_request_and_saves_checked_comparison(notebook, monkeypatch, mode):
    with DB.begin() as db:
        first = db.get(Material, notebook.refs[0]["id"])
        first.content, first.topic = CONTENT, TOPIC
        db.get(Material, notebook.refs[1]["id"]).confirmed = False
        db.get(Material, notebook.refs[2]["id"]).confirmed = False
    _config("openrouter")
    value = {"material_id": notebook.refs[0]["id"], "notebook_sources": notebook.refs[:1], "question_count": 2}
    notebook.client.headers["X-Schulpilot-Capabilities"] = "learning-entry-v1"
    response = post(notebook, value)
    assert response.status_code == 202, response.text
    job_id = response.json()["id"]
    assert post(notebook, value).json()["id"] == job_id
    calls, real_provider = [], providers.request_provider

    def request(config, function, payload, *args, **kwargs):
        assert function == "unit" and comparison.KEY in payload
        assert {source["material_id"] for source in payload["visual_context"]["sources"] if source.get("material_id")} == {notebook.refs[0]["id"]}
        _, wire = binding_and_wire(payload)
        http_mock(monkeypatch, wire, calls)
        return real_provider(config, function, payload, *args, **kwargs)

    monkeypatch.setattr(worker, "request_provider", request)
    with DB() as db:
        assert worker.claim(db) == job_id
    worker.process(job_id)
    with DB() as db:
        job = db.get(Job, job_id)
        assert job.status == "completed", job.error
        unit = db.get(LearningUnit, job.result["unit_id"])
        assert len(unit.questions) == 2 and len(calls) == 1
        assert any("Welcher Bruch ist größer" in question["prompt"] for question in unit.questions)
        assert set(db.scalars(select(UnitSource.material_id).where(UnitSource.unit_id == unit.id))) == {notebook.refs[0]["id"]}
        comparison_question = next(question for question in unit.questions if "Welcher Bruch ist größer" in question["prompt"])
        competence = db.get(QuestionCompetence, (unit.id, comparison_question["id"]))
        assert competence and competence.competence_id == "math.fractions.compare"
        questions = copy.deepcopy(unit.questions)
        assert competences.evidence(db, unit.child_id, ["math.fractions.compare"])[0]["tasks"] == 0
        assert db.scalar(select(Usage).where(Usage.job_id == job_id)).cost_micros == 1000
        assert db.get(UnitVisualSnapshot, unit.id).status == "ready"
    worker.process(job_id)
    assert len(calls) == 1
    started = notebook.client.post(f"/api/units/{unit.id}/start")
    assert started.status_code == 200, started.text
    actor = {"X-Schulpilot-Account": notebook.actor_id}
    position_url = f"/api/units/{unit.id}/visual-position"
    read = notebook.client.get(position_url, headers=actor)
    assert read.status_code == 200
    comparison_id = comparison_question["id"]
    step_id = comparison_question["explanation_steps"][0]["id"]
    visual_position = {"source_signature": read.json()["source_signature"], "revision": read.json()["revision"],
        "position": {"explanation_kind": "question", "question_id": comparison_id,
            "explanation_step_id": step_id, "graphic_index": 0, "graphic_phase": "comparison-common"}}
    assert notebook.client.put(position_url, json=visual_position, headers=actor).status_code == 409
    for index, question in enumerate(questions):
        if question["id"] == comparison_id and mode == "hint":
            hint = notebook.client.post(f"/api/units/{unit.id}/questions/{question['id']}/hint")
            assert hint.status_code == 200, hint.text
            assert notebook.client.put(position_url, json=visual_position, headers=actor).status_code == 409
        if question["id"] == comparison_id and mode == "after_wrong":
            fractions = [f"{a}/{b}" for a, b in re.findall(r"(\d+)/(\d+)", question["prompt"])]
            wrong = next(value for value in fractions if value != question["answer"])
            response = notebook.client.post(f"/api/units/{unit.id}/questions/{question['id']}/answer",
                json={"answer": wrong, "request_id": "synthetic-compare-wrong-0001"})
            assert response.status_code == 200, response.text
            assert notebook.client.put(position_url, json=visual_position, headers=actor).status_code == 409
        request = {"answer": question["answer"], "request_id": f"synthetic-compare-answer-{index:04}"}
        response = notebook.client.post(f"/api/units/{unit.id}/questions/{question['id']}/answer", json=request)
        assert response.status_code == 200, response.text
        repeated = notebook.client.post(f"/api/units/{unit.id}/questions/{question['id']}/answer", json=request)
        assert repeated.status_code == 200
    saved = notebook.client.put(position_url, json=visual_position, headers=actor)
    assert saved.status_code == 200, saved.text
    assert notebook.client.get(position_url, headers=actor).json()["position"] == visual_position["position"]
    with DB() as db:
        assert len(list(db.scalars(select(Attempt).where(Attempt.unit_id == unit.id)))) == len(questions) + (mode == "after_wrong")
        result = competences.evidence(db, notebook.child["id"], ["math.fractions.compare"])[0]
        assert result["tasks"] == 1
        assert result["independent"] == (mode == "independent")
        assert result["supported"] == (mode != "independent")


def test_comparison_competence_requires_correct_checked_question_and_matching_goal():
    question = {"id": "q1", "type": "short", "prompt": "Welcher Bruch ist größer: 1/3 oder 3/4? Gib den größeren Bruch an.",
        "answer": "3/4", "options": [], "accepted": [], "hints": ["Vergleiche die Teile."],
        "explanation": "Drei Viertel sind größer."}
    goals = [{"id": "g1", "label": "Brüche vergleichen"}]
    assert learning_entry.verified_math_identity(question, goals) == "math.fractions.compare"
    assert learning_entry.verified_math_identity({**question, "answer": "1/3"}, goals) is None
    assert learning_entry.verified_math_identity(question, [{"id": "g1", "label": "Brüche erweitern"}]) is None


def test_existing_competence_catalogue_accepts_additive_comparison_without_rewriting_existing_rows():
    with DB.begin() as db:
        rows = {row.id: copy.deepcopy(row.data) for row in db.scalars(select(CompetenceDefinition).where(
            CompetenceDefinition.version == competences.VERSION))}
        added = db.get(CompetenceDefinition, ("math.fractions.compare", competences.VERSION))
        assert added is not None
        db.delete(added)
        db.flush()
        competences.seed_connection(db.connection())
        db.flush()
        actual = {row.id: row.data for row in db.scalars(select(CompetenceDefinition).where(
            CompetenceDefinition.version == competences.VERSION))}
        assert actual == rows
