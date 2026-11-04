"""Synthetic word data: explicit deletion and expiry survive an older restore."""

from datetime import date

from conftest import create_child
from schulpilot.config import settings
from schulpilot.db import (
    DB,
    Attempt,
    Base,
    ErasureRequest,
    LearningUnit,
    Material,
    VocabularyCollection,
    VocabularyImport,
    VocabularyItem,
    VocabularyMembership,
    VocabularyReview,
    VocabularyReviewEvent,
    now,
)
from schulpilot.erasure import prune_journal, reconcile, signed, verify
from schulpilot.vocabulary import collection_data
from schulpilot.worker import maintenance
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


def snapshot():
    with DB() as db:
        return {table: list(db.execute(table.select()).mappings()) for table in Base.metadata.sorted_tables}


def restore(data, records, check):
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as con:
        con.exec_driver_sql("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    try:
        with engine.begin() as con:
            for table, rows in data.items():
                if rows:
                    con.execute(table.insert(), [dict(row) for row in rows])
        with Session(engine) as db:
            reconcile(db, records[::-1] + records)
            db.commit()
            check(db)
    finally:
        engine.dispose()


def records_for(targets):
    lines = (settings.data_dir / "erasure-ledger.jsonl").read_text().splitlines()
    return [row for line in lines if (row := verify(line, settings.master_key))["target"] in targets]


def item(child_id, word, created=None):
    row = VocabularyItem(child_id=child_id, identity=(word[0] * 64), target_locale="en-GB", word=word,
                         meaning="Künstlich", origin="manual", confirmed=True)
    if created is not None:
        row.created = created
    return row


def test_word_import_collection_deletion_survives_restore_with_cascades_and_preserves_answers(api, household):
    user, child = household
    sibling = create_child(api, user, "vocab-restore-sibling")
    with DB.begin() as db:
        page = Material(child_id=child["id"], title="Künstliche Seite", content="apple", confirmed=True)
        word, keep, sibling_word = item(child["id"], "apple"), item(child["id"], "book"), item(sibling["id"], "cat")
        group = VocabularyCollection(child_id=child["id"], title="Künstliche Sammlung", target_locale="en-GB")
        db.add_all([page, word, keep, sibling_word, group])
        db.flush()
        db.add_all([VocabularyMembership(collection_id=group.id, item_id=word.id),
                    VocabularyMembership(collection_id=group.id, item_id=keep.id)])
        pending = VocabularyImport(child_id=child["id"], user_id=user["id"], request_key="synthetic-import-key",
            request_digest="a" * 64, target_locale="en-GB", title="Künstliche Vorschläge", pairs=[], status="review")
        review = VocabularyReview(child_id=child["id"], item_id=word.id, revision=1, direction="de_to_target",
                                  skill="spelling", due=date.today().isoformat())
        unit = LearningUnit(child_id=child["id"], subject="Englisch", topic="Künstlich", explanation="Test",
                            questions=[], provider="synthetic")
        db.add_all([pending, review, unit])
        db.flush()
        attempt = Attempt(unit_id=unit.id, question_id="q1", answer="synthetic", outcome="correct")
        db.add(attempt)
        db.flush()
        db.add(VocabularyReviewEvent(attempt_id=attempt.id, review_id=review.id, day=date.today().isoformat(),
                                     advanced=False, stage=0, due=date.today().isoformat()))
        ids = {"page": page.id, "word": word.id, "keep": keep.id, "sibling": sibling_word.id, "set": group.id,
               "import": pending.id, "review": review.id, "attempt": attempt.id}
        group_snapshot = collection_data(db, group)["snapshot"]
    backup = snapshot()
    root = f"/api/children/{child['id']}/vocabulary"
    assert api.delete(f"{root}/{ids['word']}?revision=1").status_code == 200
    assert api.delete(f"{root}/imports/{ids['import']}").status_code == 200
    # Word deletion changes group membership; recalculate the explicit snapshot.
    with DB() as db:
        group_snapshot = collection_data(db, db.get(VocabularyCollection, ids["set"]))["snapshot"]
    assert api.request("DELETE", f"{root}/collections/{ids['set']}", json={"snapshot": group_snapshot}).status_code == 200
    targets = {ids["word"], ids["import"], ids["set"]}
    records = records_for(targets)
    assert {row.get("resource_kind") for row in records} == {"vocab_item", "vocab_import", "vocab_set"}
    assert all("apple" not in str(row) for row in records)
    def check(db):
        assert not db.get(VocabularyItem, ids["word"])
        assert not db.get(VocabularyImport, ids["import"])
        assert not db.get(VocabularyCollection, ids["set"])
        assert not db.get(VocabularyReview, ids["review"])
        assert not db.get(VocabularyReviewEvent, ids["attempt"])
        assert db.get(Attempt, ids["attempt"]) and db.get(Material, ids["page"])
        assert db.get(VocabularyItem, ids["keep"]) and db.get(VocabularyItem, ids["sibling"])
    restore(backup, records, check)


def test_expired_words_import_and_collection_are_journalled_once_and_cannot_return(api, household):
    user, child = household
    old = int(now()) - 366 * 86400
    with DB.begin() as db:
        word, keep = item(child["id"], "apple", old), item(child["id"], "book")
        group = VocabularyCollection(child_id=child["id"], title="Old", target_locale="en-GB", created=old)
        pending = VocabularyImport(child_id=child["id"], user_id=user["id"], request_key="retention-example",
                                   request_digest="b" * 64, target_locale="en-GB", title="Old", pairs=[], created=old)
        db.add_all([word, keep, group, pending])
        db.flush()
        ids = word.id, keep.id, group.id, pending.id
    backup = snapshot()
    maintenance()
    maintenance()
    targets = {ids[0], ids[2], ids[3]}
    records = records_for(targets)
    assert len(records) == 3
    with DB() as db:
        rows = list(db.scalars(select(ErasureRequest).where(ErasureRequest.target.in_(targets))))
        assert len(rows) == 3 and all(row.published for row in rows)
    def check(db):
        assert not db.get(VocabularyItem, ids[0]) and db.get(VocabularyItem, ids[1])
        assert not db.get(VocabularyCollection, ids[2]) and not db.get(VocabularyImport, ids[3])
    restore(backup, records, check)


def test_vocabulary_signed_deletion_retention_covers_14_day_backups(api):
    records = [{"id": digit * 32, "scope": "unit", "target": target * 32, "created": int(now()) - days * 86400,
                "resource_kind": "vocab_item"} for digit, target, days in (("a", "b", 15), ("c", "d", 36))]
    path = settings.data_dir / "erasure-ledger.jsonl"
    with path.open("a") as output:
        for record in records:
            output.write(signed(record, settings.master_key) + "\n")
    prune_journal()
    ids = {verify(line, settings.master_key)["id"] for line in path.read_text().splitlines()}
    assert records[0]["id"] in ids and records[1]["id"] not in ids


def test_deleted_deterministic_collection_cannot_be_recreated_with_old_action_key(api, household):
    _, child = household
    root = f"/api/children/{child['id']}/vocabulary/collections"
    key = {"Idempotency-Key": "synthetic-collection-replay-001"}
    body = {"title": "Künstlicher Wortschatz", "target_locale": "en-GB"}
    response = api.post(root, json=body, headers=key)
    assert response.status_code == 201
    collection = response.json()
    assert api.request("DELETE", f"{root}/{collection['id']}", json={"snapshot": collection["snapshot"]}).status_code == 200
    assert api.post(root, json=body, headers=key).status_code == 409
    assert api.post(root, json=body, headers={"Idempotency-Key": "synthetic-new-collection-0002"}).status_code == 201
