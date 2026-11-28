"""French source phases are public orientation, never an inferred language course."""
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from schulpilot import curriculum
from schulpilot.curriculum_schemas import CatalogueInput
from schulpilot.db import DB, Activity, Attempt, Child, ChildSubject, Job, LearningUnit, Subject, Usage
from schulpilot.db import engine as test_engine
from sqlalchemy import create_engine, event, func, select, text

SOURCE = Path(__file__).parents[1] / 'schulpilot/reference/curriculum-st-sekundarschule-franzoesisch-2019.json'
DOCUMENT = 'st-sek-franzoesisch-2019'


def package():
    return json.loads(SOURCE.read_text())


def test_official_french_phases_never_infer_language_year_or_enrollment():
    value = CatalogueInput.model_validate(package())
    assert value.coverage.complete is False
    assert len(value.documents) == 1 and len(value.topics) == 8
    doc = value.documents[0]
    assert (doc.state_code, doc.school_form_id, doc.edition) == (
        'DE-ST', 'de-st.sekundarschule', 'Stand 01.08.2019')
    assert doc.official_url == 'https://www.bildung-lsa.de/files/164f3f97e3adf65ff6f44685dd9e1ced/lp_sks_franz_01_08_2019.pdf'
    assert '5ba6720beecf5bf80ebcbe9349cdf5a43c63c0af8ae0192341119deb0c5f8039' in doc.source_notes
    assert 'CC BY-SA 3.0' in doc.source_notes
    assert 'keine individuelle Kursbelegung' in doc.applicability_note
    assert 'kein Sprachlernjahr' in doc.applicability_note
    assert {t.phase_label for t in value.topics} == {'Schuljahrgänge 7/8', 'Schuljahrgänge 9/10'}
    assert all(t.grades is None and t.grade_kind == 'phase' for t in value.topics)
    assert all(t.subject_key == 'franzoesisch' and t.canonical_topic_key is None for t in value.topics)
    assert all(t.page == (12 if t.phase_label.endswith('7/8') else 17) for t in value.topics)


def test_idempotent_import_and_explicit_phase_filter_never_create_child_data(api, household):
    with DB.begin() as db:
        first = curriculum.import_catalogue(db, package())
        second = curriculum.import_catalogue(db, package())
        subject_id = db.scalar(select(Subject.id).where(
            Subject.key == 'franzoesisch', Subject.owner_family_id.is_(None)))
        assert subject_id
    assert first['documents_added'] == first['topics_added'] == 0
    assert second['documents_added'] == second['topics_added'] == 0
    assert first['package_digest'] == second['package_digest']
    models = (Activity, Attempt, ChildSubject, Job, LearningUnit, Usage)
    with DB() as db:
        before = {model: db.scalar(select(func.count()).select_from(model)) for model in models}

    def rows(**extra):
        response = api.get('/api/curriculum/topics', params={
            'state_code': 'DE-ST', 'school_form_id': 'de-st.sekundarschule',
            'subject_id': subject_id, 'limit': 50, **extra,
        })
        assert response.status_code == 200
        return [r for r in response.json()['items'] if r['source']['document_id'] == DOCUMENT]

    assert len(rows()) == 8
    for phase in ('Schuljahrgänge 7/8', 'Schuljahrgänge 9/10'):
        items = rows(phase=phase)
        assert len(items) == 4
        assert all(r['grades'] is None and r['phase_label'] == phase for r in items)
    for grade in (5, 6, 7, 8, 9, 10, 11):
        assert rows(grade=grade) == []
    from test_curriculum import save
    save(api, household, state_code='DE-ST', school_form_id='de-st.sekundarschule', grade=8)
    with DB() as db:
        child = db.get(Child, household[1]['id'])
        context = curriculum.planning_context(db, child, ['Französisch'])
        assert context is not None
        assert not any(row['source']['document_id'] == DOCUMENT for row in context['topics'])
    with DB() as db:
        assert all(db.scalar(select(func.count()).select_from(model)) == before[model] for model in models)


@pytest.mark.parametrize('dialect', ['sqlite', 'postgresql'])
def test_migration_backfills_existing_installation_without_erasing_other_catalogue(tmp_path, dialect):
    schema = None
    if dialect == 'postgresql':
        if test_engine.dialect.name != 'postgresql':
            pytest.skip('Requires isolated PostgreSQL.')
        schema = 'st_french_' + uuid.uuid4().hex
        with test_engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        url, engine = os.environ['TEST_DATABASE_URL'], test_engine
    else:
        url = 'sqlite:///' + str(tmp_path / 'french.sqlite')
        engine = create_engine(url)

        @event.listens_for(engine, 'connect')
        def enable_fk(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')

    env = {**os.environ, 'DATABASE_URL': url, 'ENVIRONMENT': 'test'}
    if schema:
        env['PGOPTIONS'] = f'-c search_path={schema}'
    command = [sys.executable, '-m', 'alembic', '-c', str(Path(__file__).parents[1] / 'alembic.ini')]

    def scope(conn):
        if schema:
            conn.execute(text(f'SET LOCAL search_path TO "{schema}"'))

    try:
        result = subprocess.run([*command, 'upgrade', '0065'], env=env, capture_output=True, timeout=90, check=False)
        assert result.returncode == 0, result.stderr.decode(errors='replace')
        with engine.begin() as conn:
            scope(conn)
            conn.execute(text('DELETE FROM curriculum_topics WHERE document_id=:id'), {'id': DOCUMENT})
            conn.execute(text('DELETE FROM curriculum_documents WHERE id=:id'), {'id': DOCUMENT})
            others = conn.scalar(text('SELECT count(*) FROM curriculum_topics'))
            conn.execute(text("INSERT INTO families(id,name,synthetic,created,child_limit,call_limit,budget_micros,plan) VALUES('f','Synthetic',true,1,4,100,2000000,'Pilot')"))
            conn.execute(text("INSERT INTO users(id,username,display_name,password_hash,role,verified,disabled,created) VALUES('u','synthetic','Synthetic','SYNTHETIC-HASH','parent',true,false,1)"))
            conn.execute(text("INSERT INTO children(id,family_id,user_id,grade,subjects,school_type,region,preferences) VALUES('c','f','u',8,'[]','','','{}')"))
            conn.execute(text("INSERT INTO learning_units(id,child_id,subject,topic,explanation,questions,status,synthetic,provider,created,active_seconds) VALUES('unit','c','Französisch','Test','Synthetic','[]','completed',true,'synthetic',1,300)"))
            conn.execute(text("INSERT INTO attempts(id,unit_id,question_id,answer,outcome,assisted,created) VALUES('attempt','unit','q1','\"synthetic\"','correct',false,1)"))
        for _ in range(2):
            result = subprocess.run([*command, 'upgrade', '0066'], env=env, capture_output=True, timeout=90, check=False)
            assert result.returncode == 0, result.stderr.decode(errors='replace')
        with engine.begin() as conn:
            scope(conn)
            assert conn.scalar(text('SELECT version_num FROM alembic_version')) == '0066'
            assert conn.scalar(text('SELECT count(*) FROM curriculum_documents WHERE id=:id'), {'id': DOCUMENT}) == 1
            assert conn.scalar(text('SELECT count(*) FROM curriculum_topics WHERE document_id=:id'), {'id': DOCUMENT}) == 8
            assert conn.scalar(text('SELECT count(*) FROM curriculum_topics')) == others + 8
            assert conn.scalar(text("SELECT outcome FROM attempts WHERE id='attempt'")) == 'correct'
            assert conn.scalar(text("SELECT active_seconds FROM learning_units WHERE id='unit'")) == 300
        result = subprocess.run([*command, 'downgrade', '0065'], env=env, capture_output=True, timeout=90, check=False)
        assert result.returncode != 0
        assert b'Published curriculum evidence requires a forward correction' in result.stderr
    finally:
        if schema:
            with test_engine.begin() as conn:
                conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        else:
            engine.dispose()
