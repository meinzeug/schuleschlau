#!/usr/bin/env python3
"""Audit the locked npm dependency closure of Firebase web and worker roots.

The lock describes an npm resolution, not proof of the contents of a CDN bundle.
No account information is sent and no npm install scripts are run.
"""
import base64
import binascii
import hashlib
import hmac
import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit

try:
    from scripts.audit_firebase_web import VERSION, audit, fetch, osv_findings
except ModuleNotFoundError:
    from audit_firebase_web import VERSION, audit, fetch, osv_findings

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / 'docs/dependency-inventory/firebase-npm-compat-20261105'
REGISTRY = 'https://registry.npmjs.org/'
ROOTS = {'@firebase/app': '0.16.2', '@firebase/messaging': '0.13.3',
         '@firebase/app-compat': '0.5.18', '@firebase/messaging-compat': '0.2.30'}
MAX_ARCHIVE_BYTES = 4_000_000


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_archive(url):
    """Read a bounded package from the pinned HTTPS registry without redirects."""
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc != 'registry.npmjs.org' or parsed.query or parsed.fragment:
        raise ValueError('Invalid npm archive URL')
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(urllib.request.Request(url), timeout=30) as response:
        if response.status != 200:
            raise ValueError('Invalid npm archive response')
        return response.read(MAX_ARCHIVE_BYTES + 1)


def verify_archive(content, integrity):
    """Check raw registry archive bytes against one exact locked SRI SHA-512."""
    if not isinstance(content, bytes) or not content or len(content) > MAX_ARCHIVE_BYTES:
        raise ValueError('Invalid npm archive size')
    if not isinstance(integrity, str) or not integrity.startswith('sha512-'):
        raise ValueError('Invalid npm archive integrity')
    try:
        expected = base64.b64decode(integrity.removeprefix('sha512-'), validate=True)
    except (binascii.Error, ValueError):
        raise ValueError('Invalid npm archive integrity') from None
    if len(expected) != hashlib.sha512().digest_size:
        raise ValueError('Invalid npm archive integrity')
    if not hmac.compare_digest(hashlib.sha512(content).digest(), expected):
        raise ValueError('npm archive integrity mismatch')
    return {'bytes': len(content), 'sha512': integrity}


def locked_packages(inventory):
    package = json.loads((inventory / 'package.json').read_text())
    lock = json.loads((inventory / 'package-lock.json').read_text())
    if package.get('dependencies') != ROOTS or lock.get('lockfileVersion') != 3:
        raise ValueError('Unexpected Firebase npm roots or lock format')
    entries = lock.get('packages')
    if not isinstance(entries, dict) or entries.get('', {}).get('dependencies') != ROOTS:
        raise ValueError('Unexpected lock root')
    found = {}
    for location, entry in entries.items():
        if not location:
            continue
        if not location.startswith('node_modules/') or not isinstance(entry, dict) or entry.get('link'):
            raise ValueError('Unexpected npm lock location or link')
        name = location.split('node_modules/')[-1]
        version = entry.get('version')
        license_name = entry.get('license')
        integrity = entry.get('integrity')
        resolved = urlsplit(entry.get('resolved', ''))
        if (not re.fullmatch(r'(?:@[a-z0-9._-]+/)?[a-z0-9._-]+', name)
                or not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+\.\d+', version)
                or not isinstance(license_name, str) or not license_name.strip()
                or not isinstance(integrity, str) or not integrity.startswith('sha512-')
                or resolved.scheme != 'https' or resolved.netloc != 'registry.npmjs.org'
                or resolved.query or resolved.fragment):
            raise ValueError('Invalid npm lock entry')
        key = (name, version)
        detail = {'license': license_name, 'integrity': integrity, 'resolved': entry['resolved']}
        if key in found and found[key] != detail:
            raise ValueError('Conflicting npm lock entries')
        found[key] = detail
    if not found or len(found) > 1000 or any((name, version) not in found for name, version in ROOTS.items()):
        raise ValueError('Missing npm roots or unexpected package count')
    return found


def check_tree(inventory):
    """npm verifies lock dependency resolution offline; never install or execute scripts."""
    subprocess.run(
        ['npm', 'ls', '--package-lock-only', '--offline', '--ignore-scripts',
         '--all', '--json', '--userconfig=/dev/null'],
        cwd=inventory, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60,
    )


def audit_tree(inventory=INVENTORY, get=fetch, verify_tree=check_tree, archive_get=fetch_archive):
    packages = locked_packages(inventory)
    verify_tree(inventory)
    rows = []
    for (name, version), detail in sorted(packages.items()):
        url = f'{REGISTRY}{quote(name, safe="")}/{version}'
        metadata = json.loads(get(url))
        if (metadata.get('name') != name or metadata.get('version') != version
                or metadata.get('license') != detail['license']
                or metadata.get('dist', {}).get('integrity') != detail['integrity']
                or metadata.get('dist', {}).get('tarball') != detail['resolved']):
            raise ValueError(f'npm metadata mismatch: {name}@{version}')
        archive = verify_archive(archive_get(detail['resolved']), detail['integrity'])
        rows.append({'name': name, 'version': version, 'license': detail['license'],
                     'integrity': detail['integrity'], 'archive': archive,
                     'vulnerability_ids': osv_findings(name, version, get)})
    return {'npm_root': ROOTS, 'firebase_sdk': VERSION,
            'lock_sha256': hashlib.sha256((inventory / 'package-lock.json').read_bytes()).hexdigest(),
            'packages': rows}


def main():
    # Verify the delivered bootstrap URL and umbrella-package metadata too.
    bootstrap = audit(ROOT)
    locked = audit_tree()
    for name, version in ROOTS.items():
        if bootstrap['npm_advisories'][name]['version'] != version:
            raise ValueError('Firebase SDK and npm tree versions differ')
    result = {'queried_at_utc_local_clock': datetime.now(timezone.utc).isoformat(),
              'bootstrap': bootstrap, 'transitive_npm': locked}
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(any(item['vulnerability_ids'] for item in locked['packages'])
               or any(item['ids'] for item in bootstrap['npm_advisories'].values()))


if __name__ == '__main__':
    sys.exit(main())
