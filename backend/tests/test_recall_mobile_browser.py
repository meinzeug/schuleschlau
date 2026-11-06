"""Optional local browser walk-through; only synthetic accounts and transport."""
import os
import secrets
import shutil
import socket
import subprocess
import threading
import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import uvicorn
from fastapi import HTTPException, Request
from schulpilot import auth, coaching, learning, main, security, study_authority, worker
from schulpilot import db as database
from schulpilot.config import settings
from schulpilot.db import DB, Assignment, Attempt, Child, Family, Job, LearningUnit, UnitCoaching, now
from schulpilot.main import app
from schulpilot.providers import Result
from sqlalchemy import event, select
from sqlalchemy.engine import make_url
from test_coaching import finish, process_next
from test_coaching import normal_unit as original_profile


@pytest.fixture
def profile(api, household):
    yield from original_profile.__wrapped__(api, household)


def test_synthetic_recall_journey_in_390px_browser(profile, monkeypatch, tmp_path, request):
    if os.environ.get('RECALL_MOBILE_BROWSER') != '1':
        pytest.skip('Set RECALL_MOBILE_BROWSER=1 for the isolated browser test')
    if os.environ.get('TEST_DATABASE_URL') or settings.environment != 'test' or make_url(settings.database_url).get_backend_name() != 'sqlite':
        pytest.fail('Requires an automatically isolated SQLite test database')
    if not settings.web_dir or not (Path(settings.web_dir) / 'main.dart.js').is_file():
        pytest.fail('WEB_DIR must point to a locally built Flutter web app')
    client, root_id, _, _, child = profile
    clock = [int(now())]
    start_monotonic = time.monotonic()
    def test_now():
        return clock[0] + int(time.monotonic() - start_monotonic)
    for module in (database, auth, security, study_authority):
        monkeypatch.setattr(module, 'now', test_now)
    monkeypatch.setattr(learning, 'now', test_now)
    monkeypatch.setattr(learning, 'local_day', lambda _: datetime.fromtimestamp(test_now(), timezone.utc).date())
    def stamp(_mapper, _connection, attempt):
        if attempt.created is None:
            attempt.created = test_now()
    event.listen(Attempt, 'before_insert', stamp)
    request.addfinalizer(lambda: event.remove(Attempt, 'before_insert', stamp))
    with DB.begin() as db:
        kid = db.get(Child, child['id'])
        kid.preferences = {**kid.preferences, 'timezone': 'UTC', 'weekdays': list(range(7)), 'daily_minutes': 20}
        family = db.get(Family, kid.family_id)
        family.call_limit, family.budget_micros = 100, 100_000_000
        parent_start = (datetime.fromtimestamp(test_now(), timezone.utc).date() + timedelta(days=60)).isoformat()
        assignment = Assignment(child_id=child['id'], kind='parent', subject='Englisch',
            topic='Künstlicher Elternauftrag', mandatory=True, scheduled_for=parent_start)
        db.add(assignment)
        db.flush()
        assignment_id = assignment.id

    def coach(_config, function, payload):
        assert function == 'coach' and payload['defer_practice'] is True
        with DB() as db:
            item = db.scalar(select(UnitCoaching).where(UnitCoaching.status == 'pending'))
            data = coaching.synthetic_report(db, db.get(LearningUnit, item.unit_id), payload['next_action'])
            data['next_unit'] = None
        return Result(data, 100, 100, 0)
    def unit(_config, function, payload, *_args, **_kwargs):
        assert function == 'unit' and payload['review'] is True
        with DB() as db:
            job = db.scalar(select(Job).where(Job.kind == 'unit', Job.status == 'running'))
            data = coaching.synthetic_report(db, db.get(LearningUnit, job.payload['review_of']), 'check')['next_unit']
        return Result(data, 100, 100, 0)
    monkeypatch.setattr(coaching, 'request_provider', coach)
    monkeypatch.setattr(worker, 'request_provider', unit)
    finish(client, root_id)
    process_next()
    assert client.get(f'/api/units/{root_id}').json()['coaching']['status'] == 'ready'

    token = secrets.token_urlsafe(32)
    def check(req):
        if req.client.host != '127.0.0.1' or req.headers.get('X-QA-Token') != token:
            raise HTTPException(403)
    def advance(req: Request):
        check(req)
        with DB() as db:
            state = coaching.progress(db, db.get(LearningUnit, root_id))
            if state['secure_observation']:
                return {'done': True, 'goals': state['successful_check_days']}
            due = state['next_review']
            assert due
        clock[0] = int(datetime.fromisoformat(due).replace(hour=12, tzinfo=timezone.utc).timestamp())
        return {'done': False, 'date': due}
    def run_job(req: Request):
        check(req)
        with DB() as db:
            job_id = worker.claim(db)
        if not job_id:
            raise HTTPException(409, 'No queued synthetic job')
        worker.process(job_id)
        with DB() as db:
            job = db.get(Job, job_id)
            return {'status': job.status, 'error': job.error, 'result': job.result, 'kind': job.kind}
    def answers(unit_id: str, req: Request):
        check(req)
        with DB() as db:
            row = db.get(LearningUnit, unit_id)
            if not row or row.child_id != child['id']:
                raise HTTPException(404)
            submitted = list(db.scalars(select(Attempt).where(Attempt.unit_id == unit_id)))
            return {'questions': [{'id': q['id'], 'answer': q['answer'],
                'attempts': [{'outcome': a.outcome, 'assisted': a.assisted} for a in submitted if a.question_id == q['id']]}
                for q in row.questions]}
    routes_before = list(app.router.routes)
    app.add_api_route('/__recall_test__/advance', advance, methods=['POST'], include_in_schema=False)
    app.add_api_route('/__recall_test__/work', run_job, methods=['POST'], include_in_schema=False)
    app.add_api_route('/__recall_test__/answers/{unit_id}', answers, methods=['POST'], include_in_schema=False)
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
        import json
        config = {'base': f'http://127.0.0.1:{port}', 'token': token, 'child': child['id'],
                  'screens': str(tmp_path)}
        node = shutil.which('node')
        assert node
        result = subprocess.run([node, 'qa/recall_mobile_browser.mjs'], input=json.dumps(config), text=True,
            capture_output=True, timeout=600, env={'PATH': str(Path(node).parent) + ':/usr/bin:/bin',
                'LANG': 'C.UTF-8', 'TMPDIR': os.environ.get('TMPDIR', '/tmp')})
        assert result.returncode == 0, result.stderr[-6000:]
        print(result.stdout, end='')
        with DB() as db:
            progress = coaching.progress(db, db.get(LearningUnit, root_id))
            assert progress['secure_observation']
            for goal in progress['learning_goals']:
                if goal['assessment_applicable']:
                    dates = [datetime.fromisoformat(day).date() for day in goal['successful_check_dates']]
                    assert len(set(dates)) >= 3 and (max(dates) - min(dates)).days >= 7
            assert db.get(Assignment, assignment_id).scheduled_for == parent_start
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        app.router.routes[:] = routes_before
        assert not thread.is_alive()


def test_recall_browser_rejects_external_database_before_import():
    import sys

    environment = {**os.environ, 'PYTHONPATH': 'backend/tests:backend', 'RECALL_MOBILE_BROWSER': '1',
                   'TEST_DATABASE_URL': 'postgresql+psycopg://fixture@127.0.0.1/schulpilot_test'}
    result = subprocess.run([sys.executable, '-c', 'import conftest'], env=environment, text=True,
        capture_output=True, timeout=10)
    assert result.returncode != 0
    assert 'require an automatically isolated SQLite database' in result.stderr
