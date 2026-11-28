"""Sourced Hauswirtschaft scope and additive, non-destructive subject upgrade."""
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from schulpilot import curriculum
from schulpilot.curriculum_schemas import CatalogueInput
from schulpilot.db import DB, Activity, Attempt, Child, ChildSubject, Job, LearningUnit, Material, Usage
from schulpilot.db import engine as test_engine
from schulpilot.subject_registry import create_private_connection, resolve, seed_additional_v2
from sqlalchemy import create_engine, event, func, select, text

SOURCE = Path(__file__).parents[1] / 'schulpilot/reference/curriculum-st-sekundarschule-hauswirtschaft-2019.json'
DOCUMENT = 'st-sek-hauswirtschaft-2019'


def package():
    return json.loads(SOURCE.read_text())


def test_official_scope_uses_current_overview_and_year_nine():
    value = CatalogueInput.model_validate(package())
    assert value.coverage.complete is False and len(value.documents) == 1 and len(value.topics) == 7
    document = value.documents[0]
    assert (document.state_code, document.school_form_id, document.edition) == (
        'DE-ST', 'de-st.sekundarschule', 'Stand 01.08.2019')
    assert 'CC BY-SA 3.0' in document.source_notes
    assert 'e8904840d4b098e853f79c2a7ce04f2158226dd39dc86cfb82a27b29ee032630' in document.source_notes
    assert all(word in document.applicability_note for word in (
        'Jahrgang 9', 'Aufsicht', 'keine Aufforderung', '2019'))
    assert len([row for row in value.topics if row.grade_kind == 'band' and row.grades == [5, 6]]) == 2
    assert len([row for row in value.topics if row.grade_kind == 'band' and row.grades == [7, 8]]) == 2
    assert len([row for row in value.topics if row.grade_kind == 'exact' and row.grades == [9]]) == 2
    assert len([row for row in value.topics if row.grade_kind == 'band' and row.grades == [9, 10]]) == 1
    assert all(row.subject_key == 'hauswirtschaft' and row.canonical_topic_key is None for row in value.topics)


def test_subject_and_grade_scope_are_read_only(api, household):
    with DB.begin() as db:
        seed_additional_v2(db.connection())
        seed_additional_v2(db.connection())
        assert curriculum.import_catalogue(db, package())['topics_added'] == 0
        home = resolve(db, 'Hauswirtschaft')
        economy = resolve(db, 'Wirtschaft')
        assert home is not None and economy is not None and home.id != economy.id
        subject_id = home.id
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

    for grade, expected in [(4, 0), (5, 2), (6, 2), (7, 2), (8, 2), (9, 3), (10, 1), (11, 0)]:
        rows = selected(grade)
        assert len(rows) == expected
        assert all(row['subject_id'] == subject_id and 'Aufsicht' in row['source']['applicability_note'] for row in rows)
    assert len(selected(None)) == 7
    assert not selected(6, 'de-st.gymnasium')
    with DB() as db:
        assert all(db.scalar(select(func.count()).select_from(model)) == before[model] for model in before)


def test_planning_keeps_source_and_safety_context(api, household):
    from schulpilot.visual_references import with_visual_context
    from test_curriculum import save

    save(api, household, state_code='DE-ST', school_form_id='de-st.sekundarschule', grade=9)
    with DB.begin() as db:
        child = db.get(Child, household[1]['id'])
        context = curriculum.planning_context(db, child, ['Hauswirtschaft'])
        material = Material(child_id=child.id, title='Künstlich', subject='Hauswirtschaft',
                            topic='Zusammenleben', content='Ein künstlicher bestätigter Beispieltext.',
                            status='confirmed', confirmed=True)
        db.add(material)
        db.flush()
        assert material.subject_id == resolve(db, 'Hauswirtschaft').id
        outgoing = with_visual_context(db, child,
            {'material': {'subject': 'Hauswirtschaft', 'content': material.content}}, [material])
    for value in (context, outgoing['curriculum_context']):
        rows = [row for row in value['topics'] if row['source']['document_id'] == DOCUMENT]
        assert len(rows) == 3 and value['coverage'] == 'partial'
        assert all('Aufsicht' in row['source']['applicability_note'] and
                   'keine Aufforderung' in row['source']['applicability_note'] for row in rows)


@pytest.mark.parametrize('dialect', ['sqlite', 'postgresql'])
def test_upgrade_preserves_private_subject_and_learning_records(tmp_path, dialect):
    schema = None
    if dialect == 'postgresql':
        if test_engine.dialect.name != 'postgresql':
            pytest.skip('Requires isolated PostgreSQL.')
        schema = 'st_home_' + uuid.uuid4().hex
        with test_engine.begin() as con:
            con.execute(text(f'CREATE SCHEMA "{schema}"'))
        url, engine = os.environ['TEST_DATABASE_URL'], test_engine
    else:
        url = 'sqlite:///' + str(tmp_path / 'home-economics.sqlite')
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
        result = subprocess.run([*command, '0062'], env=env, capture_output=True)
        assert result.returncode == 0, result.stderr.decode(errors='replace')
        with engine.begin() as con:
            scope(con)
            con.execute(text("INSERT INTO families(id,name,synthetic,created,child_limit,call_limit,budget_micros,plan) VALUES('f','Synthetic',true,1,4,100,2000000,'Pilot')"))
            con.execute(text("INSERT INTO users(id,username,display_name,password_hash,role,verified,disabled,created) VALUES('u','synthetic','Synthetic','SYNTHETIC-HASH','parent',true,false,1)"))
            con.execute(text("INSERT INTO children(id,family_id,user_id,grade,subjects,school_type,region,preferences) VALUES('c','f','u',9,'[]','','','{}')"))
            private_id = create_private_connection(con, 'Hauswirtschaft', 'f')
            con.execute(text("INSERT INTO learning_units(id,child_id,subject,subject_id,topic,explanation,questions,status,synthetic,provider,created,active_seconds) VALUES('unit','c','Hauswirtschaft',:subject,'Test','Synthetic','[]','completed',true,'synthetic',1,300)"), {'subject': private_id})
            con.execute(text("INSERT INTO attempts(id,unit_id,question_id,answer,outcome,assisted,created) VALUES('attempt','unit','q1','\"synthetic\"','correct',false,1)"))
        for _ in range(2):
            result = subprocess.run([*command, '0063'], env=env, capture_output=True)
            assert result.returncode == 0, result.stderr.decode(errors='replace')
            with engine.begin() as con:
                scope(con)
                global_id = con.scalar(text("SELECT id FROM subjects WHERE key='hauswirtschaft' AND owner_family_id IS NULL"))
                assert global_id and global_id != private_id
                assert con.scalar(text("SELECT subject_id FROM learning_units WHERE id='unit'")) == private_id
                assert con.scalar(text("SELECT outcome FROM attempts WHERE id='attempt'")) == 'correct'
                assert con.scalar(text("SELECT active_seconds FROM learning_units WHERE id='unit'")) == 300
                assert con.scalar(text("SELECT count(*) FROM curriculum_topics WHERE document_id=:id AND subject_id=:subject"),
                                  {'id': DOCUMENT, 'subject': global_id}) == 7
    finally:
        if schema:
            with test_engine.begin() as con:
                con.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        else:
            engine.dispose()
