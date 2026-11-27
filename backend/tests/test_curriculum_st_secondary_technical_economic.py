"""Sourced ST overviews remain scoped and never imply a practical assignment."""
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from schulpilot import curriculum
from schulpilot.curriculum_schemas import CatalogueInput
from schulpilot.db import DB, Activity, Child, Job, Material, Subject, Usage
from schulpilot.db import engine as test_engine
from schulpilot.visual_references import with_visual_context
from sqlalchemy import create_engine, event, func, select, text

SOURCE = Path(__file__).parents[1] / 'schulpilot/reference/curriculum-st-sekundarschule-technik-wirtschaft-2019.json'
EXPECTED = {
    'technik': {(5, 6): 3, (7, 8): 2, (9, 10): 2},
    'wirtschaft': {(7, 8): 4, (9, 10): 4},
}
TITLES = {
    'technik': {'Computer als Werkzeug', 'Gebrauchsgegenstände aus Holz und Kunststoff',
                'Funktionsmodelle entwickeln und untersuchen', 'Technische Lösungen untersuchen',
                'Funktion und Einsatz von Maschinen', 'Technische Systeme beschreiben und analysieren',
                'Technische Prozesse steuern'},
    'wirtschaft': {'Privater Haushalt und Wirtschaft', 'Berufe und Arbeitsplätze in der Region',
                   'Regionaler Wirtschaftsraum', 'Entwicklungen im Handel', 'Berufsperspektiven',
                   'Soziale Marktwirtschaft', 'Unternehmerisches Handeln',
                   'Wirtschaftspolitische Entscheidungen'},
}


def package():
    return json.loads(SOURCE.read_text())


def test_source_scopes_and_safety_limitations_are_preserved():
    value = CatalogueInput.model_validate(package())
    assert value.coverage.complete is False
    assert len(value.documents) == 2 and len(value.topics) == 15
    for document in value.documents:
        assert document.state_code == 'DE-ST' and document.school_form_id == 'de-st.sekundarschule'
        assert document.edition == 'Stand 01.08.2019'
        assert 'CC BY-SA 3.0' in document.source_notes
        assert 'Schuljahrgang 9' in document.applicability_note
    notes = {document.id: document.applicability_note for document in value.documents}
    assert 'Aufsicht' in notes['st-sek-technik-2019']
    assert 'Finanzdaten' in notes['st-sek-wirtschaft-2019']
    for subject, bands in EXPECTED.items():
        assert {t.title for t in value.topics if t.subject_key == subject} == TITLES[subject]
        for grades, count in bands.items():
            rows = [t for t in value.topics if t.subject_key == subject and tuple(t.grades) == grades]
            assert len(rows) == count
            assert all(t.grade_kind == 'band' and t.section == '3.1' and t.page == 11 for t in rows)
            assert all(t.canonical_topic_key is None and not t.common_fact_keywords for t in rows)


@pytest.mark.parametrize(('subject', 'grade', 'expected'), [
    ('technik', 4, 0), ('technik', 5, 3), ('technik', 6, 3), ('technik', 7, 2),
    ('technik', 8, 2), ('technik', 9, 2), ('technik', 10, 2), ('technik', 11, 0),
    ('wirtschaft', 6, 0), ('wirtschaft', 7, 4), ('wirtschaft', 8, 4),
    ('wirtschaft', 9, 4), ('wirtschaft', 10, 4), ('wirtschaft', 11, 0),
])
def test_read_is_scoped_idempotent_and_has_no_learning_side_effects(api, household, subject, grade, expected):
    document_id = f'st-sek-{subject}-2019'
    with DB.begin() as db:
        assert curriculum.import_catalogue(db, package())['topics_added'] == 0
        subject_id = db.scalar(select(Subject.id).where(Subject.key == subject, Subject.owner_family_id.is_(None)))
    with DB() as db:
        before = {m: db.scalar(select(func.count()).select_from(m)) for m in (Activity, Job, Usage)}
    response = api.get('/api/curriculum/topics', params={'state_code':'DE-ST',
        'school_form_id':'de-st.sekundarschule', 'subject_id':subject_id, 'grade':grade, 'limit':50})
    assert response.status_code == 200
    rows = [row for row in response.json()['items'] if row['source']['document_id'] == document_id]
    assert len(rows) == expected
    assert all('Schuljahrgang 9' in row['source']['applicability_note'] for row in rows)
    assert all(('Aufsicht' if subject == 'technik' else 'Finanzdaten') in
               row['source']['applicability_note'] for row in rows)
    with DB() as db:
        assert all(db.scalar(select(func.count()).select_from(m)) == before[m] for m in before)


@pytest.mark.parametrize(('subject', 'safety'), [('Technik', 'Aufsicht'), ('Wirtschaft', 'Finanzdaten')])
def test_ai_context_carries_source_restrictions(api, household, subject, safety):
    from test_curriculum import save
    save(api, household, state_code='DE-ST', school_form_id='de-st.sekundarschule', grade=9)
    with DB.begin() as db:
        child = db.get(Child, household[1]['id'])
        context = curriculum.planning_context(db, child, [subject])
        material = Material(child_id=child.id, title='Künstlich', subject=subject, topic='Beispiel',
                            content='Ein künstlicher, bestätigter Beispieltext.', status='confirmed', confirmed=True)
        db.add(material)
        db.flush()
        outgoing = with_visual_context(db, child, {'material': {'subject': subject, 'content': material.content}}, [material])
    for value in (context, outgoing['curriculum_context']):
        rows = [row for row in value['topics'] if row['source']['document_id'] == f'st-sek-{subject.lower()}-2019']
        assert rows and value['coverage'] == 'partial'
        assert all('Schuljahrgang 9' in row['source']['applicability_note'] and safety in
                   row['source']['applicability_note'] for row in rows)


@pytest.mark.parametrize('dialect', ['sqlite', 'postgresql'])
def test_migration_preserves_existing_answers(tmp_path, dialect):
    schema = None
    if dialect == 'postgresql':
        if test_engine.dialect.name != 'postgresql':
            pytest.skip('Requires isolated PostgreSQL.')
        schema = 'st_tech_econ_' + uuid.uuid4().hex
        with test_engine.begin() as con:
            con.execute(text(f'CREATE SCHEMA "{schema}"'))
        url, engine = os.environ['TEST_DATABASE_URL'], test_engine
    else:
        url = 'sqlite:///' + str(tmp_path / 'tech-econ.sqlite')
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
        result = subprocess.run([*command, '0060'], env=env, capture_output=True)
        assert result.returncode == 0, result.stderr.decode(errors='replace')
        with engine.begin() as con:
            scope(con)
            con.execute(text("DELETE FROM curriculum_documents WHERE id IN ('st-sek-technik-2019','st-sek-wirtschaft-2019')"))
            con.execute(text("INSERT INTO families(id,name,synthetic,created,child_limit,call_limit,budget_micros,plan) VALUES('f','Synthetic',true,1,4,100,2000000,'Pilot')"))
            con.execute(text("INSERT INTO users(id,username,display_name,password_hash,role,verified,disabled,created) VALUES('u','synthetic','Synthetic','SYNTHETIC-HASH','parent',true,false,1)"))
            con.execute(text("INSERT INTO children(id,family_id,user_id,grade,subjects,school_type,region,preferences) VALUES('c','f','u',6,'[]','','','{}')"))
            con.execute(text("INSERT INTO learning_units(id,child_id,subject,topic,explanation,questions,status,synthetic,provider,created,active_seconds) VALUES('unit','c','Technik','Test','Synthetic','[]','completed',true,'synthetic',1,300)"))
            con.execute(text("INSERT INTO attempts(id,unit_id,question_id,answer,outcome,assisted,created) VALUES('attempt','unit','q1','\"synthetic\"','correct',false,1)"))
        for _ in range(2):
            result = subprocess.run([*command, '0061'], env=env, capture_output=True)
            assert result.returncode == 0, result.stderr.decode(errors='replace')
            with engine.begin() as con:
                scope(con)
                assert con.scalar(text("SELECT count(*) FROM curriculum_topics WHERE document_id IN ('st-sek-technik-2019','st-sek-wirtschaft-2019')")) == 15
                assert con.scalar(text("SELECT outcome FROM attempts WHERE id='attempt'")) == 'correct'
                assert con.scalar(text("SELECT active_seconds FROM learning_units WHERE id='unit'")) == 300
    finally:
        if schema:
            with test_engine.begin() as con:
                con.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        else:
            engine.dispose()
