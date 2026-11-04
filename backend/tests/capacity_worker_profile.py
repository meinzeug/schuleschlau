"""Bounded multi-family API and worker capacity probe on isolated PostgreSQL.

Run explicitly with scripts/test_postgres.py; never uses an external provider.
The test is intentionally outside regular CI discovery.
"""

import io
import json
import math
import os
import random
import resource
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from conftest import HEADERS, create_child, register
from fastapi.testclient import TestClient
from PIL import Image
from schulpilot import worker
from schulpilot.db import DB, Job, Material, Usage, engine
from schulpilot.main import app
from schulpilot.providers import Result
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from test_school_day import allow_synthetic_test_transport


def percentile(values):
    ordered = sorted(values)
    return round(ordered[math.ceil(len(ordered) * .95) - 1], 2)


def rss_kib(pid):
    try:
        for line in Path(f'/proc/{pid}/status').read_text().splitlines():
            if line.startswith('VmRSS:'):
                return int(line.split()[1])
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return 0
    return 0


def children(pid):
    try:
        return [int(value) for value in Path(f'/proc/{pid}/task/{pid}/children').read_text().split()]
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return []


def test_bounded_multi_family_worker_profile(api, household, mailbox, monkeypatch):
    assert engine.dialect.name == 'postgresql', 'Requires an isolated PostgreSQL test cluster'
    allow_synthetic_test_transport()
    _, child = household
    accounts = [(api.headers['Authorization'], child['id'])]
    for index in range(1, 8):
        with TestClient(app, headers=HEADERS, client=(f'198.18.0.{index + 1}', 50000)) as client:
            parent = register(client, mailbox, email=f'capacity-probe-{index}@example.org')
            other = create_child(client, parent, username=f'capacity-probe-child-{index}')
            accounts.append((client.headers['Authorization'], other['id']))

    pixels = random.Random(5519).randbytes(1800 * 1200 * 3)
    jpeg = io.BytesIO()
    Image.frombytes('RGB', (1800, 1200), pixels).save(jpeg, format='JPEG', quality=90)
    image = jpeg.getvalue()
    assert 234_000 < len(image) < 10 * 1024 * 1024
    del pixels

    provider_calls = []

    def fake_provider(config, function, payload, image_bytes=None, *, synthetic_fixture=False):
        assert function == 'extract' and image_bytes and not synthetic_fixture
        provider_calls.append(function)
        # Explicit synthetic service time; not a measurement of provider speed.
        time.sleep(.1)
        return Result({'subject': 'Mathematik', 'topic': 'Künstlicher Test',
                       'content': 'Künstlicher Seiteninhalt: 1 + 1 = 2.',
                       'uncertainties': [], 'homework': []}, 10, 20, 0)

    monkeypatch.setattr('schulpilot.worker.request_provider', fake_provider)
    socket = Path(make_url(os.environ['TEST_DATABASE_URL']).query['host'])
    pg_pid = int((socket.parent / 'database' / 'postmaster.pid').read_text().splitlines()[0])
    stop = threading.Event()
    memory = {'python_kib': 0, 'postgres_kib': 0, 'combined_kib': 0}

    def sample_memory():
        while not stop.is_set():
            app_rss = rss_kib(os.getpid())
            pg_rss = sum(rss_kib(pid) for pid in [pg_pid, *children(pg_pid)])
            memory['python_kib'] = max(memory['python_kib'], app_rss)
            memory['postgres_kib'] = max(memory['postgres_kib'], pg_rss)
            memory['combined_kib'] = max(memory['combined_kib'], app_rss + pg_rss)
            stop.wait(.25)

    sampler = threading.Thread(target=sample_memory, daemon=True)
    sampler.start()
    cpu_start = time.process_time()
    wall_start = time.perf_counter()
    profile = []
    try:
        def batch(label, tasks, concurrency):
            def one(task):
                index, method, path, kwargs = task
                token, _ = accounts[index]
                with TestClient(app, headers={**HEADERS, 'Authorization': token},
                                client=(f'198.18.0.{index + 1}', 50000)) as client:
                    started = time.perf_counter()
                    response = client.request(method, path, **kwargs)
                    return response.status_code, response.json(), (time.perf_counter() - started) * 1000

            start = time.perf_counter()
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                result = list(pool.map(one, tasks))
            profile.append({'operation': label, 'concurrency': concurrency, 'count': len(result),
                            'elapsed_s': round(time.perf_counter() - start, 3),
                            'p95_ms': percentile([v[2] for v in result]),
                            'status': dict(Counter(str(v[0]) for v in result))})
            return result

        for concurrency in (1, 4, 8):
            tasks = [(i % 8, 'GET', f'/api/children/{accounts[i % 8][1]}/overview', {})
                     for i in range(24)]
            assert all(item[0] == 200 for item in batch('overview', tasks, concurrency))

        uploads = [(i, 'POST', f'/api/children/{child_id}/materials', {
            'files': {'file': ('synthetic.jpg', image, 'image/jpeg')},
            'headers': {'Idempotency-Key': f'capacity-upload-{i:04d}'},
        }) for i, (_, child_id) in enumerate(accounts) for _ in range(2)]
        responses = batch('upload-replay', uploads, 8)
        assert all(item[0] == 201 for item in responses)
        material_ids = [responses[i * 2][1]['id'] for i in range(8)]
        assert all(responses[i * 2 + 1][1]['id'] == material_ids[i] for i in range(8))
        jobs = [(i, 'POST', f'/api/materials/{material_id}/extract', {
            'headers': {'Idempotency-Key': f'capacity-extract-{i:04d}'},
        }) for i, material_id in enumerate(material_ids) for _ in range(2)]
        responses = batch('reservation-replay', jobs, 8)
        assert all(item[0] == 202 for item in responses)
        job_ids = [responses[i * 2][1]['id'] for i in range(8)]
        assert all(responses[i * 2 + 1][1]['id'] == job_ids[i] for i in range(8))
        assert len(set(job_ids)) == 8
        with DB() as db:
            assert db.scalar(select(func.count()).select_from(Material)) == 8
            assert db.scalar(select(func.count()).select_from(Job).where(Job.status == 'queued')) == 8
            assert db.scalar(select(func.count()).select_from(Usage)) == 8
            oldest = db.scalar(select(func.min(Job.created)).where(Job.status == 'queued'))
        queue_age_before = max(0, int(time.time()) - oldest)

        # Separate connections compete for queued jobs using the real claim path.
        def claim_one(_):
            with DB() as db:
                return worker.claim(db)

        claim_started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=4) as pool:
            claimed = list(pool.map(claim_one, range(4)))
        assert len(set(claimed)) == 4 and all(item in job_ids for item in claimed)

        def drain_worker():
            for identifier in claimed:
                worker.process(identifier)
            while True:
                with DB() as db:
                    identifier = worker.claim(db)
                if identifier is None:
                    break
                worker.process(identifier)

        mixed = []
        for i, (_, child_id) in enumerate(accounts):
            mixed.append((i, 'GET', f'/api/children/{child_id}/overview', {}))
            mixed.append((i, 'GET', f'/api/children/{child_id}/materials?page=1&page_size=20', {}))
            if i < 4:
                mixed.append((i, 'POST', f'/api/children/{child_id}/materials', {
                    'files': {'file': ('synthetic.jpg', image, 'image/jpeg')},
                    'headers': {'Idempotency-Key': f'capacity-mixed-upload-{i:04d}'},
                }))
            else:
                mixed.append((i, 'POST', f'/api/materials/{material_ids[i]}/extract', {
                    'headers': {'Idempotency-Key': f'capacity-extract-{i:04d}'},
                }))
        # The real worker drains the queue while other independent sessions
        # concurrently read lists, upload, and repeat existing reservations.
        with ThreadPoolExecutor(max_workers=1) as executor:
            processing = executor.submit(drain_worker)
            mixed_results = batch('mixed-api-with-worker', mixed, 8)
            processing.result()
        for task, response in zip(mixed, mixed_results, strict=True):
            index, method, path, _ = task
            expected = 200 if method == 'GET' else (202 if path.endswith('/extract') else 201)
            assert response[0] == expected
            if expected == 202:
                assert response[1]['id'] == job_ids[index]
        worker_elapsed = time.perf_counter() - claim_started
        with DB() as db:
            states = list(db.scalars(select(Job.status)))
            assert states.count('completed') == 8 and len(states) == 8
            assert db.scalar(select(func.sum(Job.attempts))) == 8
            assert db.scalar(select(func.count()).select_from(Material)) == 12
            assert db.scalar(select(func.count()).select_from(Usage)) == 8
        assert len(provider_calls) == 8
        report = {'synthetic': True, 'database': 'isolated PostgreSQL', 'transport': 'in-process ASGI',
                  'families': 8, 'image_bytes': len(image), 'profile': profile,
                  'queue_initial': 8, 'queue_final': 0, 'queue_age_before_drain_s': queue_age_before,
                  'queue_age_drain_completed_s': max(0, int(time.time()) - oldest),
                  'contending_claimers': 4, 'unique_claims': 4, 'jobs_completed': 8,
                  'synthetic_provider_calls': len(provider_calls), 'external_provider_calls': 0,
                  'mock_provider_delay_s': .1, 'worker_elapsed_s': round(worker_elapsed, 3),
                  'total_wall_s': round(time.perf_counter() - wall_start, 3),
                  'python_cpu_s': round(time.process_time() - cpu_start, 3),
                  'python_maxrss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  'sampled_peak_rss_kib': memory}
        print('\nCAPACITY_WORKER=' + json.dumps(report, sort_keys=True))
    finally:
        stop.set()
        sampler.join(timeout=2)
