"""Tied legacy answers must not hide feedback or make it impossible to clear.

Until the response contract for ambiguous legacy ties is implemented, the
optional ambiguity/candidate fields below describe one possible explicit
representation; no historical answer is asserted to be the latest.
"""

import pytest
from schulpilot.db import DB, Activity, Attempt
from sqlalchemy import select

pytest_plugins = ("test_guided_feedback",)


@pytest.mark.xfail(strict=True, reason="Legacy timestamp ties disagree across detail, overview and acknowledgement")
def test_tied_different_questions_cannot_trap_unacknowledgeable_feedback(guided):
    kid, _, child_id, uid, questions = guided
    with DB.begin() as db:
        db.add_all([
            Attempt(id='e' * 32, unit_id=uid, question_id=questions[0]['id'], answer='wrong',
                    outcome='incorrect', assisted=False, created=100.0, evaluation={'attempt_number': 1}),
            Attempt(id='0' * 32, unit_id=uid, question_id=questions[0]['id'], answer='wrong again',
                    outcome='incorrect', assisted=True, created=101.0, evaluation={'attempt_number': 2}),
            Attempt(id='f' * 32, unit_id=uid, question_id=questions[1]['id'], answer='other',
                    outcome='incorrect', assisted=False, created=101.0, evaluation={'attempt_number': 1}),
            Activity(child_id=child_id, unit_id=uid, kind='feedback_pending', detail={'attempt_id': '0' * 32}),
        ])
    response = kid.get(f'/api/units/{uid}')
    assert response.status_code == 200
    pending = response.json()['pending_feedback']
    resume = kid.get(f'/api/children/{child_id}/overview?compact=true')
    assert resume.status_code == 200
    if pending is None:
        # A future implementation may expose the candidates separately, but
        # must not silently hide the explicitly marked unanswered feedback.
        assert response.json()['feedback_order_ambiguous'] is True
        assert '0' * 32 in [item['attempt_id'] for item in response.json()['feedback_candidates']]
        continuation = kid.post(f"/api/units/{uid}/questions/{questions[0]['id']}/answer",
                                json={'answer': 'another synthetic answer', 'guided_feedback': True})
        assert continuation.status_code == 200
    else:
        assert resume.json()['feedback_resume']['id'] == uid
        ack = kid.post(f'/api/units/{uid}/feedback/acknowledge', json={'attempt_id': pending['attempt_id']})
        assert ack.status_code == 200


@pytest.mark.xfail(strict=True, reason="Question-local attempt numbers are not used consistently for tied feedback")
def test_same_question_tied_attempts_with_proven_order_can_be_acknowledged(guided):
    kid, _, child_id, uid, questions = guided
    with DB.begin() as db:
        db.add_all([
            Attempt(id='f' * 32, unit_id=uid, question_id=questions[0]['id'], answer='first',
                    outcome='incorrect', assisted=False, created=101.0, evaluation={'attempt_number': 1}),
            Attempt(id='0' * 32, unit_id=uid, question_id=questions[0]['id'], answer='second',
                    outcome='incorrect', assisted=True, created=101.0, evaluation={'attempt_number': 2}),
            Activity(child_id=child_id, unit_id=uid, kind='feedback_pending', detail={'attempt_id': '0' * 32}),
        ])
    detail = kid.get(f'/api/units/{uid}').json()
    assert detail['pending_feedback']['attempt_id'] == '0' * 32
    overview = kid.get(f'/api/children/{child_id}/overview?compact=true').json()
    assert overview['feedback_resume'] is not None
    assert overview['feedback_resume']['id'] == uid
    assert kid.post(f'/api/units/{uid}/feedback/acknowledge', json={'attempt_id': '0' * 32}).status_code == 200


def test_equal_timestamp_records_cannot_prove_which_different_question_came_last():
    # Both possible histories produce exactly the same persisted evidence.
    # Random UUID ordering and the two question-local attempt numbers cannot
    # establish global chronology, even when one attempt has a marker.
    first = {'id': 'f' * 32, 'question_id': 'a', 'created': 101.0, 'attempt_number': 2}
    second = {'id': '0' * 32, 'question_id': 'b', 'created': 101.0, 'attempt_number': 1}
    marker = {'kind': 'feedback_pending', 'attempt_id': first['id'], 'created': 101}

    def persisted(order):
        return sorted(order, key=lambda item: item['id']), [marker.copy()]

    assert persisted([first, second]) == persisted([second, first])
    assert [first, second][-1]['id'] != [second, first][-1]['id']


@pytest.mark.xfail(strict=True, reason="Another unread tied marker is not offered after the first acknowledgement")
def test_acknowledging_one_ambiguous_marker_keeps_other_accessible(guided):
    kid, _, child_id, uid, questions = guided
    with DB.begin() as db:
        for index, marker in enumerate(('0' * 32, 'f' * 32)):
            db.add(Attempt(id=marker, unit_id=uid, question_id=questions[index]['id'], answer='synthetic',
                           outcome='incorrect', assisted=False, created=101.0, evaluation={'attempt_number': 1}))
            db.add(Activity(child_id=child_id, unit_id=uid, kind='feedback_pending', detail={'attempt_id': marker}))
    detail = kid.get(f'/api/units/{uid}').json()
    first = detail['pending_feedback']['attempt_id']
    assert kid.post(f'/api/units/{uid}/feedback/acknowledge', json={'attempt_id': first}).status_code == 200
    other = '0' * 32 if first == 'f' * 32 else 'f' * 32
    detail = kid.get(f'/api/units/{uid}').json()
    pending = detail.get('pending_feedback')
    candidates = detail.get('feedback_candidates') or []
    with DB() as db:
        events = list(db.scalars(select(Activity).where(Activity.unit_id == uid)))
        assert any(event.kind == 'feedback_pending' and event.detail['attempt_id'] == other for event in events)
        assert not any(event.kind == 'feedback_seen' and event.detail['attempt_id'] == other for event in events)
    assert (pending and pending['attempt_id'] == other) or any(item['attempt_id'] == other for item in candidates)
