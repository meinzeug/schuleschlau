"""Exercise restore erasures and message retention using synthetic data only.

Run with this runtime's interpreter and backend on PYTHONPATH. This does not
connect to the application's database, access its journal, or validate backup
continuity. It must succeed before switching a restore service to this runtime.
"""

import os

SYNTHETIC_KEY = "synthetic-key-not-a-production-secret"


def main():
    if (os.environ.get("DATABASE_URL") != "sqlite://" or os.environ.get("ENVIRONMENT") != "test"
            or os.environ.get("MASTER_KEY") != SYNTHETIC_KEY or not os.environ.get("DATA_DIR")):
        raise RuntimeError("Explicit synthetic test environment is required")

    from schulpilot.db import Base, Child, Family, Message, User, VocabularyCollection, VocabularyImport, VocabularyItem
    from schulpilot.db import engine as app_engine
    from schulpilot.erasure import reconcile, signed, verify
    from schulpilot.message_retention import RETENTION_SECONDS, purge_expired
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import Session

    if str(app_engine.url) != "sqlite://":
        raise RuntimeError("Application engine is not an in-memory SQLite database")
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            family = Family(name="Synthetic family", synthetic=True)
            user = User(username="synthetic-child", display_name="Synthetic", password_hash="unused", role="child")
            db.add_all((family, user))
            db.flush()
            child = Child(family_id=family.id, user_id=user.id, grade=6)
            db.add(child)
            db.flush()
            deleted = VocabularyItem(child_id=child.id, identity="a" * 64, target_locale="en-GB", word="test",
                                     meaning="synthetic", origin="manual")
            kept = VocabularyItem(child_id=child.id, identity="b" * 64, target_locale="en-GB", word="keep",
                                  meaning="synthetic", origin="manual")
            collection = VocabularyCollection(child_id=child.id, title="Synthetic", target_locale="en-GB")
            imported = VocabularyImport(child_id=child.id, user_id=user.id, request_key="synthetic",
                                        request_digest="c" * 64, target_locale="en-GB", title="Synthetic")
            db.add_all((deleted, kept, collection, imported))
            db.flush()
            targets = (("vocab_item", deleted.id), ("vocab_import", imported.id), ("vocab_set", collection.id))
            kept_id = kept.id
            key = SYNTHETIC_KEY
            records = [verify(signed({"id": str(i) * 32, "scope": "unit", "target": target,
                                      "created": 1, "resource_kind": kind}, key), key)
                       for i, (kind, target) in enumerate(targets, start=1)]
            reconcile(db, records + list(reversed(records)))
            db.flush()
            for (kind, target), model in zip(targets, (VocabularyItem, VocabularyImport, VocabularyCollection)):
                if db.get(model, target) is not None:
                    raise RuntimeError(f"Synthetic {kind} deletion failed")
            if db.get(VocabularyItem, kept_id) is None:
                raise RuntimeError("Unrelated synthetic vocabulary item was deleted")
            current = 1_900_000_000
            old_message = Message(child_id=child.id, kind="help", body="Synthetic", created=current - RETENTION_SECONDS - 1)
            kept_message = Message(child_id=child.id, kind="reply", body="Synthetic", created=current - RETENTION_SECONDS)
            db.add_all((old_message, kept_message))
            db.flush()
            old_id, kept_message_id = old_message.id, kept_message.id
            purge_expired(db, current)
            if db.get(Message, old_id) is not None or db.get(Message, kept_message_id) is None:
                raise RuntimeError("Synthetic message retention failed")
            from visual_restore_probe import probe

            probe(db, SYNTHETIC_KEY)
        print("Synthetic signed visual-review erasures: OK (isolated in-memory database).")
        print("Synthetic signed vocabulary erasures: OK (isolated in-memory database).")
        print("Synthetic restored-message retention: OK (isolated in-memory database).")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
