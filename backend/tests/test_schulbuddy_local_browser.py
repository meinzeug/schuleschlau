"""Browser-to-worker check using only synthetic content and a mocked provider."""
import json
import os
import secrets
import shutil
import socket
import subprocess
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest
import uvicorn
from conftest import HEADERS, register
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient
from schulpilot import main, worker
from schulpilot.config import settings
from schulpilot.db import DB, Attempt, Job, Mastery, SchulbuddyTurn
from schulpilot.main import app
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from test_schulbuddy import book as book
from test_schulbuddy import transport as transport


@pytest.fixture(autouse=True)
def restore_synthetic_settings():
    names = ('codex_approved', 'codex_socket', 'codex_auth_mode', 'synthetic_ai_enabled')
    previous = {name: getattr(settings, name) for name in names}
    yield
    for name, value in previous.items():
        object.__setattr__(settings, name, value)


@pytest.mark.skipif(os.getenv('SCHULBUDDY_LOCAL_BROWSER') != '1', reason='Requires isolated browser opt-in')
def test_schulbuddy_source_and_saved_reply_in_mobile_browser(book, transport, mailbox, monkeypatch, tmp_path):
    if os.getenv('SCHULBUDDY_LOCAL_BROWSER') != '1':
        pytest.skip('Set SCHULBUDDY_LOCAL_BROWSER=1 for the isolated browser test')
    if os.getenv('TEST_DATABASE_URL') or settings.environment != 'test' or make_url(settings.database_url).get_backend_name() != 'sqlite':
        pytest.fail('An isolated SQLite database is required')
    if not settings.web_dir or not (Path(settings.web_dir) / 'main.dart.js').is_file():
        pytest.fail('A local Flutter web build is required')
    token = secrets.token_urlsafe(32)

    def run_job(req: Request):
        if req.client.host != '127.0.0.1' or req.headers.get('X-QA-Token') != token:
            raise HTTPException(403)
        with DB() as db:
            job_id = worker.claim(db)
        if not job_id:
            raise HTTPException(409)
        worker.process(job_id)
        with DB() as db:
            job = db.get(Job, job_id)
            return {'status': job.status}

    routes = list(app.router.routes)
    app.add_api_route('/__buddy_test__/work', run_job, methods=['POST'], include_in_schema=False)
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
        data = {'base': f'http://127.0.0.1:{port}', 'token': token, 'material': book['material_id'], 'screens': str(tmp_path)}
        result = subprocess.run([node, 'qa/schulbuddy_local_browser.mjs'], input=json.dumps(data), text=True,
            capture_output=True, timeout=240, env={'PATH': str(Path(node).parent) + ':/usr/bin:/bin',
                'LANG': 'C.UTF-8', 'TMPDIR': os.environ.get('TMPDIR', '/tmp')})
        assert result.returncode == 0, result.stderr[-4000:]
        assert json.loads(result.stdout)['passed'] is True
        assert len(transport['calls']) == 1
        with DB() as db:
            turn = db.scalar(select(SchulbuddyTurn))
            assert turn.status == 'ready' and turn.reply['answer'] == 'Die Sonne ist ein Stern.'
            turn_id = turn.id
            assert db.scalar(select(func.count()).select_from(Job)) == 1
            assert db.scalar(select(func.count()).select_from(Attempt)) == 0
            assert db.scalar(select(func.count()).select_from(Mastery)) == 0
        with TestClient(app, headers=HEADERS) as other:
            register(other, mailbox, 'foreign-buddy-parent@example.org')
            assert other.get('/api/schulbuddy/questions/' + turn_id).status_code == 404
    finally:
        server.should_exit = True
        thread.join(timeout=15)
        sock.close()
        app.router.routes[:] = routes
        assert not thread.is_alive()


def test_schulbuddy_browser_rejects_external_database_before_import():
    import sys

    env = {**os.environ, 'PYTHONPATH': 'backend/tests:backend', 'SCHULBUDDY_LOCAL_BROWSER': '1',
           'TEST_DATABASE_URL': 'postgresql+psycopg://fixture@127.0.0.1/schulpilot_test'}
    result = subprocess.run([sys.executable, '-c', 'import conftest'], env=env, text=True,
                            capture_output=True, timeout=10)
    assert result.returncode != 0
    assert 'require an automatically isolated SQLite database' in result.stderr
