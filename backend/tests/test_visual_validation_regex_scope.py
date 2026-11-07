"""Regression for numeric prose checks in unrelated graphic recipes."""

from types import SimpleNamespace

import pytest
from schulpilot import visual_references
from schulpilot.source_lineage import digest


@pytest.fixture(autouse=True)
def clean_database():
    # This test performs no DB, provider or network operations.
    yield


@pytest.mark.parametrize(
    ("kind", "subject", "numbers", "unit", "correct", "wrong"),
    [
        ("fraction", "Mathematik", [1, 2], "", "Das ist 1/2.", "Das ist 1/3."),
        ("triangle", "Mathematik", [2, 3], "cm", "g = 2 und h = 3.", "g = 4 und h = 3."),
        ("reflection", "Physik", [30], "°", "Der Winkel ist 30°.", "Der Winkel ist 41°."),
    ],
)
def test_general_graphic_prose_checks_still_reject_mismatching_numbers(
    monkeypatch, kind, subject, numbers, unit, correct, wrong
):
    # The purpose of this regression is the final numeric/prose consistency
    # check, after the ordinary recipe and source checks have already passed.
    monkeypatch.setattr(visual_references, "validate_question", lambda *a, **kw: None)
    monkeypatch.setattr(visual_references, "_meaningful", lambda *a, **kw: None)
    recipe = {"id": "general.test.recipe", "kind": kind}
    fingerprint = digest(recipe)
    db = SimpleNamespace(
        get=lambda *_args, **_kwargs: SimpleNamespace(id=recipe["id"], version=1, recipe=recipe, digest=fingerprint)
    )
    context = {
        "references": [{"id": recipe["id"], "version": 1, "subject": subject, "digest": fingerprint}],
        "sources": [{"ref": "p1", "subject": subject, "group_id": None, "content": "Geprüftes Testbeispiel"}],
    }
    block = {
        "kind": kind,
        "title": "Test",
        "disclosure": "given",
        "source_excerpt": "Geprüftes Testbeispiel",
        "labels": [],
        "numbers": numbers,
        "connections": [],
        "unit": unit,
        "variant": "",
    }
    step = {
        "id": "test1",
        "text": correct,
        "competence_id": None,
        "disclosure": "given",
        "reference": {"id": recipe["id"], "version": 1},
        "source_refs": ["p1"],
        "presentation": {"version": 1, "evidence_kind": "knowledge", "blocks": [block]},
    }
    assert len(visual_references.validate_steps(db, [step], subject, context, introduction=True)) == 1
    with pytest.raises(ValueError):
        visual_references.validate_steps(db, [{**step, "text": wrong}], subject, context, introduction=True)
