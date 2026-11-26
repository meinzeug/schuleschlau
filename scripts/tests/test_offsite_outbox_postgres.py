"""Explicit isolated-PostgreSQL proof of the offsite outbox read."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import psycopg
import pytest
from cryptography.fernet import Fernet
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend/tests'))
sys.path.insert(0, str(ROOT / 'deploy'))
import capacity_guard  # noqa: E402
import restore_check  # noqa: E402


def test_actual_outbox_read_is_isolated_and_bounded(monkeypatch):
    url_text = os.environ.get('TEST_DATABASE_URL', '')
    if not url_text:
        pytest.skip('requires the isolated PostgreSQL runner')
    capacity_guard.require_private_profile_database()
    url = make_url(url_text)
    options = {'dbname': url.database, 'user': url.username, 'host': url.query['host'], 'port': url.query['port']}
    monkeypatch.setattr(restore_check, 'RUNTIME_ROOT', ROOT)
    monkeypatch.setattr(restore_check, 'runtime_command', lambda code: [sys.executable, '-c', code])
    config = {'DATABASE_URL': url_text, 'ENVIRONMENT': 'test', 'DATA_DIR': tempfile.gettempdir(),
              'MASTER_KEY': Fernet.generate_key().decode()}
    with psycopg.connect(**options, autocommit=True) as admin:
        admin.execute('CREATE TABLE erasure_requests (id varchar(32) PRIMARY KEY, published boolean NOT NULL)')
        try:
            assert restore_check.live_outbox_pending(config, timeout=10) is False
            admin.execute("INSERT INTO erasure_requests (id, published) VALUES ('synthetic', false)")
            assert restore_check.live_outbox_pending(config, timeout=10) is True
            admin.execute('UPDATE erasure_requests SET published = true')
            assert restore_check.live_outbox_pending(config, timeout=10) is False
            with psycopg.connect(**options) as blocker:
                blocker.execute('LOCK TABLE erasure_requests IN ACCESS EXCLUSIVE MODE')
                with pytest.raises(subprocess.CalledProcessError):
                    restore_check.live_outbox_pending(config, timeout=10)
            assert restore_check.live_outbox_pending(config, timeout=10) is False
        finally:
            admin.execute('DROP TABLE erasure_requests')
