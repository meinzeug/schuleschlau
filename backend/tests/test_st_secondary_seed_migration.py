"""The ST source addition must not alter prior student evidence."""
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from schulpilot.db import engine as test_engine
from sqlalchemy import create_engine, event, text


@pytest.mark.parametrize('dialect', ['sqlite', 'postgresql'])
def test_0052_adds_public_st_sources_once_without_changing_private_work(tmp_path, dialect):
    schema = None
    if dialect == 'postgresql':
        if test_engine.dialect.name != 'postgresql':
            pytest.skip('Requires isolated PostgreSQL runner.')
        schema = 'st_seed_' + uuid.uuid4().hex
        with test_engine.begin() as con:
            con.execute(text(f'CREATE SCHEMA "{schema}"'))
        url, engine = os.environ['TEST_DATABASE_URL'], test_engine
    else:
        url = 'sqlite:///' + str(tmp_path / 'st-upgrade.sqlite')
        engine = create_engine(url)
        @event.listens_for(engine, 'connect')
        def enable_fk(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
    config = Path(__file__).resolve().parents[1] / 'alembic.ini'
    env = {**os.environ, 'DATABASE_URL': url, 'ENVIRONMENT': 'test'}
    if schema:
        env['PGOPTIONS'] = f'-c search_path={schema}'
    def scope(con):
        if schema:
            con.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    command = [sys.executable, '-m', 'alembic', '-c', str(config), 'upgrade']
    try:
        first = subprocess.run([*command, '0051'], env=env, capture_output=True)
        assert first.returncode == 0, first.stderr.decode(errors='replace')
        ids = ('st-sek-biology-2019', 'de-st-sek-mathe-2019-v1', 'de-st-sek-deutsch-2019-v1',
               'de-st-sek-englisch-2019-v1', 'de-st-sek-geschichte-2019-v1')
        with engine.begin() as con:
            scope(con)
            # Simulate an existing installation created before these packages.
            for doc in ids:
                con.execute(text('DELETE FROM curriculum_documents WHERE id=:doc'), {'doc': doc})
            con.execute(text("INSERT INTO families(id,name,synthetic,created,child_limit,call_limit,budget_micros,plan) VALUES('f','Synthetic',true,1,4,100,2000000,'Pilot')"))
            con.execute(text("INSERT INTO users(id,username,display_name,password_hash,role,verified,disabled,created) VALUES('u','synthetic','Synthetic','SYNTHETIC-HASH','parent',true,false,1)"))
            con.execute(text("INSERT INTO children(id,family_id,user_id,grade,subjects,school_type,region,preferences) VALUES('c','f','u',6,'[]','','','{}')"))
            con.execute(text("INSERT INTO learning_units(id,child_id,subject,topic,explanation,questions,status,synthetic,provider,created,active_seconds) VALUES('unit','c','Mathematik','Test','Synthetic','[]','completed',true,'synthetic',1,300)"))
            con.execute(text("INSERT INTO attempts(id,unit_id,question_id,answer,outcome,assisted,created) VALUES('attempt','unit','q1','\"synthetic\"','correct',false,1)"))
        for _ in range(2):
            result = subprocess.run([*command, '0052'], env=env, capture_output=True)
            assert result.returncode == 0, result.stderr.decode(errors='replace')
            with engine.begin() as con:
                scope(con)
                assert con.scalar(text('SELECT version_num FROM alembic_version')) == '0052'
                assert con.scalar(text("SELECT count(*) FROM curriculum_documents WHERE id IN ('st-sek-biology-2019','de-st-sek-mathe-2019-v1','de-st-sek-deutsch-2019-v1','de-st-sek-englisch-2019-v1','de-st-sek-geschichte-2019-v1')")) == 5
                assert con.scalar(text("SELECT count(*) FROM curriculum_topics WHERE document_id IN ('st-sek-biology-2019','de-st-sek-mathe-2019-v1','de-st-sek-deutsch-2019-v1','de-st-sek-englisch-2019-v1','de-st-sek-geschichte-2019-v1')")) == 103
                assert con.scalar(text("SELECT outcome FROM attempts WHERE id='attempt'")) == 'correct'
                assert con.scalar(text("SELECT active_seconds FROM learning_units WHERE id='unit'")) == 300
    finally:
        if schema:
            with test_engine.begin() as con:
                con.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        else:
            engine.dispose()
