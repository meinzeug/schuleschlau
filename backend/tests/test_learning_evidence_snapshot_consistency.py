"""Statement consistency of private evidence metadata, not atomic publication."""

import hashlib
import json
from unittest.mock import patch

import pytest
from schulpilot.competence_models import QuestionCompetence
from schulpilot.competences import VERSION as COMPETENCE_VERSION
from schulpilot.db import DB, Activity, Attempt, AttemptAssessment, Material, UnitSource, engine
from schulpilot.learning_evidence_marker import VERSION, matches, snapshot
from sqlalchemy import event
from test_learning_evidence_marker import add_attempt, add_unit


def test_single_metadata_statement_preserves_existing_digest(api, household):
    _, child = household
    with DB.begin() as db:
        unit = add_unit(db, child["id"])
        answer = add_attempt(db, unit)
        page = Material(child_id=child["id"], title="Künstlich", content="Übung", subject="Mathematik",
                        topic="Brüche", confirmed=True, status="confirmed")
        db.add(page)
        db.flush()
        source = UnitSource(unit_id=unit.id, material_id=page.id, revision=page.revision)
        hint = Activity(child_id=child["id"], unit_id=unit.id, kind="hint", detail={})
        correction = AttemptAssessment(attempt_id=answer.id, rules_version="fixture", previous_outcome="incorrect",
                                       outcome="incorrect", evaluation={}, previous_evaluation={})
        binding = QuestionCompetence(unit_id=unit.id, child_id=child["id"], question_id="q1",
                                     competence_id="math.fractions.reduce", catalog_version=COMPETENCE_VERSION,
                                     role="practice", question_digest="a" * 64, source_refs=[], reference_ids=[])
        db.add_all([source, hint, correction, binding])
        db.flush()
        payload = {
            "version": VERSION, "competence_catalog_version": COMPETENCE_VERSION,
            "child": child["id"], "subject": "mathematik", "units": [[unit.id, "study_block"]],
            "attempts": [[unit.id, "q1", answer.id, answer.created, "incorrect", False, "exact", None, 1]],
            "corrections": [[correction.id, answer.id, "fixture", "incorrect", correction.created]],
            "hints": [[hint.id, unit.id, hint.created]],
            "sources": [[unit.id, page.id, source.revision, page.revision, True]],
            "bindings": [[unit.id, "q1", "math.fractions.reduce", COMPETENCE_VERSION, "practice", "a" * 64]],
        }
        digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                           separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        statements = []
        def inspect(_conn, _cursor, statement, _parameters, _context, _executemany):
            if statement.lstrip().lower().startswith("select"):
                statements.append(statement)
        event.listen(engine, "before_cursor_execute", inspect)
        captured = []
        original_hash = hashlib.sha256
        def record_hash(value):
            captured.append(value.decode())
            return original_hash(value)
        try:
            with patch("schulpilot.learning_evidence_marker.hashlib.sha256", record_hash):
                result = snapshot(db, child["id"], "Mathe")
        finally:
            event.remove(engine, "before_cursor_execute", inspect)
        assert json.loads(captured[0]) == payload
        assert result == {"version": VERSION, "digest": digest}, (captured, payload)
        combined = [item for item in statements if "UNION ALL" in item.upper()]
        assert len(combined) == 1 and len(statements) <= 2


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="PostgreSQL READ COMMITTED statement snapshots")
def test_postgres_statement_sees_one_committed_evidence_version(api, household):
    _, child = household
    with DB.begin() as db:
        unit = add_unit(db, child["id"])
        answer = add_attempt(db, unit)
        answer_id = answer.id
    with DB() as db:
        assert db.connection().get_isolation_level() == "READ COMMITTED"
        before = snapshot(db, child["id"], "Mathe")
        called = []
        def commit_after_select(_conn, _cursor, statement, _parameters, _context, _executemany):
            if "UNION ALL" not in statement.upper() or called:
                return
            called.append(True)
            with DB.begin() as other:
                other.get(Attempt, answer_id).outcome = "correct"
        event.listen(engine, "after_cursor_execute", commit_after_select)
        try:
            observed = snapshot(db, child["id"], "Mathe")
        finally:
            event.remove(engine, "after_cursor_execute", commit_after_select)
        assert called == [True] and matches(before, observed)
        assert not matches(observed, snapshot(db, child["id"], "Mathe"))
