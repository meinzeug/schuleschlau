"""Explicit bounded loopback HTTP/worker profile; synthetic test data only.

Start only with scripts/test_postgres.py. No production host or provider access.
"""
import socket
import threading
import time

import uvicorn
from capacity_worker_profile import run_worker_profile
from schulpilot.main import app


def run_loopback_profile(api, household, mailbox, monkeypatch, *, families=16, gate_reservations=False):
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port,
                                           log_level='error', access_log=False,
                                           lifespan='off'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 15
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(.05)
        assert server.started and thread.is_alive(), 'Isolated loopback server did not start'
        run_worker_profile(api, household, mailbox, monkeypatch, provider_delay=2, worker_threads=2,
                           families=families, network_base=f'http://127.0.0.1:{port}',
                           gate_reservations=gate_reservations)
    finally:
        server.should_exit = True
        thread.join(timeout=15)
        listener.close()
        assert not thread.is_alive(), 'Isolated loopback server failed to stop'


def test_bounded_loopback_multi_family_worker_profile(api, household, mailbox, monkeypatch):
    run_loopback_profile(api, household, mailbox, monkeypatch)
