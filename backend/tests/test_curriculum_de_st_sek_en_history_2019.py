"""ST official scope test: no school choice, language variant or achievement inferred."""
import json
from pathlib import Path

from schulpilot.curriculum import import_catalogue
from schulpilot.curriculum_models import CurriculumDocument, CurriculumTopic
from schulpilot.curriculum_schemas import CatalogueInput
from schulpilot.db import DB, Activity, Job, Subject, Usage
from sqlalchemy import func, select

PACKAGE = Path(__file__).resolve().parents[1] / 'schulpilot/reference/curriculum-de-st-sek-englisch-geschichte-2019-v1.json'


def package():
    return json.loads(PACKAGE.read_text())


def test_official_sources_and_bands_are_specific_but_not_exhaustive():
    value = CatalogueInput.model_validate(package())
    assert value.coverage.complete is False
    assert len(value.documents) == 2 and len(value.topics) == 46
    assert {d.state_code for d in value.documents} == {'DE-ST'}
    assert {d.school_form_id for d in value.documents} == {'de-st.sekundarschule'}
    assert all(d.edition == '01.08.2019' and d.source_status == 'current_verified' for d in value.documents)
    assert all('CC BY-SA 3.0' in d.source_notes and 'PDF-SHA256' in d.source_notes for d in value.documents)
    assert all(d.official_url.startswith('https://www.bildung-lsa.de/') for d in value.documents)
    assert all(t.page and len(t.quote.split()) == 1 and not t.common_fact_keywords for t in value.topics)
    assert all(t.grades is None for t in value.topics if t.grade_kind == 'phase')
    assert all('3.2.1' in t.section and '3.3.1' in t.section
               for t in value.topics if t.subject_key == 'englisch' and t.grades == [7, 8])
    assert all(t.grade_kind == 'phase' and t.grades is None and 'mindestens zwei' in t.section
               for t in value.topics if '-wahl56-' in t.id)
    assert all(t.subject_key == 'geschichte' and t.grades in ([9], [10])
               for t in value.topics if t.grade_kind == 'exact')


def test_repeat_import_and_grade_filters_never_infer_track_or_optional_choice(api, household):
    raw = package()
    ids = [t['id'] for t in raw['topics']]
    doc_ids = [d['id'] for d in raw['documents']]
    with DB.begin() as db:
        before_docs = db.scalar(select(func.count()).select_from(CurriculumDocument).where(CurriculumDocument.id.in_(doc_ids)))
        before_topics = db.scalar(select(func.count()).select_from(CurriculumTopic).where(CurriculumTopic.id.in_(ids)))
        first = import_catalogue(db, raw)
    with DB.begin() as db:
        second = import_catalogue(db, raw)
    assert first['documents_added'] == 2 - before_docs
    assert first['topics_added'] == 46 - before_topics
    assert second['documents_added'] == second['topics_added'] == 0
    assert first['package_digest'] == second['package_digest']
    with DB() as db:
        subjects = {key: db.scalar(select(Subject.id).where(Subject.key == key, Subject.owner_family_id.is_(None)))
                    for key in ('englisch', 'geschichte')}
    assert all(subjects.values())
    def rows(subject, **params):
        value = api.get('/api/curriculum/topics', params={'state_code':'DE-ST',
            'school_form_id':'de-st.sekundarschule','subject_id':subjects[subject], 'limit':50, **params})
        assert value.status_code == 200
        return [x for x in value.json()['items'] if x['id'] in ids]
    for grade in (5, 6, 7, 8):
        assert rows('englisch', grade=grade)
        history = rows('geschichte', grade=grade)
        assert history and not any('-wahl56-' in x['id'] for x in history)
        assert all(grade in (x['grades'] or []) and x['grade_kind'] != 'phase' for x in history)
    assert rows('englisch', grade=9) == rows('englisch', grade=10) == []
    assert any('-9-erster-weltkrieg-' in x['id'] for x in rows('geschichte', grade=9))
    assert not any('-10-ausstellung-' in x['id'] for x in rows('geschichte', grade=9))
    assert any('-10-ausstellung-' in x['id'] for x in rows('geschichte', grade=10))
    assert not any('-9-erster-weltkrieg-' in x['id'] for x in rows('geschichte', grade=10))
    optional = rows('geschichte', phase='Wahlgruppe Schuljahrgänge 5/6')
    assert len(optional) == 3 and all(x['grades'] is None for x in optional)
    for phase in ('Realschulabschlussbezogener Unterricht 9/10', 'Hauptschulabschlussbezogener Unterricht 9'):
        english = rows('englisch', phase=phase)
        assert english and all(x['grades'] is None for x in english)
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Job)) == 0
        assert db.scalar(select(func.count()).select_from(Usage)) == 0
        assert db.scalar(select(func.count()).select_from(Activity)) == 0
