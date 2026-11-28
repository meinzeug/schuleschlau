"""Private evidence change markers: artificial data only, no AI calls."""

import json

import pytest
from conftest import create_child
from schulpilot import competences
from schulpilot.competence_models import QuestionCompetence
from schulpilot.db import DB, Activity, Attempt, AttemptAssessment, LearningUnit, Material, UnitSource
from schulpilot.learning_evidence_marker import LEGACY_VERSION, VERSION, matches, snapshot
from sqlalchemy import event

CANARY = "ARTIFICIAL_PRIVATE_ANSWER_DO_NOT_READ"


def add_unit(db, child_id, subject="Mathematik"):
    unit = LearningUnit(child_id=child_id, subject=subject, topic="Künstlich", explanation=CANARY,
                        questions=[{"id": "q1", "answer": CANARY}], provider="fixture", synthetic=False,
                        round_kind="study_block")
    db.add(unit)
    db.flush()
    return unit


def add_attempt(db, unit, *, question="q1", outcome="incorrect", created=100.0):
    item = Attempt(unit_id=unit.id, question_id=question, answer=CANARY, outcome=outcome,
                   assisted=False, created=created, evaluation={"method": "exact", "attempt_number": 1})
    db.add(item)
    db.flush()
    return item


def test_no_answer_or_material_text_is_selected_or_returned(api, household):
    _, child = household
    with DB.begin() as db:
        unit = add_unit(db, child["id"])
        add_attempt(db, unit)
        page = Material(child_id=child["id"], title="Künstliche Seite", content=CANARY,
                        confirmed=True, status="confirmed", subject="Mathematik", topic="Künstlich")
        db.add(page)
        db.flush()
        db.add(UnitSource(unit_id=unit.id, material_id=page.id, revision=page.revision))
    statements = []
    with DB() as db:
        engine = db.get_bind()
        def inspect(_conn, _cursor, statement, _parameters, _context, _executemany):
            statements.append(statement.casefold())
        event.listen(engine, "before_cursor_execute", inspect)
        try:
            value = snapshot(db, child["id"], "Mathe")
        finally:
            event.remove(engine, "before_cursor_execute", inspect)
    assert value.keys() == {"version", "digest"} and value["version"] == VERSION
    assert CANARY not in json.dumps(value)
    assert all("attempts.answer" not in item and "learning_units.questions" not in item
               and "materials.content" not in item and "activities.detail" not in item
               and "question_competences.source_refs" not in item
               for item in statements)


def test_new_attempts_hints_and_corrected_assessments_change_marker(api, household):
    _, child = household
    with DB.begin() as db:
        unit = add_unit(db, child["id"])
        before = snapshot(db, child["id"], "Mathematik")
        first = add_attempt(db, unit)
        after = snapshot(db, child["id"], "Mathe")
        assert not matches(before, after)
        second = add_attempt(db, unit, outcome="correct", created=first.created)
        later = snapshot(db, child["id"], "Mathematik")
        assert not matches(after, later)  # Same-second retries remain distinct.
        db.add(Activity(child_id=child["id"], unit_id=unit.id, kind="hint", detail={"private": CANARY}))
        db.flush()
        helped = snapshot(db, child["id"], "Mathematik")
        assert not matches(later, helped)
        db.add(AttemptAssessment(attempt_id=second.id, rules_version="synthetic-v1", previous_outcome="correct",
            outcome="correct", evaluation={"private": CANARY}, previous_evaluation={"private": CANARY}))
        db.flush()
        corrected = snapshot(db, child["id"], "Mathematik")
        assert not matches(helped, corrected)  # Even an equal aggregate retains the explicit reassessment.
        second.outcome = "uncertain"
        db.flush()
        assert not matches(corrected, snapshot(db, child["id"], "Mathematik"))


def test_other_children_subjects_and_unanswered_rounds_are_not_evidence(api, household):
    parent, child = household
    sibling = create_child(api, parent, username="marker-sibling")
    with DB.begin() as db:
        initial = snapshot(db, child["id"], "Mathematik")
        unused = add_unit(db, child["id"])
        add_attempt(db, add_unit(db, child["id"], "Deutsch"))
        add_attempt(db, add_unit(db, sibling["id"]))
        db.add(Activity(child_id=child["id"], unit_id=unused.id, kind="hint", detail={}))
        db.flush()
        assert matches(initial, snapshot(db, child["id"], "Mathe"))
        assert not matches(initial, snapshot(db, sibling["id"], "Mathematik"))
        assert not matches(initial, snapshot(db, child["id"], "Deutsch"))
        add_attempt(db, unused)
        assert not matches(initial, snapshot(db, child["id"], "Mathematik"))
        assert matches(initial, snapshot(db, child["id"], "Mathematik", exclude_unit_id=unused.id))


def test_explanation_metadata_changes_only_new_marker_for_attempted_owned_subject(api, household):
    parent, child = household
    sibling = create_child(api, parent, username="marker-help-sibling")
    with DB.begin() as db:
        unit = add_unit(db, child["id"])
        other_subject = add_unit(db, child["id"], "Deutsch")
        other_child = add_unit(db, sibling["id"])
        unused = add_unit(db, child["id"])
        for candidate in (unit, other_subject, other_child):
            add_attempt(db, candidate)
        before = snapshot(db, child["id"], "Mathe")
        excluded = snapshot(db, child["id"], "Mathe", exclude_unit_id=unit.id)
        old = snapshot(db, child["id"], "Mathe", version=LEGACY_VERSION)
        for candidate in (other_subject, other_child, unused):
            db.add(Activity(child_id=candidate.child_id, unit_id=candidate.id, kind="explanation",
                            detail={"via": "schulbuddy", "text": CANARY}))
        db.flush()
        assert matches(before, snapshot(db, child["id"], "Mathe"))
        db.add(Activity(child_id=child["id"], unit_id=unit.id, kind="explanation",
                        detail={"via": "schulbuddy", "text": CANARY}))
        db.flush()
        after = snapshot(db, child["id"], "Mathe")
        assert not matches(before, after) and CANARY not in json.dumps(after)
        assert matches(old, snapshot(db, child["id"], "Mathe", version=LEGACY_VERSION))
        assert not matches(old, after)
        assert matches(excluded, snapshot(db, child["id"], "Mathe", exclude_unit_id=unit.id))


def test_malformed_marker_versions_are_unknown(api, household):
    _, child = household
    with DB() as db:
        current = snapshot(db, child["id"], "Mathe")
        for bad in ([], {}, None, 123, "unknown"):
            assert not matches({**current, "version": bad}, current)
            with pytest.raises(ValueError):
                snapshot(db, child["id"], "Mathe", version=bad)


def test_source_revision_and_answered_competence_binding_are_tracked(api, household):
    _, child = household
    with DB.begin() as db:
        unit = add_unit(db, child["id"])
        add_attempt(db, unit)
        page = Material(child_id=child["id"], title="Künstlich", content="Übung", subject="Mathematik",
                        topic="Brüche", confirmed=True, status="confirmed")
        db.add(page)
        db.flush()
        db.add(UnitSource(unit_id=unit.id, material_id=page.id, revision=page.revision))
        db.flush()
        before = snapshot(db, child["id"], "Mathe")
        page.revision += 1
        db.flush()
        revised = snapshot(db, child["id"], "Mathe")
        assert not matches(before, revised)
        binding = QuestionCompetence(unit_id=unit.id, child_id=child["id"], question_id="q1",
            competence_id="math.fractions.reduce", catalog_version=competences.VERSION, role="practice",
            question_digest="a" * 64, source_refs=[{"material_id": page.id, "revision": page.revision,
                "source_digest": "b" * 64, "ignored_private_text": CANARY}], reference_ids=[])
        db.add(binding)
        db.flush()
        bound = snapshot(db, child["id"], "Mathe")
        assert not matches(revised, bound) and CANARY not in json.dumps(bound)
        binding.role = "recall"
        db.flush()
        assert not matches(bound, snapshot(db, child["id"], "Mathe"))


def test_invalid_or_legacy_markers_are_never_reported_as_matches(api, household):
    _, child = household
    with DB() as db:
        current = snapshot(db, child["id"], "Mathematik")
        assert matches(current, current)
        assert not matches(None, current)
        assert not matches({**current, "version": "old"}, current)
        assert not matches({**current, "extra": True}, current)
        assert not matches({**current, "digest": "z" * 64}, current)
        with pytest.raises(ValueError):
            snapshot(db, "missing-child", "Mathematik")
        with pytest.raises(ValueError):
            snapshot(db, child["id"], " ")


def test_foreign_source_changes_are_not_attributed_to_child(api, household):
    parent, child = household
    sibling = create_child(api, parent, username="marker-source-sibling")
    with DB.begin() as db:
        unit = add_unit(db, child["id"])
        add_attempt(db, unit)
        foreign = Material(child_id=sibling["id"], title="Nicht zugeordnet", content=CANARY,
                           confirmed=True, status="confirmed", subject="Mathematik", topic="Künstlich")
        db.add(foreign)
        db.flush()
        db.add(UnitSource(unit_id=unit.id, material_id=foreign.id, revision=foreign.revision))
        db.flush()
        initial = snapshot(db, child["id"], "Mathematik")
        foreign.revision += 1
        foreign.confirmed = False
        foreign.content = "Anderer künstlicher Inhalt"
        db.flush()
        assert matches(initial, snapshot(db, child["id"], "Mathematik"))
