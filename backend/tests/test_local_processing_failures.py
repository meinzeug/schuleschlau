"""Artificial failures only: no input, answer, filename or image in receipts."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from conftest import HEADERS, create_child, register
from fastapi.testclient import TestClient
from schulpilot.db import (
    DB,
    Activity,
    Attempt,
    Child,
    Job,
    LearningUnit,
    LocalProcessingFailure,
    Mastery,
    Usage,
    engine,
    now,
)
from schulpilot.main import app
from schulpilot.preparation_retention import purge
from sqlalchemy import func, select
from test_coaching import normal_unit as normal_unit
from test_material_auto_review import operator as operator
from test_material_auto_review import pipeline as pipeline

SECRET = 'PRIVATE-SYNTHETIC-CONTENT-DO-NOT-STORE'


def counts():
    with DB() as db:
        return tuple(db.scalar(select(func.count()).select_from(model))
                     for model in (Job, Usage, Attempt, Activity, Mastery))


def test_invalid_upload_has_private_parent_only_receipt_and_no_learning_effects(pipeline, operator, mailbox):
    api, child = pipeline['api'], pipeline['child']
    before = counts()
    response = api.post(f"/api/children/{child['id']}/materials",
                        files={'file': (SECRET + '.jpg', SECRET.encode(), 'image/jpeg')})
    assert response.status_code == 422
    receipt = response.headers['X-Processing-Receipt']
    details = api.get(f'/api/processing-errors/{receipt}')
    assert details.status_code == 200
    assert details.json()['phase'] == 'upload' and details.json()['code'] == 'photo_invalid'
    assert details.json()['status'] == 'failed'
    assert details.json()['unit_id'] is None and SECRET not in details.text
    listed = api.get(f"/api/children/{child['id']}/processing-errors").json()['errors']
    assert [row['id'] for row in listed] == [receipt]
    assert counts() == before
    assert operator.get(f'/api/processing-errors/{receipt}').status_code == 403
    with TestClient(app, headers=HEADERS) as other:
        register(other, mailbox, 'different-family@example.org')
        assert other.get(f'/api/processing-errors/{receipt}').status_code == 404
    with TestClient(app, headers=HEADERS) as kid:
        login = kid.post('/api/auth/login', json={'username': 'test-child', 'password': 'secure-child-pass-123'})
        assert login.status_code == 200
        kid.headers['Authorization'] = 'Bearer ' + login.json()['token']
        assert kid.get(f'/api/processing-errors/{receipt}').status_code == 403
    with DB() as db:
        row = db.get(LocalProcessingFailure, receipt)
        assert SECRET not in json.dumps({column.name: getattr(row, column.name) for column in row.__table__.columns})


@pytest.mark.parametrize(('status', 'code'), [(413, 'photo_too_large'), (503, 'photo_unavailable')])
def test_upload_decoder_failures_are_separately_classified_without_input(pipeline, monkeypatch, status, code):
    from fastapi import HTTPException

    def rejected(raw):
        raise HTTPException(status, 'synthetic decoder error')

    monkeypatch.setattr('schulpilot.materials.normalize_photo', rejected)
    api, child = pipeline['api'], pipeline['child']
    before = counts()
    response = api.post(f"/api/children/{child['id']}/materials",
                        files={'file': (SECRET + '.jpg', SECRET.encode(), 'image/jpeg')})
    assert response.status_code == status
    details = api.get(f"/api/processing-errors/{response.headers['X-Processing-Receipt']}")
    assert details.status_code == 200 and details.json()['code'] == code
    assert SECRET not in details.text and counts() == before


def test_missing_question_receipt_is_bounded_and_never_records_answer(api, normal_unit):
    kid, unit_id, _, _, child = normal_unit
    assert kid.post(f'/api/units/{unit_id}/start').status_code == 200
    before = counts()
    response = kid.post(f'/api/units/{unit_id}/questions/{SECRET}/answer', json={'answer': SECRET})
    assert response.status_code == 404
    receipt = response.headers['X-Processing-Receipt']
    details = api.get(f'/api/processing-errors/{receipt}')
    assert details.status_code == 200
    assert details.json()['phase'] == 'answer' and details.json()['code'] == 'question_missing'
    assert details.json()['unit_id'] == unit_id and SECRET not in details.text
    assert counts() == before
    for _ in range(2):
        assert api.get(f"/api/children/{child['id']}/processing-errors").status_code == 200
    assert counts() == before
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(LocalProcessingFailure)) == 1


def test_retention_and_child_deletion_remove_receipts(pipeline):
    from schulpilot.families import export_child

    api, child = pipeline['api'], pipeline['child']
    response = api.post(f"/api/children/{child['id']}/materials", files={'file': ('x.jpg', b'invalid', 'image/jpeg')})
    identifier = response.headers['X-Processing-Receipt']
    with DB() as db:
        exported = export_child(db, db.get(Child, child['id']))['local_processing_failures']
        assert [row['id'] for row in exported] == [identifier]
    with DB.begin() as db:
        db.get(LocalProcessingFailure, identifier).created = int(now() - timedelta(days=31).total_seconds())
    assert api.get(f'/api/processing-errors/{identifier}').status_code == 404
    assert api.get(f"/api/children/{child['id']}/processing-errors").json()['errors'] == []
    with DB() as db:
        assert export_child(db, db.get(Child, child['id']))['local_processing_failures'] == []
    with DB.begin() as db:
        purge(db, int(now()))
    assert api.get(f'/api/processing-errors/{identifier}').status_code == 404
    response = api.post(f"/api/children/{child['id']}/materials", files={'file': ('x.jpg', b'invalid', 'image/jpeg')})
    identifier = response.headers['X-Processing-Receipt']
    with DB.begin() as db:
        db.delete(db.get(Child, child['id']))
    with DB() as db:
        assert db.get(LocalProcessingFailure, identifier) is None


def test_receipt_cap_preserves_original_error_without_unbounded_records(api, normal_unit):
    kid, unit_id, _, _, child = normal_unit
    assert kid.post(f'/api/units/{unit_id}/start').status_code == 200
    before = counts()
    for index in range(21):
        response = kid.post(f'/api/units/{unit_id}/questions/unknown/answer', json={'answer': SECRET})
        assert response.status_code == 404
        assert ('X-Processing-Receipt' in response.headers) == (index < 20)
    assert len(api.get(f"/api/children/{child['id']}/processing-errors").json()['errors']) == 20
    assert counts() == before


def test_parallel_receipt_limit_serializes_per_child_on_postgres(api, normal_unit):
    if engine.dialect.name != 'postgresql':
        pytest.skip('Requires isolated PostgreSQL concurrency')
    kid, unit_id, _, _, child = normal_unit
    assert kid.post(f'/api/units/{unit_id}/start').status_code == 200
    authorization = kid.headers['Authorization']
    before = counts()

    def send(_):
        with TestClient(app, headers={**HEADERS, 'Authorization': authorization}) as client:
            response = client.post(f'/api/units/{unit_id}/questions/unknown/answer', json={'answer': SECRET})
            return response.status_code, 'X-Processing-Receipt' in response.headers

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(send, range(24)))
    assert all(status == 404 for status, _ in results)
    assert sum(receipt for _, receipt in results) == 20
    assert len(api.get(f"/api/children/{child['id']}/processing-errors").json()['errors']) == 20
    assert counts() == before


def test_revoked_session_during_receipt_does_not_change_original_rejection(pipeline, monkeypatch):
    from fastapi import HTTPException
    from schulpilot import local_processing_failures

    def rejected(*args, **kwargs):
        raise HTTPException(401, 'synthetic session ended')

    monkeypatch.setattr(local_processing_failures, 'lock_session_after_child', rejected)
    response = pipeline['api'].post(f"/api/children/{pipeline['child']['id']}/materials",
                                    files={'file': ('x.jpg', b'invalid', 'image/jpeg')})
    assert response.status_code == 422 and 'X-Processing-Receipt' not in response.headers
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(LocalProcessingFailure)) == 0


def test_foreign_unit_binding_is_not_returned_even_within_same_family(api, normal_unit):
    from schulpilot.families import export_child

    _, unit_id, _, parent, child = normal_unit
    sibling = create_child(api, parent, username='synthetic-sibling')
    with DB.begin() as db:
        original = db.get(LearningUnit, unit_id)
        foreign = LearningUnit(child_id=sibling['id'], subject='Mathematik', topic='Künstlich',
            explanation='Test', questions=original.questions, provider='synthetic', model='synthetic')
        db.add(foreign)
        db.flush()
        receipt = LocalProcessingFailure(child_id=child['id'], unit_id=foreign.id,
            phase='answer', code='question_missing', created=int(now()))
        db.add(receipt)
        db.flush()
        identifier = receipt.id
    assert api.get(f'/api/processing-errors/{identifier}').status_code == 404
    assert api.get(f"/api/children/{child['id']}/processing-errors").json()['errors'] == []
    with DB() as db:
        assert export_child(db, db.get(Child, child['id']))['local_processing_failures'] == []


def test_unit_erasure_replay_removes_associated_receipt(api, normal_unit):
    from schulpilot.erasure import reconcile

    kid, unit_id, _, _, _ = normal_unit
    response = kid.post(f'/api/units/{unit_id}/questions/unknown/answer', json={'answer': SECRET})
    identifier = response.headers['X-Processing-Receipt']
    with DB.begin() as db:
        reconcile(db, [{'scope': 'unit', 'target': unit_id}])
        reconcile(db, [{'scope': 'unit', 'target': unit_id}])
    with DB() as db:
        assert db.get(LearningUnit, unit_id) is None
        assert db.get(LocalProcessingFailure, identifier) is None
    assert api.get(f'/api/processing-errors/{identifier}').status_code == 404
