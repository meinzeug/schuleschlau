"""Actual 0044 -> 0046 migration on an isolated SQLite or PostgreSQL schema."""
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import make_url

SCRIPT = r'''
import sys
from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, Table, select
from schulpilot.db import DB, engine, Family, User, Child
config = Config('backend/alembic.ini')
command.upgrade(config, '0044')
with DB.begin() as db:
    db.add(Family(id='f'*32, name='Artificial family'))
    db.add(User(id='u'*32, username='artificial-child',display_name='Artificial child',password_hash='not-a-login',role='child',verified=True))
    db.flush()
    children=Table('children',MetaData(),autoload_with=db.connection())
    db.execute(children.insert().values(id='c'*32, family_id='f'*32,user_id='u'*32,grade=6,
        subjects=[],school_type='',region='',preferences={'daily_minutes': 35}))
    materials=Table('materials',MetaData(),autoload_with=db.connection())
    values={'id':'m'*32,'child_id':'c'*32,'title':'Original','status':'review',
            'subject':'Mathematik','topic':'Brüche','content':'Originaltext',
            'uncertainties':[],'homework':[],'confirmed':False,'synthetic':False,'created':1}
    db.execute(materials.insert().values(**values))
command.upgrade(config, 'head')
with engine.begin() as connection:
    row=connection.execute(select(Table('materials',MetaData(),autoload_with=connection))).mappings().one()
    assert row['content']=='Originaltext' and row['visual_observations']==[]
    child=connection.execute(select(Table('children',MetaData(),autoload_with=connection))).mappings().one()
    assert child['preferences']=={'daily_minutes': 35} and child['preferences_revision']==1
    assert connection.exec_driver_sql('select version_num from alembic_version').scalar_one()=='0047'
try:
    command.downgrade(config, '0046')
except RuntimeError as error:
    assert 'Preferences revision' in str(error)
else:
    raise AssertionError('unsafe preferences downgrade must fail closed')
with engine.connect() as connection:
    assert connection.exec_driver_sql('select version_num from alembic_version').scalar_one()=='0047'
sys.path.insert(0, 'deploy')
from visual_restore_probe import probe
with DB.begin() as db:
    probe(db, 'synthetic-test-key')
print('legacy material and preferences preserved, head 0047, signed replay verified')
'''


def test_0044_real_upgrade_preserves_old_material(tmp_path):
    original = os.environ.get('TEST_DATABASE_URL')
    schema = 'visual_migration_' + uuid4().hex
    if original:
        from schulpilot.db import engine
        with engine.begin() as connection:
            connection.execute(text('CREATE SCHEMA "' + schema + '"'))
        url = make_url(original).update_query_dict({'options': '-csearch_path=' + schema}).render_as_string(hide_password=False)
    else:
        url = 'sqlite:///' + str(tmp_path / 'migration.sqlite')
    root = Path(__file__).resolve().parents[2]
    pythonpath = os.pathsep.join(filter(None, (str(root / 'backend'), os.environ.get('PYTHONPATH'))))
    environment = {**os.environ, 'DATABASE_URL': url, 'DATA_DIR': str(tmp_path / 'data'),
                   'TEST_DATABASE_URL': '', 'PYTHONPATH': pythonpath}
    try:
        run = subprocess.run([sys.executable, '-c', SCRIPT], cwd=root, env=environment,
                             capture_output=True, text=True, timeout=90)
        assert run.returncode == 0, run.stdout + run.stderr
        assert 'head 0047' in run.stdout
    finally:
        if original:
            with engine.begin() as connection:
                connection.execute(text('DROP SCHEMA "' + schema + '" CASCADE'))
