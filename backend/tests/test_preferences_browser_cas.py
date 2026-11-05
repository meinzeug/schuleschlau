"""Optional real-browser preference conflict test against isolated synthetic SQLite."""
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest
import uvicorn
from conftest import HEADERS
from fastapi.testclient import TestClient
from schulpilot import main, providers
from schulpilot.config import settings
from schulpilot.db import DB, Assignment, Child, Job, Membership, PushDevice, Session, User
from schulpilot.main import app
from schulpilot.security import password_hash
from sqlalchemy import select


def test_real_browser_preferences_cas(api, household, monkeypatch, tmp_path):
    if os.getenv('PARENT_PREFS_CAS_BROWSER') != '1':
        pytest.skip('Requires opt-in and local Flutter Web release')
    assert settings.environment == 'test'
    assert settings.web_dir and (Path(settings.web_dir) / 'main.dart.js').is_file()
    parent, child = household
    family = parent['families'][0]['id']
    with DB.begin() as db:
        row = db.get(Child, child['id'])
        row.preferences = {**row.preferences, 'push_consent': True}
        second = User(username='synthetic-cas-parent', display_name='Synthetic parent', role='parent',
                      verified=True, password_hash=password_hash('secure-parent-pass-123'))
        db.add(second)
        db.flush()
        db.add(Membership(user_id=second.id, family_id=family, permission='manage'))
    with TestClient(app, headers=HEADERS) as kid:
        assert kid.post('/api/auth/login', json={'username': 'test-child', 'password': 'secure-child-pass-123'}).status_code == 200
    with DB.begin() as db:
        row = db.get(Child, child['id'])
        session = db.scalar(select(Session).where(Session.user_id == row.user_id))
        db.add(PushDevice(user_id=row.user_id, session_id=session.id, token_hash='e' * 64,
                          encrypted_token='synthetic-only', platform='web', timezone='Europe/Berlin',
                          quiet_start=0, quiet_end=0))
    calls = []
    monkeypatch.setattr(providers, 'request_provider', lambda *args, **kwargs: calls.append(True))
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    sock.listen(128)
    port = sock.getsockname()[1]
    monkeypatch.setattr(main, 'settings', replace(settings, public_url=f'http://127.0.0.1:{port}'))
    server = uvicorn.Server(uvicorn.Config(app, log_level='error', lifespan='off'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if server.started:
                break
            time.sleep(.05)
        assert server.started
        node = shutil.which('node')
        assert node is not None
        result = subprocess.run([node, 'qa/preferences_cas_browser.mjs'], input=json.dumps({
            'base': f'http://127.0.0.1:{port}', 'child': child['id'], 'family': family, 'screens': str(tmp_path),
            'first': 'parent@example.org', 'second': 'synthetic-cas-parent', 'password': 'secure-parent-pass-123',
        }), text=True, capture_output=True, timeout=240,
            env={'PATH': str(Path(node).parent) + ':/usr/bin:/bin', 'LANG': 'C.UTF-8'})
        assert result.returncode == 0, result.stderr[-4000:]
        with DB() as db:
            saved = db.get(Child, child['id'])
            assert saved.preferences['daily_minutes'] == 37
            assert saved.preferences['push_consent'] is False
            assert saved.preferences['repeat_topics'] == ['Mathematik: Künstliches Ziel']
            assert saved.preferences_revision == 2
            assert not db.scalar(select(PushDevice.id).where(PushDevice.user_id == saved.user_id))
            rows = list(db.scalars(select(Assignment).where(Assignment.child_id == saved.id)))
            assert len(rows) == 1 and rows[0].subject == 'Mathematik' and rows[0].topic == 'Künstliches Ziel'
            assert not list(db.scalars(select(Job)))
        assert calls == []
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        assert not thread.is_alive()


def test_browser_cas_refuses_external_test_database_before_import():
    environment = {**os.environ, 'PYTHONPATH': 'backend/tests:backend', 'PARENT_PREFS_CAS_BROWSER': '1',
                   'TEST_DATABASE_URL': 'postgresql+psycopg://fixture@127.0.0.1/schulpilot_test'}
    result = subprocess.run([sys.executable, '-c', 'import conftest'], env=environment,
                            text=True, capture_output=True, timeout=10)
    assert result.returncode != 0
    assert 'require an automatically isolated SQLite database' in result.stderr
