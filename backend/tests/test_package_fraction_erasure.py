"""Only synthetic source/plan examples; deletion follows existing owner paths."""
import copy

from sqlalchemy import select
from schulpilot import erasure, package_fraction_reservation as reservation
from schulpilot.db import DB, Job, Material, SchoolDay
from test_package_fraction_reservation import running_job


def _saved_plan(api, household):
    day_id, job_id, request = running_job(api, household)
    with DB.begin() as db:
        plan = reservation.prepare(db, job_id, request)['package_fraction_plan']
        job = db.get(Job, job_id)
        material_id = job.payload['package_partition_sources'][0]['id']
        job.status = 'completed'
    return day_id, job_id, material_id, plan


def test_deleting_own_page_scrubs_only_its_source_bound_job_plan(api, household):
    _, job_id, material_id, plan = _saved_plan(api, household)
    with DB.begin() as db:
        job = db.get(Job, job_id)
        other = Job(child_id=job.child_id, kind='package', status='completed', idempotency='other-source-plan',
                    payload={'package_partition_sources': [{'id': 'f' * 32, 'revision': 1}],
                             'package_fraction_plan': copy.deepcopy(plan)})
        db.add(other); db.flush(); other_id = other.id
    response = api.delete(f'/api/materials/{material_id}')
    assert response.status_code == 200, response.text
    with DB() as db:
        assert db.get(Material, material_id) is None
        assert 'package_fraction_plan' not in db.get(Job, job_id).payload
        assert db.get(Job, other_id).payload['package_fraction_plan'] == plan


def test_restore_replay_scrubs_plan_even_when_page_row_already_missing(api, household):
    day_id, job_id, material_id, plan = _saved_plan(api, household)
    with DB.begin() as db:
        day = db.get(SchoolDay, day_id)
        day.preparation = {**day.preparation, 'package_outputs': {'0': {'job_id': job_id, 'private_plan': plan}}}
        page = db.get(Material, material_id)
        db.delete(page)
        db.flush()
        erasure.reconcile(db, [{'scope': 'material', 'target': material_id}])
        db.flush()
        assert 'package_fraction_plan' not in db.get(Job, job_id).payload
        assert 'package_outputs' not in db.get(SchoolDay, day_id).preparation


def test_restore_replay_scrubs_plan_and_existing_page(api, household):
    _, job_id, material_id, _ = _saved_plan(api, household)
    with DB.begin() as db:
        erasure.reconcile(db, [{'scope': 'material', 'target': material_id}])
        db.flush()
        assert db.get(Material, material_id) is None
        assert 'package_fraction_plan' not in db.get(Job, job_id).payload


def test_restore_replay_scrubs_plan_with_corrupt_source_list(api, household):
    _, job_id, material_id, _ = _saved_plan(api, household)
    with DB.begin() as db:
        job = db.get(Job, job_id)
        job.payload = {**job.payload, 'package_partition_sources': None}
        db.delete(db.get(Material, material_id))
        db.flush()
        erasure.reconcile(db, [{'scope': 'material', 'target': material_id}])
        db.flush()
        assert 'package_fraction_plan' not in db.get(Job, job_id).payload
