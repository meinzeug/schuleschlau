"""Source-linked Saxony-Anhalt secondary Biology curriculum sample."""
import json
from pathlib import Path

from schulpilot import curriculum
from schulpilot.curriculum_schemas import CatalogueInput
from schulpilot.db import DB, Activity, Job, Usage
from sqlalchemy import func, select

SOURCE = (Path(__file__).parents[1] / 'schulpilot/reference/'
          'curriculum-st-sekundarschule-biologie-2019.json')


def package():
    return json.loads(SOURCE.read_text())


def test_biology_source_scope_and_9th_grade_footnote():
    data = CatalogueInput.model_validate(package())
    assert len(data.documents) == 1
    doc = data.documents[0]
    assert (doc.state_code, doc.school_form_id, doc.edition) == (
        'DE-ST', 'de-st.sekundarschule', '01.08.2019')
    assert doc.effective_from is None
    assert '7cab061d2e72d48c463691bfbe7ae101ed4412b4e292724f3f5cc42fa39c5022' in doc.source_notes
    assert 'CC BY-SA 3.0' in doc.source_notes
    assert len(data.topics) == 8
    by_id = {row.id.rsplit('.', 1)[-1]: row for row in data.topics}
    assert by_id['living-things'].grades == [5, 6]
    assert by_id['microbiology'].grades == [7, 8]
    assert by_id['heredity'].grades == [9, 10]
    for name in ('behaviour', 'ecosystems'):
        assert by_id[name].grade_kind == 'exact'
        assert by_id[name].grades == [9]
        assert 'Fußnote' in by_id[name].section
    assert all(row.subject_key == 'biologie' and row.document_id == doc.id for row in data.topics)
    assert data.coverage.complete is False


def test_reviewed_package_import_is_idempotent_and_respects_scope(api, household):
    with DB.begin() as db:
        first = curriculum.import_catalogue(db, package())
        second = curriculum.import_catalogue(db, package())
        # Fresh installations seed the same package; replay never duplicates it.
        assert (first['documents_added'], first['topics_added']) == (0, 0)
        assert (second['documents_added'], second['topics_added']) == (0, 0)
    before = {}
    with DB() as db:
        for model in (Activity, Job, Usage):
            before[model] = db.scalar(select(func.count()).select_from(model))

    def selected(grade, form='de-st.sekundarschule'):
        response = api.get('/api/curriculum/topics', params={
            'state_code': 'DE-ST', 'school_form_id': form, 'grade': grade,
            'query': '', 'limit': 50,
        })
        assert response.status_code == 200
        return [row for row in response.json()['items']
                if row['source']['document_id'] == 'st-sek-biology-2019']

    assert len(selected(5)) == len(selected(6)) == 2
    assert len(selected(7)) == len(selected(8)) == 2
    assert len(selected(9)) == 4 and len(selected(10)) == 2
    assert not selected(4) and not selected(11)
    assert not selected(6, 'de-st.gymnasium')
    assert all(row['grade_kind'] == 'band' and row['grades'] == [5, 6] for row in selected(6))
    assert all(row['source']['url'].startswith('https://www.bildung-lsa.de/') for row in selected(6))
    with DB() as db:
        assert all(db.scalar(select(func.count()).select_from(model)) == before[model] for model in before)
