"""Official ST secondary sport areas and safe scope, not activity advice."""
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

SOURCE = Path(__file__).parents[1] / 'schulpilot/reference/curriculum-st-sekundarschule-sport-2019.json'
DOCUMENT = 'st-sek-sport-2019'
AREAS = {
    'Fitness und Gesundheit', 'Spielen und Fairness', 'Laufen, Springen und Werfen',
    'Turnerische Bewegungen', 'Rhythmus, Tanz und Gestaltung', 'Faires Kämpfen',
    'Bewegung auf Rollen', 'Bewegung im Wasser', 'Bewegung auf dem Wasser',
    'Bewegung auf Schnee und Eis',
}


def package():
    return json.loads(SOURCE.read_text())


def test_official_areas_retain_choices_and_three_band_scope():
    value = CatalogueInput.model_validate(package())
    assert value.coverage.complete is False and len(value.documents) == 1 and len(value.topics) == 30
    document = value.documents[0]
    assert (document.state_code, document.school_form_id, document.edition) == (
        'DE-ST', 'de-st.sekundarschule', 'Stand 01.08.2019')
    assert all(word in document.applicability_note for word in ('Pflichtfelder', 'Wahlfelder', 'Wahlkurse', 'Aufsicht'))
    assert 'CC BY-SA 3.0' in document.source_notes
    assert '694c8eb9917cc036e576c7f3064ae0584993fa58685f1fcd83c05f61fab23551' in document.source_notes
    assert 'Belastungsempfehlung' in value.coverage.note
    for grades in ([5, 6], [7, 8], [9, 10]):
        rows = [row for row in value.topics if row.grades == grades]
        assert len(rows) == 10
        assert all(row.grade_kind == 'band' and row.page == 13 and row.section == '3.1' for row in rows)
        assert all(row.subject_key == 'sport' and row.canonical_topic_key is None for row in rows)
        assert {row.title for row in rows} == AREAS


def test_read_and_import_do_not_change_learning_or_start_ai(api, household):
    with DB.begin() as db:
        assert curriculum.import_catalogue(db, package())['topics_added'] == 0
        assert curriculum.import_catalogue(db, package())['topics_added'] == 0
        subject_id = db.scalar(select(Subject.id).where(Subject.key == 'sport', Subject.owner_family_id.is_(None)))
    with DB() as db:
        before = {model: db.scalar(select(func.count()).select_from(model)) for model in (Activity, Job, Usage)}

    def selected(grade, form='de-st.sekundarschule'):
        response = api.get('/api/curriculum/topics', params={'state_code': 'DE-ST', 'school_form_id': form,
                           'subject_id': subject_id, 'grade': grade, 'limit': 50})
        assert response.status_code == 200
        return [row for row in response.json()['items'] if row['source']['document_id'] == DOCUMENT]

    for grade in range(5, 11):
        rows = selected(grade)
        assert len(rows) == 10
        assert all('Wahlkurse' in row['source']['applicability_note'] for row in rows)
    assert not selected(4) and not selected(11) and not selected(6, 'de-st.gymnasium')
    with DB() as db:
        assert all(db.scalar(select(func.count()).select_from(model)) == before[model] for model in before)


def test_ai_context_preserves_choice_and_supervision_without_creating_work(api, household):
    from schulpilot.db import Material
    from schulpilot.visual_references import with_visual_context
    from test_curriculum import save

    child_id = household[1]['id']
    save(api, household, state_code='DE-ST', school_form_id='de-st.sekundarschule', grade=9)
    with DB.begin() as db:
        child = db.get(Child, child_id)
        context = curriculum.planning_context(db, child, ['Sport'])
        material = Material(child_id=child.id, title='Künstlich', subject='Sport', topic='Fairness',
                            content='Faires Spielen ist ein allgemeines Beispiel.', status='confirmed', confirmed=True)
        db.add(material)
        db.flush()
        outgoing = with_visual_context(db, child, {'material': {'subject': 'Sport', 'content': material.content}}, [material])
    for value in (context, outgoing['curriculum_context']):
        items = [row for row in value['topics'] if row['source']['document_id'] == DOCUMENT]
        assert len(items) == 8  # Existing cross-subject context ceiling, not a complete syllabus.
        assert value['coverage'] == 'partial'
        assert all('Wahlkurse' in row['source']['applicability_note'] and
                   'Aufsicht' in row['source']['applicability_note'] for row in items)


@pytest.mark.parametrize('dialect', ['sqlite', 'postgresql'])
def test_migration_preserves_attempts_and_is_idempotent(tmp_path, dialect):
    schema = None
    if dialect == 'postgresql':
        if test_engine.dialect.name != 'postgresql':
            pytest.skip('Requires isolated PostgreSQL.')
        schema = 'st_sport_' + uuid.uuid4().hex
        with test_engine.begin() as con:
            con.execute(text(f'CREATE SCHEMA "{schema}"'))
        url, engine = os.environ['TEST_DATABASE_URL'], test_engine
    else:
        url = 'sqlite:///' + str(tmp_path / 'sport.sqlite')
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
        result = subprocess.run([*command, '0059'], env=env, capture_output=True)
        assert result.returncode == 0, result.stderr.decode(errors='replace')
        with engine.begin() as con:
            scope(con)
            con.execute(text("DELETE FROM curriculum_documents WHERE id = 'st-sek-sport-2019'"))
            con.execute(text("INSERT INTO families(id,name,synthetic,created,child_limit,call_limit,budget_micros,plan) VALUES('f','Synthetic',true,1,4,100,2000000,'Pilot')"))
            con.execute(text("INSERT INTO users(id,username,display_name,password_hash,role,verified,disabled,created) VALUES('u','synthetic','Synthetic','SYNTHETIC-HASH','parent',true,false,1)"))
            con.execute(text("INSERT INTO children(id,family_id,user_id,grade,subjects,school_type,region,preferences) VALUES('c','f','u',6,'[]','','','{}')"))
            con.execute(text("INSERT INTO learning_units(id,child_id,subject,topic,explanation,questions,status,synthetic,provider,created,active_seconds) VALUES('unit','c','Sport','Test','Synthetic','[]','completed',true,'synthetic',1,300)"))
            con.execute(text("INSERT INTO attempts(id,unit_id,question_id,answer,outcome,assisted,created) VALUES('attempt','unit','q1','\"synthetic\"','correct',false,1)"))
        for _ in range(2):
            result = subprocess.run([*command, '0060'], env=env, capture_output=True)
            assert result.returncode == 0, result.stderr.decode(errors='replace')
            with engine.begin() as con:
                scope(con)
                assert con.scalar(text("SELECT count(*) FROM curriculum_topics WHERE document_id = 'st-sek-sport-2019'")) == 30
                assert con.scalar(text("SELECT outcome FROM attempts WHERE id='attempt'")) == 'correct'
                assert con.scalar(text("SELECT active_seconds FROM learning_units WHERE id='unit'")) == 300
    finally:
        if schema:
            with test_engine.begin() as con:
                con.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        else:
            engine.dispose()
