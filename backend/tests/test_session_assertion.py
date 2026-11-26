"""Synthetic same-account session assertions: denial only, never authority."""

from fastapi.testclient import TestClient
from schulpilot.main import app
from test_accounts import HEADERS


def test_same_account_other_session_is_rejected_before_read_or_logout(household):
    with TestClient(app, headers=HEADERS) as older, TestClient(app, headers=HEADERS) as newer:
        credentials = {'username': 'parent@example.org', 'password': 'secure-parent-pass-123'}
        old_login = older.post('/api/auth/login', json=credentials)
        new_login = newer.post('/api/auth/login', json=credentials)
        assert old_login.status_code == new_login.status_code == 200
        old_user, new_user = old_login.json()['user'], new_login.json()['user']
        assert old_user['id'] == new_user['id']
        assert len(old_user['session_assertion']) == 64
        assert old_user['session_assertion'] != new_user['session_assertion']
        assert older.get('/api/auth/me').json()['session_assertion'] == old_user['session_assertion']
        assert newer.get('/api/auth/me').json()['session_assertion'] == new_user['session_assertion']
        claimed = {'X-Schulpilot-Account': new_user['id'], 'X-Schulpilot-Session': new_user['session_assertion']}
        assert newer.get('/api/auth/me', headers=claimed).status_code == 200
        rejected = older.get('/api/auth/me', headers=claimed)
        assert rejected.status_code == 409
        assert rejected.headers['X-Schulpilot-Account-Changed'] == '1'
        assert older.post('/api/auth/logout', headers=claimed).status_code == 409
        assert older.get('/api/auth/me').status_code == 200  # no wrong-session logout
        assert newer.get('/api/auth/me', headers=claimed).status_code == 200


def test_assertion_does_not_authenticate_and_malformed_markers_fail_closed(household):
    with TestClient(app, headers=HEADERS) as client:
        anonymous = client.get('/api/auth/me', headers={'X-Schulpilot-Session': 'a' * 64})
        assert anonymous.status_code == 401
        login = client.post('/api/auth/login', json={'username': 'parent@example.org', 'password': 'secure-parent-pass-123'})
        assert login.status_code == 200
        marker = login.json()['user']['session_assertion']
        assert client.get('/api/auth/me', headers={'X-Schulpilot-Session': marker}).status_code == 200
        for wrong in ('', 'a' * 64, 'x' * 64, 'a' * 65):
            response = client.get('/api/auth/me', headers={'X-Schulpilot-Session': wrong})
            assert response.status_code == 409
        assert client.get('/api/auth/me').status_code == 200  # older clients remain compatible
