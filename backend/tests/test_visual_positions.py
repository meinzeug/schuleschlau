"""Artificial private reading positions, never answer or time evidence."""
import copy

import pytest
from schulpilot.db import DB, Activity, Attempt, LearningMemory, LearningUnit, Material, User
from schulpilot.visual_positions import export_user
from schulpilot.visual_reference_models import UnitVisualPosition, UnitVisualSnapshot
from test_visual_references import generated_visual_unit as original_generated_visual_unit


@pytest.fixture
def visual(api, household):
    api.headers['X-Schulpilot-Account'] = household[0]['id']
    return original_generated_visual_unit.__wrapped__(household)


def read(api, uid):
    return api.get(f"/api/units/{uid}/visual-position")


def value(api, uid, **changes):
    data = read(api, uid).json()
    result = {"source_signature": data["source_signature"], "revision": data["revision"],
              "position": {"explanation_kind": "intro", "question_id": None, "explanation_step_id": "e1",
                           "graphic_index": 0, "graphic_phase": "fraction-bar-numerator"}}
    result.update(changes)
    return result


def save(api, uid, body):
    return api.put(f"/api/units/{uid}/visual-position", json=body)


def test_position_read_is_empty_and_write_cas_keeps_answers_time_and_unit_unchanged(api, visual):
    uid, _, _ = visual
    with DB() as db:
        original = copy.deepcopy(db.get(LearningUnit, uid).questions)
        before = db.query(Attempt).count(), db.query(Activity).count()
    assert read(api, uid).json()["position"] is None
    body = value(api, uid)
    response = save(api, uid, body)
    assert response.status_code == 200, response.text
    assert response.json()["revision"] == 1
    assert read(api, uid).json()["position"] == body["position"]
    assert save(api, uid, body).status_code == 409
    with DB() as db:
        assert before == (db.query(Attempt).count(), db.query(Activity).count())
        assert db.get(LearningUnit, uid).questions == original
        user_id = db.query(UnitVisualPosition).one().user_id
        assert export_user(db, user_id)[0]["position"] == body["position"]
        assert export_user(db, "f" * 32) == []


@pytest.mark.parametrize("change", [{"graphic_index": 1}, {"graphic_phase": "scene-0"},
    {"graphic_phase": "science-0"}, {"explanation_step_id": "unknown"},
    {"question_id": "q1"}, {"explanation_kind": "question", "question_id": "missing"}])
def test_position_rejects_unknown_step_or_graphic_without_write(api, visual, change):
    uid, _, _ = visual
    body = value(api, uid)
    body["position"].update(change)
    assert save(api, uid, body).status_code in (409, 422)
    with DB() as db:
        assert db.query(UnitVisualPosition).count() == 0


def test_source_replacement_invalidates_position_on_read_without_deleting_or_mutating_it(api, visual):
    uid, mid, _ = visual
    assert save(api, uid, value(api, uid)).status_code == 200
    with DB.begin() as db:
        db.get(Material, mid).revision += 1
    before = read(api, uid).json()
    assert before == {"source_signature": None, "revision": 0, "position": None}
    with DB() as db:
        assert db.query(UnitVisualPosition).count() == 1
    body = {"source_signature": "f" * 64, "revision": 0, "position": value(api, uid)["position"]}
    assert save(api, uid, body).status_code == 409


def test_positions_are_private_to_authenticated_user_and_delete_with_unit(api, visual, household):
    uid, _, _ = visual
    save(api, uid, value(api, uid))
    with DB.begin() as db:
        another = User(username="other@example.org", email="other@example.org", password_hash="unused", display_name="Other", role="parent", verified=True)
        db.add(another)
        db.flush()
        db.add(UnitVisualPosition(unit_id=uid, user_id=another.id, source_signature="f" * 64, revision=99,
                                  position={"private": "not returned"}, updated=1))
    assert read(api, uid).json()["revision"] == 1
    with DB.begin() as db:
        db.delete(db.get(LearningUnit, uid))
    with DB() as db:
        assert db.query(UnitVisualPosition).count() == 0


def test_explicit_save_expires_only_own_old_positions(api, visual):
    uid, _, _ = visual
    save(api, uid, value(api, uid))
    with DB.begin() as db:
        row = db.query(UnitVisualPosition).one()
        row.updated = 1
    assert read(api, uid).json()["revision"] == 0
    assert save(api, uid, value(api, uid)).status_code == 200
    assert read(api, uid).json()["revision"] == 1


def test_child_cannot_restore_hidden_question_solution_until_explicit_explanation(api, visual):
    uid, _, _ = visual
    login = api.post('/api/auth/login', json={'username': 'test-child', 'password': 'secure-child-pass-123'})
    assert login.status_code == 200
    api.headers['Authorization'] = 'Bearer ' + login.json()['token']
    api.headers['X-Schulpilot-Account'] = login.json()['user']['id']
    body = value(api, uid)
    body['position'].update(explanation_kind='question', question_id='q1')
    assert save(api, uid, body).status_code == 409
    assert api.post(f'/api/units/{uid}/explanation', json={'question_id': 'q1'}).status_code == 200
    assert save(api, uid, body).status_code == 200
    with DB() as db:
        assert db.query(Attempt).count() == 0
        assert db.query(Activity).filter(Activity.kind == 'explanation').count() == 1


def test_explicit_intro_before_entry_probe_can_save_only_its_opened_graphic(api, visual, household):
    from schulpilot import competences
    from schulpilot.learning import unit_data

    uid, mid, cid = visual
    with DB.begin() as db:
        unit, material = db.get(LearningUnit, uid), db.get(Material, mid)
        unit.status, unit.round_kind = 'active', 'learning'
        source = competences.source_ref(db, material)
        assert source is not None
        entry = {'version': 1, 'catalog_version': competences.VERSION, 'source_refs': [source],
            'source_signature': competences.fingerprint([source]), 'entry_mode': 'prerequisite_probe',
            'competence_ids': [], 'questions': [{'id': 'q1', 'role': 'prior_check', 'competence_id': None}]}
        db.add(LearningMemory(unit_id=uid, child_id=cid, source_signature='a' * 64,
            working={'entry_plan': entry}, decision={}))
        db.flush()
        assert unit_data(db, unit)['explanation_steps'] == []
    login = api.post('/api/auth/login', json={'username': 'test-child', 'password': 'secure-child-pass-123'})
    assert login.status_code == 200
    api.headers['Authorization'] = 'Bearer ' + login.json()['token']
    api.headers['X-Schulpilot-Account'] = login.json()['user']['id']
    other_uid, _, _ = original_generated_visual_unit.__wrapped__(household)
    body = value(api, uid)
    assert save(api, uid, body).status_code == 409
    # Historical events have no evidence of the graphic that was opened.
    with DB.begin() as db:
        db.add(Activity(child_id=cid, unit_id=uid, kind='explanation', detail={'text': 'legacy'}))
    assert save(api, uid, body).status_code == 409
    assert api.post(f'/api/units/{other_uid}/explanation').status_code == 200
    assert save(api, uid, body).status_code == 409
    # Opening a question is not permission to reopen the separate intro.
    assert api.post(f'/api/units/{uid}/explanation', json={'question_id': 'q1'}).status_code == 200
    assert save(api, uid, body).status_code == 409
    opened = api.post(f'/api/units/{uid}/explanation')
    assert opened.status_code == 200 and opened.json()['explanation_steps'][0]['id'] == 'e1'
    response = save(api, uid, body)
    assert response.status_code == 200, response.text
    assert response.json()['position'] == body['position']
    assert read(api, uid).json()['position'] == body['position']
    wrong_step = value(api, uid)
    wrong_step['position']['explanation_step_id'] = 'not-opened'
    assert save(api, uid, wrong_step).status_code == 409
    with DB.begin() as db:
        assert db.query(Attempt).count() == 0
        assert db.query(Activity).filter(Activity.kind == 'explanation', Activity.unit_id == uid).count() == 3
        assert db.get(LearningUnit, uid).active_seconds == 0
        db.get(LearningUnit, uid).explanation += ' Geänderte Erklärung.'
    body['revision'] = 1
    assert save(api, uid, body).status_code == 409
    assert api.post(f'/api/units/{uid}/explanation').status_code == 200
    assert save(api, uid, body).status_code == 200
    body['revision'] = 2
    with DB.begin() as db:
        row = db.get(UnitVisualSnapshot, uid)
        changed = copy.deepcopy(row.steps)
        changed[0]['text'] += ' Geänderter Grafikschritt.'
        row.steps = changed
    assert save(api, uid, body).status_code == 409
    assert api.post(f'/api/units/{uid}/explanation').status_code == 200
    assert save(api, uid, body).status_code == 200
    body['revision'] = 3
    with DB.begin() as db:
        db.get(Material, mid).revision += 1
    assert read(api, uid).json()['position'] is None
    assert save(api, uid, body).status_code == 409


def test_positions_are_bounded_to_eight_and_do_not_delete_another_users_state(api, household):
    api.headers['X-Schulpilot-Account'] = household[0]['id']
    ids=[]
    for _ in range(9):
        uid, _, _ = original_generated_visual_unit.__wrapped__(household)
        ids.append(uid)
        assert save(api, uid, value(api, uid)).status_code == 200
    with DB() as db:
        assert db.query(UnitVisualPosition).count() == 8
        assert db.get(UnitVisualPosition, (ids[-1], db.query(UnitVisualPosition).first().user_id)) is not None


def test_cross_tab_actor_mismatch_cannot_read_or_save_another_accounts_position(api, visual):
    uid, _, _ = visual
    body = value(api, uid)
    api.headers['X-Schulpilot-Account'] = 'f' * 32
    assert read(api, uid).status_code == 409
    assert save(api, uid, body).status_code == 409
    with DB() as db:
        assert db.query(UnitVisualPosition).count() == 0
