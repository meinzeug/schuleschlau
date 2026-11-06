"""Bounded multi-family API and worker capacity probe on isolated PostgreSQL.

Run explicitly with scripts/test_postgres.py; never uses an external provider.
The test is intentionally outside regular CI discovery.
"""

import io
import json
import math
import os
import queue
import random
import resource
import stat
import tempfile
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

from conftest import HEADERS, create_child, register
from fastapi.testclient import TestClient
import httpx
from PIL import Image
from schulpilot import worker
from schulpilot.db import DB, Job, Material, Usage, engine
from schulpilot.main import app
from schulpilot.providers import Result
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from test_school_day import allow_synthetic_test_transport


def require_private_profile_database():
    """Check at collection, before the shared fixture can drop any tables."""
    database_url = os.environ.get('TEST_DATABASE_URL')
    if not database_url:
        raise RuntimeError('Run this profile only through scripts/test_postgres.py')
    url = make_url(database_url)
    socket_dir = Path(url.query.get('host', ''))
    root = socket_dir.parent
    if (url.drivername != 'postgresql+psycopg' or url.database != 'schulpilot_isolated_test'
            or url.host is not None or str(url.query.get('port')) != '55440'
            or socket_dir.name != 'socket' or root.parent != Path(tempfile.gettempdir())
            or not root.name.startswith('schulpilot-isolated-pg-')
            or root.is_symlink() or socket_dir.is_symlink()):
        raise RuntimeError('Capacity profile requires the private local PostgreSQL runner')
    try:
        for path in (root, socket_dir):
            meta = path.stat()
            if not stat.S_ISDIR(meta.st_mode) or meta.st_uid != os.getuid() or stat.S_IMODE(meta.st_mode) != 0o700:
                raise RuntimeError('Capacity profile socket directory is not private')
        if not stat.S_ISSOCK((socket_dir / '.s.PGSQL.55440').stat().st_mode):
            raise RuntimeError('Capacity profile requires the runner socket')
    except FileNotFoundError as exc:
        raise RuntimeError('Capacity profile requires a running isolated PostgreSQL runner') from exc


require_private_profile_database()


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


def run_worker_profile(api, household, mailbox, monkeypatch, *, provider_delay, worker_threads,
                       families=8, network_base=None, gate_reservations=False):
    assert engine.dialect.name == 'postgresql', 'Requires an isolated PostgreSQL test cluster'
    assert 1 <= families <= 16 and 1 <= worker_threads <= min(4, families)
    if network_base is not None:
        target = urlparse(network_base)
        assert (target.scheme, target.hostname, target.path, target.query, target.fragment) == (
            'http', '127.0.0.1', '', '', '') and target.port and not target.username
    allow_synthetic_test_transport()
    _, child = household
    accounts = [(api.headers['Authorization'], child['id'])]
    for index in range(1, families):
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
    provider_lock = threading.Lock()
    provider_parallel = {'current': 0, 'maximum': 0}

    def fake_provider(config, function, payload, image_bytes=None, *, synthetic_fixture=False):
        assert function == 'extract' and image_bytes and not synthetic_fixture
        with provider_lock:
            provider_calls.append(function)
            provider_parallel['current'] += 1
            provider_parallel['maximum'] = max(provider_parallel['maximum'], provider_parallel['current'])
        try:
            # Explicit synthetic service time; not a measurement of provider speed.
            time.sleep(provider_delay)
        finally:
            with provider_lock:
                provider_parallel['current'] -= 1
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
                options = {'headers': {**HEADERS, 'Authorization': token}}
                client = (httpx.Client(base_url=network_base, trust_env=False, timeout=30, **options)
                          if network_base else TestClient(app, client=(f'198.18.0.{index + 1}', 50000), **options))
                with client:
                    started = time.perf_counter()
                    try:
                        response = client.request(method, path, **kwargs)
                    except httpx.HTTPError as error:
                        return 0, {'transport_error': type(error).__name__}, (time.perf_counter() - started) * 1000
                    return response.status_code, response.json(), (time.perf_counter() - started) * 1000

            start = time.perf_counter()
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                result = list(pool.map(one, tasks))
            profile.append({'operation': label, 'concurrency': concurrency, 'count': len(result),
                            'elapsed_s': round(time.perf_counter() - start, 3),
                            'p95_ms': percentile([v[2] for v in result]),
                            'status': dict(Counter(str(v[0]) for v in result)),
                            'transport_errors': dict(Counter(v[1]['transport_error'] for v in result if v[0] == 0))})
            if network_base:
                print('\nCAPACITY_STAGE=' + json.dumps(profile[-1], sort_keys=True), flush=True)
            return result

        for concurrency in ((1, 4, 8, 16) if families == 16 else (1, 4, 8)):
            tasks = [(i % families, 'GET', f'/api/children/{accounts[i % families][1]}/overview', {})
                     for i in range(3 * families)]
            assert all(item[0] == 200 for item in batch('overview', tasks, concurrency))

        uploads = [(i, 'POST', f'/api/children/{child_id}/materials', {
            'files': {'file': ('synthetic.jpg', image, 'image/jpeg')},
            'headers': {'Idempotency-Key': f'capacity-upload-{i:04d}'},
        }) for i, (_, child_id) in enumerate(accounts) for _ in range(2)]
        responses = batch('upload-replay', uploads, families)
        assert all(item[0] == 201 for item in responses)
        material_ids = [responses[i * 2][1]['id'] for i in range(families)]
        assert all(responses[i * 2 + 1][1]['id'] == material_ids[i] for i in range(families))
        jobs = [(i, 'POST', f'/api/materials/{material_id}/extract', {
            'headers': {'Idempotency-Key': f'capacity-extract-{i:04d}'},
        }) for i, material_id in enumerate(material_ids) for _ in range(2)]
        if gate_reservations:
            from schulpilot import providers

            assert network_base and families == 15
            # Match SQLAlchemy's default 5 + 10 pool size. Each request has its
            # own already-open transaction and waits only in this synthetic
            # barrier before the real provider safety/reservation path.
            gate = threading.Barrier(families, timeout=15)
            original = providers.external_allowed

            def gated_provider_check(*args, **kwargs):
                gate.wait()
                return original(*args, **kwargs)

            monkeypatch.setattr(providers, 'external_allowed', gated_provider_check)
            monkeypatch.setattr(engine.pool, '_timeout', 2)
            try:
                gated = batch('saturated-pool-reservations', jobs[::2], families)
            finally:
                monkeypatch.setattr(providers, 'external_allowed', original)
            assert all(item[0] == 202 for item in gated)
        responses = batch('reservation-replay', jobs, families)
        assert all(item[0] == 202 for item in responses)
        job_ids = [responses[i * 2][1]['id'] for i in range(families)]
        assert all(responses[i * 2 + 1][1]['id'] == job_ids[i] for i in range(families))
        assert len(set(job_ids)) == families
        with DB() as db:
            assert db.scalar(select(func.count()).select_from(Material)) == families
            assert db.scalar(select(func.count()).select_from(Job).where(Job.status == 'queued')) == families
            assert db.scalar(select(func.count()).select_from(Usage)) == families
            oldest = db.scalar(select(func.min(Job.created)).where(Job.status == 'queued'))
        queue_age_before = max(0, int(time.time()) - oldest)

        # Separate connections compete for queued jobs using the real claim path.
        def claim_one(_):
            with DB() as db:
                return worker.claim(db)

        claim_started = time.perf_counter()
        claim_workers = 4 if worker_threads == 1 else worker_threads
        with ThreadPoolExecutor(max_workers=claim_workers) as pool:
            claimed = list(pool.map(claim_one, range(claim_workers)))
        assert len(set(claimed)) == claim_workers and all(item in job_ids for item in claimed)

        preclaimed = queue.Queue()
        for identifier in claimed:
            preclaimed.put(identifier)

        queue_stop = threading.Event()
        queue_samples = []
        queue_errors = []

        def sample_queue():
            try:
                while not queue_stop.is_set():
                    with DB() as db:
                        queued = db.scalar(select(func.count()).select_from(Job).where(Job.status == 'queued'))
                        running = db.scalar(select(func.count()).select_from(Job).where(Job.status == 'running'))
                        oldest_queued = db.scalar(select(func.min(Job.created)).where(Job.status == 'queued'))
                    queue_samples.append({
                        'queued': queued,
                        'running': running,
                        'oldest_queued_s': max(0, int(time.time()) - oldest_queued) if oldest_queued else 0,
                    })
                    queue_stop.wait(.5)
            except Exception as exc:
                queue_errors.append(type(exc).__name__)

        def drain_worker():
            while True:
                try:
                    identifier = preclaimed.get_nowait()
                except queue.Empty:
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
        queue_sampler = threading.Thread(target=sample_queue, daemon=True)
        queue_sampler.start()
        try:
            with ThreadPoolExecutor(max_workers=worker_threads) as executor:
                processing = [executor.submit(drain_worker) for _ in range(worker_threads)]
                mixed_results = batch('mixed-api-with-worker', mixed, families)
                for process in processing:
                    process.result()
        finally:
            queue_stop.set()
            queue_sampler.join(timeout=5)
        assert not queue_sampler.is_alive() and not queue_errors and queue_samples
        for task, response in zip(mixed, mixed_results, strict=True):
            index, method, path, _ = task
            expected = 200 if method == 'GET' else (202 if path.endswith('/extract') else 201)
            assert response[0] == expected
            if expected == 202:
                assert response[1]['id'] == job_ids[index]
        worker_elapsed = time.perf_counter() - claim_started
        with DB() as db:
            states = list(db.scalars(select(Job.status)))
            assert states.count('completed') == families and len(states) == families
            assert db.scalar(select(func.sum(Job.attempts))) == families
            assert db.scalar(select(func.count()).select_from(Material)) == families + min(families, 4)
            assert db.scalar(select(func.count()).select_from(Usage)) == families
        assert len(provider_calls) == families
        assert provider_parallel['current'] == 0 and provider_parallel['maximum'] == worker_threads
        report = {'synthetic': True, 'database': 'isolated PostgreSQL',
                  'transport': 'localhost TCP HTTP' if network_base else 'in-process ASGI',
                  'families': families, 'image_bytes': len(image), 'profile': profile,
                  'queue_initial': families, 'queue_final': 0, 'queue_age_before_drain_s': queue_age_before,
                  'queue_age_drain_completed_s': max(0, int(time.time()) - oldest),
                  'queue_sample_count': len(queue_samples),
                  'queue_sampled_max_queued': max(item['queued'] for item in queue_samples),
                  'queue_sampled_max_running': max(item['running'] for item in queue_samples),
                  'queue_sampled_max_queued_age_s': max(item['oldest_queued_s'] for item in queue_samples),
                  'contending_claimers': claim_workers, 'unique_claims': len(set(claimed)), 'jobs_completed': families,
                  'synthetic_provider_calls': len(provider_calls), 'external_provider_calls': 0,
                  'mock_provider_delay_s': provider_delay, 'worker_threads': worker_threads,
                  'mock_provider_max_parallel': provider_parallel['maximum'],
                  'worker_elapsed_s': round(worker_elapsed, 3),
                  'total_wall_s': round(time.perf_counter() - wall_start, 3),
                  'python_cpu_s': round(time.process_time() - cpu_start, 3),
                  'python_maxrss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  'sampled_peak_rss_kib': memory}
        print('\nCAPACITY_WORKER=' + json.dumps(report, sort_keys=True))
    finally:
        stop.set()
        sampler.join(timeout=2)


def test_bounded_multi_family_worker_profile(api, household, mailbox, monkeypatch):
    run_worker_profile(api, household, mailbox, monkeypatch, provider_delay=.1, worker_threads=1)
