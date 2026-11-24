"""Real browser file picker and crop, with synthetic photos and no provider."""
import json
import os
import re
import shutil
import socket
import subprocess
import threading
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest
import uvicorn
from PIL import Image
from schulpilot import main
from schulpilot.config import settings
from schulpilot.db import DB, Job, Material, Usage
from schulpilot.main import app
from sqlalchemy import select
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(os.getenv('NOTEBOOK_LOCAL_BROWSER') != '1', reason='Requires isolated browser opt-in')
def test_photo_picker_and_crop_in_mobile_browser(household, monkeypatch, tmp_path):
    if os.getenv('TEST_DATABASE_URL') or settings.environment != 'test' or make_url(settings.database_url).get_backend_name() != 'sqlite':
        pytest.fail('An isolated SQLite database is required')
    if not settings.web_dir or not (Path(settings.web_dir) / 'main.dart.js').is_file():
        pytest.fail('A local Flutter web build is required')
    previous_data_dir = settings.data_dir
    object.__setattr__(settings, 'data_dir', tmp_path / 'data')
    object.__setattr__(settings, 'real_data_approved', True)
    object.__setattr__(settings, 'privacy_evidence', 'Isolated synthetic browser photo fixture')
    child = household[1]
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    sock.listen(128)
    port = sock.getsockname()[1]
    monkeypatch.setattr(main, 'settings', replace(settings, public_url=f'http://127.0.0.1:{port}'))
    caddy = (ROOT / 'deploy/Caddyfile.schulpilot').read_text()
    match = re.search(r'^\s*header @application Content-Security-Policy "([^"\n]+)"', caddy, re.MULTILINE)
    assert match, 'The deployed application CSP must be present'
    policy = match.group(1).encode('ascii')

    async def with_application_csp(scope, receive, send):
        async def with_policy(message):
            if message['type'] == 'http.response.start':
                headers = [(key, value) for key, value in message['headers'] if key.lower() != b'content-security-policy']
                message['headers'] = [*headers, (b'content-security-policy', policy)]
            await send(message)
        await app(scope, receive, with_policy)

    server = uvicorn.Server(uvicorn.Config(with_application_csp, log_level='error', lifespan='off'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if server.started:
                break
            time.sleep(.05)
        assert server.started
        node = shutil.which('node')
        assert node
        data = {'base': f'http://127.0.0.1:{port}', 'child': child['id'], 'screens': str(tmp_path),
                'photo': str(ROOT / 'testdata/notebook_synthetic/arbeitsblatt.jpg')}
        result = subprocess.run([node, 'qa/photo_local_browser.mjs'], input=json.dumps(data), text=True,
            capture_output=True, timeout=240, env={'PATH': str(Path(node).parent) + ':/usr/bin:/bin',
                'LANG': 'C.UTF-8', 'TMPDIR': os.environ.get('TMPDIR', '/tmp')})
        assert result.returncode == 0, result.stderr[-4000:]
        evidence = json.loads(result.stdout)
        assert evidence['passed'] is True
        for width in (390, 1280):
            box = evidence['buttonBoxes'][str(width)]
            bounds = (int(box['x']), int(box['y']), int(box['x'] + box['width']), int(box['y'] + box['height']))
            with Image.open(tmp_path / f'photo-cropped-{width}.png') as image:
                colors = Counter(image.convert('RGB').crop(bounds).get_flattened_data())
            background = colors.most_common(1)[0][0]
            # Use colors that are actually present in the rendered control.
            def luminance(color):
                values = [channel / 255 for channel in color]
                values = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4 for value in values]
                return .2126 * values[0] + .7152 * values[1] + .0722 * values[2]
            foreground = max((color for color, count in colors.items() if count >= 8), key=luminance)
            low, high = sorted((luminance(background), luminance(foreground)))
            assert (high + .05) / (low + .05) >= 4.5
        with DB() as db:
            pages = list(db.scalars(select(Material).where(Material.child_id == child['id'])))
            assert len(pages) == 2 and all(page.status == 'uploaded' for page in pages)
            assert not list(db.scalars(select(Job))) and not list(db.scalars(select(Usage)))
    finally:
        server.should_exit = True
        thread.join(timeout=15)
        sock.close()
        object.__setattr__(settings, 'data_dir', previous_data_dir)
        assert not thread.is_alive()
