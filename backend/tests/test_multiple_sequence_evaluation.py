"""A narrow numeric sequence is checked independently of a model's answer key."""

import pytest

from schulpilot.answer_evaluation import evaluate


def question(prompt="Übung: Die Vielfachen von 5 beginnen mit 5;10;15;20. Welche Zahl kommt als Nächstes?", key="25"):
    return {"type": "short", "prompt": prompt, "answer": key, "accepted": []}


def test_explicit_sequence_is_assessed_and_does_not_disclose_answer():
    assert evaluate(question(), "25")["outcome"] == "correct"
    wrong = evaluate(question(), "23")
    assert wrong["outcome"] == "incorrect"
    assert wrong["method"] == "explicit_multiple_sequence_v1"
    assert "25" not in wrong["reason"]


def test_different_and_multidigit_factors_are_independently_computed():
    q = question("Die Vielfachen von 7 beginnen mit 7; 14; 21. Welche Zahl kommt als Nächstes?", "28")
    assert evaluate(q, "28")["outcome"] == "correct"
    assert evaluate(q, "29")["outcome"] == "incorrect"


def test_latex_inline_delimiters_do_not_hide_the_integer_sequence():
    q = question(r"Übung: Die Vielfachen von \(7\) beginnen mit \(7;14;21\). Welche Zahl kommt als Nächstes?", "28")
    assert evaluate(q, "28")["outcome"] == "correct"
    wrong = evaluate(q, "29")
    assert wrong["outcome"] == "incorrect"
    assert wrong["method"] == "explicit_multiple_sequence_v1"
    assert "28" not in wrong["reason"]


@pytest.mark.parametrize("prompt", [
    r"Die Vielfachen von \(7 beginnen mit \(7;14;21\). Welche Zahl kommt als Nächstes?",
    r"Die Vielfachen von \(7\) beginnen mit \(7;14;21+1\). Welche Zahl kommt als Nächstes?",
    r"Die Vielfachen von \(7\) beginnen mit \(7;14;20\). Welche Zahl kommt als Nächstes?",
])
def test_latex_format_never_makes_incomplete_or_inconsistent_math_valid(prompt):
    assert evaluate(question(prompt, "28"), "29")["outcome"] == "uncertain"


def test_ambiguous_or_inconsistent_sequence_and_key_stay_uncertain():
    bad_sequence = question("Die Vielfachen von 5 beginnen mit 5;10;14;20. Welche Zahl kommt als Nächstes?")
    assert evaluate(bad_sequence, "23")["outcome"] == "uncertain"
    assert evaluate(question(key="23"), "24")["outcome"] == "uncertain"
    assert evaluate(question(key="23"), "23")["outcome"] == "uncertain"
    assert evaluate(question(), "etwa fünfundzwanzig")["outcome"] == "uncertain"
    assert evaluate(question("Nenne ein Vielfaches von 5."), "58")["outcome"] == "uncertain"


def test_explicit_recheck_preserves_old_verdict_and_does_not_create_attempts_or_jobs(api, household):
    from conftest import HEADERS
    from fastapi.testclient import TestClient
    from schulpilot.db import DB, Attempt, AttemptAssessment, Job, LearningUnit, Usage
    from schulpilot.main import app
    from sqlalchemy import func, select

    _, child = household
    q = {**question(r"Übung: Die Vielfachen von \(7\) beginnen mit \(7;14;21\). Welche Zahl kommt als Nächstes?", "28"),
         'id': 'q1', 'options': [], 'hints': ['Zähle weiter.'], 'explanation': 'Addiere die Schrittweite.'}
    with DB.begin() as db:
        unit = LearningUnit(child_id=child['id'], subject='Mathematik', topic='Künstliche Vielfache',
                            questions=[q], explanation=q['explanation'], provider='synthetic', synthetic=True,
                            status='paused', active_seconds=23)
        db.add(unit)
        db.flush()
        uid = unit.id
        attempt = Attempt(unit_id=uid, question_id=q['id'], answer='29', outcome='uncertain', assisted=True,
                          evaluation={'method': 'subject_rules_v8', 'outcome': 'uncertain', 'attempt_number': 1,
                                      'independent_attempt': False, 'support_reasons': ['hint']})
        db.add(attempt)
        db.flush()
        aid = attempt.id
        db.add(AttemptAssessment(attempt_id=aid, rules_version='subject_rules_v8', previous_outcome='uncertain',
                                 outcome='uncertain', previous_evaluation=attempt.evaluation,
                                 evaluation=attempt.evaluation, actor_id=None))
    route = f'/api/units/{uid}/questions/q1/recheck'
    with TestClient(app, headers=HEADERS) as kid:
        login = kid.post('/api/auth/login', json={'username': 'test-child', 'password': 'secure-child-pass-123'}).json()
        kid.headers['Authorization'] = 'Bearer ' + login['token']
        for _ in range(2):
            response = kid.post(route)
            assert response.status_code == 200, response.text
            assert response.json()['outcome'] == 'incorrect'
    with DB() as db:
        saved = db.get(Attempt, aid)
        assert saved.answer == '29' and saved.outcome == 'incorrect' and saved.assisted
        assert saved.evaluation['support_reasons'] == ['hint']
        history = list(db.scalars(select(AttemptAssessment).where(AttemptAssessment.attempt_id == aid)))
        assert {item.rules_version for item in history} == {'subject_rules_v8', 'subject_rules_v9'}
        assert next(item for item in history if item.rules_version == 'subject_rules_v8').outcome == 'uncertain'
        assert db.get(LearningUnit, uid).active_seconds == 23
        assert db.scalar(select(func.count()).select_from(Attempt)) == 1
        for model in (Job, Usage):
            assert db.scalar(select(func.count()).select_from(model)) == 0
