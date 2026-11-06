"""Opt-in synthetic browser evidence for delayed successful login responses.

This documents current behavior; it does not claim to fix the cookie race.
Uses the same isolated-database opt-in guard as the logout browser test.
"""
import asyncio
import json
import os
import signal
import socket
import subprocess
import tempfile
import threading
import time
from dataclasses import replace

import pytest
import uvicorn
from schulpilot import main
from schulpilot.config import settings
from schulpilot.db import DB, User
from schulpilot.main import app
from schulpilot.security import password_hash


@pytest.mark.skipif(os.getenv('LOGOUT_COOKIE_RACE_BROWSER') != '1', reason='isolated browser evidence only')
def test_late_successful_login_response_replaces_newer_browser_cookie(household, monkeypatch):
    old, _ = household
    with DB.begin() as db:
        user = User(username='synthetic-new-parent', display_name='Synthetic parent', role='parent',
                    verified=True, password_hash=password_hash('secure-parent-pass-123'))
        db.add(user)
        db.flush()
        new_id = user.id
    pending, release, done = threading.Event(), threading.Event(), threading.Event()
    outcome = {}
    html = b'''<!doctype html><html><body><script>
    (async()=>{
      const headers={'Content-Type':'application/json','X-Schulpilot-Request':'1'};
      const login=(username,held)=>fetch('/api/auth/login',{method:'POST',
        headers:{...headers,...(held?{'X-Test-Hold':'1'}:{})},
        body:JSON.stringify({username,password:'secure-parent-pass-123'})}).then(async r=>({status:r.status,body:await r.json()}));
      try {
        const older=login('parent@example.org',true);
        let held=false;
        for(let i=0;i<200&&!held;i++) { held=(await(await fetch('/__race/status')).json()).pending; if(!held) await new Promise(r=>setTimeout(r,25)); }
        if(!held) throw Error('old response not held');
        const newer=await login('synthetic-new-parent',false);
        const before=await(await fetch('/api/auth/me')).json();
        await fetch('/__race/release');
        const old=await older;
        const after=await(await fetch('/api/auth/me')).json();
        const expected={...headers,'X-Schulpilot-Account':newer.body.user.id};
        const guardedRead=await fetch('/api/auth/me',{headers:expected});
        const guardedLogout=await fetch('/api/auth/logout',{method:'POST',headers:expected});
        const afterDenied=await fetch('/api/auth/me');
        await fetch('/__race/result',{method:'POST',headers,body:JSON.stringify({old,newer,before,after,
          guardedRead:guardedRead.status,guardedLogout:guardedLogout.status,
          afterDenied:afterDenied.status,afterDeniedUser:(await afterDenied.json()).id})});
      } catch(e) { await fetch('/__race/result',{method:'POST',headers,body:JSON.stringify({error:String(e)})}); }
    })();</script></body></html>'''

    async def isolated(scope, receive, send):
        if scope['type'] == 'http' and scope['path'].startswith('/__race/'):
            path = scope['path']
            if path == '/__race/release':
                release.set()
            if path == '/__race/result':
                body = b''
                while True:
                    message = await receive()
                    body += message.get('body', b'')
                    if not message.get('more_body'):
                        break
                outcome.update(json.loads(body))
                done.set()
            body = json.dumps({'pending': pending.is_set()}).encode()
            await send({'type': 'http.response.start', 'status': 200, 'headers': [(b'content-type', b'application/json')]})
            await send({'type': 'http.response.body', 'body': body})
            return
        if scope['type'] == 'http' and scope['path'] == '/':
            await send({'type': 'http.response.start', 'status': 200, 'headers': [(b'content-type', b'text/html')]})
            await send({'type': 'http.response.body', 'body': html})
            return
        held = scope['type'] == 'http' and scope['path'] == '/api/auth/login' and (b'x-test-hold', b'1') in scope['headers']
        if held:
            async def gate(message):
                if message['type'] == 'http.response.start':
                    pending.set()
                    if not await asyncio.to_thread(release.wait, 20):
                        raise RuntimeError('synthetic login gate expired')
                await send(message)
            await app(scope, receive, gate)
            return
        await app(scope, receive, send)

    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    sock.listen(128)
    port = sock.getsockname()[1]
    monkeypatch.setattr(main, 'settings', replace(settings, public_url=f'http://127.0.0.1:{port}'))
    server = uvicorn.Server(uvicorn.Config(isolated, log_level='error', lifespan='off'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    chrome = None
    profile = None
    try:
        for _ in range(100):
            if server.started:
                break
            time.sleep(.05)
        assert server.started
        profile = tempfile.TemporaryDirectory(prefix='sp-login-race-chrome-')
        chrome = subprocess.Popen(['/opt/google/chrome/chrome', '--headless', '--no-sandbox', '--disable-gpu',
                                   '--disable-background-networking', '--no-first-run',
                                   f'--user-data-dir={profile.name}', f'http://127.0.0.1:{port}/'],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        assert done.wait(40), 'synthetic browser did not complete'
        assert not outcome.get('error'), outcome
        assert outcome['old']['status'] == 200
        assert outcome['newer']['status'] == 200
        assert outcome['before']['id'] == new_id
        assert outcome['after']['id'] == old['id']
        # New clients state which account they display. A stale cookie must
        # neither return the other account nor revoke its session.
        assert outcome['guardedRead'] == 409
        assert outcome['guardedLogout'] == 409
        assert outcome['afterDenied'] == 200
        assert outcome['afterDeniedUser'] == old['id']
    finally:
        release.set()
        if chrome:
            try:
                os.killpg(chrome.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                chrome.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(chrome.pid, signal.SIGKILL)
                chrome.wait(timeout=10)
        if profile:
            profile.cleanup()
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        assert not thread.is_alive()
