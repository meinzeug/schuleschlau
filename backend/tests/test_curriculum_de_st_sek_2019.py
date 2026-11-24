"""Official ST material: source scopes remain separate from child ability evidence."""
import json
from pathlib import Path

from schulpilot.curriculum import import_catalogue
from schulpilot.curriculum_models import CurriculumDocument, CurriculumTopic
from schulpilot.curriculum_schemas import CatalogueInput
from schulpilot.db import DB, Activity, Job, Usage
from sqlalchemy import func, select

PACKAGE = Path(__file__).resolve().parents[1] / 'schulpilot/reference/curriculum-de-st-sek-math-deutsch-2019-v1.json'


def package():
    return json.loads(PACKAGE.read_text())


def import_package():
    with DB.begin() as db:
        return import_catalogue(db, package())


def test_source_package_is_versioned_scoped_and_cannot_claim_complete():
    value = CatalogueInput.model_validate(package())
    assert value.coverage.complete is False
    assert len(value.documents) == 2 and len(value.topics) == 49
    assert {d.state_code for d in value.documents} == {'DE-ST'}
    assert {d.edition for d in value.documents} == {'01.08.2019'}
    assert {d.school_form_id for d in value.documents} == {'de-st.sekundarschule'}
    assert all(d.source_status == 'current_verified' and 'CC BY-SA 3.0' in d.source_notes for d in value.documents)
    assert all(d.official_url.startswith('https://www.bildung-lsa.de/') for d in value.documents)
    assert all(t.page and len(t.quote.split()) == 1 for t in value.topics)
    assert all(t.grades is None for t in value.topics if t.grade_kind == 'phase')
    assert all(t.grades == [9] and t.subject_key == 'mathematik'
               for t in value.topics if t.grade_kind == 'exact')
    assert all(t.grades in ([5, 6], [7, 8]) for t in value.topics if t.grade_kind == 'band')
    assert all('3.3.1' in t.section and '3.4.1' in t.section
               for t in value.topics if t.grades == [7, 8] and t.subject_key == 'mathematik')
    assert all('3.2.1' in t.section and '3.3.1' in t.section
               for t in value.topics if t.grades == [7, 8] and t.subject_key == 'deutsch')


def test_actual_import_is_immutable_idempotent_and_preserves_track_uncertainty(api, household):
    first = import_package()
    second = import_package()
    # Normal initialization has already seeded the reviewed package.
    assert first['documents_added'] == first['topics_added'] == 0
    assert second['documents_added'] == second['topics_added'] == 0
    assert first['package_digest'] == second['package_digest']
    for grade in (5, 6, 7, 8, 9, 10):
        response = api.get('/api/curriculum/topics', params={
            'state_code': 'DE-ST', 'school_form_id': 'de-st.sekundarschule', 'grade': grade, 'limit': 50,
        })
        assert response.status_code == 200
        rows = [row for row in response.json()['items'] if row['source']['document_id'] in {
            'de-st-sek-mathe-2019-v1', 'de-st-sek-deutsch-2019-v1'}]
        assert all(grade in (r['grades'] or []) and r['grade_kind'] != 'phase' for r in rows)
        if grade in (5, 6, 7, 8, 9):
            assert any(r['id'].startswith('de-st-sek-') for r in rows)
        if grade == 10:
            assert rows == []  # Never infer the missing graduation track.
    for phase in ('Realschulabschlussbezogener Unterricht 9/10', 'Hauptschulabschlussbezogener Unterricht 9'):
        result = api.get('/api/curriculum/topics', params={'state_code':'DE-ST',
            'school_form_id':'de-st.sekundarschule','phase':phase,'limit':50}).json()['items']
        assert result and all(r['grade_kind'] == 'phase' and r['grades'] is None for r in result)
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(CurriculumDocument).where(CurriculumDocument.id.in_(
            [d['id'] for d in package()['documents']]))) == 2
        assert db.scalar(select(func.count()).select_from(CurriculumTopic).where(CurriculumTopic.id.in_(
            [t['id'] for t in package()['topics']]))) == 49
        assert db.scalar(select(func.count()).select_from(Job)) == 0
        assert db.scalar(select(func.count()).select_from(Usage)) == 0
        assert db.scalar(select(func.count()).select_from(Activity)) == 0
