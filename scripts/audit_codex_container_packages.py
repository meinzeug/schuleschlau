#!/usr/bin/env python3
"""Check a captured, non-sensitive Debian/Python package inventory via OSV.

This is not an image scan: it does not cover the copied Codex binary, locally
compiled Python, native binary dependencies, non-dpkg files, or unknown CVEs.
"""
import argparse
import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = 'https://api.osv.dev/v1/querybatch'
TOKEN = re.compile(r'[A-Za-z0-9][A-Za-z0-9.+:~_-]{0,199}')


def read_inventory(dpkg, pypi):
    packages = set()
    rows = dpkg.decode('utf-8').splitlines()
    if not rows or len(rows) > 10000:
        raise ValueError('Invalid Debian inventory length')
    for line in rows:
        fields = line.split('\t')
        if len(fields) != 5 or fields[0] != 'installed' or not all(TOKEN.fullmatch(v) for v in fields[1:]):
            raise ValueError('Invalid installed Debian package')
        packages.add(('Debian:12', fields[3], fields[4]))
    values = json.loads(pypi)
    if not isinstance(values, list) or not 1 <= len(values) <= 1000:
        raise ValueError('Invalid Python inventory length')
    seen_python = set()
    for item in values:
        if not isinstance(item, dict) or set(item) != {'name', 'version'} or not all(
            isinstance(item[k], str) and TOKEN.fullmatch(item[k]) for k in ('name', 'version')
        ):
            raise ValueError('Invalid Python distribution')
        name = re.sub('[-_.]+', '-', item['name']).lower()
        if name in seen_python:
            raise ValueError('Duplicate Python distribution')
        seen_python.add(name)
        packages.add(('PyPI', name, item['version']))
    return sorted(packages)


def post(body):
    request = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read(16_000_001)
    if len(raw) > 16_000_000:
        raise ValueError('Oversized OSV response')
    return json.loads(raw)


def query(packages, send=post):
    pending = [(key, None) for key in packages]
    found = {key: set() for key in packages}
    seen = set()
    while pending:
        queries = []
        for (ecosystem, name, version), token in pending:
            entry = {'package': {'ecosystem': ecosystem, 'name': name}, 'version': version}
            if token is not None:
                entry['page_token'] = token
            queries.append(entry)
        response = send({'queries': queries})
        rows = response.get('results') if isinstance(response, dict) else None
        if not isinstance(rows, list) or len(rows) != len(pending):
            raise ValueError('Incomplete OSV batch')
        following = []
        for (key, _), row in zip(pending, rows, strict=True):
            if not isinstance(row, dict) or row.keys() - {'vulns', 'next_page_token'}:
                raise ValueError('Invalid OSV result')
            vulns = row.get('vulns', [])
            if not isinstance(vulns, list):
                raise ValueError('Invalid OSV vulnerability list')
            for vuln in vulns:
                if not isinstance(vuln, dict) or not isinstance(vuln.get('id'), str) or not vuln['id'].strip():
                    raise ValueError('Invalid OSV advisory')
                found[key].add(vuln['id'])
            if 'next_page_token' in row:
                token = row['next_page_token']
                if not isinstance(token, str) or not token or (key, token) in seen or len(seen) >= 500:
                    raise ValueError('Invalid OSV pagination')
                seen.add((key, token))
                following.append((key, token))
        pending = following
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dpkg', type=Path, required=True)
    parser.add_argument('--pypi', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    debian, python = args.dpkg.read_bytes(), args.pypi.read_bytes()
    packages = read_inventory(debian, python)
    hits = query(packages)
    result = {'queried_at_utc_local_clock': datetime.now(timezone.utc).isoformat(), 'source': URL,
              'inventory_sha256': {'dpkg': hashlib.sha256(debian).hexdigest(),
                                   'pypi': hashlib.sha256(python).hexdigest()},
              'packages': [{'ecosystem': eco, 'name': name, 'version': version,
                            'vulnerability_ids': sorted(hits[(eco, name, version)])}
                           for eco, name, version in packages]}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    affected = sum(bool(ids) for ids in hits.values())
    print(f'Queried {len(packages)} versions; {affected} have OSV matches.')
    return int(affected > 0)


if __name__ == '__main__':
    raise SystemExit(main())
