"""A display-limit notice must not impersonate an image-quality defect."""
from types import SimpleNamespace

import pytest
from schulpilot.db import DB, Job, Material, uid
from schulpilot.image_quality import VISUAL_OVERFLOW_WARNING, poor_image
from schulpilot.model_routing import features_for


@pytest.mark.parametrize('warnings,uncertainties,legibility,expected', [
    ([VISUAL_OVERFLOW_WARNING], [], 'readable', False),
    ([VISUAL_OVERFLOW_WARNING, 'Foto ist schief.'], [], 'readable', True),
    (['Foto ist schief.'], [], 'readable', True),
    ([], ['Unklare Schrift'], 'readable', True),
    ([], [], 'partial', True),
    ([], [], 'unreadable', True),
    ([], [], 'readable', False),
])
def test_quality_helper_preserves_real_signals(warnings, uncertainties, legibility, expected):
    assert poor_image(SimpleNamespace(quality_warnings=warnings, uncertainties=uncertainties,
                                     legibility=legibility)) is expected


def test_reserved_job_features_ignore_only_the_visual_display_notice(api, household):
    _, child = household
    with DB.begin() as db:
        material = Material(child_id=child['id'], title='Künstlich', content='Text', legibility='readable',
                            quality_warnings=[VISUAL_OVERFLOW_WARNING], uncertainties=[])
        db.add(material)
        db.flush()
        job = Job(child_id=child['id'], kind='extract', idempotency=uid(), payload={'material_id': material.id})
        db.add(job)
        db.flush()
        assert features_for(db, child['id'], job.id)['poor_image'] is False
        material.quality_warnings = [VISUAL_OVERFLOW_WARNING, 'Foto ist schief.']
        db.flush()
        assert features_for(db, child['id'], job.id)['poor_image'] is True


def test_preparation_preflight_uses_same_quality_rule(api, household, monkeypatch):
    from schulpilot import job_failures
    from schulpilot.providers import ProviderError
    from test_school_preparation import capture, step, submit

    _, child = household
    day, _ = capture(api, child, monkeypatch, 2)
    submit(api, day, 'quality-visual-test')
    assert step()

    def fail(*args, **kwargs):
        raise ProviderError('Künstliche Störung.')

    monkeypatch.setattr('schulpilot.worker.request_provider', fail)
    assert step()
    with DB.begin() as db:
        failed = db.query(Job).filter(Job.status == 'failed').one()
        target = db.get(Material, failed.payload['material_id'])
        target.quality_warnings = [VISUAL_OVERFLOW_WARNING]
        target.uncertainties = []
        target.legibility = 'readable'
        target_id = target.id
    seen = []

    def availability(*args, **kwargs):
        seen.append(kwargs['routing_features']['poor_image'])
        return None

    monkeypatch.setattr(job_failures, 'generation_availability', availability)
    assert api.get(f"/api/school-days/{day['id']}").status_code == 200
    assert seen == [False]
    with DB.begin() as db:
        db.get(Material, target_id).quality_warnings = [VISUAL_OVERFLOW_WARNING, 'Foto ist schief.']
    seen.clear()
    assert api.get(f"/api/school-days/{day['id']}").status_code == 200
    assert seen == [True]
