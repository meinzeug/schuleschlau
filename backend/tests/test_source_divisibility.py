"""Bounded literal checks; all pages and readings here are artificial."""

from types import SimpleNamespace

import pytest
from schulpilot.material_review import _protected_readings
from schulpilot.source_lineage import false_divisibility, learning_source


@pytest.mark.parametrize("text", [
    "3 teilt 25",
    "3 teilt 24 nicht.",
    "3 ∣ 25",
    "3 ∤ 24",
    "Sachliche Überschrift\n3 TEILT 25.\nEine andere Zeile",
])
def test_unambiguous_false_statements_are_detected(text):
    assert false_divisibility(text)


@pytest.mark.parametrize("text", [
    "3 teilt 24", "3 teilt 25 nicht", "3 ∣ 24", "3 ∤ 25", "3 teilt 0",
    "0 teilt 0", "0 ∤ 1", "-3 teilt 25", "3 | 25", "3 teilt 2,5",
    "Prüfe: 3 teilt 25", "3 teilt 25?", "3 teilt 25 oder 24",
    "Die 3 teilt 25 nicht immer", "1.000 teilt 2000", "1234567890 ∣ 25",
    "3 teilt 24\n3 teilt 25 nicht", "3 " + " " * 10000 + "∣ 25",
])
def test_correct_or_ambiguous_statements_are_not_guessed(text):
    assert not false_divisibility(text)


def test_unsafe_block_is_excluded_but_the_original_is_unchanged():
    blocks = [
        {"kind": "paragraph", "text": "Eine Zahl kann Teiler einer anderen Zahl sein."},
        {"kind": "paragraph", "text": "3 teilt 25"},
    ]
    original = "\n\n".join(block["text"] for block in blocks)
    material = SimpleNamespace(id="a" * 32, revision=1, purpose="notebook", confirmed=True,
                               legibility="readable", uncertainties=[], content=original, source_blocks=blocks)
    result = learning_source(None, material)
    assert result["policy_version"] == "literal-safety-6"
    assert result["content"] == blocks[0]["text"]
    assert [item["reason"] for item in result["exclusions"]] == ["false_divisibility"]
    assert material.content == original and material.source_blocks == blocks


def test_countercheck_preserves_historical_policy_and_original_reading():
    old_block = {"kind": "paragraph", "text": "3 teilt 25"}
    new_block = {"kind": "paragraph", "text": "3 teilt 24"}
    data = {"source_blocks": [new_block], "content": "", "legibility": "readable", "uncertainties": []}
    old = SimpleNamespace(snapshot={"source_blocks": [old_block]}, receipt={"policy_version": "literal-safety-4"})
    new = SimpleNamespace(snapshot={"source_blocks": [old_block]}, receipt={"policy_version": "literal-safety-5"})
    previous_merge = _protected_readings(data, old)
    protected_merge = _protected_readings(data, new)
    assert previous_merge["source_blocks"][0]["text"] == new_block["text"]
    assert previous_merge["legibility"] == "readable"
    retained = next(block for block in protected_merge["source_blocks"] if block["text"] == old_block["text"])
    assert retained["reading_uncertainties"]
    assert all(block["reading_uncertainties"] for block in protected_merge["source_blocks"])
    assert protected_merge["legibility"] == "partial"


@pytest.mark.parametrize("statement,compatible", [("3 teilt 25", False), ("3 teilt 24", True)])
def test_old_learning_path_only_survives_unchanged_safe_projection(monkeypatch, statement, compatible):
    from schulpilot import source_lineage, study_path

    block = {"kind": "paragraph", "text": statement}
    material = SimpleNamespace(id="b" * 32, revision=1, purpose="notebook", confirmed=True,
                               legibility="readable", uncertainties=[], content=statement, source_blocks=[block])
    with monkeypatch.context() as patch:
        patch.setattr(source_lineage, "false_divisibility", lambda _text: False)
        old_fingerprint = study_path.fingerprint([material])
    assert (old_fingerprint in study_path.compatible_fingerprints([material], None)) is compatible
