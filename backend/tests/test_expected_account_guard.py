"""The account assertion is only a denial guard, never an authority."""
import pytest
from fastapi.testclient import TestClient
from schulpilot.main import app


@pytest.mark.parametrize('method,path', [('get', '/api/auth/me'), ('post', '/api/auth/logout')])
def test_mismatch_rejects_read_and_mutation_without_logging_out(household, method, path):
    parent, _ = household
    with TestClient(app, headers={'X-Schulpilot-Request': '1'}) as browser:
        response = browser.post('/api/auth/login', json={
            'username': 'parent@example.org', 'password': 'secure-parent-pass-123',
        })
        assert response.status_code == 200
        assert response.json()['user']['id'] == parent['id']
        denied = getattr(browser, method)(path, headers={'X-Schulpilot-Account': 'f' * 32})
        assert denied.status_code == 409
        assert parent['id'] not in denied.text
        assert 'f' * 32 not in denied.text
        assert browser.get('/api/auth/me').json()['id'] == parent['id']
        assert browser.get('/api/auth/me', headers={'X-Schulpilot-Account': parent['id']}).status_code == 200


def test_header_does_not_grant_authentication(api, household):
    parent, _ = household
    api.headers.pop('Authorization', None)
    api.cookies.clear()
    response = api.get('/api/auth/me', headers={'X-Schulpilot-Account': parent['id']})
    assert response.status_code == 401


def test_child_session_remains_restricted_despite_parent_assertion(household):
    parent, _ = household
    with TestClient(app, headers={'X-Schulpilot-Request': '1'}) as browser:
        login = browser.post('/api/auth/login', json={
            'username': 'test-child', 'password': 'secure-child-pass-123',
        })
        assert login.status_code == 200
        child_id = login.json()['user']['id']
        assert browser.get('/api/auth/me', headers={'X-Schulpilot-Account': parent['id']}).status_code == 409
        assert browser.get('/api/auth/me', headers={'X-Schulpilot-Account': child_id}).json()['id'] == child_id


def test_explicit_login_switches_accounts_then_rejects_old_assertion(household):
    parent, _ = household
    with TestClient(app, headers={'X-Schulpilot-Request': '1'}) as browser:
        assert browser.post('/api/auth/login', json={
            'username': 'parent@example.org', 'password': 'secure-parent-pass-123',
        }).status_code == 200
        login = browser.post('/api/auth/login', headers={'X-Schulpilot-Account': parent['id']}, json={
            'username': 'test-child', 'password': 'secure-child-pass-123',
        })
        assert login.status_code == 200
        child_account = login.json()['user']['id']
        stale = browser.get('/api/auth/me', headers={'X-Schulpilot-Account': parent['id']})
        assert stale.status_code == 409
        assert stale.headers['X-Schulpilot-Account-Changed'] == '1'
        assert 'Bitte melde dich erneut an' in stale.text
        assert browser.get('/api/auth/me', headers={'X-Schulpilot-Account': child_account}).json()['id'] == child_account


def test_stale_assertion_does_not_prevent_explicit_fresh_login(household):
    parent, _ = household
    with TestClient(app, headers={'X-Schulpilot-Request': '1'}) as browser:
        login = browser.post('/api/auth/login', headers={'X-Schulpilot-Account': 'f' * 32}, json={
            'username': 'parent@example.org', 'password': 'secure-parent-pass-123',
        })
        assert login.status_code == 200
        assert login.json()['user']['id'] == parent['id']
        assert browser.get('/api/auth/me', headers={'X-Schulpilot-Account': parent['id']}).status_code == 200


def test_stale_account_is_rejected_before_photo_intake(api, household):
    from schulpilot.db import DB, Job, Material
    from sqlalchemy import func, select

    _, child = household
    with DB() as db:
        before_materials = db.scalar(select(func.count()).select_from(Material))
        before_jobs = db.scalar(select(func.count()).select_from(Job))
    response = api.post(
        f"/api/children/{child['id']}/materials",
        headers={'X-Schulpilot-Account': 'f' * 32, 'Idempotency-Key': 'synthetic-stale-account-photo'},
        files={'file': ('synthetic.jpg', b'not a real photo', 'image/jpeg')},
    )
    assert response.status_code == 409
    assert response.headers['X-Schulpilot-Account-Changed'] == '1'
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Material)) == before_materials
        assert db.scalar(select(func.count()).select_from(Job)) == before_jobs
