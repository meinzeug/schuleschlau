"""Synthetic proof that a deleted grade can return from a prior snapshot."""

from contextlib import contextmanager
from dataclasses import replace
from uuid import uuid4

import pytest
from schulpilot import erasure
from schulpilot.config import settings
from schulpilot.db import DB, Base, LearningUnit, SchoolGrade, engine
from schulpilot.erasure import flush_journal, journal_write_lock, reconcile, request, verify
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


def test_current_journal_prevents_grade_resurrection(api, household, tmp_path, monkeypatch):
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

    # A separate record provides a positive control for journal signing and replay.
    with journal_write_lock(), DB.begin() as db:
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


@pytest.mark.parametrize('snapshot_before_confirmation', [True, False])
def test_restore_redacts_explicit_import_position_even_when_link_follows_snapshot(
    api, household, tmp_path, monkeypatch, snapshot_before_confirmation
):
    from schulpilot.db import GradeImport
    from test_grade_pdf_imports import confirm, pdf, today_year, upload

    monkeypatch.setattr(erasure, 'settings', replace(settings, data_dir=tmp_path))
    _, child = household
    raw = pdf(today_year(child['id']), [('Mathematik', 1, 'other', 1, '4'), ('Biologie', 1, 'other', 1, '4')])
    preview = upload(api, child, raw=raw).json()

    def snapshot():
        with DB() as db:
            return {table: list(db.execute(table.select()).mappings()) for table in Base.metadata.sorted_tables}

    before = snapshot() if snapshot_before_confirmation else None
    assert confirm(api, child, preview).status_code == 200
    if before is None:
        before = snapshot()
    with DB() as db:
        from sqlalchemy import select
        target = db.scalar(select(SchoolGrade).where(SchoolGrade.child_id == child['id'],
                                                      SchoolGrade.subject == 'Mathematik'))
        grade_id = target.id
    assert api.delete(f"/api/children/{child['id']}/grades/{grade_id}").status_code == 200
    records = [verify(line, settings.master_key) for line in (tmp_path/'erasure-ledger.jsonl').read_text().splitlines()]
    with isolated_restore() as restored:
        Base.metadata.create_all(restored)
        with restored.begin() as connection:
            for table, rows in before.items():
                if rows:
                    connection.execute(table.insert(), [dict(row) for row in rows])
        with Session(restored) as db:
            reconcile(db, records)
            reconcile(db, records)
            db.commit()
            batch = db.get(GradeImport, preview['id'])
            assert batch.entries[0] == {'redacted': True}
            assert batch.entries[1]['subject'] == 'Biologie' and batch.entries[1]['value'] == '4'
            assert db.get(SchoolGrade, grade_id) is None


def test_grade_erasure_record_authentication_and_unknown_version_rejection():
    from schulpilot.erasure import signed

    record = {'id': 'a' * 32, 'scope': 'unit', 'target': 'b' * 32, 'created': 1,
              'resource_kind': 'grade', 'details': {'version': 1, 'child_id': 'c' * 32,
              'entries': [{'import_id': 'd' * 32, 'entry_index': 0}], 'excluded': [], 'slots': ['e' * 32],
              'request_digest': None}}
    raw = signed(record, settings.master_key)
    assert verify(raw, settings.master_key) == record
    altered = {**record, 'details': {**record['details'], 'version': 2}}
    with pytest.raises(ValueError):
        verify(signed(altered, settings.master_key), settings.master_key)
    with pytest.raises(ValueError):
        verify(raw, settings.master_key + 'different')
    with pytest.raises(ValueError):
        verify(signed({**record, 'scope': 'grade'}, settings.master_key), settings.master_key)


def test_expired_grade_is_journalled_and_does_not_reappear_in_restore(api, household, tmp_path, monkeypatch):
    from schulpilot.db import now
    from schulpilot.worker import maintenance

    monkeypatch.setattr(erasure, 'settings', replace(settings, data_dir=tmp_path))
    _, child = household
    with DB.begin() as db:
        grade = SchoolGrade(child_id=child['id'], subject='Synthetic', topic='', kind='test', scale='grade_1_6',
                            value=3, weight=1, assessed_on='2025-01-01', note='', created=int(now())-366*86400)
        db.add(grade)
        db.flush()
        grade_id = grade.id
    with DB() as db:
        snapshot = {table: list(db.execute(table.select()).mappings()) for table in Base.metadata.sorted_tables}
    maintenance()
    with DB() as db:
        assert db.get(SchoolGrade, grade_id) is None
    records = [verify(line, settings.master_key) for line in (tmp_path/'erasure-ledger.jsonl').read_text().splitlines()]
    assert any(record.get('resource_kind') == 'grade' and record['target'] == grade_id for record in records)
    with isolated_restore() as restored:
        Base.metadata.create_all(restored)
        with restored.begin() as connection:
            for table, rows in snapshot.items():
                if rows:
                    connection.execute(table.insert(), [dict(row) for row in rows])
        with Session(restored) as db:
            reconcile(db, records)
            db.commit()
            assert db.get(SchoolGrade, grade_id) is None


def test_expired_grade_redacts_ambiguous_possible_copies_without_deleting_other_grades(
    api, household, tmp_path, monkeypatch
):
    from schulpilot.db import GradeImport, GradeImportGradeLink, GradeSourceSlot, now
    from schulpilot.worker import maintenance
    from sqlalchemy import delete, select
    from test_grade_pdf_imports import confirm, pdf, today_year, upload

    monkeypatch.setattr(erasure, 'settings', replace(settings, data_dir=tmp_path))
    _, child = household
    raw = pdf(today_year(child['id']), [('Mathematik', 1, 'other', 1, '4'),
                                       ('Biologie', 1, 'other', 2, '4')])
    original = upload(api, child, raw=raw).json()
    assert confirm(api, child, original).status_code == 200
    new_preview = upload(api, child, raw=raw).json()
    with DB.begin() as db:
        slots = list(db.scalars(select(GradeSourceSlot).where(
            GradeSourceSlot.child_id == child['id']).order_by(GradeSourceSlot.id)))
        grades = [db.get(SchoolGrade, slot.grade_id) for slot in slots]
        expired = next(grade for grade in grades if grade.subject == 'Mathematik')
        other = next(grade for grade in grades if grade.subject == 'Biologie')
        expired_id, other_id = expired.id, other.id
        expired.created = int(now()) - 366 * 86400
        db.execute(delete(GradeImportGradeLink).where(
            GradeImportGradeLink.import_id == original['id'],
            GradeImportGradeLink.grade_id == expired_id))
    with DB() as db:
        snapshot = {table: list(db.execute(table.select()).mappings()) for table in Base.metadata.sorted_tables}

    maintenance()
    records = [verify(line, settings.master_key) for line in (tmp_path/'erasure-ledger.jsonl').read_text().splitlines()]
    grade_record = next(record for record in records if record.get('resource_kind') == 'grade'
                        and record['target'] == expired_id)
    assert {(row['import_id'], row['entry_index']) for row in grade_record['details']['entries']} == {
        (original['id'], 0), (new_preview['id'], 0)}
    with DB() as db:
        assert db.get(SchoolGrade, expired_id) is None
        assert db.get(SchoolGrade, other_id) is not None
        for batch_id in (original['id'], new_preview['id']):
            entries = db.get(GradeImport, batch_id).entries
            assert entries[0] == {'redacted': True}
            assert entries[1]['subject'] == 'Biologie'
    assert [item['subject'] for item in api.get(
        f"/api/children/{child['id']}/grade-imports/{new_preview['id']}").json()['items']] == ['Biologie']
    maintenance()  # A repeated cleanup must not recreate or delete other records.
    with DB() as db:
        assert db.get(SchoolGrade, expired_id) is None
        assert db.get(SchoolGrade, other_id) is not None
        assert db.get(GradeImport, new_preview['id']).entries[1]['subject'] == 'Biologie'

    with isolated_restore() as restored:
        Base.metadata.create_all(restored)
        with restored.begin() as connection:
            for table, rows in snapshot.items():
                if rows:
                    connection.execute(table.insert(), [dict(row) for row in rows])
        with Session(restored) as db:
            reconcile(db, records)
            db.commit()
            assert db.get(SchoolGrade, expired_id) is None
            assert db.get(SchoolGrade, other_id) is not None
            for batch_id in (original['id'], new_preview['id']):
                entries = db.get(GradeImport, batch_id).entries
                assert entries[0] == {'redacted': True}
                assert entries[1]['subject'] == 'Biologie'


def test_expired_import_is_deleted_but_slot_of_retained_grade_survives_restore(api, household, tmp_path, monkeypatch):
    from schulpilot.db import GradeImport, GradeSourceSlot, now
    from schulpilot.worker import maintenance
    from sqlalchemy import select
    from test_grade_pdf_imports import confirm, pdf, today_year, upload

    monkeypatch.setattr(erasure, 'settings', replace(settings, data_dir=tmp_path))
    _, child = household
    raw = pdf(today_year(child['id']), [('Mathematik', 1, 'other', 1, '4')])
    preview = upload(api, child, raw=raw).json()
    assert confirm(api, child, preview).status_code == 200
    with DB.begin() as db:
        batch = db.get(GradeImport, preview['id'])
        slot = db.scalar(select(GradeSourceSlot).where(GradeSourceSlot.child_id == child['id']))
        grade_id, slot_id = slot.grade_id, slot.id
        batch.created = slot.created = int(now()) - 366 * 86400
    with DB() as db:
        snapshot = {table: list(db.execute(table.select()).mappings()) for table in Base.metadata.sorted_tables}
    maintenance()
    records = [verify(line, settings.master_key) for line in (tmp_path/'erasure-ledger.jsonl').read_text().splitlines()]
    with isolated_restore() as restored:
        Base.metadata.create_all(restored)
        with restored.begin() as connection:
            for table, rows in snapshot.items():
                if rows:
                    connection.execute(table.insert(), [dict(row) for row in rows])
        with Session(restored) as db:
            reconcile(db, records)
            db.commit()
            assert db.get(GradeImport, preview['id']) is None
            assert db.get(GradeSourceSlot, slot_id) is not None
            assert db.get(SchoolGrade, grade_id) is not None


def test_expired_unlinked_slot_is_journalled(api, household, tmp_path, monkeypatch):
    from schulpilot.db import GradeSourceSlot, now
    from schulpilot.worker import maintenance
    from sqlalchemy import select
    from test_grade_pdf_imports import confirm, pdf, today_year, upload

    monkeypatch.setattr(erasure, 'settings', replace(settings, data_dir=tmp_path))
    _, child = household
    preview = upload(api, child, raw=pdf(today_year(child['id']), [('Mathematik', 1, 'other', 1, '4')])).json()
    assert confirm(api, child, preview).status_code == 200
    with DB.begin() as db:
        slot = db.scalar(select(GradeSourceSlot).where(GradeSourceSlot.child_id == child['id']))
        slot.created = int(now()) - 366 * 86400
        grade_id, slot_id = slot.grade_id, slot.id
    assert api.delete(f"/api/children/{child['id']}/grades/{grade_id}").status_code == 200
    with DB() as db:
        snapshot = {table: list(db.execute(table.select()).mappings()) for table in Base.metadata.sorted_tables}
    maintenance()
    with DB() as db:
        assert db.get(GradeSourceSlot, slot_id) is None
    records = [verify(line, settings.master_key) for line in (tmp_path/'erasure-ledger.jsonl').read_text().splitlines()]
    assert any(record.get('resource_kind') == 'grade_slot' and record['target'] == slot_id for record in records)
    with isolated_restore() as restored:
        Base.metadata.create_all(restored)
        with restored.begin() as connection:
            for table, rows in snapshot.items():
                if rows:
                    connection.execute(table.insert(), [dict(row) for row in rows])
        with Session(restored) as db:
            reconcile(db, records)
            db.commit()
            assert db.get(GradeSourceSlot, slot_id) is None
