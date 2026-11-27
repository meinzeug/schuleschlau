"""Conservative checks for artificial literal unit-conversion examples."""

from types import SimpleNamespace

import pytest
from schulpilot.material_review import _protected_readings
from schulpilot.source_lineage import false_unit_conversion, learning_source


@pytest.mark.parametrize("text", [
    "⅔ Minute = 60 Sekunden",
    "2/3 min = 60 s",
    r"\(\frac{2}{3} Minute = 60 Sekunden\)",
    "$\\dfrac{2}{3} min = 60 s$",
    "1 km = 100 m",
    "1,5 h = 60 min",
    "2 kg = 20 g",
    "1 L = 10 ml",
    "Überschrift\n2 m = 20 cm\nWeitere Zeile",
])
def test_unambiguous_false_conversion_is_detected(text):
    assert false_unit_conversion(text)


@pytest.mark.parametrize("text", [
    "⅔ Minute = 40 Sekunden", "2/3 min = 40 s", "1 km = 1000 m",
    "1 m = 1000 mm", "1,5 h = 90 min", "2 kg = 2000 g", "1 L = 1000 ml",
    "2 m = 2 min", "2 M = 20 cm", "1.000 m = 1 km", "1,000 m = 1 km",
    "1/0 h = 2 min", "-1 m = 2 cm", "1 1/2 h = 40 min",
    "2 m + 1 cm = 20 cm", "2 m = 20 cm = 200 mm", "2 m = 20 cm?",
    "Ist 2 m = 20 cm?", "2 m = 20 cm oder 30 cm", "2 Meter = x cm",
    "1234567890 m = 20 cm", "2 " + " " * 10000 + "m = 20 cm",
])
def test_valid_or_ambiguous_conversion_is_not_guessed(text):
    assert not false_unit_conversion(text)


def test_unsafe_block_excluded_without_rewriting_original():
    blocks = [
        {"kind": "paragraph", "text": "Eine Minute hat 60 Sekunden."},
        {"kind": "paragraph", "text": "⅔ Minute = 60 Sekunden"},
    ]
    original = "\n\n".join(block["text"] for block in blocks)
    material = SimpleNamespace(id="a" * 32, revision=1, purpose="notebook", confirmed=True,
                               legibility="readable", uncertainties=[], content=original, source_blocks=blocks)
    result = learning_source(None, material)
    assert result["policy_version"] == "literal-safety-8"
    assert result["content"] == blocks[0]["text"]
    assert [item["reason"] for item in result["exclusions"]] == ["false_unit_conversion"]
    assert material.content == original and material.source_blocks == blocks


def test_countercheck_preserves_recorded_old_policy_and_original():
    old_block = {"kind": "paragraph", "text": "⅔ Minute = 60 Sekunden"}
    new_block = {"kind": "paragraph", "text": "⅔ Minute = 40 Sekunden"}
    data = {"source_blocks": [new_block], "content": "", "legibility": "readable", "uncertainties": []}
    previous = SimpleNamespace(snapshot={"source_blocks": [old_block]}, receipt={"policy_version": "literal-safety-5"})
    current = SimpleNamespace(snapshot={"source_blocks": [old_block]}, receipt={"policy_version": "literal-safety-6"})
    previous_merge = _protected_readings(data, previous)
    protected_merge = _protected_readings(data, current)
    assert previous_merge["source_blocks"][0]["text"] == new_block["text"]
    assert previous_merge["legibility"] == "readable"
    assert any(block["text"] == old_block["text"] for block in protected_merge["source_blocks"])
    assert all(block["reading_uncertainties"] for block in protected_merge["source_blocks"])
    assert protected_merge["legibility"] == "partial"


@pytest.mark.parametrize("statement,compatible", [("⅔ Minute = 60 Sekunden", False), ("⅔ Minute = 40 Sekunden", True)])
def test_old_learning_path_only_survives_unchanged_safe_projection(monkeypatch, statement, compatible):
    from schulpilot import source_lineage, study_path

    block = {"kind": "paragraph", "text": statement}
    material = SimpleNamespace(id="b" * 32, revision=1, purpose="notebook", confirmed=True,
                               legibility="readable", uncertainties=[], content=statement, source_blocks=[block])
    with monkeypatch.context() as patch:
        patch.setattr(source_lineage, "false_unit_conversion", lambda _text: False)
        old_fingerprint = study_path.fingerprint([material])
    assert (old_fingerprint in study_path.compatible_fingerprints([material], None)) is compatible
