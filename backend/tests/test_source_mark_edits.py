"""Artificial transcript edits must not erase the safety context of a page."""

import copy

import pytest
from schulpilot.db import DB, Material
from schulpilot.learning import material_data
from schulpilot.material_vocabulary import preview
from schulpilot.source_lineage import REVIEW_MARKS_AFTER_EDIT, learning_source
from test_learning import child_client

UNSET = object()


def confirm(api, child, blocks, edited, *, warnings=UNSET):
    with DB.begin() as db:
        material = Material(child_id=child["id"], title="Künstliche Seite", subject="Mathematik",
            topic="Addition", content="\n\n".join(block["text"] for block in blocks),
            source_blocks=copy.deepcopy(blocks), status="review", confirmed=False,
            uncertainties=[] if warnings is UNSET else copy.deepcopy(warnings))
        db.add(material)
        db.flush()
        if warnings is None:
            material.uncertainties = None  # Historical JSON null, not SQL NULL.
            db.flush()
        mid = material.id
    response = api.put(f"/api/materials/{mid}/confirm", json={"revision": 1, "subject": "Mathematik",
        "topic": "Addition", "content": edited, "homework": [], "uncertainties_resolved": True})
    assert response.status_code == 200, response.text
    return mid, response.json()


@pytest.mark.parametrize("unsafe", [
    {"kind": "paragraph", "text": "Meine Lösung: 4", "literal_role": "student_work"},
    {"kind": "paragraph", "text": "Alt 4 neu 5", "literal_role": "annotation"},
    {"kind": "paragraph", "text": "Alt 4 neu 5", "annotations": [
        {"kind": "correction", "quote": "5", "color": "red"}]},
])
def test_edit_of_other_block_cannot_promote_unchanged_marked_work(api, household, unsafe):
    _, child = household
    rule = {"kind": "paragraph", "text": "Zuerst addierän."}
    mid, visible = confirm(api, child, [rule, unsafe], "Zuerst addieren.\n\n" + unsafe["text"])
    assert visible["content"].startswith("Zuerst addieren.")
    assert visible["source_blocks"][1]["text"] == unsafe["text"]
    with DB() as db:
        page = db.get(Material, mid)
        result = learning_source(db, page)
        assert result["content"] == "Zuerst addieren."
        assert result["exclusions"][0]["reason"] in ("student_work", "visible_annotation")
        assert REVIEW_MARKS_AFTER_EDIT not in page.uncertainties


@pytest.mark.parametrize("unsafe", [
    {"kind": "paragraph", "text": "Meine Lösung: 4", "literal_role": "student_work"},
    {"kind": "paragraph", "text": "Alt 4 neu 5", "annotations": [
        {"kind": "correction", "quote": "5", "color": "red"}]},
])
def test_edit_of_marked_block_is_quarantined_and_old_marks_not_shown(api, household, unsafe):
    _, child = household
    rule = {"kind": "paragraph", "text": "Zuerst addieren."}
    edited = "Zuerst addieren.\n\n" + unsafe["text"] + " korrigiert"
    mid, visible = confirm(api, child, [rule, unsafe], edited)
    assert visible["content"] == edited and visible["source_blocks"] == []
    assert REVIEW_MARKS_AFTER_EDIT in visible["uncertainties"]
    with DB() as db:
        result = learning_source(db, db.get(Material, mid))
        assert result["content"] == "" and result["factual_status"] == "blocked"
        assert result["exclusions"][0]["reason"] == "unstructured_annotations"


def test_changed_layout_cannot_hide_unplaced_markings(api, household):
    _, child = household
    blocks = [{"kind": "paragraph", "text": "Eine Regel."},
        {"kind": "paragraph", "text": "Meine Lösung: 4", "literal_role": "student_work"}]
    mid, visible = confirm(api, child, blocks, "Eine Regel.\nMeine Lösung: 4")
    assert visible["source_blocks"] == [] and REVIEW_MARKS_AFTER_EDIT in visible["uncertainties"]
    with DB() as db:
        assert learning_source(db, db.get(Material, mid))["factual_status"] == "blocked"


def test_parent_can_restore_exact_original_without_discarding_marks(api, household):
    _, child = household
    blocks = [{"kind": "paragraph", "text": "Eine Regel."},
        {"kind": "paragraph", "text": "Meine Lösung: 4", "literal_role": "student_work"}]
    original = "\n\n".join(block["text"] for block in blocks)
    mid, changed = confirm(api, child, blocks, "Eine Regel.\nMeine Lösung: 4")
    restore = {"revision": changed["revision"],
        "subject": "Mathematik", "topic": "Addition", "content": original, "homework": [],
        "uncertainties_resolved": True}
    with child_client({"credentials": {"child_username": "test-child", "child_password": "secure-child-pass-123"}}) as client:
        assert client.put(f"/api/materials/{mid}/confirm", json=restore).status_code == 403
    restored = api.put(f"/api/materials/{mid}/confirm", json=restore)
    assert restored.status_code == 200, restored.text
    view = restored.json()
    assert REVIEW_MARKS_AFTER_EDIT not in view["uncertainties"]
    assert view["source_blocks"][1]["literal_role"] == "student_work"
    with DB() as db:
        result = learning_source(db, db.get(Material, mid))
        assert result["content"] == "Eine Regel."
        assert result["exclusions"][0]["reason"] == "student_work"


def test_unmarked_transcription_can_still_be_corrected_and_used(api, household):
    _, child = household
    blocks = [{"kind": "paragraph", "text": "Zuerst addierän."}]
    mid, visible = confirm(api, child, blocks, "Zuerst addieren.")
    assert REVIEW_MARKS_AFTER_EDIT not in visible["uncertainties"]
    with DB() as db:
        assert learning_source(db, db.get(Material, mid))["content"] == "Zuerst addieren."


@pytest.mark.parametrize("edit_uncertain", [False, True])
def test_block_reading_uncertainty_remains_visible_after_a_text_edit(api, household, edit_uncertain):
    _, child = household
    warning = "Letzter Buchstabe undeutlich."
    blocks = [{"kind": "paragraph", "text": "Eine Regel."},
        {"kind": "paragraph", "text": "Buchstabä", "reading_uncertainties": [warning]}]
    edited = ("Eine Regel.\n\nBuchstabe" if edit_uncertain else "Eine kurze Regel.\n\nBuchstabä")
    mid, visible = confirm(api, child, blocks, edited, warnings=[warning])
    assert visible["source_blocks"][1]["reading_uncertainties"] == [warning]
    assert warning in visible["uncertainties"]
    with DB() as db:
        page = db.get(Material, mid)
        assert page.source_blocks[1]["reading_uncertainties"] == [warning]
        assert learning_source(db, page)["reading_status"] == "explicitly_confirmed"


@pytest.mark.parametrize("warnings", [None, [None, "", "Alter Hinweis"]])
def test_invalid_historic_page_warnings_do_not_crash_or_hide_lost_marks(api, household, warnings):
    _, child = household
    blocks = [{"kind": "paragraph", "text": "Meine Lösung: 4", "literal_role": "student_work"}]
    mid, visible = confirm(api, child, blocks, "Meine Lösung: 5", warnings=warnings)
    if warnings:
        assert "Alter Hinweis" in visible["uncertainties"]
    assert "Frühere Lesehinweise konnten nicht vollständig übernommen werden." in visible["uncertainties"]
    assert REVIEW_MARKS_AFTER_EDIT in visible["uncertainties"]
    with DB() as db:
        assert learning_source(db, db.get(Material, mid))["factual_status"] == "blocked"


def test_extra_legacy_block_cannot_hide_a_mark_beyond_the_block_limit(api, household):
    _, child = household
    blocks = [{"kind": "paragraph", "text": f"Absatz {index}"} for index in range(80)]
    blocks.append({"kind": "paragraph", "text": "Unsichtbare alte Lösung", "literal_role": "student_work"})
    with DB.begin() as db:
        page = Material(child_id=child["id"], title="Künstliche alte Seite", subject="Mathematik",
            topic="Addition", content="\n\n".join(row["text"] for row in blocks[:80]),
            source_blocks=blocks, status="confirmed", confirmed=True, uncertainties=[])
        db.add(page)
        db.flush()
        assert material_data(page)["source_blocks"] == []
        result = learning_source(db, page)
        assert result["factual_status"] == "blocked"
        assert result["exclusions"][0]["reason"] == "unstructured_annotations"


def test_old_vocabulary_metadata_is_ignored_after_a_text_change():
    old = [{"kind": "paragraph", "text": "dog = Hund", "purpose": "rule"}]
    result = preview("Englisch", "Vokabeln", "dog = Hund\ncat = Katze", old)
    assert {(row["word"], row["meaning"]) for row in result["pairs"]} == {("dog", "Hund"), ("cat", "Katze")}


@pytest.mark.parametrize("malformed", [42, 0, "kein Block", {"kind": "paragraph"}])
def test_malformed_historic_block_container_is_quarantined_in_api(api, household, malformed):
    _, child = household
    with DB.begin() as db:
        page = Material(child_id=child["id"], title="Künstliche alte Seite", subject="Mathematik",
            topic="Addition", content="Eine Regel.", source_blocks=malformed,
            status="review", confirmed=False, uncertainties=[])
        db.add(page)
        db.flush()
        mid = page.id
    response = api.put(f"/api/materials/{mid}/confirm", json={"revision": 1, "subject": "Mathematik",
        "topic": "Addition", "content": "Eine kurze Regel.", "homework": [], "uncertainties_resolved": True})
    assert response.status_code == 200, response.text
    assert response.json()["source_blocks"] == []
    assert REVIEW_MARKS_AFTER_EDIT in response.json()["uncertainties"]
    with DB() as db:
        result = learning_source(db, db.get(Material, mid))
        assert result["content"] == "" and result["factual_status"] == "blocked"
        assert result["exclusions"][0]["reason"] == "unstructured_annotations"


@pytest.mark.parametrize("invalid", [
    {"kind": "paragraph", "text": "Eine Regel.", "literal_role": "unbekannte-rolle"},
    {"kind": "unbekannter-block", "text": "Eine Regel."},
    {"kind": "paragraph", "text": "Eine Regel.", "reading_uncertainties": [42]},
    {"kind": "paragraph", "text": "Eine Regel.", "annotations": [{"kind": "correction", "quote": "nicht vorhanden"}]},
])
def test_unparseable_historic_block_is_never_promoted_after_edit(api, household, invalid):
    _, child = household
    mid, visible = confirm(api, child, [invalid], "Eine kurze Regel.")
    assert visible["source_blocks"] == [] and REVIEW_MARKS_AFTER_EDIT in visible["uncertainties"]
    with DB() as db:
        result = learning_source(db, db.get(Material, mid))
        assert result["factual_status"] == "blocked" and result["content"] == ""
        assert result["exclusions"][0]["reason"] == "unstructured_annotations"
