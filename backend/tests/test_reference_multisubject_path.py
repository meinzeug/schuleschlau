"""Trace artificial source-bound graphics through persistence and projection."""

import pytest
from schulpilot import visual_references
from schulpilot.db import DB, Child, LearningUnit, Material, UnitSource
from schulpilot.schemas import PackageOutput
from test_package_prepared_graphics import bind, payload_for
from test_package_source_graphics import response


@pytest.mark.parametrize('subject,source,expected_reference', [
    ('Deutsch', 'Vorsilbe (Präfix) | + | Wortstamm | + | Nachsilbe (Suffix)', 'german.word_formation.parts'),
    ('Biologie', 'Raupe → Puppe → Schmetterling.', 'general.source_relation.phases'),
    ('Geographie', 'Quelle -> Fluss -> Mündung.', 'general.source_relation.phases'),
])
def test_real_source_reference_is_saved_and_projected_without_private_quotes(household, subject, source, expected_reference):
    _, child_data = household
    with DB.begin() as db:
        child = db.get(Child, child_data['id'])
        page = Material(child_id=child.id, title='Künstliche Seite', subject=subject,
                        topic='Künstliche Folge', content=source, confirmed=True, status='confirmed')
        db.add(page)
        db.flush()
        payload = visual_references.with_visual_context(
            db, child, {**payload_for(source, subject), 'function': 'package'}, [page],
            groups=[{'id': 'g1', 'material_ids': [page.id]}],
        )
        _, binding = bind(payload)
        wire = response(payload, binding)
        decoded = PackageOutput.model_validate(binding.hydrate(wire)).model_dump(mode='json')
        data = decoded['units'][0]
        visual_references.validate_output(db, decoded, payload)
        unit = LearningUnit(child_id=child.id, subject=subject, topic='Künstliche Folge',
                            explanation=data['explanation'], questions=data['questions'],
                            provider='synthetic', model='synthetic', status='paused')
        db.add(unit)
        db.flush()
        db.add(UnitSource(unit_id=unit.id, material_id=page.id, revision=page.revision))
        db.flush()
        visual_references.remember(db, unit, data, payload)
        db.flush()
        projected = visual_references.projection(db, unit)
        assert projected['explanation_visual_status'] == 'ready'
        step = projected['explanation_steps'][0]
        assert step['reference']['id'] == expected_reference and step['reference']['version'] == 1
        assert len(step['reference']['digest']) == len(step['reference']['parameter_digest']) == 64
        assert step['source_refs'][0]['material_id'] == page.id
        assert step['presentation']['blocks'][0].get('source_excerpt') is None
        assert step['presentation']['blocks'][0]['labels']
