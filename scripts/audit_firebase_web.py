#!/usr/bin/env python3
"""Inspect pinned Firebase web and service-worker scripts and npm advisories.

This read-only check sends no account or user data. It does not inspect dynamically
loaded payment scripts or establish correspondence between bundles and npm sources.
"""
import hashlib
import json
import re
import urllib.request
from pathlib import Path

VERSION = '12.19.0'
BASE = f'https://www.gstatic.com/firebasejs/{VERSION}/'
MODULES = ('firebase-app.js', 'firebase-messaging.js')
WORKER_MODULES = ('firebase-app-compat.js', 'firebase-messaging-compat.js')
REGISTRY = f'https://registry.npmjs.org/firebase/{VERSION}'
OSV = 'https://api.osv.dev/v1/query'
MAX_OSV_PAGES = 500


def fetch(url, body=None):
    headers = {'Accept': 'application/json'} if body is not None else {}
    data = json.dumps(body).encode() if body is not None else None
    if data is not None:
        headers['Content-Type'] = 'application/json'
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=30) as response:
        return response.read(4_000_001)


def osv_findings(name, version, get=fetch):
    query = {'package': {'name': name, 'ecosystem': 'npm'}, 'version': version}
    found = []
    seen_tokens = set()
    while True:
        result = json.loads(get(OSV, query))
        # OSV legitimately returns {} for no findings, or only a page token
        # when a page times out. An error-shaped 200 response is not an empty
        # vulnerability list and must never be reported as a successful audit.
        if not isinstance(result, dict) or result.keys() - {'vulns', 'next_page_token'}:
            raise ValueError('Invalid OSV response')
        vulnerabilities = result.get('vulns', [])
        if not isinstance(vulnerabilities, list):
            raise ValueError('Invalid OSV vulnerability list')
        for item in vulnerabilities:
            if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id'].strip():
                raise ValueError('Invalid OSV vulnerability ID')
            found.append(item['id'])
        if 'next_page_token' not in result:
            return sorted(set(found))
        token = result['next_page_token']
        if not isinstance(token, str) or not token:
            raise ValueError('Invalid OSV page token')
        if token in seen_tokens:
            raise ValueError('OSV returned a repeated page token')
        if len(seen_tokens) >= MAX_OSV_PAGES - 1:
            raise ValueError('OSV page limit exceeded')
        seen_tokens.add(token)
        query['page_token'] = token


def audit(root, get=fetch):
    bootstrap = (root / 'app/web/push_bootstrap.js').read_text()
    actual = re.findall(r"\bimport\(\s*['\"]([^'\"]+)['\"]\s*\)", bootstrap)
    expected = {BASE + module for module in MODULES}
    if (set(actual) != expected or len(actual) != len(expected)
            or len(re.findall(r'\bimport\s*\(', bootstrap)) != len(expected)):
        raise ValueError('Firebase bootstrap imports differ from the fixed audit scope')
    # The background worker is served by the backend, not the Flutter web
    # directory. Its compat SDK has its own dependency tree and must not be
    # omitted when assessing the actual scripts loaded for web push.
    worker = (root / 'backend/schulpilot/notifications.py').read_text()
    worker_actual = re.findall(r"importScripts\(\s*['\"]([^'\"]+)['\"]\s*\)", worker)
    worker_expected = {BASE + module for module in WORKER_MODULES}
    if (set(worker_actual) != worker_expected or len(worker_actual) != len(worker_expected)
            or len(re.findall(r'\bimportScripts\s*\(', worker)) != len(worker_expected)):
        raise ValueError('Firebase service-worker imports differ from the fixed audit scope')
    metadata = json.loads(get(REGISTRY))
    if metadata['name'] != 'firebase' or metadata['version'] != VERSION:
        raise ValueError('Unexpected npm package metadata')
    packages = {'firebase': VERSION}
    for name in ('@firebase/app', '@firebase/messaging', '@firebase/app-compat', '@firebase/messaging-compat'):
        version = metadata['dependencies'][name]
        if not re.fullmatch(r'\d+\.\d+\.\d+', version):
            raise ValueError(f'Non-exact dependency for {name}')
        packages[name] = version
    resources = {}
    for module in (*MODULES, *WORKER_MODULES):
        content = get(BASE + module)
        if not content or len(content) > 4_000_000:
            raise ValueError(f'Invalid response size for {module}')
        resources[module] = {'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
    return {'sdk_version': VERSION, 'npm_license': metadata['license'], 'resources': resources,
            'npm_advisories': {name: {'version': version, 'ids': osv_findings(name, version, get)}
                               for name, version in packages.items()}}


def main():
    result = audit(Path(__file__).resolve().parents[1])
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(any(item['ids'] for item in result['npm_advisories'].values()))


if __name__ == '__main__':
    raise SystemExit(main())
