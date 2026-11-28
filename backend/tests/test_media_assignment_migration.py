"""Upgrade existing editorial mappings without inventing their history."""
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import make_url

SCRIPT = r'''
from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, Table, select
from schulpilot.db import engine
config = Config('backend/alembic.ini')
command.upgrade(config, '0068')
with engine.begin() as db:
    meta = MetaData()
    topics = Table('curriculum_topics', meta, autoload_with=db)
    topic = db.execute(select(topics).order_by(topics.c.id).limit(1)).mappings().one()
    resources = Table('media_resources', meta, autoload_with=db)
    db.execute(resources.insert().values(id='a'*32, provider='youtube', provider_id='Abcdefgh_12',
        title='Synthetic public medium', channel='Synthetic', url='https://www.youtube.com/watch?v=Abcdefgh_12',
        checked_region='DE', duration_seconds=60, available=True, checked_at=1, revision=1, created=1))
    links = Table('media_curriculum_links', meta, autoload_with=db)
    db.execute(links.insert().values(resource_id='a'*32, topic_id=topic['id'], topic_digest=topic['digest'],
        level_kind='klasse', min_level=5, max_level=6))
    saved_topic = topic['id']
command.upgrade(config, 'head')
with engine.begin() as db:
    meta = MetaData()
    links = Table('media_curriculum_links', meta, autoload_with=db)
    link = db.execute(select(links)).mappings().one()
    assert link['topic_id'] == saved_topic and link['active'] is True and link['revision'] == 1
    assert link['min_level'] == 5 and link['max_level'] == 6
    events = Table('media_curriculum_link_events', meta, autoload_with=db)
    assert db.execute(select(events)).all() == []
try:
    command.downgrade(config, '0068')
except RuntimeError as error:
    assert 'forward correction' in str(error)
else:
    raise AssertionError('Editorial history must not be silently discarded')
print('legacy mapping preserved, no invented events, downgrade guarded')
'''


def test_legacy_mapping_migrates_without_invented_events(tmp_path):
    original = os.environ.get("TEST_DATABASE_URL")
    schema = "media_assignment_migration_" + uuid4().hex
    if original:
        from schulpilot.db import engine
        with engine.begin() as connection:
            connection.execute(text('CREATE SCHEMA "' + schema + '"'))
        url = make_url(original).update_query_dict({"options": "-csearch_path=" + schema}).render_as_string(hide_password=False)
    else:
        url = "sqlite:///" + str(tmp_path / "media-migration.sqlite")
    root = Path(__file__).resolve().parents[2]
    pythonpath = os.pathsep.join(filter(None, (str(root / "backend"), os.environ.get("PYTHONPATH"))))
    environment = {**os.environ, "DATABASE_URL": url, "DATA_DIR": str(tmp_path / "data"),
                   "TEST_DATABASE_URL": "", "PYTHONPATH": pythonpath}
    try:
        run = subprocess.run([sys.executable, "-c", SCRIPT], cwd=root, env=environment,
                             capture_output=True, text=True, timeout=180)
        assert run.returncode == 0, run.stdout + run.stderr
        assert "legacy mapping preserved" in run.stdout
    finally:
        if original:
            with engine.begin() as connection:
                connection.execute(text('DROP SCHEMA "' + schema + '" CASCADE'))
