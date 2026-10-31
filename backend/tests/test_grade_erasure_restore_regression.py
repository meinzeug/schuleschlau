"""Synthetic proof that a deleted grade can return from a prior snapshot."""

from contextlib import contextmanager
from dataclasses import replace
from uuid import uuid4

import pytest
from schulpilot import erasure
from schulpilot.config import settings
from schulpilot.db import DB, Base, LearningUnit, SchoolGrade, engine
from schulpilot.erasure import flush_journal, reconcile, request, verify
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


class DeletedGradeRestored(AssertionError):
    """The one known failure which this strict xfail is allowed to mask."""


@contextmanager
def isolated_restore():
    if engine.dialect.name == "sqlite":
        restored = create_engine("sqlite:///:memory:")
        with restored.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        try:
            yield restored
        finally:
            restored.dispose()
        return

    # A separate schema is permitted only inside scripts/test_postgres.py's
    # temporary local cluster, never on a general or merely similarly named DB.
    host = engine.url.query.get("host", "")
    if (engine.dialect.name != "postgresql" or engine.url.database != "schulpilot_isolated_test"
            or "/schulpilot-isolated-pg-" not in host):
        pytest.fail("Restore test requires the dedicated local PostgreSQL test cluster")
    schema = "restore_" + uuid4().hex
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    restored = create_engine(engine.url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        yield restored
    finally:
        restored.dispose()
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))


@pytest.mark.xfail(strict=True, raises=DeletedGradeRestored,
                   reason="Grade deletion is absent from the authenticated restore journal")
def test_current_journal_does_not_yet_prevent_grade_resurrection(api, household, tmp_path, monkeypatch):
    monkeypatch.setattr(erasure, "settings", replace(settings, data_dir=tmp_path))
    _, child = household
    with DB.begin() as db:
        grade = SchoolGrade(child_id=child["id"], subject="Synthetic", topic="Synthetic", kind="test",
                            scale="grade_1_6", value=3, weight=1, assessed_on="2026-01-01", note="")
        control = LearningUnit(child_id=child["id"], subject="Synthetic", topic="Synthetic", explanation="Test",
                               questions=[], provider="synthetic")
        db.add_all([grade, control])
        db.flush()
        grade_id, control_id = grade.id, control.id
    with DB() as db:
        snapshot = {table: list(db.execute(table.select()).mappings()) for table in Base.metadata.sorted_tables}

    # A real outbox record provides a positive control for journal signing and
    # replay independently of the missing grade record.
    with DB.begin() as db:
        request(db, "unit", control_id)
        db.delete(db.get(LearningUnit, control_id))
    flush_journal()
    result = api.delete(f"/api/children/{child['id']}/grades/{grade_id}")
    assert result.status_code == 200, result.text
    with DB() as db:
        assert db.get(SchoolGrade, grade_id) is None
        assert db.get(LearningUnit, control_id) is None

    ledger = tmp_path / "erasure-ledger.jsonl"
    records = [verify(line, settings.master_key) for line in ledger.read_text().splitlines()]
    assert any(record["scope"] == "unit" and record["target"] == control_id for record in records)
    with isolated_restore() as restored:
        Base.metadata.create_all(restored)
        with restored.begin() as connection:
            for table, rows in snapshot.items():
                if rows:
                    connection.execute(table.insert(), [dict(row) for row in rows])
        with Session(restored) as db:
            assert db.get(SchoolGrade, grade_id) is not None
            assert db.get(LearningUnit, control_id) is not None
            reconcile(db, records)
            db.commit()
            # Verify the restore path actually applied the current journal.
            assert db.get(LearningUnit, control_id) is None
            deleted_grade_reappeared = db.get(SchoolGrade, grade_id) is not None
    if deleted_grade_reappeared:
        raise DeletedGradeRestored("An individually deleted grade returned from the separate snapshot")
