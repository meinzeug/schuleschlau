"""The review migration is additive and preserves old public images."""
import os
import subprocess
import sys
from pathlib import Path


def test_upgrade_0050_to_0051_preserves_saved_images(tmp_path):
    root = Path(__file__).resolve().parents[2]
    script = '''
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from schulpilot.db import engine
c = Config('backend/alembic.ini')
command.upgrade(c, '0050')
with engine.begin() as db:
    db.execute(text("insert into public_images (cache_key, lookup_key, specification, format_version, model, upstream, region, png, png_sha256, width, height, factual_status, created) values (:key,:lookup,:spec,:fmt,:model,:upstream,:region,:png,:sha,:width,:height,:status,:created)"), dict(key='a'*64, lookup='b'*64, spec='{}', fmt='test', model='test/image', upstream='azure', region='standard', png=b'artificial', sha='c'*64, width=80, height=80, status='unassessed', created=1))
command.upgrade(c, '0051')
command.upgrade(c, '0051')
with engine.connect() as db:
    assert db.execute(text('select count(*) from public_images')).scalar_one() == 1
    assert db.execute(text('select count(*) from public_image_reviews')).scalar_one() == 0
    assert db.execute(text('select version_num from alembic_version')).scalar_one() == '0051'
assert {f['referred_table'] for f in inspect(engine).get_foreign_keys('public_image_reviews')} == {'jobs', 'public_images'}
'''
    environment = {**os.environ, 'DATABASE_URL': 'sqlite:///' + str(tmp_path / 'migration.sqlite'),
        'DATA_DIR': str(tmp_path / 'data'), 'TEST_DATABASE_URL': '', 'PYTHONPATH': str(root / 'backend')}
    result = subprocess.run([sys.executable, '-c', script], cwd=root, env=environment,
                            capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
