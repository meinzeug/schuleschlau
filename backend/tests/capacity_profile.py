"""Explicit, bounded artificial ASGI load profile; run via scripts/test_postgres.py.

Not collected by the normal CI test discovery. No provider or production access.
"""
import io
import json
import math
import resource
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from conftest import HEADERS
from fastapi.testclient import TestClient
from PIL import Image
from schulpilot.db import DB, Job, Material, Usage, engine
from schulpilot.main import app
from sqlalchemy import func, select
from test_school_day import allow_synthetic_test_transport


def percentile(values):
    values = sorted(values)
    return round(values[math.ceil(len(values) * 0.95) - 1], 2)


def test_artificial_capacity_profile(api, household, monkeypatch):
    """Exercise reads, image replays and one normally reserved queued request."""
    assert engine.dialect.name == "postgresql", "Use the isolated PostgreSQL test runner"
    _, child = household
    allow_synthetic_test_transport()

    def no_provider(*_args, **_kwargs):
        raise AssertionError("The capacity profile must not call any external provider")

    monkeypatch.setattr("schulpilot.worker.request_provider", no_provider)
    cpu_start = time.process_time()
    token = api.headers["Authorization"]
    headers = {**HEADERS, "Authorization": token}
    child_id = child["id"]
    jpeg = io.BytesIO()
    Image.new("RGB", (1200, 900), (224, 232, 238)).save(jpeg, format="JPEG", quality=90)
    image = jpeg.getvalue()

    def request(method, path, **kwargs):
        with TestClient(app, headers=headers) as client:
            start = time.perf_counter()
            response = client.request(method, path, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            return response.status_code, response.json(), elapsed

    def batch(workers, jobs):
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(lambda task: request(*task[0], **task[1]), jobs))
        return results, round(time.perf_counter() - started, 3)

    profile = []
    for parallel in (1, 4, 8):
        jobs = [(('GET', f'/api/children/{child_id}/overview'), {}) for _ in range(parallel * 3)]
        values, elapsed = batch(parallel, jobs)
        assert all(status == 200 for status, _, _ in values)
        profile.append({"operation": "overview", "parallel": parallel, "requests": len(values),
                        "elapsed_s": elapsed, "p95_ms": percentile([value[2] for value in values]),
                        "statuses": dict(Counter(str(value[0]) for value in values))})

    upload_key = 'capacity-synthetic-upload-00001'
    jobs = [(('POST', f'/api/children/{child_id}/materials'), {
        'files': {'file': ('artificial.jpg', image, 'image/jpeg')},
        'headers': {'Idempotency-Key': upload_key},
    }) for _ in range(4)]
    values, elapsed = batch(4, jobs)
    assert all(status == 201 for status, _, _ in values), [v[0] for v in values]
    assert len({value[1]['id'] for value in values}) == 1
    material_id = values[0][1]['id']
    profile.append({"operation": "upload-replay", "parallel": 4, "requests": len(values),
                    "elapsed_s": elapsed, "p95_ms": percentile([value[2] for value in values]),
                    "statuses": dict(Counter(str(value[0]) for value in values))})

    jobs = [(('POST', f'/api/materials/{material_id}/extract'), {
        'headers': {'Idempotency-Key': 'capacity-synthetic-extract-0001'},
    }) for _ in range(4)]
    values, elapsed = batch(4, jobs)
    assert all(status == 202 for status, _, _ in values), [v[0] for v in values]
    assert len({value[1]['id'] for value in values}) == 1
    profile.append({"operation": "reserve-replay", "parallel": 4, "requests": len(values),
                    "elapsed_s": elapsed, "p95_ms": percentile([value[2] for value in values]),
                    "statuses": dict(Counter(str(value[0]) for value in values))})
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Material).where(Material.id == material_id)) == 1
        assert db.scalar(select(func.count()).select_from(Job).where(Job.child_id == child_id)) == 1
        assert db.scalar(select(func.count()).select_from(Usage)) == 1
        queue = db.scalar(select(func.count()).select_from(Job).where(Job.status == 'queued'))
    report = {"synthetic": True, "transport": "in-process ASGI", "database": "isolated PostgreSQL",
              "image": {"width": 1200, "height": 900, "bytes": len(image)},
              "profile": profile, "queued_jobs": queue, "provider_calls": 0,
              "max_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              "process_cpu_s": round(time.process_time() - cpu_start, 3)}
    print('\nCAPACITY_PROFILE=' + json.dumps(report, sort_keys=True))


def test_artificial_multi_family_profile(api, household, mailbox, monkeypatch):
    """Three isolated families use realistic-sized artificial images; no workers run."""
    import random

    from conftest import create_child, register

    assert engine.dialect.name == "postgresql", "Use the isolated PostgreSQL test runner"
    allow_synthetic_test_transport()

    def no_provider(*_args, **_kwargs):
        raise AssertionError("The capacity profile must not call any external provider")

    monkeypatch.setattr("schulpilot.worker.request_provider", no_provider)
    _, child = household
    accounts = [(api.headers["Authorization"], child["id"])]
    for index in range(2):
        with TestClient(app, headers=HEADERS) as client:
            parent = register(client, mailbox, email=f"capacity-parent-{index}@example.org")
            other = create_child(client, parent, username=f"capacity-child-{index}")
            accounts.append((client.headers["Authorization"], other["id"]))
    random_pixels = random.Random(9174).randbytes(1800 * 1200 * 3)
    source = io.BytesIO()
    Image.frombytes("RGB", (1800, 1200), random_pixels).save(source, format="JPEG", quality=90)
    image = source.getvalue()
    assert 234_000 < len(image) < 10 * 1024 * 1024
    started_cpu = time.process_time()

    def one(index):
        token, child_id = accounts[index]
        durations = {}
        with TestClient(app, headers={**HEADERS, "Authorization": token}) as client:
            def call(name, method, path, **kwargs):
                start = time.perf_counter()
                response = client.request(method, path, **kwargs)
                durations[name] = round((time.perf_counter() - start) * 1000, 2)
                return response

            assert call('overview', 'GET', f'/api/children/{child_id}/overview').status_code == 200
            page = call('upload', 'POST', f'/api/children/{child_id}/materials',
                        files={'file': ('artificial.jpg', image, 'image/jpeg')},
                        headers={'Idempotency-Key': f'capacity-family-upload-{index:05d}'})
            assert page.status_code == 201, page.status_code
            job = call('reserve', 'POST', f"/api/materials/{page.json()['id']}/extract",
                       headers={'Idempotency-Key': f'capacity-family-extract-{index:05d}'})
            assert job.status_code == 202, job.status_code
        return durations

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(one, range(3)))
    elapsed = round(time.perf_counter() - started, 3)
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Job).where(Job.status == 'queued')) == 3
        assert db.scalar(select(func.count()).select_from(Usage)) == 3
    print('\nCAPACITY_MULTI=' + json.dumps({
        'synthetic': True, 'database': 'isolated PostgreSQL', 'transport': 'in-process ASGI',
        'families': 3, 'concurrent_clients': 3, 'image_bytes': len(image),
        'elapsed_s': elapsed, 'process_cpu_s': round(time.process_time() - started_cpu, 3),
        'max_process_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'p95_ms': {name: percentile([item[name] for item in results]) for name in ('overview', 'upload', 'reserve')},
        'queued_jobs': 3, 'reservations': 3, 'provider_calls': 0,
    }, sort_keys=True))
