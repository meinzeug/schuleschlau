"""A real worker process may die; no provider traffic leaves this test."""

import json
import os
import select as io_select
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from schulpilot import school_preparation, worker
from schulpilot.config import settings
from schulpilot.db import DB, Attempt, Job, LearningUnit, SchoolDay, UnitSource, Usage, engine
from schulpilot.providers import Result
from sqlalchemy import func, select
from test_package_parts_worker import artificial_day, bounded_output, preparation, run_one, snapshot

# Start a fresh interpreter: do not fork a live SQLAlchemy pool or pytest's
# threaded HTTP client. The provider is replaced before the worker can call it.
CHILD = r'''
import json
import os
import sys
import time
from schulpilot import worker
from schulpilot.config import settings
from schulpilot.db import DB
from schulpilot.providers import Result
object.__setattr__(settings, 'real_data_approved', True)
object.__setattr__(settings, 'privacy_evidence', 'Isolated artificial transport test')
def blocked(config, function, payload, image_bytes=None, *, synthetic_fixture=False):
    if function != 'package':
        raise RuntimeError('Unexpected artificial job')
    if os.environ['TEST_WORKER_MODE'] == 'halt':
        if payload.get('package_partition') != 1:
            raise RuntimeError('Unexpected artificial partition')
        print('ENTERED:' + identifier, flush=True)
        time.sleep(120)
        raise RuntimeError('Artificial transport must be terminated')
    print('PAYLOAD:' + json.dumps({'job_id': identifier, 'payload': payload}), flush=True)
    return Result(json.loads(sys.stdin.readline()), 20, 40, 101, cost_source='reported')
worker.request_provider = blocked
with DB() as db:
    identifier = worker.claim(db)
if not identifier:
    raise RuntimeError('No isolated job to claim')
worker.process(identifier)
print('FINISHED', flush=True)
'''


@pytest.mark.skipif(engine.dialect.name != 'postgresql', reason='Requires isolated PostgreSQL for a real worker process')
def test_real_worker_kill_preserves_parts_and_requires_explicit_retry(api, household, monkeypatch, tmp_path):
    assert settings.environment == 'test'
    assert engine.url.database.endswith('_test')
    day_id, _, old = artificial_day(api, household)
    calls = []

    def provider(config, function, payload, image_bytes=None, *, synthetic_fixture=False):
        calls.append(payload['package_partition'])
        return Result(bounded_output(payload), 20, 40, 101, cost_source='reported')

    monkeypatch.setattr(worker, 'request_provider', provider)
    preparation(api, day_id, 'real-worker-stop-start')
    assert run_one() and calls == [0]
    first_receipt = snapshot(day_id)['package_outputs']['0']
    school_preparation.advance_one()
    with DB() as db:
        queued = list(db.scalars(select(Job).where(Job.status == 'queued')))
        assert len(queued) == 1 and queued[0].payload['package_partition'] == 1
        interrupted_id = queued[0].id

    # Keep the exact dedicated test DB, test key and private scratch directory;
    # no other environment, credentials or host integrations reach the child.
    env = {
        'PATH': '/usr/bin:/bin',
        'PYTHONPATH': str(Path(__file__).resolve().parents[1]),
        'DATABASE_URL': str(engine.url.render_as_string(hide_password=False)),
        'MASTER_KEY': os.environ['MASTER_KEY'],
        'ENVIRONMENT': 'test',
        'DATA_DIR': str(tmp_path / 'child-data'),
        'PUBLIC_URL': 'http://testserver',
        'LANG': 'C.UTF-8',
        'TEST_WORKER_MODE': 'halt',
    }
    child = subprocess.Popen(
        [sys.executable, '-u', '-c', CHILD], env=env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True,
    )
    try:
        assert child.stdout is not None
        ready, _, _ = io_select.select([child.stdout], [], [], 45)
        assert ready, 'Isolated worker did not reach the artificial transport in time'
        assert child.stdout.readline().strip() == f'ENTERED:{interrupted_id}'
        with DB() as db:
            job = db.get(Job, interrupted_id)
            assert job.status == 'running' and job.payload['package_partition'] == 1
        child.kill()
        assert child.wait(timeout=15) == -signal.SIGKILL
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=15)

    with DB.begin() as db:
        db.get(Job, interrupted_id).started = int(time.time()) - 1000
    worker.maintenance()
    school_preparation.advance_one()
    failed = api.get(f'/api/school-days/{day_id}').json()['preparation']
    assert failed['status'] == 'failed' and failed['error_code'] == 'interrupted'
    assert snapshot(day_id)['package_outputs']['0'] == first_receipt
    with DB() as db:
        stopped = db.get(Job, interrupted_id)
        usage = db.scalar(select(Usage).where(Usage.job_id == interrupted_id))
        assert stopped.status == 'failed' and stopped.result is None
        assert usage.status == 'failed_unknown' and usage.cost_micros is None
        assert usage.reserved_micros > 0 and usage.settlement_version == 1
        assert db.get(Attempt, old['attempt']).answer == 'Künstliche Altantwort'
        assert db.get(LearningUnit, old['unit']).active_seconds == 17
        before = db.scalar(select(func.count()).select_from(Job))
    for _ in range(3):
        assert run_one() is None
        assert api.get(f'/api/school-days/{day_id}').json()['preparation']['status'] == 'failed'
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Job)) == before
    assert calls == [0]
    preparation(api, day_id, 'real-worker-stop-explicit-retry')

    def run_fresh_worker(expected_partition):
        school_preparation.advance_one()
        fresh_env = {**env, 'TEST_WORKER_MODE': 'complete'}
        fresh = subprocess.Popen(
            [sys.executable, '-u', '-c', CHILD], env=fresh_env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            assert fresh.stdout is not None
            ready, _, _ = io_select.select([fresh.stdout], [], [], 45)
            assert ready, 'Fresh isolated worker did not reach the artificial transport'
            line = fresh.stdout.readline().strip()
            assert line.startswith('PAYLOAD:')
            item = json.loads(line.removeprefix('PAYLOAD:'))
            assert item['payload']['package_partition'] == expected_partition
            calls.append(expected_partition)
            out, _ = fresh.communicate(json.dumps(bounded_output(item['payload'])) + '\n', timeout=45)
            assert fresh.returncode == 0 and 'FINISHED' in out
            with DB() as db:
                assert db.get(Job, item['job_id']).status == 'completed'
        finally:
            if fresh.poll() is None:
                fresh.kill()
                fresh.communicate(timeout=15)
        school_preparation.advance_one()

    run_fresh_worker(1)
    run_fresh_worker(2)
    assert calls == [0, 1, 2]
    assert api.get(f'/api/school-days/{day_id}').json()['preparation']['status'] == 'ready'
    with DB() as db:
        assert db.get(Job, interrupted_id).status == 'failed'
        assert db.get(SchoolDay, day_id).preparation['status'] == 'ready'
        usage = db.scalar(select(Usage).where(Usage.job_id == interrupted_id))
        assert usage.status == 'failed_unknown' and usage.settlement_version == 1
        units = list(db.scalars(select(LearningUnit).where(LearningUnit.school_day_id == day_id)))
        assert len(units) == 3 and all(unit.status == 'not_started' for unit in units)
        sources = list(db.scalars(select(UnitSource).where(UnitSource.unit_id.in_([unit.id for unit in units]))))
        assert sorted((source.material_id, source.revision) for source in sources) == sorted(
            (source['id'], source['revision']) for source in old['sources']
        )
        assert db.scalar(select(func.count()).select_from(Attempt)) == 1
        assert db.get(Attempt, old['attempt']).answer == 'Künstliche Altantwort'
        assert db.get(LearningUnit, old['unit']).active_seconds == 17
