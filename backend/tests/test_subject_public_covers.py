"""Only the two public generic covers may be updated; private data stays put."""
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from schulpilot.db import DB
from schulpilot.db import engine as test_engine
from schulpilot.subject_registry import create_private_connection, resolve, seed_public_covers_v4
from sqlalchemy import create_engine, event, text


def test_seed_preserves_non_generic_and_private_covers(household):
    with DB.begin() as db:
        home, astro = resolve(db, 'Hauswirtschaft'), resolve(db, 'Astronomie')
        home.cover_key = 'mathematik'
        astro.cover_key = 'other'
        private = create_private_connection(db.connection(), 'Astronomie', household[0]['families'][0]['id'])
        db.flush()
        seed_public_covers_v4(db.connection())
        seed_public_covers_v4(db.connection())
        db.refresh(home)
        db.refresh(astro)
        assert home.cover_key == 'mathematik'
        assert astro.cover_key == 'astronomie'
        assert db.connection().scalar(text('SELECT cover_key FROM subjects WHERE id=:id'), {'id': private}) == 'other'


@pytest.mark.parametrize('dialect', ['sqlite', 'postgresql'])
def test_cover_migration_is_additive_and_keeps_private_subjects(tmp_path, dialect):
    schema = None
    if dialect == 'postgresql':
        if test_engine.dialect.name != 'postgresql':
            pytest.skip('Requires isolated PostgreSQL.')
        schema = 'cover_' + uuid.uuid4().hex
        with test_engine.begin() as con:
            con.execute(text(f'CREATE SCHEMA "{schema}"'))
        url, engine = os.environ['TEST_DATABASE_URL'], test_engine
    else:
        url = 'sqlite:///' + str(tmp_path / 'covers.sqlite')
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
        result = subprocess.run([*command, '0064'], env=env, capture_output=True)
        assert result.returncode == 0, result.stderr.decode(errors='replace')
        with engine.begin() as con:
            scope(con)
            con.execute(text("UPDATE subjects SET cover_key='other' WHERE key IN ('hauswirtschaft','astronomie') AND owner_family_id IS NULL"))
            con.execute(text("INSERT INTO families(id,name,synthetic,created,child_limit,call_limit,budget_micros,plan) VALUES('f','Synthetic',true,1,4,100,2000000,'Pilot')"))
            private = create_private_connection(con, 'Astronomie', 'f')
        for _ in range(2):
            result = subprocess.run([*command, '0065'], env=env, capture_output=True)
            assert result.returncode == 0, result.stderr.decode(errors='replace')
            with engine.begin() as con:
                scope(con)
                for key in ('hauswirtschaft', 'astronomie'):
                    assert con.scalar(text('SELECT cover_key FROM subjects WHERE key=:key AND owner_family_id IS NULL'), {'key': key}) == key
                assert con.scalar(text('SELECT cover_key FROM subjects WHERE id=:id'), {'id': private}) == 'other'
    finally:
        if schema:
            with test_engine.begin() as con:
                con.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        else:
            engine.dispose()
