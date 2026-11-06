"""Opt-in actual cached old Flutter Web build against an isolated new backend."""

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest
import uvicorn
from schulpilot import main, providers
from schulpilot.config import settings
from schulpilot.db import DB, Installation, ProviderConfig, User
from schulpilot.main import app
from schulpilot.security import password_hash


def test_cached_old_flutter_admin_form_cannot_overwrite_new_site(api, monkeypatch, tmp_path):
    if os.getenv("SITE_CAS_LEGACY_BROWSER") != "1":
        pytest.skip("Requires opt-in and a separate synthetic old Flutter Web build")
    assert not os.getenv("TEST_DATABASE_URL") and settings.environment == "test"
    root = Path(settings.web_dir).resolve(strict=True)
    assert root.is_relative_to(Path("/dev/shm"))
    assert root.parent.name.startswith("schulpilot-site-cas-browser-")
    assert (root.parent / ".synthetic-old-bundle").read_text() == "synthetic old build only\n"
    assert (root / "main.dart.js").is_file()
    worker = root / "site-cas-cache-sw.js"
    worker.write_text("""self.addEventListener('install', e => e.waitUntil(self.skipWaiting()));
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {
  if (new URL(e.request.url).pathname !== '/main.dart.js') return;
  e.respondWith(caches.open('synthetic-legacy-v1').then(async c =>
    (await c.match(e.request, {ignoreSearch: true})) || fetch(e.request)));
});
""")
    with DB.begin() as db:
        db.add(User(username="synthetic-cached-admin", display_name="Synthetic admin", role="admin",
                    verified=True, password_hash=password_hash("synthetic-admin-password-123")))
        db.get(ProviderConfig, 1).emergency_stop = False
        starting_revision = db.get(Installation, 1).revision
    calls = []
    monkeypatch.setattr(providers, "request_provider", lambda *args, **kwargs: calls.append(True))
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    port = sock.getsockname()[1]
    monkeypatch.setattr(main, "settings", replace(settings, public_url=f"http://127.0.0.1:{port}"))
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="off"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if server.started:
                break
            time.sleep(.05)
        assert server.started
        node = shutil.which("node")
        assert node
        result = subprocess.run([node, "qa/site_cas_legacy_browser.mjs"], input=json.dumps({
            "base": f"http://127.0.0.1:{port}", "screens": str(tmp_path),
        }), text=True, capture_output=True, timeout=180,
            env={"PATH": str(Path(node).parent) + ":/usr/bin:/bin", "LANG": "C.UTF-8"})
        assert result.returncode == 0, result.stderr[-4000:]
        with DB() as db:
            assert db.get(Installation, 1).revision == starting_revision
            assert db.get(ProviderConfig, 1).emergency_stop is True
        assert calls == []
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        worker.unlink(missing_ok=True)
        assert not thread.is_alive()


def test_legacy_browser_rejects_external_test_database_before_import():
    environment = {**os.environ, "PYTHONPATH": "backend/tests:backend", "SITE_CAS_LEGACY_BROWSER": "1",
                   "TEST_DATABASE_URL": "postgresql+psycopg://fixture@127.0.0.1/schulpilot_test"}
    result = subprocess.run([sys.executable, "-c", "import conftest"], env=environment,
                            text=True, capture_output=True, timeout=10)
    assert result.returncode != 0
    assert "require an automatically isolated SQLite database" in result.stderr
