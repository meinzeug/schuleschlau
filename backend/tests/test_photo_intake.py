import asyncio
import socket
import threading
import time

import httpx
import pytest
import uvicorn
from fastapi import HTTPException
from schulpilot import main, materials
from schulpilot.db import DB, Material
from sqlalchemy import func, select
from starlette.responses import JSONResponse
from test_photo_isolation import fixture
from test_school_day import allow_synthetic_test_transport


def test_intake_requires_auth_before_slot_and_expires_slow_body(api, monkeypatch):
    def authorization(scope):
        if (b'x-test-authorized', b'yes') not in scope['headers']:
            raise HTTPException(401, 'Bitte erneut anmelden.')

    monkeypatch.setattr(main, 'authorize_photo_before_intake', authorization)
    monkeypatch.setattr(main, '_PHOTO_BODY_TIMEOUT', .12)
    monkeypatch.setattr(main, '_PHOTO_WAIT_TIMEOUT', .04)

    async def scenario():
        async def inner(scope, receive, send):
            try:
                while (await receive()).get('more_body'):
                    pass
                await JSONResponse({'ok': True})(scope, receive, send)
            except HTTPException as exc:
                await JSONResponse({'detail': exc.detail}, status_code=exc.status_code)(scope, receive, send)

        gate = main.PhotoIntakeLimit(inner)
        entered = asyncio.Event()
        async def slow_receive():
            entered.set()
            await asyncio.sleep(2)
            return {'type': 'http.request', 'body': b'', 'more_body': False}
        async def ready_receive():
            return {'type': 'http.request', 'body': b'', 'more_body': False}
        async def run(headers, receive):
            result = []
            async def send(message):
                result.append(message)
            scope = {'type': 'http', 'method': 'POST', 'path': '/api/children/synthetic/materials',
                     'headers': headers}
            await gate(scope, receive, send)
            return next(message['status'] for message in result if message['type'] == 'http.response.start')
        first = asyncio.create_task(run([(b'x-test-authorized', b'yes')], slow_receive))
        await entered.wait()
        assert await run([], ready_receive) == 401
        assert await run([(b'x-test-authorized', b'yes')], ready_receive) == 503
        assert await first == 408
        assert await run([(b'x-test-authorized', b'yes')], ready_receive) == 200

    asyncio.run(scenario())


def test_real_anonymous_upload_does_not_wait_for_busy_intake(api, monkeypatch):
    assert main._PHOTO_REQUEST_SLOT.acquire(blocking=False)
    api.headers.pop('Authorization', None)
    try:
        started = time.monotonic()
        response = api.post('/api/children/irrelevant/materials', files={'file': ('x.jpg', b'fake', 'image/jpeg')})
        assert response.status_code == 401
        assert time.monotonic() - started < 1.5
    finally:
        main._PHOTO_REQUEST_SLOT.release()


def test_real_client_disconnect_keeps_sync_guard_until_worker_finishes(api, household, monkeypatch):
    allow_synthetic_test_transport()
    _, child = household
    started, release = threading.Event(), threading.Event()
    original = materials.normalize_photo
    def slow_normalize(raw):
        started.set()
        assert release.wait(10)
        return original(raw)
    monkeypatch.setattr(materials, 'normalize_photo', slow_normalize)
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(main.app, log_level='error', access_log=False, lifespan='off'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(.05)
    assert server.started
    image = fixture('JPEG')
    boundary = 'synthetic-test-boundary'
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="synthetic.jpg"\r\n'
            'Content-Type: image/jpeg\r\n\r\n').encode() + image + f'\r\n--{boundary}--\r\n'.encode()
    path = f"/api/children/{child['id']}/materials"
    key = 'disconnect-synthetic-key-00001'
    headers = {'Authorization': api.headers['Authorization'], 'X-Schulpilot-Request': '1',
               'X-Client-Platform': 'native', 'Idempotency-Key': key}
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=5) as client:
            request = (f'POST {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n'
                       f'Content-Type: multipart/form-data; boundary={boundary}\r\n'
                       f'Content-Length: {len(body)}\r\n' + ''.join(f'{k}: {v}\r\n' for k, v in headers.items())
                       + '\r\n').encode() + body
            client.sendall(request)
            assert started.wait(5)
        with httpx.Client(base_url=f'http://127.0.0.1:{port}', headers=headers, trust_env=False, timeout=8) as client:
            second = client.post(path, files={'file': ('x.jpg', image, 'image/jpeg')})
            assert second.status_code == 503 and second.headers.get('retry-after') == '2'
        release.set()
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if materials._SYNC_PHOTO_SLOT.acquire(blocking=False):
                materials._SYNC_PHOTO_SLOT.release()
                break
            time.sleep(.05)
        else:
            pytest.fail('Disconnected synchronous upload did not release its slot')
        retry = api.post(path, files={'file': ('x.jpg', image, 'image/jpeg')}, headers={'Idempotency-Key': key})
        assert retry.status_code == 201
        with DB() as db:
            assert db.scalar(select(func.count()).select_from(Material)) == 1
    finally:
        release.set()
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
        assert not thread.is_alive()


def test_authorized_slow_socket_expires_and_other_account_cannot_block(api, household, monkeypatch):
    allow_synthetic_test_transport()
    _, child = household
    monkeypatch.setattr(main, '_PHOTO_BODY_TIMEOUT', .8)
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(main.app, log_level='error', access_log=False, lifespan='off'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(.05)
    assert server.started
    path = f"/api/children/{child['id']}/materials"
    boundary = 'synthetic-slow-body'
    headers = {'Authorization': api.headers['Authorization'], 'X-Schulpilot-Request': '1',
               'X-Client-Platform': 'native', 'Idempotency-Key': 'slow-photo-synthetic-key-01'}
    request = (f'POST {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n'
               f'Content-Type: multipart/form-data; boundary={boundary}\r\nContent-Length: 4096\r\n'
               + ''.join(f'{k}: {v}\r\n' for k, v in headers.items()) + '\r\n'
               + f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="x.jpg"\r\n\r\npartial').encode()
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=5) as client:
            client.settimeout(5)
            client.sendall(request)
            # Wait until the authorized upload owns the slot, without assuming
            # fixed scheduler timing. A competing anonymous request must fail
            # before waiting for that slot.
            until = time.monotonic() + .5
            while time.monotonic() < until:
                if not main._PHOTO_REQUEST_SLOT.acquire(blocking=False):
                    break
                main._PHOTO_REQUEST_SLOT.release()
                time.sleep(.01)
            else:
                pytest.fail('Authorized slow upload did not reach the intake')
            with httpx.Client(base_url=f'http://127.0.0.1:{port}', trust_env=False, timeout=3,
                              headers={'X-Schulpilot-Request': '1', 'X-Client-Platform': 'native'}) as outsider:
                response = outsider.post(path, files={'file': ('x.jpg', b'fake', 'image/jpeg')})
                assert response.status_code == 401
            received = b''
            while b'\r\n\r\n' not in received:
                chunk = client.recv(1024)
                if not chunk:
                    break
                received += chunk
            assert received.startswith(b'HTTP/1.1 408 '), received[:80]
        retry = api.post(path, files={'file': ('x.jpg', fixture('JPEG'), 'image/jpeg')},
                         headers={'Idempotency-Key': 'slow-photo-synthetic-key-01'})
        assert retry.status_code == 201
        with DB() as db:
            assert db.scalar(select(func.count()).select_from(Material)) == 1
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
        assert not thread.is_alive()


@pytest.mark.parametrize('revocation', ['session', 'membership', 'permission', 'privacy'])
def test_access_revoked_while_decoding_never_saves_or_returns_replay(api, household, monkeypatch, revocation):
    import json

    from schulpilot.db import Installation, Membership, Session
    from schulpilot.security import digest, encrypt
    from sqlalchemy import delete, update

    allow_synthetic_test_transport()
    _, child = household
    token = api.headers['Authorization'][7:]
    # Keep one preexisting upload to ensure the replay path rechecks rights too.
    key = 'photo-revocation-synthetic-01'
    path = f"/api/children/{child['id']}/materials"
    image = fixture('JPEG')
    first = api.post(path, files={'file': ('x.jpg', image, 'image/jpeg')}, headers={'Idempotency-Key': key})
    assert first.status_code == 201
    started, release = threading.Event(), threading.Event()
    original = materials.normalize_photo

    def blocked(raw):
        started.set()
        assert release.wait(10)
        return original(raw)

    monkeypatch.setattr(materials, 'normalize_photo', blocked)
    results = []
    def replay():
        results.append(api.post(path, files={'file': ('x.jpg', image, 'image/jpeg')}, headers={'Idempotency-Key': key}))
    thread = threading.Thread(target=replay)
    thread.start()
    try:
        assert started.wait(5)
        with DB.begin() as db:
            session = db.scalar(select(Session).where(Session.token_hash == digest(token)))
            assert session
            if revocation == 'session':
                db.execute(update(Session).where(Session.id == session.id).values(revoked=True))
            elif revocation == 'privacy':
                db.get(Installation, 1).encrypted_settings = encrypt(json.dumps({'real_data_approved': False}))
            else:
                membership = db.scalar(select(Membership).where(Membership.user_id == session.user_id))
                assert membership
                if revocation == 'membership':
                    db.execute(delete(Membership).where(Membership.id == membership.id))
                else:
                    db.execute(update(Membership).where(Membership.id == membership.id).values(permission='view'))
    finally:
        release.set()
        thread.join(timeout=12)
    assert not thread.is_alive() and len(results) == 1
    assert results[0].status_code in (401, 403, 404, 503)
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Material)) == 1


def test_photo_auth_checks_are_bounded_without_consuming_the_database_pool(monkeypatch):
    entered = threading.Barrier(5, timeout=5)
    release = threading.Event()
    class Principal:
        class User:
            role = 'parent'
        user = User()
    def blocked(*args):
        entered.wait()
        assert release.wait(5)
        return Principal()
    monkeypatch.setattr(main, 'authenticated', blocked)
    monkeypatch.setattr(main, 'child_access', lambda *args, **kwargs: None)
    scope = {'type': 'http', 'method': 'POST', 'path': '/api/children/synthetic/materials',
             'scheme': 'http', 'server': ('testserver', 80), 'query_string': b'',
             'headers': [(b'authorization', b'Bearer synthetic')]}
    errors = []
    def check():
        try:
            main.authorize_photo_before_intake(scope)
        except Exception as exc:
            errors.append(exc)
    threads = [threading.Thread(target=check) for _ in range(4)]
    for thread in threads:
        thread.start()
    try:
        entered.wait()
        with pytest.raises(HTTPException) as exc:
            main.authorize_photo_before_intake(scope)
        assert exc.value.status_code == 503 and exc.value.headers == {'Retry-After': '2'}
    finally:
        release.set()
        for thread in threads:
            thread.join(timeout=5)
    assert not errors and all(not thread.is_alive() for thread in threads)


@pytest.mark.parametrize('failure', ['write', 'chmod'])
def test_photo_file_failure_removes_partial_private_image(api, household, monkeypatch, failure):
    from pathlib import Path

    from schulpilot.config import settings

    allow_synthetic_test_transport()
    _, child = household
    existing = set((settings.data_dir / 'uploads').glob('*.jpg'))
    original_write, original_chmod = Path.write_bytes, Path.chmod
    def write(path, data):
        if failure == 'write' and path.parent == settings.data_dir / 'uploads':
            original_write(path, b'synthetic partial')
            raise OSError('synthetic write failure')
        return original_write(path, data)
    def chmod(path, mode, *args, **kwargs):
        if failure == 'chmod' and path.parent == settings.data_dir / 'uploads':
            raise OSError('synthetic chmod failure')
        return original_chmod(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, 'write_bytes', write)
    monkeypatch.setattr(Path, 'chmod', chmod)
    response = api.post(f"/api/children/{child['id']}/materials",
                        files={'file': ('x.jpg', fixture('JPEG'), 'image/jpeg')},
                        headers={'Idempotency-Key': 'photo-file-error-test-001'})
    assert response.status_code == 500
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Material)) == 0
    assert set((settings.data_dir / 'uploads').glob('*.jpg')) == existing
