import copy
import json
from pathlib import Path
from urllib.parse import quote

import pytest

from scripts.audit_firebase_npm_tree import INVENTORY, REGISTRY, audit_tree, check_tree, locked_packages
from scripts.audit_firebase_web import OSV


def test_real_lock_resolves_offline_without_installing():
    packages = locked_packages(INVENTORY)
    assert ('@firebase/app', '0.16.2') in packages
    assert ('@firebase/messaging', '0.13.3') in packages
    assert ('idb', '7.1.1') in packages
    check_tree(INVENTORY)


def test_checks_all_locked_versions_licenses_integrities_and_advisories():
    packages = locked_packages(INVENTORY)
    requested = []
    metadata = {
        f'{REGISTRY}{quote(name, safe="")}/{version}': json.dumps({
            'name': name, 'version': version, 'license': details['license'],
            'dist': {'integrity': details['integrity']},
        }).encode()
        for (name, version), details in packages.items()
    }

    def get(url, body=None):
        requested.append((url, body))
        return b'{}' if url == OSV else metadata[url]

    result = audit_tree(INVENTORY, get=get, verify_tree=lambda _: None)
    assert len(result['packages']) == len(packages)
    assert len([url for url, _ in requested if url == OSV]) == len(packages)
    assert len([url for url, _ in requested if url != OSV]) == len(packages)
    assert all(not item['vulnerability_ids'] for item in result['packages'])


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
