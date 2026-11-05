import base64
import copy
import hashlib
import json
from pathlib import Path
from urllib.parse import quote

import pytest

from scripts import audit_firebase_npm_tree as tree
from scripts.audit_firebase_npm_tree import INVENTORY, REGISTRY, audit_tree, check_tree, locked_packages, verify_archive
from scripts.audit_firebase_web import OSV


def test_real_lock_resolves_offline_without_installing():
    packages = locked_packages(INVENTORY)
    assert ('@firebase/app', '0.16.2') in packages
    assert ('@firebase/messaging', '0.13.3') in packages
    assert ('idb', '7.1.1') in packages
    check_tree(INVENTORY)


def test_checks_all_locked_versions_licenses_integrities_and_advisories(monkeypatch):
    packages = locked_packages(INVENTORY)
    archives = {}
    for (name, version), details in packages.items():
        content = f'synthetic-{name}-{version}'.encode()
        details['integrity'] = 'sha512-' + base64.b64encode(hashlib.sha512(content).digest()).decode()
        archives[details['resolved']] = content
    monkeypatch.setattr(tree, 'locked_packages', lambda _: packages)
    requested = []
    metadata = {
        f'{REGISTRY}{quote(name, safe="")}/{version}': json.dumps({
            'name': name, 'version': version, 'license': details['license'],
            'dist': {'integrity': details['integrity'], 'tarball': details['resolved']},
        }).encode()
        for (name, version), details in packages.items()
    }

    def get(url, body=None):
        requested.append((url, body))
        return b'{}' if url == OSV else archives[url] if url in archives else metadata[url]

    result = audit_tree(INVENTORY, get=get, verify_tree=lambda _: None, archive_get=get)
    assert len(result['packages']) == len(packages)
    assert len([url for url, _ in requested if url == OSV]) == len(packages)
    assert len([url for url, _ in requested if url != OSV]) == 2 * len(packages)
    assert all(not item['vulnerability_ids'] for item in result['packages'])
    assert all(item['archive']['bytes'] > 0 and item['archive']['sha512'] == item['integrity'] for item in result['packages'])


def test_archive_verification_rejects_modified_or_unbounded_data():
    content = b'synthetic package archive'
    integrity = 'sha512-' + base64.b64encode(hashlib.sha512(content).digest()).decode()
    assert verify_archive(content, integrity)['bytes'] == len(content)
    for invalid in (b'', b'x' * (tree.MAX_ARCHIVE_BYTES + 1), content + b'changed'):
        with pytest.raises(ValueError):
            verify_archive(invalid, integrity)
    for invalid in ('sha512-%%%', 'sha512-' + base64.b64encode(b'too-short').decode(), 'sha256-value'):
        with pytest.raises(ValueError):
            verify_archive(content, invalid)


def test_archive_download_does_not_follow_unlocked_registry_metadata(monkeypatch):
    packages = locked_packages(INVENTORY)
    monkeypatch.setattr(tree, 'locked_packages', lambda _: packages)
    requested = []
    name, version = sorted(packages)[0]
    def get(url, body=None):
        requested.append(url)
        return json.dumps({'name': name, 'version': version, 'license': packages[(name, version)]['license'],
            'dist': {'integrity': packages[(name, version)]['integrity'], 'tarball': 'https://example.invalid/p.tgz'}}).encode()
    with pytest.raises(ValueError, match='metadata mismatch'):
        audit_tree(INVENTORY, get=get, verify_tree=lambda _: None)
    assert len(requested) == 1


@pytest.mark.parametrize('url', [
    'http://registry.npmjs.org/x.tgz', 'https://other.invalid/x.tgz',
    'https://registry.npmjs.org:443/x.tgz', 'https://registry.npmjs.org/x.tgz?redirect=1',
    'https://registry.npmjs.org/x.tgz#fragment',
])
def test_archive_transport_refuses_unpinned_origin_before_network(url):
    with pytest.raises(ValueError, match='Invalid npm archive URL'):
        tree.fetch_archive(url)


def test_archive_transport_does_not_follow_redirects():
    assert tree.NoRedirect().redirect_request(None, None, 302, 'redirect', {}, 'https://other.invalid/') is None


def test_rejects_changed_registry_metadata():
    def get(_url, _body=None):
        return b'{"name":"wrong"}'

    with pytest.raises(ValueError, match='metadata mismatch'):
        audit_tree(INVENTORY, get=get, verify_tree=lambda _: None)


@pytest.mark.parametrize('change', ['root', 'format', 'missing', 'link', 'url', 'integrity', 'license'])
def test_rejects_modified_lock(tmp_path: Path, change):
    package = json.loads((INVENTORY / 'package.json').read_text())
    lock = json.loads((INVENTORY / 'package-lock.json').read_text())
    package = copy.deepcopy(package)
    lock = copy.deepcopy(lock)
    entry = lock['packages']['node_modules/@firebase/app']
    if change == 'root':
        package['dependencies']['@firebase/app'] = '0.0.0'
    elif change == 'format':
        lock['lockfileVersion'] = 2
    elif change == 'missing':
        del lock['packages']['node_modules/@firebase/app']
    elif change == 'link':
        entry['link'] = True
    elif change == 'url':
        entry['resolved'] = 'https://attacker.example/path'
    elif change == 'integrity':
        entry['integrity'] = 'bad'
    else:
        entry.pop('license')
    (tmp_path / 'package.json').write_text(json.dumps(package))
    (tmp_path / 'package-lock.json').write_text(json.dumps(lock))
    with pytest.raises(ValueError):
        locked_packages(tmp_path)
