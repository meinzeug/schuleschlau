"""Official provisional computing topics, bounded grades and migration."""
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from schulpilot import curriculum
from schulpilot.curriculum_schemas import CatalogueInput
from schulpilot.db import DB, Activity, Child, Job, Subject, Usage
from schulpilot.db import engine as test_engine
from sqlalchemy import create_engine, event, func, select, text

SOURCE = Path(__file__).parents[1] / 'schulpilot/reference/curriculum-st-sekundarschule-informatik-2026.json'
DOCUMENT = 'st-sek-informatik-erprobung-2026'


def package():
    return json.loads(SOURCE.read_text())


def test_official_provisional_scope_and_exact_years():
    value = CatalogueInput.model_validate(package())
    assert value.coverage.complete is False and len(value.documents) == 1 and len(value.topics) == 11
    document = value.documents[0]
    assert (document.state_code, document.school_form_id, document.edition) == (
        'DE-ST', 'de-st.sekundarschule', '01.08.2026 (Erprobungsfassung)')
    assert document.effective_from.isoformat() == '2026-08-01'
    assert 'Erprobung' in document.applicability_note and 'CC BY-SA 4.0' in document.source_notes
    assert '320030ded3a3b512de057da344ee4080f97cfe1a0cf895c84883471936b885a1' in document.source_notes
    for grades, count, kind in [([5, 6], 3, 'band'), ([7, 8], 4, 'band'),
                               ([9], 2, 'exact'), ([10], 2, 'exact')]:
        rows = [row for row in value.topics if row.grades == grades]
        assert len(rows) == count
        assert all(row.grade_kind == kind and row.page == 9 and row.section == '3.1' for row in rows)
        assert all(row.subject_key == 'informatik' and row.canonical_topic_key is None for row in rows)


def test_read_and_import_do_not_change_learning_or_start_ai(api, household):
    with DB.begin() as db:
        assert curriculum.import_catalogue(db, package())['topics_added'] == 0
        assert curriculum.import_catalogue(db, package())['topics_added'] == 0
        subject_id = db.scalar(select(Subject.id).where(Subject.key == 'informatik', Subject.owner_family_id.is_(None)))
    with DB() as db:
        before = {model: db.scalar(select(func.count()).select_from(model)) for model in (Activity, Job, Usage)}

    def selected(grade, form='de-st.sekundarschule'):
        response = api.get('/api/curriculum/topics', params={'state_code': 'DE-ST', 'school_form_id': form,
                           'subject_id': subject_id, 'grade': grade, 'limit': 50})
        assert response.status_code == 200
        return [row for row in response.json()['items'] if row['source']['document_id'] == DOCUMENT]

    for grade, count in [(5, 3), (6, 3), (7, 4), (8, 4), (9, 2), (10, 2)]:
        rows = selected(grade)
        assert len(rows) == count
        assert all('Erprobungsfassung' in row['source']['edition'] for row in rows)
        assert all('Erprobung' in row['source']['applicability_note'] for row in rows)
    assert not selected(4) and not selected(11) and not selected(6, 'de-st.gymnasium')
    with DB() as db:
        assert all(db.scalar(select(func.count()).select_from(model)) == before[model] for model in before)


def test_ai_planning_keeps_provisional_edition_in_source_metadata(api, household):
    from test_curriculum import save

    child_id = household[1]['id']
    save(api, household, state_code='DE-ST', school_form_id='de-st.sekundarschule', grade=6)
    with DB() as db:
        context = curriculum.planning_context(db, db.get(Child, child_id), ['Informatik'])
    items = [row for row in context['topics'] if row['source']['document_id'] == DOCUMENT]
    assert len(items) == 3
    assert all('Erprobungsfassung' in row['source']['edition'] for row in items)
    assert context['coverage'] == 'partial'


def test_future_edition_is_not_used_before_its_local_effective_date(api, household, monkeypatch):
    from datetime import datetime, timezone

    from test_curriculum import save

    child_id = household[1]['id']
    save(api, household, state_code='DE-ST', school_form_id='de-st.sekundarschule', grade=6)
    before = datetime(2026, 7, 31, 21, 59, 59, tzinfo=timezone.utc).timestamp()
    boundary = datetime(2026, 7, 31, 22, 0, 0, tzinfo=timezone.utc).timestamp()
    with DB() as db:
        child = db.get(Child, child_id)
        monkeypatch.setattr(curriculum, 'now', lambda: before)
        assert not [row for row in curriculum.planning_context(db, child, ['Informatik'])['topics']
                    if row['source']['document_id'] == DOCUMENT]
        monkeypatch.setattr(curriculum, 'now', lambda: boundary)
        assert len([row for row in curriculum.planning_context(db, child, ['Informatik'])['topics']
                    if row['source']['document_id'] == DOCUMENT]) == 3


@pytest.mark.parametrize('dialect', ['sqlite', 'postgresql'])
def test_migration_preserves_existing_attempts_and_is_idempotent(tmp_path, dialect):
    schema = None
    if dialect == 'postgresql':
        if test_engine.dialect.name != 'postgresql':
            pytest.skip('Requires isolated PostgreSQL.')
        schema = 'st_informatics_' + uuid.uuid4().hex
        with test_engine.begin() as con:
            con.execute(text(f'CREATE SCHEMA "{schema}"'))
        url, engine = os.environ['TEST_DATABASE_URL'], test_engine
    else:
        url = 'sqlite:///' + str(tmp_path / 'informatics.sqlite')
        engine = create_engine(url)

        @event.listens_for(engine, 'connect')
        def enable_fk(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')

    env = {**os.environ, 'DATABASE_URL': url, 'ENVIRONMENT': 'test'}
    if schema:
        env['PGOPTIONS'] = f'-c search_path={schema}'
    command = [sys.executable, '-m', 'alembic', '-c', str(Path(__file__).parents[1] / 'alembic.ini'), 'upgrade']

    def scope(con):
        if schema:
            con.execute(text(f'SET LOCAL search_path TO "{schema}"'))

    try:
        result = subprocess.run([*command, '0056'], env=env, capture_output=True)
        assert result.returncode == 0, result.stderr.decode(errors='replace')
        with engine.begin() as con:
            scope(con)
            con.execute(text("DELETE FROM curriculum_documents WHERE id = 'st-sek-informatik-erprobung-2026'"))
            con.execute(text("INSERT INTO families(id,name,synthetic,created,child_limit,call_limit,budget_micros,plan) VALUES('f','Synthetic',true,1,4,100,2000000,'Pilot')"))
            con.execute(text("INSERT INTO users(id,username,display_name,password_hash,role,verified,disabled,created) VALUES('u','synthetic','Synthetic','SYNTHETIC-HASH','parent',true,false,1)"))
            con.execute(text("INSERT INTO children(id,family_id,user_id,grade,subjects,school_type,region,preferences) VALUES('c','f','u',6,'[]','','','{}')"))
            con.execute(text("INSERT INTO learning_units(id,child_id,subject,topic,explanation,questions,status,synthetic,provider,created,active_seconds) VALUES('unit','c','Informatik','Test','Synthetic','[]','completed',true,'synthetic',1,300)"))
            con.execute(text("INSERT INTO attempts(id,unit_id,question_id,answer,outcome,assisted,created) VALUES('attempt','unit','q1','\"synthetic\"','correct',false,1)"))
        for _ in range(2):
            result = subprocess.run([*command, '0057'], env=env, capture_output=True)
            assert result.returncode == 0, result.stderr.decode(errors='replace')
            with engine.begin() as con:
                scope(con)
                assert con.scalar(text("SELECT count(*) FROM curriculum_topics WHERE document_id = 'st-sek-informatik-erprobung-2026'")) == 11
                assert con.scalar(text("SELECT outcome FROM attempts WHERE id='attempt'")) == 'correct'
                assert con.scalar(text("SELECT active_seconds FROM learning_units WHERE id='unit'")) == 300
    finally:
        if schema:
            with test_engine.begin() as con:
                con.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        else:
            engine.dispose()
