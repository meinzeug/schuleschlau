"""The ST civics overview is sourced, scoped, and never a learner record."""
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from schulpilot import curriculum
from schulpilot.curriculum_schemas import CatalogueInput
from schulpilot.db import DB, Activity, Attempt, Child, ChildSubject, Job, LearningUnit, Material, Subject, Usage
from schulpilot.db import engine as test_engine
from sqlalchemy import create_engine, event, func, select, text

SOURCE = Path(__file__).parents[1] / 'schulpilot/reference/curriculum-st-sekundarschule-sozialkunde-2019.json'
DOCUMENT = 'st-sek-sozialkunde-2019'


def package():
    return json.loads(SOURCE.read_text())


def test_official_scope_marks_year_nine_and_unassigned_elections():
    value = CatalogueInput.model_validate(package())
    assert value.coverage.complete is False and len(value.documents) == 1 and len(value.topics) == 13
    document = value.documents[0]
    assert (document.state_code, document.school_form_id, document.edition) == (
        'DE-ST', 'de-st.sekundarschule', 'Stand 01.08.2019')
    assert all(term in document.applicability_note for term in (
        'Sozialkunde', 'Gemeinschaftskunde', 'keine Kursbelegung', 'ausgewogen', 'keinem einzelnen Schuljahr'))
    assert 'CC BY-SA 3.0' in document.source_notes
    assert 'fed964b5ca7173a267dfc03176f060e16b2dfe12bc1e3750339e47c1929c2c59' in document.source_notes
    assert len([row for row in value.topics if row.grade_kind == 'exact' and row.grades == [8]]) == 4
    assert len([row for row in value.topics if row.grade_kind == 'exact' and row.grades == [9]]) == 3
    assert len([row for row in value.topics if row.grade_kind == 'band' and row.grades == [9, 10]]) == 5
    election = next(row for row in value.topics if row.id.endswith('.wahltermin'))
    assert election.grade_kind == 'unclassified' and election.grades is None
    assert all(row.subject_key == 'gemeinschaftskunde' and row.canonical_topic_key is None for row in value.topics)


def test_grade_and_school_scope_do_not_create_activity_or_ai(api, household):
    with DB.begin() as db:
        assert curriculum.import_catalogue(db, package())['topics_added'] == 0
        assert curriculum.import_catalogue(db, package())['topics_added'] == 0
        subject_id = db.scalar(select(Subject.id).where(
            Subject.key == 'gemeinschaftskunde', Subject.owner_family_id.is_(None)))
        assert subject_id
    with DB() as db:
        before = {model: db.scalar(select(func.count()).select_from(model))
                  for model in (Activity, Attempt, ChildSubject, Job, LearningUnit, Usage)}

    def selected(grade, form='de-st.sekundarschule'):
        params = {'state_code': 'DE-ST', 'school_form_id': form, 'subject_id': subject_id, 'limit': 50}
        if grade is not None:
            params['grade'] = grade
        response = api.get('/api/curriculum/topics', params=params)
        assert response.status_code == 200
        return [row for row in response.json()['items'] if row['source']['document_id'] == DOCUMENT]

    for grade, expected in [(5, 0), (6, 0), (7, 0), (8, 4), (9, 8), (10, 5), (11, 0)]:
        rows = selected(grade)
        assert len(rows) == expected
        assert all(row['subject_id'] == subject_id for row in rows)
        assert all('ausgewogen' in row['source']['applicability_note'] for row in rows)
        assert not any(row['id'].endswith('.wahltermin') for row in rows)
    assert len(selected(None)) == 13
    assert not selected(8, 'de-st.gymnasium')
    with DB() as db:
        assert all(db.scalar(select(func.count()).select_from(model)) == before[model] for model in before)


def test_planning_context_preserves_scope_and_does_not_infer_elections(api, household):
    from schulpilot.visual_references import with_visual_context
    from test_curriculum import save
    save(api, household, state_code='DE-ST', school_form_id='de-st.sekundarschule', grade=9)
    with DB.begin() as db:
        child = db.get(Child, household[1]['id'])
        context = curriculum.planning_context(db, child, ['Gemeinschaftskunde'])
        material = Material(child_id=child.id, title='Künstlich', subject='Gemeinschaftskunde',
                            topic='Demokratie', content='Ein künstlicher, bestätigter Beispieltext.',
                            status='confirmed', confirmed=True)
        db.add(material)
        db.flush()
        outgoing = with_visual_context(db, child,
            {'material': {'subject': 'Gemeinschaftskunde', 'content': material.content}}, [material])
    for value in (context, outgoing['curriculum_context']):
        rows = [row for row in value['topics'] if row['source']['document_id'] == DOCUMENT]
        assert len(rows) == 8 and value['coverage'] == 'partial'
        assert all('keine Kursbelegung' in row['source']['applicability_note'] and
                   'ausgewogen' in row['source']['applicability_note'] for row in rows)
        assert not any(row['id'].endswith('.wahltermin') for row in rows)


def test_other_subjects_do_not_receive_civics_context(api, household):
    from test_curriculum import save
    save(api, household, state_code='DE-ST', school_form_id='de-st.sekundarschule', grade=9)
    with DB() as db:
        child = db.get(Child, household[1]['id'])
        context = curriculum.planning_context(db, child, ['Mathematik'])
    assert not any(row['source']['document_id'] == DOCUMENT for row in context['topics'])


@pytest.mark.parametrize('dialect', ['sqlite', 'postgresql'])
def test_additive_migration_keeps_answers_and_time(tmp_path, dialect):
    schema = None
    if dialect == 'postgresql':
        if test_engine.dialect.name != 'postgresql':
            pytest.skip('Requires isolated PostgreSQL.')
        schema = 'st_civics_' + uuid.uuid4().hex
        with test_engine.begin() as con:
            con.execute(text(f'CREATE SCHEMA "{schema}"'))
        url, engine = os.environ['TEST_DATABASE_URL'], test_engine
    else:
        url = 'sqlite:///' + str(tmp_path / 'civics.sqlite')
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
        result = subprocess.run([*command, '0061'], env=env, capture_output=True)
        assert result.returncode == 0, result.stderr.decode(errors='replace')
        with engine.begin() as con:
            scope(con)
            con.execute(text("DELETE FROM curriculum_documents WHERE id = 'st-sek-sozialkunde-2019'"))
            con.execute(text("INSERT INTO families(id,name,synthetic,created,child_limit,call_limit,budget_micros,plan) VALUES('f','Synthetic',true,1,4,100,2000000,'Pilot')"))
            con.execute(text("INSERT INTO users(id,username,display_name,password_hash,role,verified,disabled,created) VALUES('u','synthetic','Synthetic','SYNTHETIC-HASH','parent',true,false,1)"))
            con.execute(text("INSERT INTO children(id,family_id,user_id,grade,subjects,school_type,region,preferences) VALUES('c','f','u',8,'[]','','','{}')"))
            con.execute(text("INSERT INTO learning_units(id,child_id,subject,topic,explanation,questions,status,synthetic,provider,created,active_seconds) VALUES('unit','c','Gemeinschaftskunde','Test','Synthetic','[]','completed',true,'synthetic',1,300)"))
            con.execute(text("INSERT INTO attempts(id,unit_id,question_id,answer,outcome,assisted,created) VALUES('attempt','unit','q1','\"synthetic\"','correct',false,1)"))
        for _ in range(2):
            result = subprocess.run([*command, '0062'], env=env, capture_output=True)
            assert result.returncode == 0, result.stderr.decode(errors='replace')
            with engine.begin() as con:
                scope(con)
                assert con.scalar(text("SELECT count(*) FROM curriculum_topics WHERE document_id = 'st-sek-sozialkunde-2019'")) == 13
                assert con.scalar(text("SELECT outcome FROM attempts WHERE id='attempt'")) == 'correct'
                assert con.scalar(text("SELECT active_seconds FROM learning_units WHERE id='unit'")) == 300
    finally:
        if schema:
            with test_engine.begin() as con:
                con.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        else:
            engine.dispose()
