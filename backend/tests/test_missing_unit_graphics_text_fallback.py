"""Synthetic source only; verify fallback and preserve closed task validation."""
import pytest
from schulpilot import providers
from test_model_routing import policy
from test_presentation_capability_paths import _config, _transport


def payload():
    source = "Die Biene besitzt sechs Beine und zwei Fühler."
    return {"function": "unit", "grade": 6, "material": {"subject": "Biologie", "topic": "Biene", "content": source},
        "review": False, "visual_context": {"required": True,
        "references": [{"id": "general.source_relation.phases", "version": 1, "kind": "scene", "subject": "Biologie"}],
        "sources": [{"ref": "p1", "subject": "Biologie", "group_id": None, "content": source}]}}


def unit(answer="sechs"):
    return {"subject": "Biologie", "topic": "Biene", "explanation": "Die Biene hat sechs Beine.",
        "explanation_steps": None, "questions": [{"id": "q1", "type": "short", "prompt": "Wie viele Beine hat die Biene?",
        "answer": answer, "options": [], "accepted": [], "hints": ["Denke an die Anzahl."],
        "explanation": "Es sind sechs.", "presentation": None, "explanation_steps": None}]}


def test_missing_visual_sends_text_only_unit_and_keeps_questions(monkeypatch):
    config = _config("openrouter")
    approved = policy()
    config._selected_route = {"reason": "material_graphic_teaching", "tier": "sol", "region": "standard",
        "route": {**approved["routes"]["sol"], "upstreams": ["fixture-upstream"]}, "budget": approved["budget"]}
    calls = _transport(monkeypatch, "openrouter", unit())
    result = providers.request_provider(config, "unit", payload())
    assert len(calls) == 1
    assert result.data.get("explanation_steps") is None
    assert result.data["questions"][0]["answer"] == "sechs"
    assert result.data["questions"][0].get("presentation") is None


def test_unrelated_binding_failure_is_not_swallowed(monkeypatch):
    from schulpilot import unit_reference_graphics
    config = _config("openrouter")
    approved = policy()
    config._selected_route = {"reason": "material_graphic_teaching", "tier": "sol", "region": "standard",
        "route": {**approved["routes"]["sol"], "upstreams": ["fixture-upstream"]}, "budget": approved["budget"]}
    calls = _transport(monkeypatch, "openrouter", unit())
    def broken(*args):
        raise ValueError("unexpected binding error")
    monkeypatch.setattr(unit_reference_graphics, "bind_schema", broken)
    with pytest.raises(ValueError, match="unexpected binding error"):
        providers.request_provider(config, "unit", payload())
    assert calls == []


def test_duplicate_transient_ids_are_unique_without_changing_answers(monkeypatch):
    config = _config("openrouter")
    approved = policy()
    config._selected_route = {"reason": "material_graphic_teaching", "tier": "sol", "region": "standard",
        "route": {**approved["routes"]["sol"], "upstreams": ["fixture-upstream"]}, "budget": approved["budget"]}
    data = unit()
    data["questions"].append({**data["questions"][0], "prompt": "Wie viele Fühler besitzt die Biene?",
        "answer": "zwei", "explanation": "Es sind zwei."})
    _transport(monkeypatch, "openrouter", data)
    result = providers.request_provider(config, "unit", payload())
    assert [q["id"] for q in result.data["questions"]] == ["q1", "auto_q2"]
    assert [q["answer"] for q in result.data["questions"]] == ["sechs", "zwei"]
    assert result.telemetry["normalized_question_ids"] == 1
