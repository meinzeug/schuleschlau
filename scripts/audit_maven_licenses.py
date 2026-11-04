#!/usr/bin/env python3
"""Inventory declared POM license metadata for versioned Gradle runtime trees.

The results are metadata, not a legal evaluation or proof of bundled artifacts.
Only fixed public Maven endpoints are queried; the result does not prove which
repository supplied an artifact during the original build.
"""
import argparse
import hashlib
import json
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.extract_gradle_runtime import coordinates
except ModuleNotFoundError:
    from extract_gradle_runtime import coordinates

REPOSITORIES = ('https://dl.google.com/dl/android/maven2/', 'https://repo.maven.apache.org/maven2/')
FLUTTER_REPOSITORY = 'https://storage.googleapis.com/download.flutter.io/'
JITPACK_REPOSITORY = 'https://jitpack.io/'
POM_NS = '{http://maven.apache.org/POM/4.0.0}'
TOKEN = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.+-]{0,199}')
MAX_POM_BYTES = 2_000_000


def safe_gav(group, artifact, version):
    if not all(isinstance(part, str) and TOKEN.fullmatch(part) and '..' not in part
               for part in (group, artifact, version)):
        raise ValueError('Invalid Maven coordinate')
    return group, artifact, version


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            body = response.read(MAX_POM_BYTES + 1)
            if len(body) > MAX_POM_BYTES:
                raise ValueError('Oversized Maven POM')
            return body
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def find_pom(gav, fetch=get):
    group, artifact, version = safe_gav(*gav)
    path = f'{group.replace(".", "/")}/{artifact}/{version}/{artifact}-{version}.pom'
    extras = (FLUTTER_REPOSITORY,) if group == 'io.flutter' else (
        (JITPACK_REPOSITORY,) if group == 'com.github.davidliu' else ())
    for repository in REPOSITORIES + extras:
        url = repository + path
        body = fetch(url)
        if body is not None:
            return url, body
    return None, None


def parse_pom(body, gav):
    if len(body) > MAX_POM_BYTES or b'<!DOCTYPE' in body.upper() or b'<!ENTITY' in body.upper():
        raise ValueError('Unsafe Maven POM')
    root = ET.fromstring(body)
    if root.tag not in (POM_NS + 'project', 'project'):
        raise ValueError('Unexpected Maven POM root')
    namespace = POM_NS if root.tag.startswith('{') else ''
    def text(name):
        return root.findtext(namespace + name)
    parent = root.find(namespace + 'parent')
    parent_gav = tuple(parent.findtext(namespace + part) for part in ('groupId', 'artifactId', 'version')) if parent is not None else None
    actual = (text('groupId') or (parent_gav and parent_gav[0]), text('artifactId'),
              text('version') or (parent_gav and parent_gav[2]))
    if actual != gav:
        raise ValueError(f'Maven POM coordinate mismatch: {gav}')
    license_nodes = root.findall(namespace + 'licenses/' + namespace + 'license')
    licenses = []
    for node in license_nodes:
        name = node.findtext(namespace + 'name')
        url = node.findtext(namespace + 'url')
        if not name or not name.strip() or '${' in name or (url and '${' in url):
            return None, parent_gav, True
        licenses.append({'name': name.strip(), 'url': url.strip() if url else None})
    return licenses, parent_gav, False


def inspect(pair, fetch=get):
    name, version = pair
    group, artifact = name.split(':')
    gav = safe_gav(group, artifact, version)
    chain = []
    seen = set()
    for _ in range(6):
        if gav in seen:
            raise ValueError('Maven POM parent cycle')
        seen.add(gav)
        url, body = find_pom(gav, fetch)
        if body is None:
            return {'name': name, 'version': version, 'status': 'pom_unavailable', 'chain': chain, 'licenses': []}
        try:
            licenses, parent, unresolved = parse_pom(body, gav)
        except (ValueError, ET.ParseError) as exc:
            raise ValueError(f'Invalid POM for {gav}: {exc}') from exc
        chain.append({'coordinate': ':'.join(gav), 'url': url, 'sha256': hashlib.sha256(body).hexdigest()})
        if unresolved:
            return {'name': name, 'version': version, 'status': 'unresolved_property', 'chain': chain, 'licenses': []}
        if licenses:
            return {'name': name, 'version': version,
                    'status': 'declared' if len(chain) == 1 else 'parent_declared',
                    'chain': chain, 'licenses': licenses}
        if parent is None:
            return {'name': name, 'version': version, 'status': 'not_declared', 'chain': chain, 'licenses': []}
        try:
            gav = safe_gav(*parent)
        except ValueError:
            return {'name': name, 'version': version, 'status': 'unresolved_parent', 'chain': chain, 'licenses': []}
    return {'name': name, 'version': version, 'status': 'parent_depth_limit', 'chain': chain, 'licenses': []}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trees', type=Path, nargs='+')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    inputs = {path.name: path.read_bytes() for path in args.trees}
    if len(inputs) != len(args.trees):
        raise ValueError('Duplicate inventory names')
    pairs = sorted({pair for raw in inputs.values() for pair in coordinates(raw.decode('utf-8'))})
    if not pairs or len(pairs) > 1000:
        raise ValueError('Unexpected number of Maven coordinates')
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(inspect, pairs))
    result = {'queried_at_utc_local_clock': datetime.now(timezone.utc).isoformat(),
              'repositories': [*REPOSITORIES, FLUTTER_REPOSITORY, JITPACK_REPOSITORY],
              'inventories': {name: hashlib.sha256(raw).hexdigest() for name, raw in inputs.items()},
              'packages': results}
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    missing = sum(item['status'] not in ('declared', 'parent_declared') for item in results)
    print(f'Inspected {len(results)} POMs; {missing} without resolved license metadata.')
    return int(missing > 0)


if __name__ == '__main__':
    raise SystemExit(main())
