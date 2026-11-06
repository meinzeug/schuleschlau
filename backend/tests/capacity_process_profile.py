"""Private synthetic multi-process loopback capacity profile (not regular CI).

Run only via scripts/test_postgres.py; no external provider is ever called.
"""
import io
import json
import os
import random
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from capacity_worker_profile import percentile, require_private_profile_database, rss_kib
from conftest import HEADERS, create_child, register
from fastapi.testclient import TestClient
from PIL import Image
from schulpilot.db import DB, Job, Material, Usage, engine
from schulpilot.main import app
from sqlalchemy import func, select
from test_school_day import allow_synthetic_test_transport

require_private_profile_database()


def wait_ready(path, process):
    until = time.monotonic() + 30
    while time.monotonic() < until:
        if process.poll() is not None:
            raise AssertionError(f'Isolated process exited before ready: {process.returncode}')
        if path.exists():
            return int(path.read_text())
        time.sleep(.05)
    raise AssertionError('Isolated process did not become ready')


def test_bounded_process_capacity(api, household, mailbox):
    assert engine.dialect.name == 'postgresql'
    allow_synthetic_test_transport()
    families = int(os.getenv("CAPACITY_FAMILIES", "4")) if os.getenv("CAPACITY_LARGE") == "1" else 8
    assert (1 <= families <= 4 if os.getenv("CAPACITY_LARGE") == "1" else families == 8)
    _, child = household
    accounts = [(api.headers['Authorization'], child['id'])]
    for i in range(1, families):
        with TestClient(app, headers=HEADERS, client=(f'198.18.1.{i + 1}', 50000)) as client:
            parent = register(client, mailbox, email=f'process-load-{i}@example.org')
            other = create_child(client, parent, username=f'process-load-child-{i}')
            accounts.append((client.headers['Authorization'], other['id']))

    dimensions, quality = ((3990, 3990), 65) if os.getenv("CAPACITY_LARGE") == "1" else ((1800, 1200), 90)
    pixels = random.Random(5519).randbytes(dimensions[0] * dimensions[1] * 3)
    output = io.BytesIO()
    Image.frombytes('RGB', dimensions, pixels).save(output, format='JPEG', quality=quality)
    image = output.getvalue()
    del pixels
    assert len(image) > 234000
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    port = listener.getsockname()[1]
    listener.close()
    results = []
    with tempfile.TemporaryDirectory(prefix='schulpilot-capacity-process-') as directory:
        root = Path(directory)
        helper = str(Path(__file__).with_name('capacity_process_service.py').resolve())
        processes = []
        stop_sampling = threading.Event()
        cgroups = {}
        def sample_cgroups():
            while not stop_sampling.wait(.02):
                for role, entry in list(cgroups.items()):
                    try:
                        entry['memory_peak'] = int((entry['path'] / 'memory.peak').read_text())
                        entry['events'] = (entry['path'] / 'memory.events').read_text().strip().replace('\n', ',')
                    except OSError:
                        pass
        sampler = threading.Thread(target=sample_cgroups, daemon=True)
        sampler.start()
        def track(role, pid):
            cgroup = Path(f'/proc/{pid}/cgroup').read_text().strip().split(':', 2)[2]
            cgroups[role] = {'path': Path('/sys/fs/cgroup') / cgroup.lstrip('/'), 'memory_peak': 0, 'events': ''}
        try:
            def start(role, memory, *args):
                log = (root / (role + '.log')).open('w+')
                cmd = ['systemd-run', '--user', '--quiet', '--scope', '-p', 'MemoryMax=' + memory,
                       '-p', 'TasksMax=64', sys.executable, helper, role, str(root), str(port), *args]
                proc = subprocess.Popen(cmd, stdout=log, stderr=log, start_new_session=True)
                processes.append((proc, log))
                return proc

            api_process = start('api', '350M')
            api_pid = wait_ready(root / 'api.ready', api_process)
            track('api', api_pid)
            assert int((cgroups['api']['path'] / 'memory.max').read_text()) == 350 * 1024 * 1024
            base = f'http://127.0.0.1:{port}'
            samples = {'api_rss': [], 'worker_rss': [], 'queue': []}

            def batch(label, tasks, parallel):
                def one(task):
                    i, method, path, kwargs = task
                    with httpx.Client(base_url=base, headers={**HEADERS, 'Authorization': accounts[i][0]},
                                      trust_env=False, timeout=60) as client:
                        start_time = time.perf_counter()
                        overloads = 0
                        while True:
                            response = client.request(method, path, **kwargs)
                            if response.status_code != 503 or response.headers.get('retry-after') != '2':
                                break
                            overloads += 1
                            assert overloads <= 15, 'Synthetic explicit retries exhausted'
                            time.sleep(.75)
                        return response.status_code, response.json(), (time.perf_counter() - start_time) * 1000, overloads
                start_time = time.perf_counter()
                with ThreadPoolExecutor(max_workers=parallel) as pool:
                    result = list(pool.map(one, tasks))
                measure = {'stage': label, 'parallel': parallel, 'requests': len(result),
                           'elapsed_s': round(time.perf_counter() - start_time, 3),
                           'p95_ms': percentile([row[2] for row in result]),
                           'statuses': dict(Counter(str(row[0]) for row in result)),
                           'explicit_overload_retries': sum(row[3] for row in result)}
                print('\nCAPACITY_PROCESS_STAGE=' + json.dumps(measure, sort_keys=True), flush=True)
                results.append(measure)
                samples['api_rss'].append(rss_kib(api_pid))
                return result

            for parallel in (1, 4, families):
                tasks = [(i % families, 'GET', f'/api/children/{accounts[i % families][1]}/overview', {})
                         for i in range(4 * families)]
                assert all(v[0] == 200 for v in batch('overview', tasks, parallel))
            uploads = [(i, 'POST', f'/api/children/{cid}/materials', {
                'files': {'file': ('synthetic.jpg', image, 'image/jpeg')},
                'headers': {'Idempotency-Key': f'process-upload-{i:04d}'},
            }) for i, (_, cid) in enumerate(accounts) for _ in range(2)]
            concurrent_stop = threading.Event()
            concurrent_results = []
            def keep_reading():
                index = 0
                with httpx.Client(base_url=base, trust_env=False, timeout=30, headers=HEADERS) as client:
                    while not concurrent_stop.is_set():
                        token, cid = accounts[index % families]
                        try:
                            response = client.get(f'/api/children/{cid}/overview', headers={'Authorization': token})
                            concurrent_results.append(response.status_code)
                        except httpx.HTTPError:
                            concurrent_results.append(0)
                        index += 1
            concurrent_reader = threading.Thread(target=keep_reading, daemon=True)
            concurrent_reader.start()
            try:
                responses = batch('upload-replay', uploads, families)
            finally:
                concurrent_stop.set()
                concurrent_reader.join(timeout=30)
            assert not concurrent_reader.is_alive() and concurrent_results and all(v == 200 for v in concurrent_results)
            print('CAPACITY_CONCURRENT_GETS=' + json.dumps({'count': len(concurrent_results), 'statuses': dict(Counter(concurrent_results))}), flush=True)
            assert all(r[0] == 201 for r in responses)
            materials = [responses[2 * i][1]['id'] for i in range(families)]
            assert all(responses[2 * i + 1][1]['id'] == materials[i] for i in range(families))
            jobs = [(i, 'POST', f'/api/materials/{material}/extract', {
                'headers': {'Idempotency-Key': f'process-extract-{i:04d}'},
            }) for i, material in enumerate(materials) for _ in range(2)]
            responses = batch('reservation-replay', jobs, families)
            assert all(r[0] == 202 for r in responses)
            ids = [responses[2 * i][1]['id'] for i in range(families)]
            assert len(set(ids)) == families and all(responses[2 * i + 1][1]['id'] == ids[i] for i in range(families))
            with DB() as db:
                assert db.scalar(select(func.count()).select_from(Job).where(Job.status == 'queued')) == families
            worker_started = time.perf_counter()
            worker = start('worker', '300M', str(families))
            worker_pid = wait_ready(root / 'worker.ready', worker)
            track('worker', worker_pid)
            assert int((cgroups['worker']['path'] / 'memory.max').read_text()) == 300 * 1024 * 1024
            mixed = [(i, 'GET', f'/api/children/{cid}/overview', {}) for i, (_, cid) in enumerate(accounts)]
            mixed += [(i, 'GET', f'/api/children/{cid}/materials?page=1&page_size=20', {})
                      for i, (_, cid) in enumerate(accounts)]
            mixed += jobs[::2]
            responses = batch('mixed-with-worker', mixed, families)
            assert all(row[0] == (202 if task[1] == 'POST' else 200)
                       for task, row in zip(mixed, responses, strict=True))
            while worker.poll() is None and time.perf_counter() - worker_started < 90:
                samples['api_rss'].append(rss_kib(api_pid))
                samples['worker_rss'].append(rss_kib(worker_pid))
                with DB() as db:
                    samples['queue'].append(db.scalar(select(func.count()).select_from(Job).where(Job.status == 'queued')))
                time.sleep(.5)
            assert worker.wait(timeout=3) == 0
            with DB() as db:
                states = list(db.scalars(select(Job.status)))
                assert states.count('completed') == families and len(states) == families
                assert db.scalar(select(func.sum(Job.attempts))) == families
                assert db.scalar(select(func.count()).select_from(Material)) == families
                assert db.scalar(select(func.count()).select_from(Usage)) == families
            report = {'families': families, 'cpu_affinity': sorted(os.sched_getaffinity(0)),
                      'provider_delay_s': 2, 'external_calls': 0, 'image_bytes': len(image),
                      'worker_s': round(time.perf_counter() - worker_started, 3), 'stages': results,
                      'sampled_max_rss_kib': {k: max(samples[k], default=0) for k in ('api_rss', 'worker_rss')},
                      'queue_max_sampled': max(samples['queue'], default=0), 'completed': families}
            print('\nCAPACITY_PROCESSES=' + json.dumps(report, sort_keys=True), flush=True)
        finally:
            stop_sampling.set()
            sampler.join(timeout=5)
            print('CAPACITY_CGROUPS=' + json.dumps({role: {'memory_peak': v['memory_peak'], 'events': v['events']} for role, v in cgroups.items()}, sort_keys=True), flush=True)
            for process, log in reversed(processes):
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=5)
                log.seek(0)
                if process.returncode not in (0, -signal.SIGTERM, 143):
                    print('ISOLATED_PROCESS_ERROR=' + str(process.returncode) + ':' + log.read()[-4000:], flush=True)
                log.close()
