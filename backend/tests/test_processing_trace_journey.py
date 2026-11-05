"""One artificial image from upload to a stored supported learning answer.

The normal APIs, DB, worker and post-provider validators are real. The model
transport alone is a deterministic synthetic fixture: this test is not a
claim about live OCR accuracy, provider availability, or all subject formats.
"""
import copy

from conftest import HEADERS
from fastapi.testclient import TestClient
from schulpilot.db import DB, Activity, Attempt, Job, LearningUnit, Mastery, Material, SchoolDay, UnitSource, Usage
from schulpilot.main import app
from schulpilot.providers import Result
from schulpilot.school_preparation import _advance, advance_one
from schulpilot.source_lineage_models import SourceImageReceipt, SourceRevision
from schulpilot.visual_reference_models import UnitVisualSnapshot
from schulpilot.worker import claim, process
from sqlalchemy import func, select
from test_material_auto_review import operator as operator
from test_material_auto_review import pipeline as pipeline
from test_material_auto_review import reading, upload
from test_package_parts_worker import CASE, bounded_output


def test_upload_review_package_visual_answer_trace_is_private_and_read_only_on_get(pipeline, operator, monkeypatch):
    api, child = pipeline['api'], pipeline['child']
    day = api.post(f"/api/children/{child['id']}/school-day/today").json()
    page = upload(pipeline, day)
    pipeline['outputs'][:] = [
        reading(CASE['source'], subject=CASE['subject'], topic='Künstlicher Wasserkreislauf'),
        reading(CASE['source'], subject=CASE['subject'], topic='Künstlicher Wasserkreislauf'),
    ]
    assert api.post(f"/api/school-days/{day['id']}/prepare", headers={'Idempotency-Key': 'synthetic-trace'}).status_code == 202
    extract_jobs = []
    for _ in range(2):
        advance_one()
        with DB() as db:
            job_id = claim(db)
            assert job_id
            extract_jobs.append(job_id)
        process(job_id)
    with DB() as db:
        material = db.get(Material, page['id'])
        image = db.get(SourceImageReceipt, material.id)
        versions = list(db.scalars(select(SourceRevision).where(SourceRevision.material_id == material.id)
            .order_by(SourceRevision.sequence)))
        assert image and len(image.image_digest) == 64 and image.normalization_version
        assert [v.cause for v in versions] == ['extraction', 'auto_check_reading', 'auto_check']
        assert [versions[0].receipt['job_id'], versions[1].receipt['job_id']] == extract_jobs
        assert versions[2].receipt['first_snapshot_id'] == versions[0].id
        assert versions[2].receipt['second_snapshot_id'] == versions[1].id
        assert all(len(v.digest) == 64 for v in versions)
        for version, identifier in zip(versions[:2], extract_jobs, strict=True):
            usage = db.scalar(select(Usage).where(Usage.job_id == identifier))
            assert version.receipt['usage_id'] == usage.id
            assert (version.receipt['provider'], version.receipt['model']) == (usage.provider, usage.model)
            assert len(version.receipt['base_prompt_digest']) == 64
            assert len(version.receipt['base_schema_digest']) == 64
            assert version.receipt['effective_request']['status'] == 'not_reported'
        assert material.confirmed and material.revision == versions[-1].revision
        assert all(db.get(Job, identifier).status == 'completed' for identifier in extract_jobs)
        assert all(db.scalar(select(Usage).where(Usage.job_id == identifier)).status == 'completed' for identifier in extract_jobs)
        revision = material.revision

    calls = []
    def package(config, function, payload, *args, **kwargs):
        assert function == 'package'
        calls.append(copy.deepcopy(payload))
        return Result(bounded_output(payload), 20, 50, 23, cost_source='reported')

    monkeypatch.setattr('schulpilot.worker.request_provider', package)
    advance_one()
    with DB() as db:
        job_id = claim(db)
        assert job_id
    process(job_id)
    with DB.begin() as db:
        _advance(db, db.get(SchoolDay, day['id']))
    with DB() as db:
        saved_day = db.get(SchoolDay, day['id'])
        package_job = db.get(Job, job_id)
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        unit = db.scalar(select(LearningUnit).where(LearningUnit.school_day_id == day['id']))
        assert saved_day.preparation['status'] == 'ready'
        assert package_job.status == 'completed' and usage.status == 'completed'
        assert unit and unit.status == 'not_started'
        assert db.get(UnitSource, (unit.id, page['id'])).revision == revision
        assert db.get(UnitVisualSnapshot, unit.id).status == 'ready'
        uid, question_id, answer = unit.id, unit.questions[0]['id'], unit.questions[0]['answer']
        counts_before = tuple(db.scalar(select(func.count()).select_from(model))
            for model in (Job, Usage, Attempt, Activity, Mastery))
    assert len(calls) == 1


    assert operator.get(f"/api/materials/{page['id']}").status_code == 403
    assert operator.get(f'/api/jobs/{job_id}').status_code == 403
    assert operator.get(f'/api/units/{uid}').status_code == 403

    with TestClient(app, headers=HEADERS) as kid:
        login = kid.post('/api/auth/login', json={'username': 'test-child', 'password': 'secure-child-pass-123'})
        assert login.status_code == 200
        kid.headers['Authorization'] = 'Bearer ' + login.json()['token']
        for _ in range(3):
            shown = kid.get(f'/api/units/{uid}')
            assert shown.status_code == 200
            assert shown.json()['explanation_visual_status'] == 'ready'
            step = shown.json()['explanation_steps'][0]
            assert step['reference']['id'] == 'general.source_relation.phases'
            assert step['reference']['version'] == 1
            assert len(step['reference']['parameter_digest']) == 64
            assert step['source_refs'][0]['material_id'] == page['id']
            assert step['source_refs'][0]['revision'] == revision
            assert all('answer' not in question for question in shown.json()['questions'])
            assert kid.get(f'/api/jobs/{job_id}').status_code == 200
        with DB() as db:
            assert tuple(db.scalar(select(func.count()).select_from(model))
                for model in (Job, Usage, Attempt, Activity, Mastery)) == counts_before
        assert kid.post(f'/api/units/{uid}/start').status_code == 200
        assert kid.post(f'/api/units/{uid}/questions/{question_id}/hint').status_code == 200
        result = kid.post(f'/api/units/{uid}/questions/{question_id}/answer', json={'answer': answer})
        assert result.status_code == 200 and result.json()['outcome'] == 'correct'
    with DB() as db:
        attempt = db.scalar(select(Attempt).where(Attempt.unit_id == uid, Attempt.question_id == question_id))
        assert attempt and attempt.outcome == 'correct' and attempt.assisted is True
        assert db.get(UnitSource, (uid, page['id'])).revision == revision
        assert db.scalar(select(func.count()).select_from(Attempt)) == counts_before[2] + 1
    assert len(calls) == 1


def test_source_revision_changed_during_generation_cannot_become_a_ready_package(pipeline, monkeypatch):
    api, child = pipeline['api'], pipeline['child']
    day = api.post(f"/api/children/{child['id']}/school-day/today").json()
    page = upload(pipeline, day)
    pipeline['outputs'][:] = [
        reading(CASE['source'], subject=CASE['subject'], topic='Künstlicher Wasserkreislauf'),
        reading(CASE['source'], subject=CASE['subject'], topic='Künstlicher Wasserkreislauf'),
    ]
    assert api.post(f"/api/school-days/{day['id']}/prepare", headers={'Idempotency-Key': 'synthetic-stale-trace'}).status_code == 202
    for _ in range(2):
        advance_one()
        with DB() as db:
            identifier = claim(db)
            assert identifier
        process(identifier)
    calls = []
    def package(config, function, payload, *args, **kwargs):
        calls.append(function)
        output = bounded_output(payload)
        with DB.begin() as db:
            material = db.get(Material, page['id'])
            material.revision += 1
        return Result(output, 20, 50, 23, cost_source='reported')

    monkeypatch.setattr('schulpilot.worker.request_provider', package)
    advance_one()
    with DB() as db:
        identifier = claim(db)
        assert identifier
    process(identifier)
    with DB() as db:
        job = db.get(Job, identifier)
        usage = db.scalar(select(Usage).where(Usage.job_id == identifier))
        assert job.status == 'failed' and job.result is None
        assert usage.status == 'failed_billed' and usage.cost_micros == 23
        assert db.scalar(select(func.count()).select_from(LearningUnit)) == 0
        assert db.scalar(select(func.count()).select_from(Attempt)) == 0
    for _ in range(3):
        result = api.get(f'/api/school-days/{day["id"]}')
        assert result.status_code == 200
        assert result.json()['preparation']['status'] in ('failed', 'blocked')
        assert result.json()['units'] == []
    assert calls == ['package']
