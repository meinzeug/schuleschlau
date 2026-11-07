"""An unavailable preparation link does not erase or hide saved rounds."""
from conftest import HEADERS, create_child
from fastapi.testclient import TestClient
from schulpilot.db import DB, Job, LearningUnit, Material, Usage
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


def test_graphic_preflight_links_only_current_confirmed_own_sources(api, household):
    parent, child = household
    sibling = create_child(api, parent, username='other-source-child')
    with DB.begin() as db:
        own = Material(child_id=child['id'], title='Eigene künstliche Seite', confirmed=True)
        foreign = Material(child_id=sibling['id'], title='Andere künstliche Seite', confirmed=True)
        db.add_all([own, foreign])
        db.flush()
        own_id, foreign_id = own.id, foreign.id
        samples = {
            'own': ('visual_unavailable', {'sources': [{'id': own_id, 'revision': own.revision}]}),
            'foreign': ('visual_unavailable', {'sources': [{'id': foreign_id, 'revision': foreign.revision}]}),
            'stale': ('visual_unavailable', {'sources': [{'id': own_id, 'revision': 999}]}),
            'generic': ('invalid_output', {'material_id': own_id}),
            'primary': ('visual_unavailable', {'material_id': own_id}),
            'unversioned_source': ('visual_unavailable', {'sources': [{'id': own_id}]}),
        }
        jobs = {}
        for name, (code, payload) in samples.items():
            job = Job(child_id=child['id'], kind='unit', status='failed', error_code=code,
                      payload=payload, idempotency='synthetic-source-navigation-' + name)
            db.add(job)
            db.flush()
            jobs[name] = job.id
    with TestClient(app, headers=HEADERS) as client:
        login = client.post('/api/auth/login', json={'username': child['username'], 'password': 'secure-child-pass-123'})
        assert login.status_code == 200
        client.headers['Authorization'] = 'Bearer ' + login.json()['token']
        for name, job_id in jobs.items():
            response = client.get('/api/jobs/' + job_id)
            assert response.status_code == 200
            assert response.json()['review_material_id'] == (own_id if name == 'own' else None)
        # An originally valid source must stop linking after the page changes.
        with DB.begin() as db:
            db.get(Material, own_id).revision += 1
        assert client.get('/api/jobs/' + jobs['own']).json()['review_material_id'] is None
        assert client.get('/api/jobs/' + jobs['primary']).json()['review_material_id'] is None
    with TestClient(app, headers=HEADERS) as client:
        login = client.post('/api/auth/login', json={'username': sibling['username'], 'password': 'secure-child-pass-123'})
        client.headers['Authorization'] = 'Bearer ' + login.json()['token']
        assert client.get('/api/jobs/' + jobs['own']).status_code == 404
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Job)) == len(jobs)
        assert db.scalar(select(func.count()).select_from(Usage)) == 0
