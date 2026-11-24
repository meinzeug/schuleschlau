"""Two isolated browser sessions against the real inbox; no provider or push."""
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
from conftest import HEADERS, register
from fastapi.testclient import TestClient
from schulpilot import main
from schulpilot.config import settings
from schulpilot.db import DB, Job, Membership, Message, NotificationRead, PushDelivery, Usage, now
from schulpilot.main import app
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from test_round_ready_notifications import case as case
from test_round_ready_notifications import remember
from test_school_preparation import capture, step, submit

ROOT = Path(__file__).resolve().parents[2]


def test_browser_cross_device_notice_reads_and_round_link(api, case, household, mailbox, monkeypatch, tmp_path):
    if os.environ.get('NOTIFICATION_LOCAL_BROWSER') != '1':
        pytest.skip('Set NOTIFICATION_LOCAL_BROWSER=1 for an isolated browser test')
    if os.getenv('TEST_DATABASE_URL') or settings.environment != 'test' or make_url(settings.database_url).get_backend_name() != 'sqlite':
        pytest.fail('A fresh isolated SQLite database is required')
    if not settings.web_dir or not (Path(settings.web_dir) / 'main.dart.js').is_file():
        pytest.fail('WEB_DIR must name a local Flutter web build')
    owner, child = household
    assert remember(case)
    # The normal synthetic photo pipeline produces a separate review notice.
    day, provider_calls = capture(api, child, monkeypatch, 1)
    submit(api, day)
    assert step()
    assert api.get(f"/api/school-days/{day['id']}").json()['preparation']['status'] == 'needs_review'
    assert provider_calls == ['extract']
    with DB.begin() as db:
        for index in range(60):
            db.add(Message(id=f'{index + 1:032x}', child_id=child['id'], kind='help',
                           body='Artificial notification', created=int(now()) - index - 5))
    with TestClient(app, headers=HEADERS) as other:
        other_user = register(other, mailbox, 'other-notice-parent@example.org')
        with DB.begin() as db:
            db.add(Membership(user_id=other_user['id'], family_id=owner['families'][0]['id'], permission='view'))

    # A separate family cannot read either the notice or its destination.
    with TestClient(app, headers=HEADERS) as foreign:
        register(foreign, mailbox, 'foreign-notice-parent@example.org')
        assert foreign.get('/api/units/' + case['unit']).status_code == 404
        assert foreign.post('/api/notifications/inbox/read', json={'ids': ['message:' + f'{1:032x}']}).status_code == 404
        assert foreign.get('/api/notifications/inbox', params={'paginate': '1'}).json()['items'] == []

    before = api.get('/api/notifications/inbox', params={'paginate': '1'}).json()
    assert len(before['items']) == 50 and before['next_cursor']
    assert any(item['kind'] == 'round_ready' and item['route'] == '/unit/' + case['unit'] for item in before['items'])
    assert any(item['kind'] == 'preparation' and item['route'] == f"/after-school/{child['id']}?day={day['id']}"
               for item in before['items'])
    with DB() as db:
        jobs_before = db.scalar(select(func.count()).select_from(Job))
        usage_before = db.scalar(select(func.count()).select_from(Usage))
        assert db.scalar(select(func.count()).select_from(NotificationRead)) == 0
        assert db.scalar(select(func.count()).select_from(PushDelivery)) == 0
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
        result = subprocess.run([node, 'qa/notification_cross_device.mjs'],
            input=json.dumps({'base': f'http://127.0.0.1:{port}', 'unit': case['unit'], 'child': child['id'],
                              'day': day['id'], 'screens': str(tmp_path)}),
            text=True, capture_output=True, timeout=240,
            env={'PATH': str(Path(node).parent) + ':/usr/bin:/bin', 'LANG': 'C.UTF-8',
                 'TMPDIR': os.environ.get('TMPDIR', '/tmp')})
        assert result.returncode == 0, result.stderr[-4000:]
        observed = json.loads(result.stdout)
        assert observed['passed'] is True and observed['contexts'] == 4
        assert observed['childPreparation'] is True and observed['childRound'] is True
        assert provider_calls == ['extract']
        with DB() as db:
            assert db.scalar(select(func.count()).select_from(Job)) == jobs_before
            assert db.scalar(select(func.count()).select_from(Usage)) == usage_before
            assert db.scalar(select(func.count()).select_from(PushDelivery)) == 0
            assert db.scalar(select(func.count()).select_from(NotificationRead)) > 0
    finally:
        server.should_exit = True
        thread.join(timeout=15)
        sock.close()
        assert not thread.is_alive()


def test_notification_browser_rejects_external_database_before_import():
    import sys

    env = {**os.environ, 'PYTHONPATH': 'backend/tests:backend', 'NOTIFICATION_LOCAL_BROWSER': '1',
           'TEST_DATABASE_URL': 'postgresql+psycopg://fixture@127.0.0.1/schulpilot_test'}
    result = subprocess.run([sys.executable, '-c', 'import conftest'], env=env, text=True,
                            capture_output=True, timeout=10)
    assert result.returncode != 0
    assert 'require an automatically isolated SQLite database' in result.stderr
