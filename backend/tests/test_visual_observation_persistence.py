"""Artificial image observations are private provisional data, never lesson text."""
from types import SimpleNamespace

from schulpilot.db import DB, Child, Material
from schulpilot.families import export_child
from schulpilot.material_review import _protected_readings, request
from schulpilot.source_lineage import learning_source, save_snapshot, source_snapshot
from schulpilot.source_lineage_models import SourceRevision
from sqlalchemy import select


def obs(description):
    return {"description": description, "image_region": None, "uncertainty": "vorläufig"}


def test_snapshot_projection_export_and_delete(api, household):
    _, child = household
    with DB.begin() as db:
        material = Material(child_id=child['id'], title='Test', content='Wörtlicher Text', confirmed=True,
                            visual_observations=[obs('Zwei blaue Felder')])
        db.add(material)
        db.flush()
        mid = material.id
        snapshot = save_snapshot(db, material, 'test')
        assert snapshot.snapshot['visual_observations'] == [obs('Zwei blaue Felder')]
        assert 'Zwei blaue Felder' not in learning_source(db, material)['content']
        exported = export_child(db, db.get(Child, child['id']))
        assert next(row for row in exported['materials'] if row['id'] == mid)['visual_observations'] == [obs('Zwei blaue Felder')]
    response = api.get('/api/materials/' + mid)
    assert response.status_code == 200
    assert response.json()['visual_observations_status'] == 'unverified'
    assert response.json()['visual_observations'] == [obs('Zwei blaue Felder')]
    with DB.begin() as db:
        db.delete(db.get(Material, mid))
    with DB() as db:
        assert not db.scalars(select(SourceRevision).where(SourceRevision.material_id == mid)).all()


def test_contradictory_readings_remain_separate_and_bounded():
    first = obs('Zwei Felder sind blau')
    second = obs('Drei Felder sind blau')
    snapshot = SimpleNamespace(snapshot={'source_blocks': [], 'visual_observations': [first]})
    data = {'source_blocks': [], 'content': '', 'legibility': 'readable', 'uncertainties': [],
            'visual_observations': [second]}
    merged = _protected_readings(data, snapshot)
    assert merged['visual_observations'] == [first, second]
    assert merged['content'] == ''
    snapshot.snapshot['visual_observations'] = [obs(str(n)) for n in range(20)]
    assert len(_protected_readings(data, snapshot)["visual_observations"]) == 20


def test_historical_snapshot_without_visual_field_can_be_checked():
    old = SimpleNamespace(snapshot={'subject': 'Mathematik', 'topic': 'Brüche', 'content': 'Text',
        'source_blocks': [], 'uncertainties': [], 'homework': [], 'legibility': 'readable'})
    assert request(old)['transcription_check']['first_reading'].get('visual_observations', []) == []


def test_empty_field_does_not_change_legacy_source_snapshot_digest(api, household):
    _, child = household
    with DB.begin() as db:
        material = Material(child_id=child['id'], title='Altseite', content='Text', confirmed=True)
        db.add(material)
        db.flush()
        original = source_snapshot(material)
        assert 'visual_observations' not in original
        saved = save_snapshot(db, material, 'legacy')
        material.visual_observations = []
        assert source_snapshot(material) == original
        assert save_snapshot(db, material, 'legacy').id == saved.id


def test_journal_replay_erases_visual_observation_and_snapshot(api, household):
    from schulpilot.erasure import reconcile

    _, child = household
    with DB.begin() as db:
        material = Material(child_id=child['id'], title='Wiederherstellung', content='Text', confirmed=True,
                            visual_observations=[obs('Privater Bildbefund')])
        db.add(material)
        db.flush()
        mid = material.id
        save_snapshot(db, material, 'test')
    with DB.begin() as db:
        reconcile(db, [{'scope': 'material', 'target': mid}])
        assert db.get(Material, mid) is None
        assert not db.scalars(select(SourceRevision).where(SourceRevision.material_id == mid)).all()


def test_visual_observation_cannot_be_read_by_other_family(api, household, mailbox):
    from conftest import register

    _, child = household
    with DB.begin() as db:
        material = Material(child_id=child['id'], title='Privat', content='Text',
                            visual_observations=[obs('Privater Bildbefund')])
        db.add(material)
        db.flush()
        mid = material.id
    register(api, mailbox, email='other-family@example.org')
    response = api.get('/api/materials/' + mid)
    assert response.status_code in (403, 404)
    assert 'Privater Bildbefund' not in response.text


def test_explicit_review_is_separate_revision_bound_exported_and_deleted(api, household):
    from schulpilot.source_lineage import digest
    from schulpilot.source_lineage_models import VisualObservationReview

    _, child = household
    observations = [obs('Zwei blaue Felder'), obs('Drei graue Felder')]
    with DB.begin() as db:
        material = Material(child_id=child['id'], title='Test', content='Wortlaut', confirmed=True,
            status='confirmed', image_digest='a' * 64, visual_observations=observations)
        db.add(material)
        db.flush()
        mid = material.id
        snapshot = source_snapshot(material)
        revision = material.revision
    path = f'/api/materials/{mid}/visual-observations/0/review'
    body = {'revision': revision, 'image_digest': 'a' * 64, 'observations_digest': digest(observations),
            'review_version': 0, 'decision': 'corrected', 'observation': obs('Ein blaues Feld')}
    shifted = obs('Ein blaues Feld') | {'image_region': {'left': 10, 'top': 10, 'right': 30, 'bottom': 30}}
    assert api.put(path, json={**body, 'observation': shifted}).status_code == 422
    response = api.put(path, json=body)
    assert response.status_code == 200, response.text
    review = response.json()['visual_observation_reviews']
    assert len(review) == 1 and review[0]['index'] == 0 and review[0]['review_version'] == 1
    assert response.json()['visual_observations'] == observations
    assert api.put(path, json=body).status_code == 200  # lost-response retry
    assert api.put(path, json={**body, 'observation': obs('Andere Angabe')}).status_code == 409
    assert api.put(path, json={**body, 'observations_digest': 'f' * 64}).status_code == 409
    second = api.put(path, json={**body, 'review_version': 1, 'observation': obs('Jetzt zwei Felder')})
    assert second.status_code == 200 and second.json()['visual_observation_reviews'][0]['review_version'] == 2
    with DB() as db:
        material = db.get(Material, mid)
        assert material.revision == revision and source_snapshot(material) == snapshot
        assert 'Ein blaues Feld' not in learning_source(db, material)['content']
        exported = export_child(db, db.get(Child, child['id']))
        assert len(exported['visual_observation_reviews']) == 2
    with DB.begin() as db:
        db.delete(db.get(Material, mid))
    with DB() as db:
        assert not db.scalars(select(VisualObservationReview).where(VisualObservationReview.material_id == mid)).all()


def test_revoked_session_after_wait_cannot_write_review(api, household, monkeypatch):
    from schulpilot import materials
    from schulpilot.source_lineage import digest
    from schulpilot.source_lineage_models import VisualObservationReview

    _, child = household
    observations = [obs('Ein Balken')]
    with DB.begin() as db:
        material = Material(child_id=child['id'], title='Test', content='Text', status='review',
                            image_digest='a' * 64, visual_observations=observations)
        db.add(material)
        db.flush()
        mid, revision = material.id, material.revision
    original = materials.get_material

    def revoke_while_waiting(db, principal, material_id, write=False):
        result = original(db, principal, material_id, write=write)
        principal.session.revoked = True
        db.flush()
        return result

    monkeypatch.setattr(materials, 'get_material', revoke_while_waiting)
    body = {'revision': revision, 'image_digest': 'a' * 64, 'observations_digest': digest(observations),
            'review_version': 0, 'decision': 'confirmed', 'observation': observations[0]}
    response = api.put(f'/api/materials/{mid}/visual-observations/0/review', json=body)
    assert response.status_code == 401
    with DB() as db:
        assert not db.scalars(select(VisualObservationReview).where(VisualObservationReview.material_id == mid)).all()


def test_signed_material_journal_replay_removes_snapshot_and_all_visual_reviews(api, household):
    from schulpilot.config import settings
    from schulpilot.erasure import signed, verify
    from schulpilot.source_lineage import digest
    from schulpilot.source_lineage_models import VisualObservationReview
    from test_vocabulary_erasure_restore import restore, snapshot

    _, child = household
    observation = obs('Künstlicher Balken')
    with DB.begin() as db:
        material = Material(child_id=child['id'], title='Künstlich', content='Text', status='review',
                            image_digest='a' * 64, visual_observations=[observation])
        db.add(material)
        db.flush()
        mid = material.id
        snapshot_id = save_snapshot(db, material, 'extraction').id
        db.add(VisualObservationReview(material_id=mid, child_id=child['id'], source_revision=material.revision,
            image_digest=material.image_digest, observations_digest=digest([observation]), observation_index=0,
            version=1, decision='confirmed', observation=observation))
        db.flush()
        assert len(export_child(db, db.get(Child, child['id']))['visual_observation_reviews']) == 1
    backup = snapshot()
    record = {'id': 'f' * 32, 'scope': 'material', 'target': mid}
    verified = verify(signed(record, settings.master_key), settings.master_key)

    def check(db):
        assert db.get(Material, mid) is None
        assert db.get(SourceRevision, snapshot_id) is None
        assert not db.scalars(select(VisualObservationReview).where(VisualObservationReview.material_id == mid)).all()

    restore(backup, [verified], check)


def test_ocr_observation_without_region_can_be_confirmed(api, household):
    from schulpilot.extraction import TranscriptionOutput
    from schulpilot.source_lineage import digest

    _, child = household
    extracted = TranscriptionOutput.model_validate({
        'blocks': [{'kind': 'paragraph', 'text': 'Wortlaut'}], 'legibility': 'readable',
        'subject': 'Mathematik', 'topic': 'Bild', 'uncertainties': [], 'homework': [],
        'visual_observations': [{'description': 'Blauer Balken', 'image_region': None, 'uncertainty': ''}],
    }).as_material()
    observations = extracted['visual_observations']
    assert 'image_region' not in observations[0]
    with DB.begin() as db:
        material = Material(child_id=child['id'], title='Test', content=extracted['content'], status='review',
                            image_digest='a' * 64, visual_observations=observations)
        db.add(material)
        db.flush()
        mid, revision = material.id, material.revision
    body = {'revision': revision, 'image_digest': 'a' * 64, 'observations_digest': digest(observations),
            'review_version': 0, 'decision': 'confirmed',
            'observation': {'description': 'Blauer Balken', 'image_region': None, 'uncertainty': ''}}
    response = api.put(f'/api/materials/{mid}/visual-observations/0/review', json=body)
    assert response.status_code == 200, response.text
    assert response.json()['visual_observation_reviews'][0]['decision'] == 'confirmed'
