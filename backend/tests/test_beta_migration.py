"""Upgrade real preceding schema with preserved artificial account data."""
import os
import subprocess
import sys
from pathlib import Path


def test_upgrade_0049_to_0050_preserves_family_and_user(tmp_path):
    root = Path(__file__).resolve().parents[2]
    script = '''
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from schulpilot.db import DB, Family, User, engine
c = Config('backend/alembic.ini')
command.upgrade(c, '0049')
with DB.begin() as db:
    db.add(Family(id='a'*32, name='Artificial family'))
    db.add(User(id='b'*32, username='artificial@example.org', email='artificial@example.org',
                display_name='Artificial parent', password_hash='never-a-login', role='parent', verified=True))
command.upgrade(c, '0050')
command.upgrade(c, '0050')
with engine.connect() as db:
    assert db.execute(text("select name from families where id=:i"), {'i':'a'*32}).scalar_one() == 'Artificial family'
    assert db.execute(text('select count(*) from beta_applications')).scalar_one() == 0
    assert db.execute(text('select version_num from alembic_version')).scalar_one() == '0050'
assert {x['name'] for x in inspect(engine).get_columns('beta_applications')} == {
    'id','family_id','user_id','status','revision','created','approved_at','decided_at','decided_by'}
'''
    env = {**os.environ, "DATABASE_URL": "sqlite:///" + str(tmp_path / "beta-migration.sqlite"),
           "DATA_DIR": str(tmp_path / "data"), "TEST_DATABASE_URL": "", "PYTHONPATH": str(root / "backend")}
    result = subprocess.run([sys.executable, "-c", script], cwd=root, env=env,
                            capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
