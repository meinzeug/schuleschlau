"""Synthetic cross-session read receipts for a paginated inbox, no push or AI."""

from conftest import HEADERS, register
from fastapi.testclient import TestClient
from schulpilot.db import DB, Job, Membership, Message, NotificationRead, now
from schulpilot.main import app
from sqlalchemy import func, select


def test_old_page_read_is_shared_between_sessions_but_not_other_family_member(api, household, mailbox):
    owner, child = household
    stamp = int(now())
    with DB.begin() as db:
        for index in range(60):
            db.add(Message(id=f'{index + 1:032x}', child_id=child['id'], kind='help',
                           body='Synthetic notification', created=stamp - index))
    with TestClient(app, headers=HEADERS) as second, TestClient(app, headers=HEADERS) as other:
        login = second.post('/api/auth/login', json={
            'username': 'parent@example.org', 'password': 'secure-parent-pass-123'})
        assert login.status_code == 200
        second.headers['Authorization'] = 'Bearer ' + login.json()['token']
        assert second.headers['Authorization'] != api.headers['Authorization']
        other_user = register(other, mailbox, 'second-parent@example.org')
        with DB.begin() as db:
            db.add(Membership(user_id=other_user['id'], family_id=owner['families'][0]['id'], permission='view'))

        first = api.get('/api/notifications/inbox', params={'paginate': '1'}).json()
        assert len(first['items']) == 50 and first['next_cursor']
        old = second.get('/api/notifications/inbox', params={
            'paginate': '1', 'cursor': first['next_cursor']}).json()
        assert len(old['items']) == 10
        target, untouched = old['items'][0]['id'], old['items'][1]['id']
        assert not old['items'][0]['read'] and not old['items'][1]['read']
        assert second.post('/api/notifications/inbox/read', json={'ids': [target]}).status_code == 200
        assert second.post('/api/notifications/inbox/read', json={'ids': [target]}).status_code == 200

        for client, expected in ((api, True), (second, True), (other, False)):
            page = client.get('/api/notifications/inbox', params={
                'paginate': '1', 'cursor': first['next_cursor']}).json()
            states = {item['id']: item['read'] for item in page['items']}
            assert states[target] is expected
            assert states[untouched] is False
        with DB() as db:
            assert db.scalar(select(func.count()).select_from(NotificationRead)) == 1
            assert db.scalar(select(func.count()).select_from(Job)) == 0
