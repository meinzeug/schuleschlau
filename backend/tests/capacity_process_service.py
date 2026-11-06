"""Restricted helper for capacity_process_profile.py; never use with real data."""
import os
import socket
import stat
import sys
import tempfile
import threading
import time
from pathlib import Path

from sqlalchemy.engine import make_url


def require_isolated_database():
    url_text = os.environ.get('TEST_DATABASE_URL', '')
    if not url_text or os.environ.get('DATABASE_URL') != url_text or os.environ.get('ENVIRONMENT') != 'test':
        raise RuntimeError('Missing explicit synthetic database and test environment')
    url = make_url(url_text)
    sock = Path(url.query.get('host', ''))
    root = sock.parent
    if (url.drivername != 'postgresql+psycopg' or url.database != 'schulpilot_isolated_test'
            or url.host is not None or str(url.query.get('port')) != '55440'
            or sock.name != 'socket' or root.parent != Path(tempfile.gettempdir())
            or not root.name.startswith('schulpilot-isolated-pg-') or root.is_symlink() or sock.is_symlink()):
        raise RuntimeError('Requires the private isolated PostgreSQL runner')
    for path in (root, sock):
        meta = path.stat()
        if not stat.S_ISDIR(meta.st_mode) or meta.st_uid != os.getuid() or stat.S_IMODE(meta.st_mode) != 0o700:
            raise RuntimeError('Insecure synthetic database directory')
    if not stat.S_ISSOCK((sock / '.s.PGSQL.55440').stat().st_mode):
        raise RuntimeError('Synthetic database socket missing')


require_isolated_database()

# After the private database check, deny any external Internet access in both
# test processes; PostgreSQL uses a Unix socket and the API only loopback.
original_connect = socket.socket.connect


def restricted_connect(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6) and address[0] not in ('127.0.0.1', '::1'):
        raise RuntimeError('External connections forbidden in synthetic process')
    return original_connect(self, address)


socket.socket.connect = restricted_connect
from schulpilot.config import settings  # noqa: E402
from schulpilot.db import DB  # noqa: E402

object.__setattr__(settings, 'real_data_approved', True)
object.__setattr__(settings, 'privacy_evidence', 'Isolated synthetic mock process')
role, directory, port, *args = sys.argv[1:]
root = Path(directory)
if root.parent != Path(tempfile.gettempdir()) or not root.name.startswith('schulpilot-capacity-process-'):
    raise RuntimeError('Invalid private test directory')
if root.stat().st_uid != os.getuid() or stat.S_IMODE(root.stat().st_mode) != 0o700:
    raise RuntimeError('Insecure test directory')

if role == 'api':
    import uvicorn
    from schulpilot.main import app

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', int(port)))
    listener.listen(128)
    server = uvicorn.Server(uvicorn.Config(app, log_level='error', access_log=False, lifespan='off'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(.05)
    if not server.started:
        raise RuntimeError('Synthetic API failed to start')
    (root / 'api.ready').write_text(str(os.getpid()))
    thread.join()
elif role == 'worker':
    from schulpilot import worker
    from schulpilot.providers import Result

    def fake_provider(config, function, payload, image_bytes=None, *, synthetic_fixture=False):
        if function != 'extract' or not image_bytes or synthetic_fixture:
            raise RuntimeError('Unexpected synthetic provider request')
        time.sleep(2)
        return Result({'subject': 'Mathematik', 'topic': 'Künstlicher Test',
                       'content': 'Künstlicher Seiteninhalt: 1 + 1 = 2.',
                       'uncertainties': [], 'homework': []}, 10, 20, 0)

    worker.request_provider = fake_provider
    (root / 'worker.ready').write_text(str(os.getpid()))
    count = int(args[0])
    if not 1 <= count <= 16:
        raise RuntimeError('Invalid synthetic job count')
    completed = 0
    deadline = time.monotonic() + 75
    while completed < count and time.monotonic() < deadline:
        with DB() as db:
            identifier = worker.claim(db)
        if identifier is None:
            time.sleep(.1)
            continue
        worker.process(identifier)
        completed += 1
    if completed != count:
        raise RuntimeError('Synthetic worker did not process all jobs')
else:
    raise RuntimeError('Unknown synthetic process role')
