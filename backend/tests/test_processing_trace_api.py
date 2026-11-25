"""Private, read-only, bounded processing metadata; all examples artificial."""

import copy

import pytest
from conftest import HEADERS, create_child, register
from fastapi.testclient import TestClient
from schulpilot.db import DB, Activity, Assignment, Attempt, Job, LearningUnit, Material, Usage, uid
from schulpilot.main import app
from schulpilot.source_lineage_models import SourceRevision
from schulpilot.synthetic import sample_unit
from schulpilot.visual_reference_models import UnitVisualSnapshot, VisualReference
from sqlalchemy import func, select
from test_coaching import normal_unit as normal_unit
from test_codex_models import operator as operator
from test_visual_references import generated_visual_unit as generated_visual_unit

CANARY = "ARTIFICIAL_PRIVATE_CONTENT_DO_NOT_EXPOSE_IN_TRACE"


def test_only_current_child_bound_competence_is_traced_without_question_content(api, normal_unit):
    from schulpilot import competences
    from schulpilot.competence_models import QuestionCompetence

    _, unit_id, material_id, _, child = normal_unit
    with DB.begin() as db:
        unit = db.get(LearningUnit, unit_id)
        page = db.get(Material, material_id)
        question = unit.questions[0]
        goal = Assignment(child_id=child['id'], kind='parent', subject='Mathematik', topic='Künstlich')
        db.add(goal)
        db.flush()
        unit.assignment_id, unit.goal_revision = goal.id, goal.revision
        db.add(QuestionCompetence(unit_id=unit.id, child_id=child['id'], question_id=question['id'],
            competence_id='math.fractions.reduce', catalog_version=competences.VERSION, role='practice',
            question_digest=competences.question_digest(question),
            source_refs=[competences.source_ref(db, page)], reference_ids=[]))
        job = Job(child_id=child['id'], kind='unit', status='completed', idempotency=uid(),
                  payload={'material_id': material_id, 'material_revision': page.revision}, result={'unit_id': unit.id})
        db.add(job)
        db.flush()
        identifier = job.id
        goal_id = goal.id
        private_prompt = question['prompt']
    response = api.get(f'/api/jobs/{identifier}/trace')
    assert response.status_code == 200
    assert response.json()['units'][0]['competences'] == [{'id': 'math.fractions.reduce', 'version': competences.VERSION}]
    assert response.json()['units'][0]['competences_unavailable'] is False
    assert response.json()['units'][0]['goal'] == {'id': goal_id, 'revision': 1, 'current_revision': 1}
    assert private_prompt not in response.text
    with DB.begin() as db:
        binding = db.get(QuestionCompetence, (unit_id, question['id']))
        saved_refs = copy.deepcopy(binding.source_refs)
        binding.source_refs = saved_refs * 33
    limited = api.get(f'/api/jobs/{identifier}/trace').json()['units'][0]
    assert limited['competences'] == [] and limited['competences_truncated'] is True
    with DB.begin() as db:
        db.get(QuestionCompetence, (unit_id, question['id'])).source_refs = saved_refs
    with DB.begin() as db:
        db.get(Material, material_id).revision += 1
        db.get(Assignment, goal_id).revision += 1
    changed = api.get(f'/api/jobs/{identifier}/trace').json()['units'][0]
    assert changed['competences'] == [] and changed['competences_unavailable'] is True
    assert changed['goal'] == {'id': goal_id, 'revision': 1, 'current_revision': 2}


def test_foreign_goal_and_competence_binding_are_not_attributed(api, normal_unit):
    from schulpilot import competences
    from schulpilot.competence_models import QuestionCompetence

    _, unit_id, material_id, parent_data, child = normal_unit
    sibling = create_child(api, parent_data, username='trace-sibling')
    with DB.begin() as db:
        unit = db.get(LearningUnit, unit_id)
        goal = Assignment(child_id=sibling['id'], kind='parent', subject='Mathematik', topic='Künstlich')
        db.add(goal)
        db.flush()
        unit.assignment_id, unit.goal_revision = goal.id, goal.revision
        db.add(QuestionCompetence(unit_id=unit.id, child_id=sibling['id'], question_id=unit.questions[0]['id'],
            competence_id='math.fractions.reduce', catalog_version=competences.VERSION, role='practice',
            question_digest=competences.question_digest(unit.questions[0]),
            source_refs=[competences.source_ref(db, db.get(Material, material_id))], reference_ids=[]))
        job = Job(child_id=child['id'], kind='unit', status='completed', idempotency=uid(),
                  payload={}, result={'unit_id': unit.id})
        db.add(job)
        db.flush()
        job_id = job.id
    data = api.get(f'/api/jobs/{job_id}/trace').json()['units'][0]
    assert data['goal'] is None and data['competences'] == []


@pytest.mark.parametrize('fault', ['source', 'parameters', 'missing_recipe', 'unknown_reason'])
def test_trace_never_calls_damaged_or_stale_graphics_ready(api, generated_visual_unit, fault):
    unit_id, material_id, child_id = generated_visual_unit
    with DB.begin() as db:
        job = Job(child_id=child_id, kind='unit', status='completed', idempotency=uid(),
                  payload={'material_id': material_id, 'material_revision': 1}, result={'unit_id': unit_id})
        db.add(job)
        db.flush()
        job_id = job.id
    assert api.get(f'/api/jobs/{job_id}/trace').json()['units'][0]['visual_status'] == 'ready'
    with DB.begin() as db:
        if fault == 'source':
            db.get(Material, material_id).revision += 1
        elif fault == 'parameters':
            visual = db.get(UnitVisualSnapshot, unit_id)
            steps = copy.deepcopy(visual.steps)
            steps[0]['presentation']['blocks'][0]['numbers'] = [2, 3]
            visual.steps = steps
        elif fault == 'missing_recipe':
            db.delete(db.get(VisualReference, ('math.fraction.part_whole', 1)))
        else:
            visual = db.get(UnitVisualSnapshot, unit_id)
            visual.status, visual.reason = 'incomplete', 'PRIVATE_CANARY'
    response = api.get(f'/api/jobs/{job_id}/trace')
    assert response.status_code == 200
    assert response.json()['units'][0]['visual_status'] == 'incomplete'
    assert response.json()['units'][0]['visual_reason'] == (
        'source_changed' if fault == 'source' else None if fault == 'unknown_reason' else 'invalid_graphic')
    assert CANARY not in response.text
    assert 'PRIVATE_CANARY' not in response.text
    with DB() as db:
        assert db.get(UnitVisualSnapshot, unit_id).status == ('incomplete' if fault == 'unknown_reason' else 'ready')


def test_trace_is_metadata_only_family_authorized_and_read_only(api, household, mailbox, operator):
    owner, child = household
    family_id = owner["families"][0]["id"]
    with DB.begin() as db:
        material = Material(child_id=child["id"], title=CANARY, content=CANARY, confirmed=True, subject="Mathematik")
        db.add(material)
        db.flush()
        unit = LearningUnit(
            child_id=child["id"], material_id=material.id, provider="synthetic", synthetic=True, **sample_unit()
        )
        db.add(unit)
        db.flush()
        reference = db.scalar(select(VisualReference).order_by(VisualReference.id, VisualReference.version))
        db.add(
            UnitVisualSnapshot(
                unit_id=unit.id,
                source_signature="a" * 64,
                status="ready",
                receipts=[
                    {
                        "reference": {"id": reference.id, "version": reference.version},
                        "source_refs": [{"secret": CANARY}],
                    }
                ],
                steps=[],
                question_steps={},
                source_bindings=[],
            )
        )
        job = Job(
            child_id=child["id"],
            kind="unit",
            status="completed",
            idempotency=uid(),
            payload={"sources": [{"id": material.id, "revision": material.revision}], "secret": CANARY},
            result={"unit_id": unit.id, "secret": CANARY},
            error=CANARY,
        )
        db.add(job)
        db.flush()
        db.add(
            Usage(
                family_id=family_id,
                child_id=child["id"],
                job_id=job.id,
                provider="synthetic",
                model="fixture/model",
                config_revision=3,
                function="unit",
                status="completed",
                reserved_micros=0,
                bucket_ids=[],
                route_snapshot={"secret": CANARY},
                telemetry={"secret": CANARY},
            )
        )
        job_id, material_id, unit_id, ref_id, ref_version = (
            job.id,
            material.id,
            unit.id,
            reference.id,
            reference.version,
        )
    with DB() as db:
        before = tuple(db.scalar(select(func.count()).select_from(cls)) for cls in (Job, Usage, Attempt, Activity))
    for _ in range(2):
        response = api.get(f"/api/jobs/{job_id}/trace")
        assert response.status_code == 200
        data = response.json()
        assert data["phase"] == "generation" and data["status"] == "completed"
        assert data["model"] == {"provider": "synthetic", "model": "fixture/model", "config_revision": 3}
        assert data["sources"] == [{"id": material_id, "revision": 1, "current_revision": 1}]
        assert data["units"][0]["id"] == unit_id
        assert {"id": ref_id, "version": ref_version} in data["units"][0]["references"]
        assert CANARY not in response.text
    with TestClient(app, headers=HEADERS) as stranger:
        register(stranger, mailbox, "unrelated-trace@example.org")
        assert stranger.get(f"/api/jobs/{job_id}/trace").status_code == 404
    assert operator.get(f"/api/jobs/{job_id}/trace").status_code == 403
    with TestClient(app, headers=HEADERS) as kid:
        login = kid.post("/api/auth/login", json={"username": "test-child", "password": "secure-child-pass-123"})
        kid.headers["Authorization"] = "Bearer " + login.json()["token"]
        assert kid.get(f"/api/jobs/{job_id}/trace").status_code == 403
    with DB() as db:
        after = tuple(db.scalar(select(func.count()).select_from(cls)) for cls in (Job, Usage, Attempt, Activity))
    assert after == before


def test_failed_trace_exposes_controlled_category_without_error_body(api, household):
    with DB.begin() as db:
        job = Job(
            child_id=household[1]["id"],
            kind="extract",
            status="failed",
            idempotency=uid(),
            payload={"raw": CANARY},
            error=CANARY,
            error_code="provider_timeout",
        )
        db.add(job)
        db.flush()
        job_id = job.id
    response = api.get(f"/api/jobs/{job_id}/trace")
    assert response.status_code == 200
    assert response.json()["phase"] == "recognition"
    assert response.json()["error_code"] == "provider_timeout"
    assert response.json()["model"] is None
    assert CANARY not in response.text


@pytest.mark.parametrize('value,expected', [
    ('a' * 64, 'a' * 64), (CANARY, None), ({'secret': CANARY}, None), (True, None),
])
def test_only_bounded_actual_request_schema_digest_is_shown(api, household, value, expected):
    owner, child = household
    with DB.begin() as db:
        job = Job(child_id=child['id'], kind='unit', payload={}, status='failed', idempotency=uid())
        db.add(job)
        db.flush()
        db.add(Usage(family_id=owner['families'][0]['id'], child_id=child['id'], job_id=job.id,
            provider='synthetic', model='fixture/model', config_revision=3, function='unit',
            status='failed_billed', reserved_micros=0, bucket_ids=[], route_snapshot={},
            telemetry={'request_schema_sha256': value, 'secret': CANARY}))
        identifier = job.id
    response = api.get(f'/api/jobs/{identifier}/trace')
    assert response.status_code == 200
    assert response.json()['request_schema_sha256'] == expected
    assert response.json()['request_schema_status'] == ('available' if expected else 'unavailable')
    assert CANARY not in response.text


def test_multiple_usage_receipts_do_not_guess_a_request_schema(api, household):
    owner, child = household
    with DB.begin() as db:
        job = Job(child_id=child['id'], kind='unit', payload={}, status='completed', idempotency=uid())
        db.add(job)
        db.flush()
        for value in ('a' * 64, 'b' * 64):
            db.add(Usage(family_id=owner['families'][0]['id'], child_id=child['id'], job_id=job.id,
                provider='synthetic', model='fixture/model', config_revision=3, function='unit',
                status='completed', reserved_micros=0, bucket_ids=[], route_snapshot={},
                telemetry={'request_schema_sha256': value}))
        identifier = job.id
    response = api.get(f'/api/jobs/{identifier}/trace')
    assert response.status_code == 200
    assert response.json()['model_ambiguous'] is True
    assert response.json()['request_schema_sha256'] is None
    assert response.json()['request_schema_status'] == 'ambiguous'


@pytest.mark.parametrize(("telemetry", "expected"), [
    ({"finish_reason": "length", "secret": CANARY}, "output_length"),
    ({"validation": {"version": 1, "errors": [{"reason": "question_fraction_ambiguous", "input": CANARY}]}}, "question_fraction_ambiguous"),
    ({"validation": {"version": 1, "errors": [{"reason": "question_fraction_result"}]}}, "question_fraction_result"),
    ({"validation": {"version": 1, "errors": [{"reason": {"secret": CANARY}}]}}, None),
    ({"validation": {"version": True, "errors": [{"reason": "question_fraction_ambiguous"}]}}, None),
    ({"validation": {"version": 1, "errors": [{"reason": CANARY}]}}, None),
])
def test_failure_detail_is_closed_content_free_and_read_only(api, household, telemetry, expected):
    owner, child = household
    with DB.begin() as db:
        job = Job(child_id=child["id"], kind="package", payload={}, status="failed", idempotency=uid(), error_code="invalid_output")
        db.add(job)
        db.flush()
        db.add(Usage(family_id=owner["families"][0]["id"], child_id=child["id"], job_id=job.id,
                     provider="synthetic", model="fixture/model", config_revision=3, function="package",
                     status="failed_billed", reserved_micros=0, bucket_ids=[], route_snapshot={}, telemetry=telemetry))
        job_id = job.id
    response = api.get(f"/api/jobs/{job_id}/trace")
    assert response.status_code == 200
    assert response.json()["failure_detail"] == expected
    assert CANARY not in response.text


def test_stale_or_forged_snapshot_and_foreign_references_are_not_attributed(api, household):
    with DB.begin() as db:
        child = household[1]["id"]
        material = Material(
            child_id=child, title="synthetic", content="synthetic", confirmed=True, subject="Mathematik"
        )
        db.add(material)
        db.flush()
        snapshot = SourceRevision(
            material_id=material.id,
            child_id=child,
            revision=1,
            sequence=1,
            digest="a" * 64,
            cause="extraction",
            snapshot={},
            receipt={"job_id": uid()},
        )
        db.add(snapshot)
        db.flush()
        job = Job(
            child_id=child,
            kind="extract",
            status="completed",
            idempotency=uid(),
            payload={"material_id": material.id, "sources": [{"id": uid(), "revision": 1}] * 35},
            result={"source_snapshot_id": snapshot.id},
        )
        db.add(job)
        db.flush()
        identifier = job.id
    response = api.get(f"/api/jobs/{identifier}/trace")
    assert response.status_code == 200
    assert response.json()["source_snapshot"] is None
    assert response.json()["sources"] == [] and response.json()["sources_truncated"] is True


@pytest.mark.parametrize("version,prompt,schema,kind,cause,expected", [
    (1, "a" * 64, "b" * 64, 'extract', 'extraction', {"prompt_sha256": "a" * 64, "schema_sha256": "b" * 64}),
    (1, CANARY, {"private": CANARY}, 'extract', 'extraction', {"prompt_sha256": None, "schema_sha256": None}),
    (True, "a" * 64, "b" * 64, 'extract', 'extraction', None),
    (2, "a" * 64, "b" * 64, 'extract', 'extraction', None),
    (1, "a" * 64, "b" * 64, 'unit', 'extraction', None),
    (1, "a" * 64, "b" * 64, 'extract', 'auto_check_reading', None),
])
def test_ocr_template_receipt_is_bound_to_job_and_limited(api, household, version, prompt, schema, kind, cause, expected):
    with DB.begin() as db:
        material = Material(child_id=household[1]['id'], title=CANARY, content=CANARY,
                            confirmed=True, subject='Mathematik')
        db.add(material)
        db.flush()
        job = Job(child_id=material.child_id, kind=kind, status='completed', idempotency=uid(),
                  payload={'material_id': material.id, 'material_revision': 1})
        db.add(job)
        db.flush()
        snapshot = SourceRevision(material_id=material.id, child_id=material.child_id, revision=1,
            sequence=1, digest='c' * 64, cause=cause, snapshot={'secret': CANARY},
            receipt={'version': version, 'job_id': job.id, 'base_prompt_digest': prompt,
                     'base_schema_digest': schema, 'secret': CANARY})
        db.add(snapshot)
        db.flush()
        job.result = {'source_snapshot_id': snapshot.id}
        identifier = job.id
    response = api.get(f'/api/jobs/{identifier}/trace')
    assert response.status_code == 200
    assert response.json()['source_snapshot'].get('template') == expected
    assert CANARY not in response.text


def test_unknown_failure_category_is_not_echoed(api, household):
    with DB.begin() as db:
        job = Job(
            child_id=household[1]["id"],
            kind="extract",
            status="failed",
            idempotency=uid(),
            payload={},
            error_code="bad_category",
            error=CANARY,
        )
        db.add(job)
        db.flush()
        identifier = job.id
    response = api.get(f"/api/jobs/{identifier}/trace")
    assert response.status_code == 200 and response.json()["error_code"] == "unknown"
    assert CANARY not in response.text


@pytest.mark.parametrize('kind', ['extract', 'unit'])
def test_single_material_job_traces_explicit_revision_without_private_content(api, household, kind):
    with DB.begin() as db:
        material = Material(child_id=household[1]['id'], title=CANARY, content=CANARY,
                            confirmed=True, subject='Mathematik', revision=4)
        db.add(material)
        db.flush()
        job = Job(child_id=household[1]['id'], kind=kind, status='failed', idempotency=uid(),
                  error_code='provider_timeout', payload={'material_id': material.id, 'material_revision': 3})
        db.add(job)
        db.flush()
        job_id, material_id = job.id, material.id
    response = api.get(f'/api/jobs/{job_id}/trace')
    assert response.status_code == 200
    assert response.json()['sources'] == [{'id': material_id, 'revision': 3, 'current_revision': 4}]
    assert CANARY not in response.text


@pytest.mark.parametrize('revision', [None, True, 0, -1, '1'])
def test_single_material_job_does_not_invent_missing_or_invalid_revision(api, household, revision):
    with DB.begin() as db:
        material = Material(child_id=household[1]['id'], title='synthetic', subject='Mathematik', revision=4)
        db.add(material)
        db.flush()
        job = Job(child_id=household[1]['id'], kind='unit', status='queued', idempotency=uid(),
                  payload={'material_id': material.id, 'material_revision': revision})
        db.add(job)
        db.flush()
        job_id = job.id
    response = api.get(f'/api/jobs/{job_id}/trace')
    assert response.status_code == 200 and response.json()['sources'] == []


def test_single_material_job_cannot_attribute_a_siblings_source(api, household):
    owner, child = household
    sibling = create_child(api, owner, 'synthetic-trace-sibling')
    with DB.begin() as db:
        material = Material(child_id=sibling['id'], title=CANARY, subject='Mathematik')
        db.add(material)
        db.flush()
        job = Job(child_id=child['id'], kind='unit', status='queued', idempotency=uid(),
                  payload={'material_id': material.id, 'material_revision': 1})
        db.add(job)
        db.flush()
        job_id = job.id
    response = api.get(f'/api/jobs/{job_id}/trace')
    assert response.status_code == 200 and response.json()['sources'] == []
    assert CANARY not in response.text


def test_explicit_source_list_remains_authoritative_over_single_material_field(api, household):
    with DB.begin() as db:
        primary = Material(child_id=household[1]['id'], title='synthetic one', subject='Mathematik')
        other = Material(child_id=household[1]['id'], title='synthetic two', subject='Mathematik')
        db.add_all([primary, other])
        db.flush()
        job = Job(child_id=household[1]['id'], kind='unit', status='queued', idempotency=uid(),
                  payload={'material_id': primary.id, 'material_revision': 1,
                           'sources': [{'id': other.id, 'revision': 1}]})
        db.add(job)
        db.flush()
        job_id, other_id = job.id, other.id
    response = api.get(f'/api/jobs/{job_id}/trace')
    assert response.status_code == 200
    assert response.json()['sources'] == [{'id': other_id, 'revision': 1, 'current_revision': 1}]


@pytest.mark.parametrize(('kind', 'phase'), [
    ('study_block', 'generation'), ('coach_practice', 'generation'), ('controller_check', 'generation'),
    ('coach', 'feedback'), ('decision', 'decision'), ('unit_visuals', 'visual'), ('learning_asset', 'visual'),
    ('public_image', 'visual'), ('public_image_review', 'visual_review'), ('exam_review', 'exam_review'),
    ('vocabulary_import', 'vocabulary'), ('language_project', 'language'), ('tutor', 'tutor'),
    ('schulbuddy', 'tutor'), ('parent_review', 'parent_review'), ('private_unknown', 'other'),
])
def test_known_job_phases_use_closed_labels_without_echoing_unknown_kinds(api, household, kind, phase):
    with DB.begin() as db:
        job = Job(child_id=household[1]['id'], kind=kind, status='failed', idempotency=uid(),
                  payload={'private': CANARY}, error=CANARY, error_code='provider_timeout')
        db.add(job)
        db.flush()
        job_id = job.id
    response = api.get(f'/api/jobs/{job_id}/trace')
    assert response.status_code == 200 and response.json()['phase'] == phase
    assert response.json()['error_code'] == 'provider_timeout'
    assert CANARY not in response.text and 'private_unknown' not in response.text


def test_exam_review_traces_only_own_explicit_material_revisions(api, household):
    owner, child = household
    sibling = create_child(api, owner, 'synthetic-exam-trace-sibling')
    with DB.begin() as db:
        own = Material(child_id=child['id'], title=CANARY, purpose='exam', subject='Mathematik', revision=4)
        foreign = Material(child_id=sibling['id'], title=CANARY, purpose='exam', subject='Mathematik')
        db.add_all([own, foreign])
        db.flush()
        job = Job(child_id=child['id'], kind='exam_review', status='failed', idempotency=uid(),
                  error_code='provider_timeout', payload={'material_revisions': [
                      {'id': own.id, 'revision': 3, 'label': CANARY},
                      {'id': foreign.id, 'revision': 1},
                  ]})
        db.add(job)
        db.flush()
        job_id, own_id = job.id, own.id
    response = api.get(f'/api/jobs/{job_id}/trace')
    assert response.status_code == 200
    assert response.json()['phase'] == 'exam_review'
    assert response.json()['sources'] == [{'id': own_id, 'revision': 3, 'current_revision': 4}]
    assert CANARY not in response.text


def test_reference_inspection_has_one_global_budget_across_units(api, household):
    with DB.begin() as db:
        child = household[1]["id"]
        reference = db.scalar(select(VisualReference).order_by(VisualReference.id, VisualReference.version))
        receipts = [{"reference": {"id": reference.id, "version": reference.version}}] * 32
        ids = []
        for _ in range(2):
            unit = LearningUnit(child_id=child, provider="synthetic", synthetic=True, **sample_unit())
            db.add(unit)
            db.flush()
            ids.append(unit.id)
            db.add(
                UnitVisualSnapshot(
                    unit_id=unit.id,
                    source_signature="a" * 64,
                    status="ready",
                    receipts=receipts,
                    steps=[],
                    question_steps={},
                    source_bindings=[],
                )
            )
        job = Job(
            child_id=child, kind="package", status="completed", idempotency=uid(), payload={}, result={"unit_ids": ids}
        )
        db.add(job)
        db.flush()
        identifier = job.id
    response = api.get(f"/api/jobs/{identifier}/trace")
    assert response.status_code == 200
    units = response.json()["units"]
    assert units[0]["references_truncated"] is False and len(units[0]["references"]) == 1
    assert units[1]["references_truncated"] is True and units[1]["references"] == []
