"""One artificial image from upload to a stored supported learning answer.

The normal APIs, DB, worker and post-provider validators are real. The model
transport alone is a deterministic synthetic fixture: this test is not a
claim about live OCR accuracy, provider availability, or all subject formats.
"""
import copy

import pytest
from conftest import HEADERS
from fastapi.testclient import TestClient
from schulpilot.db import DB, Activity, Attempt, Job, LearningUnit, Mastery, Material, SchoolDay, UnitSource, Usage
from schulpilot.main import app
from schulpilot.providers import ProviderError, Result
from schulpilot.school_preparation import _advance, advance_one
from schulpilot.source_lineage_models import SourceImageReceipt, SourceRevision
from schulpilot.synthetic import CONTENT as PRIVATE_SOURCE_TEXT
from schulpilot.visual_reference_models import UnitVisualSnapshot
from schulpilot.worker import claim, process
from sqlalchemy import func, select
from test_coaching import finish as finish_learning_unit
from test_coaching import mocked_review, process_next
from test_coaching import normal_unit as normal_unit
from test_exam_reviews import TEXT as EXAM_TEXT
from test_exam_reviews import analyze, finish
from test_exam_reviews import paper as paper
from test_exam_reviews import transport as transport
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
        extract_revisions = [db.get(Job, identifier).payload['material_revision'] for identifier in extract_jobs]

    for identifier, phase, bound_revision in zip(extract_jobs, ('recognition', 'countercheck'), extract_revisions, strict=True):
        trace = api.get(f'/api/jobs/{identifier}/trace')
        assert trace.status_code == 200
        assert trace.json()['phase'] == phase and trace.json()['status'] == 'completed'
        assert trace.json()['source_snapshot'] is not None
        assert len(trace.json()['source_snapshot']['template']['prompt_sha256']) == 64
        assert len(trace.json()['source_snapshot']['template']['schema_sha256']) == 64
        assert trace.json()['sources'] == [{'id': page['id'], 'revision': bound_revision, 'current_revision': revision}]
        assert trace.json()['model']['config_revision'] > 0
    assert operator.get(f'/api/jobs/{extract_jobs[0]}/trace').status_code == 403

    calls = []
    def package(config, function, payload, *args, **kwargs):
        assert function == 'package'
        calls.append(copy.deepcopy(payload))
        return Result(bounded_output(payload), 20, 50, 23, cost_source='reported',
                      request_receipt={'schema_sha256': 'c' * 64})

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
    trace = api.get(f'/api/jobs/{job_id}/trace')
    assert trace.status_code == 200 and trace.json()['phase'] == 'generation'
    assert trace.json()['request_schema_sha256'] == 'c' * 64
    assert any(item['id'] == uid for item in trace.json()['units'])
    assert any(ref['id'] == 'general.source_relation.phases' and ref['version'] == 1
               for item in trace.json()['units'] for ref in item['references'])
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
        with DB() as db:
            before_invalid = tuple(db.scalar(select(func.count()).select_from(model))
                for model in (Job, Usage, Attempt, Activity, Mastery))
        invalid = kid.post(f'/api/units/{uid}/questions/unknown-question/answer', json={'answer': 'synthetic'})
        assert invalid.status_code == 404
        with DB() as db:
            assert tuple(db.scalar(select(func.count()).select_from(model))
                for model in (Job, Usage, Attempt, Activity, Mastery)) == before_invalid
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
        requested_revision = next(source['revision'] for source in job.payload['sources'] if source['id'] == page['id'])
    for _ in range(3):
        result = api.get(f'/api/school-days/{day["id"]}')
        assert result.status_code == 200
        assert result.json()['preparation']['status'] in ('failed', 'blocked')
        assert result.json()['units'] == []
        trace = api.get(f'/api/jobs/{identifier}/trace')
        assert trace.status_code == 200
        assert trace.json()['phase'] == 'generation'
        assert trace.json()['error_code'] == 'source_changed'
        assert {'id': page['id'], 'revision': requested_revision, 'current_revision': requested_revision + 1} in trace.json()['sources']
        assert CASE['source'] not in trace.text
    assert calls == ['package']


def test_exam_review_trace_tracks_actual_queued_and_completed_job_without_source_text(api, paper, transport):
    job_id = analyze(paper)['id']
    for status in ('queued', 'completed'):
        if status == 'completed':
            assert finish() == job_id
        response = api.get(f'/api/jobs/{job_id}/trace')
        assert response.status_code == 200
        data = response.json()
        assert data['phase'] == 'exam_review' and data['status'] == status
        assert data['sources'] == [{'id': paper['material_id'], 'revision': 1, 'current_revision': 1}]
        assert EXAM_TEXT not in response.text
    assert len(transport['calls']) == 1


def test_failed_exam_review_trace_is_bounded_and_read_only(api, paper, transport):
    def fail():
        raise ProviderError('synthetic private exam provider detail', code='provider_timeout')

    transport['effect'] = fail
    job_id = analyze(paper)['id']
    assert finish() == job_id
    with DB() as db:
        before = tuple(db.scalar(select(func.count()).select_from(model)) for model in (Job, Usage, Attempt, Activity, Mastery))
    for _ in range(2):
        response = api.get(f'/api/jobs/{job_id}/trace')
        assert response.status_code == 200
        data = response.json()
        assert data['phase'] == 'exam_review' and data['status'] == 'failed'
        assert data['error_code'] == 'provider_timeout'
        assert data['sources'] == [{'id': paper['material_id'], 'revision': 1, 'current_revision': 1}]
        assert EXAM_TEXT not in response.text and 'synthetic private exam provider detail' not in response.text
    with DB() as db:
        assert tuple(db.scalar(select(func.count()).select_from(model)) for model in (Job, Usage, Attempt, Activity, Mastery)) == before


def test_coach_job_trace_retains_its_bound_source_revision(api, normal_unit, monkeypatch):
    kid, unit_id, material_id, _, _ = normal_unit
    calls = mocked_review(monkeypatch)
    finish_learning_unit(kid, unit_id)
    with DB() as db:
        job = db.scalar(select(Job).where(Job.kind == 'coach'))
        assert job is not None
        job_id = job.id
    for status in ('queued', 'completed'):
        if status == 'completed':
            assert process_next() == job_id
        response = api.get(f'/api/jobs/{job_id}/trace')
        assert response.status_code == 200
        data = response.json()
        assert data['phase'] == 'feedback' and data['status'] == status
        assert data['sources'] == [{'id': material_id, 'revision': 1, 'current_revision': 1}]
        assert PRIVATE_SOURCE_TEXT not in response.text
    assert len(calls) == 1
    with DB.begin() as db:
        db.get(Material, material_id).revision = 2
    data = api.get(f'/api/jobs/{job_id}/trace').json()
    assert data['sources'] == [{'id': material_id, 'revision': 1, 'current_revision': 2}]


def test_failed_coach_job_trace_keeps_source_and_existing_answers(api, normal_unit, monkeypatch):
    kid, unit_id, material_id, _, _ = normal_unit
    def fail(*args, **kwargs):
        raise ProviderError('synthetic private provider detail', code='provider_timeout')
    monkeypatch.setattr('schulpilot.coaching.request_provider', fail)
    finish_learning_unit(kid, unit_id)
    with DB() as db:
        job_id = db.scalar(select(Job.id).where(Job.kind == 'coach'))
        before = tuple(db.scalar(select(func.count()).select_from(model)) for model in (Job, Usage, Attempt, Activity))
    assert process_next() == job_id
    for _ in range(2):
        response = api.get(f'/api/jobs/{job_id}/trace')
        assert response.status_code == 200
        data = response.json()
        assert data['phase'] == 'feedback' and data['status'] == 'failed'
        assert data['error_code'] == 'provider_timeout'
        assert data['sources'] == [{'id': material_id, 'revision': 1, 'current_revision': 1}]
        assert 'synthetic private provider detail' not in response.text
    with DB() as db:
        assert tuple(db.scalar(select(func.count()).select_from(model)) for model in (Job, Usage, Attempt, Activity)) == before


@pytest.mark.parametrize("stage", ["recognition", "countercheck"])
def test_real_worker_failure_has_private_bounded_trace_and_no_read_side_effects(pipeline, operator, stage):
    api, child = pipeline["api"], pipeline["child"]
    day = api.post(f"/api/children/{child['id']}/school-day/today").json()
    page = upload(pipeline, day)
    failure = ProviderError("synthetic private upstream body", code="provider_timeout")
    pipeline["outputs"][:] = [failure] if stage == "recognition" else [reading(), failure]
    assert (
        api.post(
            f"/api/school-days/{day['id']}/prepare", headers={"Idempotency-Key": "trace-failure-" + stage}
        ).status_code
        == 202
    )
    for _ in range(1 if stage == "recognition" else 2):
        advance_one()
        with DB() as db:
            identifier = claim(db)
            assert identifier
        process(identifier)
    with DB() as db:
        job = db.get(Job, identifier)
        assert job.status == "failed" and job.error_code == "provider_timeout"
        before = tuple(
            db.scalar(select(func.count()).select_from(model)) for model in (Job, Usage, Attempt, Activity, Mastery)
        )
        assert db.get(Material, page["id"]).confirmed is False
    for _ in range(3):
        trace = api.get(f"/api/jobs/{identifier}/trace")
        assert trace.status_code == 200 and trace.json()["phase"] == stage
        assert trace.json()["status"] == "failed" and trace.json()["error_code"] == "provider_timeout"
        assert "synthetic private upstream body" not in trace.text
        assert trace.json()["model"] is not None
        assert trace.json()["units"] == []
    assert operator.get(f"/api/jobs/{identifier}/trace").status_code == 403
    with DB() as db:
        assert (
            tuple(
                db.scalar(select(func.count()).select_from(model)) for model in (Job, Usage, Attempt, Activity, Mastery)
            )
            == before
        )
    assert len(pipeline["calls"]) == (1 if stage == "recognition" else 2)


def test_rejected_package_output_stays_billed_and_never_becomes_a_ready_unit(pipeline, operator, monkeypatch):
    api, child = pipeline["api"], pipeline["child"]
    day = api.post(f"/api/children/{child['id']}/school-day/today").json()
    page = upload(pipeline, day)
    pipeline["outputs"][:] = [reading(CASE["source"]), reading(CASE["source"])]
    assert (
        api.post(f"/api/school-days/{day['id']}/prepare", headers={"Idempotency-Key": "trace-bad-package"}).status_code
        == 202
    )
    for _ in range(2):
        advance_one()
        with DB() as db:
            identifier = claim(db)
            assert identifier
        process(identifier)
    calls = []

    def reject(config, function, payload, *args, **kwargs):
        calls.append(function)
        raise ProviderError(
            "synthetic model content is private",
            code="invalid_output",
            billing_result=Result({}, 20, 50, 23, cost_source="reported"),
        )

    monkeypatch.setattr("schulpilot.worker.request_provider", reject)
    advance_one()
    with DB() as db:
        identifier = claim(db)
        assert identifier
    process(identifier)
    with DB.begin() as db:
        _advance(db, db.get(SchoolDay, day["id"]))
    with DB() as db:
        failed = db.get(Job, identifier)
        usage = db.scalar(select(Usage).where(Usage.job_id == identifier))
        assert failed.status == "failed" and failed.error_code == "invalid_output"
        assert usage.cost_micros == 23 and usage.status == "failed_billed"
        assert db.scalar(select(func.count()).select_from(LearningUnit)) == 0
        before = tuple(
            db.scalar(select(func.count()).select_from(model)) for model in (Job, Usage, Attempt, Activity, Mastery)
        )
    for _ in range(3):
        trace = api.get(f"/api/jobs/{identifier}/trace")
        assert trace.status_code == 200
        assert trace.json()["phase"] == "generation" and trace.json()["error_code"] == "invalid_output"
        assert trace.json()["units"] == [] and "synthetic model content is private" not in trace.text
        assert api.get(f"/api/school-days/{day['id']}").json()["preparation"]["status"] == "failed"
    assert operator.get(f"/api/jobs/{identifier}/trace").status_code == 403
    with DB() as db:
        assert (
            tuple(
                db.scalar(select(func.count()).select_from(model)) for model in (Job, Usage, Attempt, Activity, Mastery)
            )
            == before
        )
        assert db.get(Material, page["id"]).confirmed is True
    assert calls == ["package"]
