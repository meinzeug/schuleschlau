import json
from pathlib import Path

import pytest

from scripts.audit_firebase_web import BASE, MODULES, OSV, REGISTRY, audit, osv_findings


def test_audit_uses_exact_bootstrap_and_queries_all_three_packages(tmp_path: Path):
    web = tmp_path / 'app/web'
    web.mkdir(parents=True)
    (web / 'push_bootstrap.js').write_text('\n'.join(f"import('{BASE}{name}')" for name in MODULES))
    calls = []

    def fake(url, data=None):
        calls.append((url, data))
        if url == REGISTRY:
            return json.dumps({'name': 'firebase', 'version': '12.19.0', 'license': 'Apache-2.0',
                               'dependencies': {'@firebase/app': '0.16.2', '@firebase/messaging': '0.13.3'}}).encode()
        if url == OSV:
            return b'{}'
        return b'public module'

    result = audit(tmp_path, fake)
    assert set(result['npm_advisories']) == {'firebase', '@firebase/app', '@firebase/messaging'}
    assert len([url for url, _ in calls if url == OSV]) == 3
    assert result['resources']['firebase-app.js']['bytes'] == 13


def test_unknown_bootstrap_does_not_fetch(tmp_path: Path):
    web = tmp_path / 'app/web'
    web.mkdir(parents=True)
    (web / 'push_bootstrap.js').write_text("import('https://www.gstatic.com/firebasejs/1.0.0/firebase-app.js')")
    with pytest.raises(ValueError, match='scope'):
        audit(tmp_path, lambda *_: pytest.fail('unexpected request'))


def test_osv_pagination_and_repeated_tokens():
    requests = []

    def fake(_url, data):
        requests.append(data.copy())
        if len(requests) == 1:
            return b'{"vulns":[{"id":"FIRST"}],"next_page_token":"next"}'
        return b'{"vulns":[{"id":"SECOND"}]}'

    assert osv_findings('firebase', '12.19.0', fake) == ['FIRST', 'SECOND']
    assert requests[1]['page_token'] == 'next'
    with pytest.raises(ValueError, match='repeated'):
        osv_findings('firebase', '12.19.0', lambda *_: b'{"next_page_token":"same"}')


@pytest.mark.parametrize('response', [
    b'{"error":{"message":"unavailable"}}',
    b'[]',
    b'{"vulns":null}',
    b'{"vulns":{}}',
    b'{"vulns":[null]}',
    b'{"vulns":[{"id":""}]}',
    b'{"vulns":[{"id":42}]}',
    b'{"next_page_token":null}',
    b'{"next_page_token":""}',
    b'{"next_page_token":false}',
])
def test_malformed_osv_results_fail_closed(response):
    with pytest.raises(ValueError, match='Invalid OSV'):
        osv_findings('firebase', '12.19.0', lambda *_: response)


def test_osv_accepts_no_findings_and_token_only_page():
    responses = iter((b'{"next_page_token":"next"}', b'{}'))
    assert osv_findings('firebase', '12.19.0', lambda *_: next(responses)) == []


def test_osv_unique_page_tokens_are_bounded(monkeypatch):
    monkeypatch.setattr('scripts.audit_firebase_web.MAX_OSV_PAGES', 3)
    count = 0

    def fake(_url, _data):
        nonlocal count
        count += 1
        return json.dumps({'next_page_token': str(count)}).encode()

    with pytest.raises(ValueError, match='page limit'):
        osv_findings('firebase', '12.19.0', fake)
    assert count == 3
