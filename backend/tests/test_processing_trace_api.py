"""Private, read-only, bounded processing metadata; all examples artificial."""

import pytest
from conftest import HEADERS, create_child, register
from fastapi.testclient import TestClient
from schulpilot.db import DB, Activity, Attempt, Job, LearningUnit, Material, Usage, uid
from schulpilot.main import app
from schulpilot.source_lineage_models import SourceRevision
from schulpilot.synthetic import sample_unit
from schulpilot.visual_reference_models import UnitVisualSnapshot, VisualReference
from sqlalchemy import func, select
from test_codex_models import operator as operator

CANARY = "ARTIFICIAL_PRIVATE_CONTENT_DO_NOT_EXPOSE_IN_TRACE"


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
