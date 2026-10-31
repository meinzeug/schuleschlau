"""Synthetic conditional rechecks against concurrent answer changes."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from conftest import HEADERS
from fastapi.testclient import TestClient
from schulpilot.db import DB, Activity, Attempt, AttemptAssessment, Job, LearningUnit, Usage
from schulpilot.main import app
from sqlalchemy import func, select, update
from test_report_regressions import question


@pytest.fixture
def recheck_setup(api, household):
    _, child = household
    q = question()
    with DB.begin() as db:
        unit = LearningUnit(child_id=child['id'], subject='Mathematik', topic='Brüche',
                            explanation=q['explanation'], questions=[q], status='paused',
                            provider='synthetic', synthetic=True)
        db.add(unit)
        db.flush()
        uid = unit.id
        db.add(Attempt(id='a' * 32, unit_id=uid, question_id=q['id'], answer='6/16',
                       outcome='uncertain', assisted=False, created=101.0,
                       evaluation={'attempt_number': 1}))
    with TestClient(app, headers=HEADERS) as kid:
        signed = kid.post('/api/auth/login', json={'username': 'test-child', 'password': 'secure-child-pass-123'})
        assert signed.status_code == 200
        kid.headers['Authorization'] = 'Bearer ' + signed.json()['token']
        yield kid, uid, q['id']


def route(uid, qid):
    return f'/api/units/{uid}/questions/{qid}/recheck'


def check_no_recheck_writes():
    with DB() as db:
        for model in (AttemptAssessment, Activity, Job, Usage):
            assert db.scalar(select(func.count()).select_from(model)) == 0


def test_conditional_recheck_is_id_bound_idempotent_and_legacy_compatible(recheck_setup):
    kid, uid, qid = recheck_setup
    assert kid.get(f'/api/units/{uid}').json()['supports_recheck_attempt_id'] is True
    for _ in range(2):
        response = kid.post(route(uid, qid), json={'attempt_id': 'a' * 32})
        assert response.status_code == 200, response.text
        assert response.json()['attempt_id'] == 'a' * 32
    assert kid.post(route(uid, qid)).status_code == 200
    assert kid.post(route(uid, qid), json={}).status_code == 200
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(AttemptAssessment)) == 1
        assert db.get(Attempt, 'a' * 32).outcome == 'correct'


@pytest.mark.parametrize('numbers', [({}, {}), ({'attempt_number': 1}, {}),
                                      ({'attempt_number': 1}, {'attempt_number': 1}),
                                      ({'attempt_number': True}, {'attempt_number': 2})])
def test_incomplete_or_ambiguous_legacy_numbers_do_not_guess(recheck_setup, numbers):
    kid, uid, qid = recheck_setup
    with DB.begin() as db:
        db.get(Attempt, 'a' * 32).evaluation = numbers[0]
        db.add(Attempt(id='f' * 32, unit_id=uid, question_id=qid, answer='2/8', outcome='incorrect',
                       assisted=True, created=101.0, evaluation=numbers[1]))
    assert kid.post(route(uid, qid), json={'attempt_id': 'a' * 32}).status_code == 409
    check_no_recheck_writes()


def test_newer_number_wins_even_when_clock_moves_back(recheck_setup):
    kid, uid, qid = recheck_setup
    with DB.begin() as db:
        db.add(Attempt(id='0' * 32, unit_id=uid, question_id=qid, answer='6/16', outcome='uncertain',
                       assisted=True, created=100.0, evaluation={'attempt_number': 2}))
    assert kid.post(route(uid, qid), json={'attempt_id': 'a' * 32}).status_code == 409
    check_no_recheck_writes()
    latest = kid.post(route(uid, qid), json={'attempt_id': '0' * 32})
    assert latest.status_code == 200 and latest.json()['attempt_id'] == '0' * 32


def test_missing_foreign_and_invalid_ids_do_not_change_answers(recheck_setup, api, household):
    kid, uid, qid = recheck_setup
    _, child = household
    q = question()
    with DB.begin() as db:
        other = LearningUnit(child_id=child['id'], subject='Mathematik', topic='Brüche',
                             explanation=q['explanation'], questions=[q], status='paused',
                             provider='synthetic', synthetic=True)
        db.add(other)
        db.flush()
        db.add(Attempt(id='b' * 32, unit_id=other.id, question_id=qid, answer='6/16',
                       outcome='uncertain', assisted=False, evaluation={'attempt_number': 1}))
    assert kid.post(route(uid, qid), json={'attempt_id': 'b' * 32}).status_code == 409
    assert api.post(route(uid, qid), json={'attempt_id': 'a' * 32}).status_code == 403
    assert kid.post(route(uid, qid), json={'attempt_id': 'invalid'}).status_code == 422
    assert kid.post(route(uid, qid), json={'attempt_id': None}).status_code == 422
    check_no_recheck_writes()


def test_blocked_recheck_sees_answer_committed_under_unit_lock(recheck_setup):
    kid, uid, qid = recheck_setup
    authorization = kid.headers['Authorization']
    started = Event()

    def recheck_from_other_device():
        device = TestClient(app, headers={**HEADERS, 'Authorization': authorization})
        started.set()
        return device.post(route(uid, qid), json={'attempt_id': 'a' * 32})

    with ThreadPoolExecutor(max_workers=1) as pool:
        with DB.begin() as db:
            # Same write lock that the answer endpoint acquires before insert.
            db.execute(update(LearningUnit).where(LearningUnit.id == uid).values(status=LearningUnit.status))
            db.add(Attempt(id='0' * 32, unit_id=uid, question_id=qid, answer='2/8', outcome='incorrect',
                           assisted=True, created=101.0, evaluation={'attempt_number': 2}))
            db.flush()
            future = pool.submit(recheck_from_other_device)
            assert started.wait(5)
            Event().wait(0.2)
            assert not future.done()
        response = future.result(timeout=20)
    assert response.status_code == 409
    check_no_recheck_writes()
    with DB() as db:
        assert db.get(Attempt, 'a' * 32).outcome == 'uncertain'
        assert db.get(Attempt, '0' * 32).outcome == 'incorrect'
