"""Combined ledger + coaching behavior, without real child data."""
import copy

from schulpilot.db import DB, LearningUnit, UnitCoaching
from schulpilot.synthetic import CONTENT
from test_coaching import normal_unit as normal_unit
from test_coaching_encounter_order import make_round


def test_today_and_independent_subject_remain_accessible_with_unknown_coaching_time(normal_unit):
    client, root_id, material_id, _, kid = normal_unit
    with DB.begin() as db:
        root = db.get(LearningUnit, root_id)
        root.status = 'completed'
        root.completed = 1700000100
        db.add(UnitCoaching(unit_id=root_id, status='ready', report={'learning_goals': [
            {'id': 'g1', 'label': 'Brüche Lernziel', 'source_excerpt': CONTENT[:100]}]}))
        _, attempt = make_round(db, root, material_id, answered=1700000000, completed=1700000100,
                                prompt='Addiere 1/4 + 1/4.')
        attempt.created = float('inf')
        other = LearningUnit(child_id=kid['id'], subject='Biologie', topic='Pflanzen',
                             explanation=root.explanation, questions=copy.deepcopy(root.questions),
                             provider='synthetic', synthetic=True)
        db.add(other)
        db.flush()
        other_id = other.id
    response = client.get(f"/api/children/{kid['id']}/overview?compact=true")
    assert response.status_code == 200, response.text
    assert response.json()['practice_summary']['uncertain_tasks'] == 1
    assert response.json()['practice_summary']['independent_tasks'] == 0
    progress = next(p for p in response.json()['learning_paths'] if p['root_unit_id'] == root_id)
    assert not progress['secure_observation']
    assert progress['successful_check_dates'] == []
    start = client.post(f'/api/units/{other_id}/start')
    assert start.status_code == 200, start.text
