import json
from pathlib import Path

import pytest

from scripts.audit_firebase_web import BASE, MODULES, OSV, REGISTRY, WORKER_MODULES, audit, osv_findings


def write_worker(root, imports=WORKER_MODULES):
    worker = root / 'backend/schulpilot/notifications.py'
    worker.parent.mkdir(parents=True, exist_ok=True)
    worker.write_text('\n'.join(f"importScripts('{BASE}{name}');" for name in imports))


def test_audit_uses_exact_scripts_and_queries_all_five_packages(tmp_path: Path):
    web = tmp_path / 'app/web'
    web.mkdir(parents=True)
    (web / 'push_bootstrap.js').write_text('\n'.join(f"import('{BASE}{name}')" for name in MODULES))
    write_worker(tmp_path)
    calls = []

    def fake(url, data=None):
        calls.append((url, data))
        if url == REGISTRY:
            return json.dumps({'name': 'firebase', 'version': '12.19.0', 'license': 'Apache-2.0',
                               'dependencies': {'@firebase/app': '0.16.2', '@firebase/messaging': '0.13.3',
                                                '@firebase/app-compat': '0.5.18', '@firebase/messaging-compat': '0.2.30'}}).encode()
        if url == OSV:
            return b'{}'
        return b'public module'

    result = audit(tmp_path, fake)
    assert set(result['npm_advisories']) == {'firebase', '@firebase/app', '@firebase/messaging',
                                              '@firebase/app-compat', '@firebase/messaging-compat'}
    assert len([url for url, _ in calls if url == OSV]) == 5
    assert set(result['resources']) == set(MODULES + WORKER_MODULES)
    assert result['resources']['firebase-app.js']['bytes'] == 13


def test_unknown_bootstrap_does_not_fetch(tmp_path: Path):
    web = tmp_path / 'app/web'
    web.mkdir(parents=True)
    (web / 'push_bootstrap.js').write_text("import('https://www.gstatic.com/firebasejs/1.0.0/firebase-app.js')")
    with pytest.raises(ValueError, match='scope'):
        audit(tmp_path, lambda *_: pytest.fail('unexpected request'))


@pytest.mark.parametrize('imports', [(), WORKER_MODULES[:1], WORKER_MODULES + (WORKER_MODULES[0],),
                                    WORKER_MODULES + ('other.js',), ('older.js', WORKER_MODULES[1])])
def test_changed_worker_imports_do_not_fetch(tmp_path: Path, imports):
    web = tmp_path / 'app/web'
    web.mkdir(parents=True)
    (web / 'push_bootstrap.js').write_text('\n'.join(f"import('{BASE}{name}')" for name in MODULES))
    write_worker(tmp_path, imports)
    with pytest.raises(ValueError, match='service-worker'):
        audit(tmp_path, lambda *_: pytest.fail('unexpected request'))


@pytest.mark.parametrize('target', ['bootstrap', 'worker'])
def test_dynamic_additional_import_does_not_hide_from_scope_check(tmp_path: Path, target):
    web = tmp_path / 'app/web'
    web.mkdir(parents=True)
    bootstrap = web / 'push_bootstrap.js'
    bootstrap.write_text('\n'.join(f"import('{BASE}{name}')" for name in MODULES))
    write_worker(tmp_path)
    worker = tmp_path / 'backend/schulpilot/notifications.py'
    path = bootstrap if target == 'bootstrap' else worker
    with path.open('a') as output:
        output.write('\nimport(dynamicUrl)' if target == 'bootstrap' else '\nimportScripts(dynamicUrl)')
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
