"""Tied legacy answers must not hide feedback or make it impossible to clear.

Until the response contract for ambiguous legacy ties is implemented, the
optional ambiguity/candidate fields below describe one possible explicit
representation; no historical answer is asserted to be the latest.
"""

import pytest
from schulpilot.db import DB, Activity, Attempt, LearningUnit
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


@pytest.mark.parametrize('invalid', [None, 0, -1, '2', 2.0, True, 1])
def test_ambiguous_same_question_numbers_are_not_used_as_ordering_proof(guided, invalid):
    from schulpilot.learning import pending_feedback

    _, _, _, uid, questions = guided
    with DB.begin() as db:
        attempts = [
            Attempt(id='0' * 32, unit_id=uid, question_id=questions[0]['id'], answer='first',
                    outcome='incorrect', assisted=False, created=101.0, evaluation={'attempt_number': 1}),
            Attempt(id='f' * 32, unit_id=uid, question_id=questions[0]['id'], answer='second',
                    outcome='incorrect', assisted=False, created=101.0, evaluation={'attempt_number': invalid}),
        ]
        # Legacy ambiguous fallback is preserved, not silently recast as proof.
        event = Activity(unit_id=uid, kind='feedback_pending', detail={'attempt_id': attempts[0].id})
        unit = db.get(LearningUnit, uid)
        assert pending_feedback(unit, attempts, [event]) is None


def test_same_question_tie_does_not_resume_an_older_marked_attempt(guided):
    kid, _, child_id, uid, questions = guided
    with DB.begin() as db:
        db.add_all([
            Attempt(id='f' * 32, unit_id=uid, question_id=questions[0]['id'], answer='old',
                    outcome='incorrect', assisted=False, created=101.0, evaluation={'attempt_number': 1}),
            Attempt(id='0' * 32, unit_id=uid, question_id=questions[0]['id'], answer='new',
                    outcome='incorrect', assisted=True, created=101.0, evaluation={'attempt_number': 2}),
            Activity(child_id=child_id, unit_id=uid, kind='feedback_pending', detail={'attempt_id': 'f' * 32}),
        ])
    assert kid.get(f'/api/units/{uid}').json()['pending_feedback'] is None
    assert kid.get(f'/api/children/{child_id}/overview?compact=true').json()['feedback_resume'] is None
    assert kid.post(f'/api/units/{uid}/feedback/acknowledge', json={'attempt_id': 'f' * 32}).status_code == 409


def test_newer_feedback_in_another_unit_remains_first(guided):
    from schulpilot.synthetic import sample_unit

    kid, _, child_id, uid, questions = guided
    with DB.begin() as db:
        newer = LearningUnit(child_id=child_id, **sample_unit(), provider='fixture', synthetic=True,
                             status='active', introduction_seen=True)
        db.add(newer)
        db.flush()
        db.add_all([
            Attempt(id='f' * 32, unit_id=uid, question_id=questions[0]['id'], answer='old',
                    outcome='incorrect', assisted=False, created=101.0, evaluation={'attempt_number': 1}),
            Attempt(id='0' * 32, unit_id=uid, question_id=questions[0]['id'], answer='new',
                    outcome='incorrect', assisted=True, created=101.0, evaluation={'attempt_number': 2}),
            Activity(child_id=child_id, unit_id=uid, kind='feedback_pending', detail={'attempt_id': '0' * 32}),
            Attempt(id='1' * 32, unit_id=newer.id, question_id=newer.questions[0]['id'], answer='later',
                    outcome='incorrect', assisted=False, created=102.0, evaluation={'attempt_number': 1}),
            Activity(child_id=child_id, unit_id=newer.id, kind='feedback_pending', detail={'attempt_id': '1' * 32}),
        ])
        newer_id = newer.id
    overview = kid.get(f'/api/children/{child_id}/overview?compact=true').json()
    assert overview['feedback_resume']['id'] == newer_id
    assert kid.post(f'/api/units/{newer_id}/feedback/acknowledge', json={'attempt_id': '1' * 32}).status_code == 200
    assert kid.get(f'/api/children/{child_id}/overview?compact=true').json()['feedback_resume']['id'] == uid


@pytest.mark.parametrize('old_id,new_id', [('f' * 32, '0' * 32), ('0' * 32, 'f' * 32)])
def test_invalid_newer_tie_does_not_hide_valid_older_unit(guided, old_id, new_id):
    from schulpilot.synthetic import sample_unit

    kid, _, child_id, uid, questions = guided
    with DB.begin() as db:
        other = LearningUnit(child_id=child_id, **sample_unit(), provider='fixture', synthetic=True,
                             status='active', introduction_seen=True)
        db.add(other)
        db.flush()
        db.add_all([
            Attempt(id=old_id, unit_id=uid, question_id=questions[0]['id'], answer='old marked',
                    outcome='incorrect', assisted=False, created=101.0, evaluation={'attempt_number': 1}),
            Attempt(id=new_id, unit_id=uid, question_id=questions[0]['id'], answer='new unmarked',
                    outcome='incorrect', assisted=True, created=101.0, evaluation={'attempt_number': 2}),
            Activity(child_id=child_id, unit_id=uid, kind='feedback_pending', detail={'attempt_id': old_id}),
            Attempt(id='1' * 32, unit_id=other.id, question_id=other.questions[0]['id'], answer='older unit',
                    outcome='incorrect', assisted=False, created=100.0, evaluation={'attempt_number': 1}),
            Activity(child_id=child_id, unit_id=other.id, kind='feedback_pending', detail={'attempt_id': '1' * 32}),
        ])
        other_id = other.id
    assert kid.get(f'/api/units/{uid}').json()['pending_feedback'] is None
    assert kid.get(f'/api/children/{child_id}/overview?compact=true').json()['feedback_resume']['id'] == other_id


def test_many_invalid_newer_units_do_not_hide_valid_older_feedback(guided):
    from schulpilot.db import engine
    from schulpilot.learning import feedback_resume_id
    from schulpilot.synthetic import sample_unit
    from sqlalchemy import event

    kid, _, child_id, uid, questions = guided
    with DB.begin() as db:
        db.add_all([
            Attempt(id='1' * 32, unit_id=uid, question_id=questions[0]['id'], answer='older',
                    outcome='incorrect', assisted=False, created=100.0, evaluation={'attempt_number': 1}),
            Activity(child_id=child_id, unit_id=uid, kind='feedback_pending', detail={'attempt_id': '1' * 32}),
        ])
        for index in range(33):
            unit = LearningUnit(child_id=child_id, **sample_unit(), provider='fixture', synthetic=True,
                                status='active', introduction_seen=True)
            db.add(unit)
            db.flush()
            marked_id = f'{index + 1:031x}f'
            unmarked_id = f'{index + 1:031x}0'
            db.add_all([
                Attempt(id=marked_id, unit_id=unit.id, question_id=unit.questions[0]['id'], answer='old',
                        outcome='incorrect', assisted=False, created=101.0, evaluation={'attempt_number': 1}),
                Attempt(id=unmarked_id, unit_id=unit.id, question_id=unit.questions[0]['id'], answer='new',
                        outcome='incorrect', assisted=True, created=101.0, evaluation={'attempt_number': 2}),
                Activity(child_id=child_id, unit_id=unit.id, kind='feedback_pending', detail={'attempt_id': marked_id}),
            ])
    statements = []

    def count_queries(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(engine, 'before_cursor_execute', count_queries)
    try:
        with DB() as db:
            assert feedback_resume_id(db, child_id) == uid
    finally:
        event.remove(engine, 'before_cursor_execute', count_queries)
    # At most 16 normal tied candidates plus the bounded untied fallback are
    # inspected. This fixture needs one fallback candidate, not all 33 units.
    assert len(statements) <= 60
    resume = kid.get(f'/api/children/{child_id}/overview?compact=true').json()['feedback_resume']
    assert resume is not None
    assert resume['id'] == uid
    assert kid.get(f'/api/units/{uid}').json()['pending_feedback']['attempt_id'] == '1' * 32
    with DB() as db:
        events = list(db.scalars(select(Activity).where(Activity.child_id == child_id,
                                                         Activity.kind.in_(('feedback_pending', 'feedback_seen')))))
        assert sum(event.kind == 'feedback_pending' for event in events) == 34
        assert not any(event.kind == 'feedback_seen' for event in events)


def test_feedback_overview_fallback_has_a_fixed_query_ceiling(guided):
    from schulpilot.db import engine
    from schulpilot.learning import feedback_resume_id
    from schulpilot.synthetic import sample_unit
    from sqlalchemy import event

    _, _, child_id, _, _ = guided
    with DB.begin() as db:
        for index in range(40):
            unit = LearningUnit(child_id=child_id, **sample_unit(), provider='fixture', synthetic=True,
                                status='active', introduction_seen=True)
            db.add(unit)
            db.flush()
            marked_id = f'{index + 100:031x}f'
            # Newer tied candidates all point at a superseded attempt. Older
            # untied candidates point at a missing question, as can occur in
            # legacy data. Neither is a usable result.
            qid = unit.questions[0]['id'] if index < 20 else 'missing-legacy-question'
            db.add(Attempt(id=marked_id, unit_id=unit.id, question_id=qid, answer='old',
                           outcome='incorrect', assisted=False, created=101.0 if index < 20 else 100.0,
                           evaluation={'attempt_number': 1}))
            db.add(Activity(child_id=child_id, unit_id=unit.id, kind='feedback_pending',
                            detail={'attempt_id': marked_id}))
            if index < 20:
                db.add(Attempt(id=f'{index + 100:031x}0', unit_id=unit.id, question_id=qid, answer='new',
                               outcome='incorrect', assisted=True, created=101.0,
                               evaluation={'attempt_number': 2}))
    statements = []

    def count_queries(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(engine, 'before_cursor_execute', count_queries)
    try:
        with DB() as db:
            assert feedback_resume_id(db, child_id) is None
    finally:
        event.remove(engine, 'before_cursor_execute', count_queries)
    # Two regular candidate queries, one fallback query, at most three reads
    # each for 16 normal candidates and one read each for 16 fallback units.
    assert len(statements) <= 67


def test_conflicting_earlier_number_is_not_used_as_ordering_proof(guided):
    from schulpilot.learning import pending_feedback

    _, _, _, uid, questions = guided
    with DB.begin() as db:
        attempts = [
            Attempt(id='a' * 32, unit_id=uid, question_id=questions[0]['id'], answer='older',
                    outcome='incorrect', assisted=False, created=100.0, evaluation={'attempt_number': 1}),
            Attempt(id='0' * 32, unit_id=uid, question_id=questions[0]['id'], answer='tie',
                    outcome='incorrect', assisted=False, created=101.0, evaluation={'attempt_number': 2}),
            Attempt(id='f' * 32, unit_id=uid, question_id=questions[0]['id'], answer='duplicate',
                    outcome='incorrect', assisted=False, created=101.0, evaluation={'attempt_number': 1}),
        ]
        event = Activity(unit_id=uid, kind='feedback_pending', detail={'attempt_id': attempts[1].id})
        assert pending_feedback(db.get(LearningUnit, uid), attempts, [event]) is None


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
