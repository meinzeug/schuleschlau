"""Official ST secondary music overview, band scope and migration."""
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

SOURCE = Path(__file__).parents[1] / 'schulpilot/reference/curriculum-st-sekundarschule-musik-2019.json'
DOCUMENT = 'st-sek-musik-2019'


def package():
    return json.loads(SOURCE.read_text())


def test_official_scope_does_not_invent_separate_ninth_grade():
    value = CatalogueInput.model_validate(package())
    assert value.coverage.complete is False and len(value.documents) == 1 and len(value.topics) == 15
    document = value.documents[0]
    assert (document.state_code, document.school_form_id, document.edition) == (
        'DE-ST', 'de-st.sekundarschule', 'Stand 01.08.2019')
    assert 'Jahrgang 9' in document.applicability_note and 'keine Zuordnung' in document.applicability_note
    assert 'CC BY-SA 3.0' in document.source_notes
    assert '039a3dfd181d56a5b77e7cd5c5e0b3c50e932ace06f0ea4393a5ac60105c54ed' in document.source_notes
    for grades in ([5, 6], [7, 8], [9, 10]):
        rows = [row for row in value.topics if row.grades == grades]
        assert len(rows) == 5
        assert all(row.grade_kind == 'band' and row.page == 9 and row.section == '3.1' for row in rows)
        assert all(row.subject_key == 'musik' and row.canonical_topic_key is None for row in rows)


def test_read_and_import_do_not_change_learning_or_start_ai(api, household):
    with DB.begin() as db:
        assert curriculum.import_catalogue(db, package())['topics_added'] == 0
        assert curriculum.import_catalogue(db, package())['topics_added'] == 0
        subject_id = db.scalar(select(Subject.id).where(Subject.key == 'musik', Subject.owner_family_id.is_(None)))
    with DB() as db:
        before = {model: db.scalar(select(func.count()).select_from(model)) for model in (Activity, Job, Usage)}

    def selected(grade, form='de-st.sekundarschule'):
        response = api.get('/api/curriculum/topics', params={'state_code': 'DE-ST', 'school_form_id': form,
                           'subject_id': subject_id, 'grade': grade, 'limit': 50})
        assert response.status_code == 200
        return [row for row in response.json()['items'] if row['source']['document_id'] == DOCUMENT]

    for grade in range(5, 11):
        rows = selected(grade)
        assert len(rows) == 5
        assert all('Jahrgang 9' in row['source']['applicability_note'] for row in rows)
    assert not selected(4) and not selected(11) and not selected(6, 'de-st.gymnasium')
    with DB() as db:
        assert all(db.scalar(select(func.count()).select_from(model)) == before[model] for model in before)


def test_ai_planning_retains_source_and_band_scope(api, household):
    from schulpilot.db import Material
    from schulpilot.visual_references import with_visual_context
    from test_curriculum import save
    child_id = household[1]['id']
    save(api, household, state_code='DE-ST', school_form_id='de-st.sekundarschule', grade=9)
    with DB.begin() as db:
        child = db.get(Child, child_id)
        context = curriculum.planning_context(db, child, ['Musik'])
        material = Material(child_id=child.id, title='Künstlich', subject='Musik', topic='Musik',
                            content='Ein künstliches Beispiel zur Musik.', status='confirmed', confirmed=True)
        db.add(material)
        db.flush()
        outgoing = with_visual_context(db, child, {'material': {'subject': 'Musik', 'content': material.content}}, [material])
    items = [row for row in context['topics'] if row['source']['document_id'] == DOCUMENT]
    assert len(items) == 5
    assert all('Jahrgang 9' in row['source']['applicability_note'] for row in items)
    assert context['coverage'] == 'partial'
    emitted = [row for row in outgoing['curriculum_context']['topics'] if row['source']['document_id'] == DOCUMENT]
    assert len(emitted) == 5
    assert all('Jahrgang 9' in row['source']['applicability_note'] for row in emitted)


@pytest.mark.parametrize('dialect', ['sqlite', 'postgresql'])
def test_migration_preserves_existing_attempts_and_is_idempotent(tmp_path, dialect):
    schema = None
    if dialect == 'postgresql':
        if test_engine.dialect.name != 'postgresql':
            pytest.skip('Requires isolated PostgreSQL.')
        schema = 'st_music_' + uuid.uuid4().hex
        with test_engine.begin() as con:
            con.execute(text(f'CREATE SCHEMA "{schema}"'))
        url, engine = os.environ['TEST_DATABASE_URL'], test_engine
    else:
        url = 'sqlite:///' + str(tmp_path / 'music.sqlite')
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
        result = subprocess.run([*command, '0057'], env=env, capture_output=True)
        assert result.returncode == 0, result.stderr.decode(errors='replace')
        with engine.begin() as con:
            scope(con)
            con.execute(text("DELETE FROM curriculum_documents WHERE id = 'st-sek-musik-2019'"))
            con.execute(text("INSERT INTO families(id,name,synthetic,created,child_limit,call_limit,budget_micros,plan) VALUES('f','Synthetic',true,1,4,100,2000000,'Pilot')"))
            con.execute(text("INSERT INTO users(id,username,display_name,password_hash,role,verified,disabled,created) VALUES('u','synthetic','Synthetic','SYNTHETIC-HASH','parent',true,false,1)"))
            con.execute(text("INSERT INTO children(id,family_id,user_id,grade,subjects,school_type,region,preferences) VALUES('c','f','u',6,'[]','','','{}')"))
            con.execute(text("INSERT INTO learning_units(id,child_id,subject,topic,explanation,questions,status,synthetic,provider,created,active_seconds) VALUES('unit','c','Musik','Test','Synthetic','[]','completed',true,'synthetic',1,300)"))
            con.execute(text("INSERT INTO attempts(id,unit_id,question_id,answer,outcome,assisted,created) VALUES('attempt','unit','q1','\"synthetic\"','correct',false,1)"))
        for _ in range(2):
            result = subprocess.run([*command, '0058'], env=env, capture_output=True)
            assert result.returncode == 0, result.stderr.decode(errors='replace')
            with engine.begin() as con:
                scope(con)
                assert con.scalar(text("SELECT count(*) FROM curriculum_topics WHERE document_id = 'st-sek-musik-2019'")) == 15
                assert con.scalar(text("SELECT outcome FROM attempts WHERE id='attempt'")) == 'correct'
                assert con.scalar(text("SELECT active_seconds FROM learning_units WHERE id='unit'")) == 300
    finally:
        if schema:
            with test_engine.begin() as con:
                con.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        else:
            engine.dispose()
