import json

import pytest

from scripts.audit_codex_container_packages import query, read_inventory


def test_inventory_deduplicates_debian_sources_and_normalizes_pypi():
    dpkg = b'installed\tlibfoo:amd64\t1.0+b1\tfoo\t1.0\ninstalled\tfoo-bin\t1.0\tfoo\t1.0\n'
    pypi = b'[{"name":"sample_pkg", "version":"1.2.3"}]'
    assert read_inventory(dpkg, pypi) == [('Debian:12', 'foo', '1.0'), ('PyPI', 'sample-pkg', '1.2.3')]


@pytest.mark.parametrize('dpkg', [b'', b'broken', b'deinstalled\ta\t1\ta\t1',
                                  b'installed\ta\t1\t../../x\t1', b'installed\ta\t1\t\t1'])
def test_inventory_rejects_invalid_debian_rows(dpkg):
    with pytest.raises(ValueError):
        read_inventory(dpkg, b'[{"name":"foo","version":"1.0"}]')


def test_inventory_rejects_duplicate_python_names():
    dpkg = b'installed\ta\t1\ta\t1'
    pypi = json.dumps([{'name': 'foo_bar', 'version': '1'}, {'name': 'foo-bar', 'version': '2'}]).encode()
    with pytest.raises(ValueError, match='Duplicate'):
        read_inventory(dpkg, pypi)


def test_query_follows_pagination_and_retains_all_findings():
    key = ('Debian:12', 'openssl', '1.0')
    seen = []

    def send(payload):
        seen.append(payload)
        if len(seen) == 1:
            return {'results': [{'vulns': [{'id': 'one'}], 'next_page_token': 'page-2'}]}
        return {'results': [{'vulns': [{'id': 'two'}]}]}

    assert query([key], send) == {key: {'one', 'two'}}
    assert seen[1]['queries'][0]['page_token'] == 'page-2'


@pytest.mark.parametrize('response', [None, {}, {'results': []}, {'results': [{'error': 'bad'}]},
                                      {'results': [{'vulns': None}]}, {'results': [{'vulns': [{'id': ''}]}]},
                                      {'results': [{'next_page_token': ''}]}])
def test_query_rejects_malformed_or_partial_responses(response):
    with pytest.raises(ValueError):
        query([('PyPI', 'foo', '1')], lambda _: response)


def test_query_rejects_repeating_token():
    with pytest.raises(ValueError, match='pagination'):
        query([('PyPI', 'foo', '1')], lambda _: {'results': [{'next_page_token': 'same'}]})
