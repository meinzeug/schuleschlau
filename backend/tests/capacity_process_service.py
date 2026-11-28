"""Restricted helper for capacity_process_profile.py; never use with real data."""
import os
import socket
import stat
import sys
import tempfile
import threading
import time
from pathlib import Path

from capacity_guard import require_private_profile_database

require_private_profile_database(helper=True)

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
        time.sleep(provider_delay)
        return Result({'subject': 'Mathematik', 'topic': 'Künstlicher Test',
                       'content': 'Künstlicher Seiteninhalt: 1 + 1 = 2.',
                       'uncertainties': [], 'homework': []}, 10, 20, 0)

    worker.request_provider = fake_provider
    (root / 'worker.ready').write_text(str(os.getpid()))
    count = int(args[0])
    provider_delay = int(args[1]) if len(args) == 2 else 2
    if not 1 <= count <= 16 or len(args) > 2 or provider_delay not in (2, 6):
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
