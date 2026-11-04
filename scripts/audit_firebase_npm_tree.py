#!/usr/bin/env python3
"""Audit the locked npm dependency closure of Firebase app and messaging.

The lock describes an npm resolution, not proof of the contents of a CDN bundle.
No account information is sent and no npm install scripts are run.
"""
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit

try:
    from scripts.audit_firebase_web import VERSION, audit, fetch, osv_findings
except ModuleNotFoundError:
    from audit_firebase_web import VERSION, audit, fetch, osv_findings

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / 'docs/dependency-inventory/firebase-npm-20261104'
REGISTRY = 'https://registry.npmjs.org/'
ROOTS = {'@firebase/app': '0.16.2', '@firebase/messaging': '0.13.3'}


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
        detail = {'license': license_name, 'integrity': integrity}
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


def audit_tree(inventory=INVENTORY, get=fetch, verify_tree=check_tree):
    packages = locked_packages(inventory)
    verify_tree(inventory)
    rows = []
    for (name, version), detail in sorted(packages.items()):
        url = f'{REGISTRY}{quote(name, safe="")}/{version}'
        metadata = json.loads(get(url))
        if (metadata.get('name') != name or metadata.get('version') != version
                or metadata.get('license') != detail['license']
                or metadata.get('dist', {}).get('integrity') != detail['integrity']):
            raise ValueError(f'npm metadata mismatch: {name}@{version}')
        rows.append({'name': name, 'version': version, 'license': detail['license'],
                     'integrity': detail['integrity'], 'vulnerability_ids': osv_findings(name, version, get)})
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
