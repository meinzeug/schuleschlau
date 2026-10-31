"""Synthetic OCR warnings keep their scope until an explicit source confirmation."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from schulpilot.db import DB, Material
from schulpilot.extraction import TranscriptionOutput
from schulpilot.source_lineage import learning_source

LOCAL = "Das zweite Wort ist unleserlich."
GLOBAL = "Der erste Absatz ist teilweise durch Schatten verdeckt."


def artificial_transcription(warnings):
    return TranscriptionOutput.model_validate({
        "blocks": [
            {"kind": "paragraph", "text": "Wasser gefriert bei null Grad."},
            {"kind": "paragraph", "text": "Ein ? steht hier.", "reading_uncertainties": [LOCAL]},
        ],
        "legibility": "partial", "subject": "Sachunterricht", "topic": "Wasser",
        "uncertainties": warnings, "homework": [],
    }).as_material()


def page(value):
    return SimpleNamespace(id="synthetic-uncertainty", revision=1, purpose="notebook", confirmed=True, **value)


def test_separate_page_warning_blocks_every_section_until_confirmed():
    data = artificial_transcription([GLOBAL])
    original = data["content"]
    result = learning_source(None, page(data))
    assert result["content"] == ""
    assert len(result["exclusions"]) == 2
    assert all(item["reason"] == "reading_uncertain" for item in result["exclusions"])
    assert data["content"] == original


def test_mirrored_local_warning_only_excludes_its_section():
    data = artificial_transcription([])
    assert data["uncertainties"] == [LOCAL]
    result = learning_source(None, page(data))
    assert result["content"] == "Wasser gefriert bei null Grad."
    assert [item["reason"] for item in result["exclusions"]] == ["reading_uncertain"]


def test_invalid_legacy_page_warnings_block_instead_of_crashing():
    for invalid in ([{"unexpected": "value"}], [["unknown"]], [""], None, "legacy"):
        data = artificial_transcription([])
        data["uncertainties"] = invalid
        result = learning_source(None, page(data))
        assert result["content"] == ""
        assert result["reading_status"] == "unresolved"
        assert all(item["reason"] == "reading_uncertain" for item in result["exclusions"])


@pytest.mark.parametrize("warning", ["", "   "])
@pytest.mark.parametrize("legibility", ["partial", "unreadable"])
def test_unreadable_or_partial_page_needs_a_real_warning(legibility, warning):
    values = {"legibility": legibility, "subject": "Sachunterricht", "topic": "Wasser",
              "uncertainties": [warning], "homework": []}
    if legibility == "partial":
        values["blocks"] = [{"kind": "paragraph", "text": "Ein künstlicher Text."}]
    else:
        values["blocks"] = []
    with pytest.raises(ValidationError):
        TranscriptionOutput.model_validate(values)


def test_explicit_confirmation_can_resolve_both_warning_scopes(api, household):
    _, child = household
    data = artificial_transcription([GLOBAL])
    with DB.begin() as db:
        material = Material(child_id=child["id"], title="Künstliche Seite", status="review", confirmed=False, **data)
        db.add(material)
        db.flush()
        material_id = material.id
        revision = material.revision
    response = api.put(f"/api/materials/{material_id}/confirm", json={
        "revision": revision, "subject": data["subject"], "topic": data["topic"],
        "content": data["content"], "homework": [], "uncertainties_resolved": True,
    })
    assert response.status_code == 200, response.text
    with DB() as db:
        material = db.get(Material, material_id)
        result = learning_source(db, material)
        assert result["reading_status"] == "explicitly_confirmed"
        assert result["content"] == data["content"]
        assert material.uncertainties == [GLOBAL, LOCAL]
