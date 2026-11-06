import hashlib
import os
import pwd
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from schulpilot import photo_isolation
from test_photo_isolation import fixture

SERVICE = Path(__file__).resolve().parents[1] / 'schulpilot/photo_service.py'
HEALTH = SERVICE.with_name('photo_health.py')
API_USER = pwd.getpwuid(os.getuid()).pw_name


@pytest.fixture
def photo_service(tmp_path, monkeypatch):
    directory = tmp_path / 'private'
    directory.mkdir(mode=0o700)
    path = directory / 'decoder.sock'
    process = subprocess.Popen([sys.executable, '-I', str(SERVICE), str(path), API_USER],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.monotonic() + 10
    while not path.exists() and process.poll() is None and time.monotonic() < deadline:
        time.sleep(.05)
    assert path.exists() and process.poll() is None
    monkeypatch.setenv('PHOTO_TEST_SOCKET', str(path))
    try:
        yield path, process
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)


def test_private_socket_photo_and_health(photo_service):
    path, _ = photo_service
    assert path.stat().st_mode & 0o777 == 0o660
    subprocess.run([sys.executable, '-I', str(HEALTH), str(path), str(os.getuid())], check=True)
    raw = fixture('JPEG', orientation=6)
    image, geometry, _ = photo_isolation.normalize_photo(raw)
    assert image.getvalue().startswith(b'\xff\xd8\xff')
    assert geometry['width'] == 501 and geometry['height'] == 733
    assert geometry['input_bytes'] == len(raw)


def test_health_can_wait_behind_active_request(photo_service):
    import importlib.util
    import threading

    path, _ = photo_service
    spec = importlib.util.spec_from_file_location('synthetic_photo_health', HEALTH)
    health = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as busy:
        busy.connect(str(path))
        busy.sendall(photo_isolation._DECODER_DIGEST[:1])
        # Leave a request incomplete to model a busy service, then release it.
        timer = threading.Timer(.2, busy.close)
        timer.start()
        try:
            health.main(str(path), os.getuid(), timeout=2)
        finally:
            timer.cancel()


def test_unavailable_and_mismatched_services_fail_closed(photo_service, monkeypatch):
    path, process = photo_service
    monkeypatch.setattr(photo_isolation, '_DECODER_DIGEST', hashlib.sha256(b'other revision').digest())
    with pytest.raises(Exception) as exc:
        photo_isolation.normalize_photo(fixture('JPEG'))
    assert getattr(exc.value, 'status_code', None) == 503
    monkeypatch.undo()
    process.kill()
    process.wait(timeout=10)
    monkeypatch.setenv('PHOTO_TEST_SOCKET', str(path))
    with pytest.raises(Exception) as exc:
        photo_isolation.normalize_photo(fixture('JPEG'))
    assert getattr(exc.value, 'status_code', None) == 503


def test_duplicate_service_never_unlinks_active_socket(photo_service):
    path, process = photo_service
    second = subprocess.run([sys.executable, '-I', str(SERVICE), str(path), API_USER],
                            capture_output=True, timeout=10)
    assert second.returncode != 0 and process.poll() is None and path.exists()
    subprocess.run([sys.executable, '-I', str(HEALTH), str(path), str(os.getuid())], check=True)


def test_unowned_file_is_never_unlinked(tmp_path):
    directory = tmp_path / 'private'
    directory.mkdir(mode=0o700)
    path = directory / 'decoder.sock'
    path.write_text('synthetic sentinel')
    second = subprocess.run([sys.executable, '-I', str(SERVICE), str(path), API_USER], capture_output=True, timeout=10)
    assert second.returncode != 0 and path.read_text() == 'synthetic sentinel'


def test_socket_rejects_excess_length_without_killing_service(photo_service):
    path, process = photo_service
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(2)
        client.connect(str(path))
        client.sendall(photo_isolation._DECODER_DIGEST + (10 * 1024 * 1024 + 1).to_bytes(4, 'big'))
        assert client.recv(1) == b''
    assert process.poll() is None
    subprocess.run([sys.executable, '-I', str(HEALTH), str(path), str(os.getuid())], check=True)


def test_client_rejects_unexpected_peer_uid(photo_service):
    path, _ = photo_service
    with pytest.raises(photo_isolation.DecoderUnavailable):
        photo_isolation._result_from_private_socket(fixture('JPEG'), str(path), os.getuid() + 1)


def test_missing_service_user_fails_closed(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(photo_isolation, 'settings', SimpleNamespace(environment='production'))
    monkeypatch.setattr(photo_isolation.pwd, 'getpwnam', lambda _: (_ for _ in ()).throw(KeyError('missing')))
    with pytest.raises(Exception) as exc:
        photo_isolation.normalize_photo(fixture('JPEG'))
    assert getattr(exc.value, 'status_code', None) == 503
    assert exc.value.headers == {'Retry-After': '2'}


def test_service_rejects_wrong_api_uid(tmp_path):
    directory = tmp_path / 'private'
    directory.mkdir(mode=0o700)
    path = directory / 'decoder.sock'
    # Local test runs as an unprivileged user; root is a deliberately wrong peer.
    assert os.getuid() != 0
    process = subprocess.Popen([sys.executable, '-I', str(SERVICE), str(path), 'root'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 10
        while not path.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(.05)
        assert path.exists()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(2)
            client.connect(str(path))
            client.sendall(photo_isolation._DECODER_DIGEST + bytes(4))
            try:
                result = client.recv(4)
            except ConnectionResetError:
                result = b''
            assert result == b''
        assert process.poll() is None
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)


def test_service_interpreter_remains_bound_to_old_release_after_symlink_switch(tmp_path):
    import shutil

    releases = tmp_path / 'releases'
    for name in ('old', 'new'):
        root = releases / name
        binary = root / 'venv/bin/python'
        binary.parent.mkdir(parents=True)
        binary.symlink_to('/usr/bin/python3')
        (root / 'venv/pyvenv.cfg').write_text('home = /usr/bin\ninclude-system-site-packages = true\n')
        package = root / 'backend/schulpilot'
        package.mkdir(parents=True)
        for filename in ('photo_service.py', 'photo_decoder.py'):
            shutil.copy2(SERVICE.with_name(filename), package / filename)
        (root / 'backend/requirements.lock').write_text('synthetic lock\n')
        (root / 'release.json').write_text('{}')
    current = tmp_path / 'current'
    current.symlink_to(releases / 'old')
    runner = '''import os,runpy,subprocess,sys
from pathlib import Path
current=Path(sys.argv[1]); new=Path(sys.argv[2])
module=runpy.run_path(str(current/'backend/schulpilot/photo_service.py'))
pinned=module['PINNED_INTERPRETER']
current.unlink(); current.symlink_to(new)
result=subprocess.run([str(pinned),'-I','-c','import sys;print(sys.prefix)'],capture_output=True,text=True,check=True)
print(pinned);print(result.stdout.strip())'''
    result = subprocess.run([str(current / 'venv/bin/python'), '-I', '-c', runner, str(current), str(releases / 'new')],
                            capture_output=True, text=True, check=True, timeout=15)
    lines = result.stdout.splitlines()
    assert lines == [str(releases / 'old/venv/bin/python'), str(releases / 'old/venv')]
