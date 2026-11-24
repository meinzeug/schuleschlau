"""Synthetic cold-start links and logout in independent local browsers."""
import json
import os
import shutil
import socket
import subprocess
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest
import uvicorn
from schulpilot import auth, main
from schulpilot.config import settings
from schulpilot.db import DB, Token, User
from schulpilot.main import app
from schulpilot.security import digest, password_hash
from sqlalchemy import select
from sqlalchemy.engine import make_url


@pytest.mark.skipif(os.getenv('AUTH_LOCAL_BROWSER') != '1', reason='Requires isolated browser opt-in')
def test_cold_start_links_and_logout_in_two_web_sizes(household, monkeypatch, tmp_path):
    if os.getenv('TEST_DATABASE_URL') or settings.environment != 'test' or make_url(settings.database_url).get_backend_name() != 'sqlite':
        pytest.fail('An isolated SQLite database is required')
    if not settings.web_dir or not (Path(settings.web_dir) / 'main.dart.js').is_file():
        pytest.fail('A local Flutter web build is required')
    family_id = household[0]['families'][0]['id']
    tokens = {}
    with DB.begin() as db:
        for width in (390, 1280):
            entries = {}
            for route in ('verify', 'reset', 'invite'):
                if route == 'invite':
                    first = auth.new_token(db, 'invite', family_id=family_id, email=f'first-{width}@example.org', permission='view')
                    second = auth.new_token(db, 'invite', family_id=family_id, email=f'second-{width}@example.org', permission='view')
                else:
                    user = User(username=f'{route}-{width}@example.org', email=f'{route}-{width}@example.org',
                                display_name='Künstlicher Elternzugang', role='parent',
                                verified=route == 'reset', password_hash=password_hash('synthetic-password-123'))
                    db.add(user)
                    db.flush()
                    purpose = 'verify' if route == 'verify' else 'recovery'
                    first = auth.new_token(db, purpose, user_id=user.id)
                    second = auth.new_token(db, purpose, user_id=user.id)
                entries[route] = {'first': first, 'second': second}
            tokens[str(width)] = entries
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
        assert node
        data = {'base': f'http://127.0.0.1:{port}', 'tokens': tokens, 'screens': str(tmp_path)}
        result = subprocess.run([node, 'qa/auth_local_browser.mjs'], input=json.dumps(data), text=True,
            capture_output=True, timeout=300, env={'PATH': str(Path(node).parent) + ':/usr/bin:/bin',
                'LANG': 'C.UTF-8', 'TMPDIR': os.environ.get('TMPDIR', '/tmp')})
        assert result.returncode == 0, result.stderr[-1000:]
        assert json.loads(result.stdout)['passed'] is True
        with DB() as db:
            for entries in tokens.values():
                for item in entries.values():
                    row = db.scalar(select(Token).where(Token.digest == digest(item['second'])))
                    assert row and row.used
    finally:
        server.should_exit = True
        thread.join(timeout=15)
        sock.close()
        assert not thread.is_alive()


def test_auth_browser_rejects_external_database_before_import():
    import sys

    env = {**os.environ, 'PYTHONPATH': 'backend/tests:backend', 'AUTH_LOCAL_BROWSER': '1',
           'TEST_DATABASE_URL': 'postgresql+psycopg://fixture@127.0.0.1/schulpilot_test'}
    result = subprocess.run([sys.executable, '-c', 'import conftest'], env=env, text=True,
                            capture_output=True, timeout=10)
    assert result.returncode != 0
    assert 'require an automatically isolated SQLite database' in result.stderr
