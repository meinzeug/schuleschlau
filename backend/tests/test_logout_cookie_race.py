"""Synthetic cross-tab HTTP cookie race against the real authentication API."""
import asyncio
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
from schulpilot import main
from schulpilot.config import settings
from schulpilot.db import DB, Child, User
from schulpilot.main import app
from schulpilot.security import password_hash


def test_isolated_logout_cookie_cannot_clear_a_new_web_login(household, tmp_path, monkeypatch):
    if os.getenv('LOGOUT_COOKIE_RACE_BROWSER') != '1':
        pytest.skip('Opt-in isolated Chrome cookie race')
    old, _ = household
    with DB.begin() as db:
        user = User(username='synthetic-new-parent', display_name='Synthetic parent', role='parent',
                    verified=True, password_hash=password_hash('secure-parent-pass-123'))
        db.add(user)
        db.flush()
        new_user_id = user.id
    pending, release = threading.Event(), threading.Event()

    async def isolated(scope, receive, send):
        if scope['type'] == 'http' and scope['path'] in ('/', '/__race/status', '/__race/release'):
            if scope['path'] == '/__race/release':
                release.set()
            body = json.dumps({'pending': pending.is_set()}).encode() if scope['path'] != '/' else b'<html></html>'
            await send({'type': 'http.response.start', 'status': 200, 'headers': [(b'content-type', b'application/json')]})
            await send({'type': 'http.response.body', 'body': body})
            return
        if scope['type'] == 'http' and scope['path'] == '/api/auth/logout' and not release.is_set():
            async def gate(message):
                if message['type'] == 'http.response.start':
                    pending.set()
                    if not await asyncio.to_thread(release.wait, 20):
                        raise RuntimeError('synthetic logout gate expired')
                await send(message)
            await app(scope, receive, gate)
            return
        await app(scope, receive, send)

    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    sock.listen(128)
    port = sock.getsockname()[1]
    monkeypatch.setattr(main, 'settings', replace(settings, public_url=f'http://127.0.0.1:{port}'))
    server = uvicorn.Server(uvicorn.Config(isolated, log_level='error', lifespan='off'))
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
        result = subprocess.run([node, 'qa/logout_cookie_race.mjs'], input=json.dumps({
            'base': f'http://127.0.0.1:{port}', 'old_user': old['id'], 'new_user': new_user_id,
            'screens': str(tmp_path),
        }), text=True, capture_output=True, timeout=90,
            env={'PATH': str(Path(node).parent) + ':/usr/bin:/bin', 'LANG': 'C.UTF-8'})
        assert result.returncode == 0, result.stderr[-4000:]
    finally:
        release.set()
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        assert not thread.is_alive()


def test_logout_browser_rejects_external_test_database_before_import():
    env = {'PATH': os.environ.get('PATH', ''), 'LANG': 'C.UTF-8', 'PYTHONPATH': 'backend/tests:backend',
           'LOGOUT_COOKIE_RACE_BROWSER': '1',
           'TEST_DATABASE_URL': 'postgresql+psycopg://fixture@127.0.0.1/schulpilot_test'}
    result = subprocess.run([sys.executable, '-c', 'import conftest'], env=env,
                            text=True, capture_output=True, timeout=10)
    assert result.returncode != 0
    assert 'require an automatically isolated SQLite database' in result.stderr


@pytest.mark.parametrize("username, password, identity", [
    ("parent@example.org", "secure-parent-pass-123", "parent"),
    ("test-child", "secure-child-pass-123", "child"),
])
def test_web_logout_revokes_retained_cookie_and_later_login_replaces_it(household, username, password, identity):
    from fastapi.testclient import TestClient

    parent, child = household
    with DB() as db:
        expected_id = parent["id"] if identity == "parent" else db.get(Child, child["id"]).user_id
    with TestClient(app, headers={'X-Schulpilot-Request': '1'}) as browser:
        credentials = {"username": username, "password": password}
        assert browser.post('/api/auth/login', json=credentials).status_code == 200
        assert browser.get('/api/auth/me').json()['id'] == expected_id
        response = browser.post('/api/auth/logout')
        assert response.status_code == 200
        assert not any(value.startswith('sp_session=') for value in response.headers.get_list('set-cookie'))
        assert browser.cookies.get('sp_session') is not None
        assert browser.get('/api/auth/me').status_code == 401
        assert browser.post('/api/auth/login', json=credentials).status_code == 200
        assert browser.get('/api/auth/me').json()['id'] == expected_id
