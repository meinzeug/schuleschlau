"""Tied legacy answers must not hide feedback or make it impossible to clear.

Until the response contract for ambiguous legacy ties is implemented, the
optional ambiguity/candidate fields below describe one possible explicit
representation; no historical answer is asserted to be the latest.
"""

import pytest
from schulpilot.db import DB, Activity, Attempt

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
