"""An unavailable preparation link does not erase or hide saved rounds."""
from conftest import HEADERS, create_child
from fastapi.testclient import TestClient
from schulpilot.db import DB, Job, LearningUnit, Usage
from schulpilot.main import app
from schulpilot.synthetic import sample_unit
from sqlalchemy import func, select


def test_missing_preparation_keeps_saved_child_unit_accessible(api, household):
    parent, child = household
    sibling = create_child(api, parent, username='other-test-child')
    data = sample_unit()
    with DB.begin() as db:
        unit = LearningUnit(child_id=child['id'], subject=data['subject'], topic=data['topic'],
                            explanation=data['explanation'], questions=data['questions'],
                            synthetic=True, provider='synthetic-fixture')
        db.add(unit)
        db.flush()
        unit_id = unit.id
    with TestClient(app, headers=HEADERS) as client:
        login = client.post('/api/auth/login', json={'username': child['username'], 'password': 'secure-child-pass-123'})
        assert login.status_code == 200
        client.headers['Authorization'] = 'Bearer ' + login.json()['token']
        assert client.get('/api/jobs/missing-preparation').status_code == 404
        saved = client.get('/api/units/' + unit_id)
        assert saved.status_code == 200 and saved.json()['id'] == unit_id
    with TestClient(app, headers=HEADERS) as client:
        login = client.post('/api/auth/login', json={'username': sibling['username'], 'password': 'secure-child-pass-123'})
        assert login.status_code == 200
        client.headers['Authorization'] = 'Bearer ' + login.json()['token']
        assert client.get('/api/units/' + unit_id).status_code == 404
    with DB() as db:
        assert db.get(LearningUnit, unit_id) is not None
        assert db.scalar(select(func.count()).select_from(Job)) == 0
        assert db.scalar(select(func.count()).select_from(Usage)) == 0
