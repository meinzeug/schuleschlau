"""Deletion outbox plus authenticated journal, kept outside database restores.

Only random record IDs, scopes and timestamps; no names or learning content.
Restore tools must verify the journal before applying any record.
"""

import fcntl
import hashlib
import hmac
import json
import os
import re
import tempfile
import threading
from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy import delete, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.sql.dml import Insert

from .config import settings
from .db import DB, Assignment, Child, ErasureRequest, Family, LearningUnit, Material, Membership, SchoolDay, User, now

VOCABULARY_SCOPES = ("vocab_item", "vocab_import", "vocab_set")
SCOPES = ("family", "child", "user", "material", "membership", "unit", "assignment", "grade", "grade_import", "grade_slot", *VOCABULARY_SCOPES)

_journal_owner = ContextVar("schulpilot_journal_owner", default=None)
_SESSION_LOCK_KEY = "schulpilot_erasure_lock"
_CONNECTION_LOCK_KEY = "schulpilot_erasure_connection_lock"


def _current_journal_owner():
    token = _journal_owner.get()
    if (token is None or not token["active"] or token["pid"] != os.getpid()
            or token["thread"] != threading.get_ident()):
        raise RuntimeError("Erasure transaction requires the journal write lock")
    return token


def _require_journal_owner(db):
    token = _current_journal_owner()
    recorded = db.info.setdefault(_SESSION_LOCK_KEY, token)
    if recorded is not token:
        raise RuntimeError("Erasure transaction outlived its journal write lock")


def _uses_application_pool(db):
    from .db import engine

    bind = db.get_bind(mapper=ErasureRequest)
    bound_engine = getattr(bind, "engine", bind)
    return getattr(bound_engine, "pool", None) is engine.pool


@event.listens_for(OrmSession, "before_flush")
def _guard_erasure_flush(db, _context, _instances):
    if any(isinstance(item, ErasureRequest) for item in db.new) and _uses_application_pool(db):
        _require_journal_owner(db)


@event.listens_for(OrmSession, "do_orm_execute")
def _guard_erasure_insert(state):
    table = getattr(state.statement, "table", None)
    if (state.is_insert and getattr(table, "name", None) == ErasureRequest.__tablename__
            and _uses_application_pool(state.session)):
        _require_journal_owner(state.session)


@event.listens_for(Engine, "before_execute")
def _guard_erasure_connection_insert(connection, clause, _multiparams, _params, _options):
    # Guard SQLAlchemy Core and legacy bulk paths on the application engine.
    # Other separately created restore engines must be able to import snapshots.
    from .db import engine

    if (connection.engine.pool is engine.pool and isinstance(clause, Insert)
            and getattr(clause.table, "name", None) == ErasureRequest.__tablename__):
        if connection.get_execution_options().get("isolation_level") == "AUTOCOMMIT":
            raise RuntimeError("Erasure records require a transactional connection")
        token = _current_journal_owner()
        recorded = connection.info.setdefault(_CONNECTION_LOCK_KEY, token)
        if recorded is not token:
            raise RuntimeError("Erasure transaction outlived its journal write lock")


@event.listens_for(Engine, "commit")
def _guard_erasure_connection_commit(connection):
    recorded = connection.info.get(_CONNECTION_LOCK_KEY)
    if recorded is not None:
        if _current_journal_owner() is not recorded:
            raise RuntimeError("Erasure transaction outlived its journal write lock")
        # The event runs before DBAPI commit. Retain the marker until pool
        # reset: commit can fail while leaving the physical transaction open.


@event.listens_for(Engine, "reset")
def _clear_erasure_pool_connection(dbapi_connection, connection_record, _reset_state):
    if _CONNECTION_LOCK_KEY in connection_record.info:
        # SQLAlchemy can regard a transaction as inactive after a failed
        # commit and skip its ordinary pool rollback even though the DBAPI
        # transaction is still open. Force the physical rollback *before*
        # clearing the guard; a failure invalidates the pooled connection.
        dbapi_connection.rollback()
        connection_record.info.pop(_CONNECTION_LOCK_KEY, None)


@event.listens_for(OrmSession, "before_commit")
def _guard_erasure_commit(db):
    if (_SESSION_LOCK_KEY in db.info
            or (any(isinstance(item, ErasureRequest) for item in db.new) and _uses_application_pool(db))):
        _require_journal_owner(db)


@event.listens_for(OrmSession, "after_transaction_end")
def _clear_erasure_transaction(db, transaction):
    if transaction.parent is None:
        db.info.pop(_SESSION_LOCK_KEY, None)


def validate_grade_details(details):
    if not isinstance(details, dict) or set(details) != {'version', 'child_id', 'entries', 'excluded', 'slots', 'request_digest'}:
        raise ValueError('Invalid grade erasure details')
    if type(details['version']) is not int or details['version'] != 1 or not isinstance(details['child_id'], str) or not re.fullmatch(r'[a-f0-9]{32}', details['child_id']):
        raise ValueError('Invalid grade erasure child or version')
    digest = details['request_digest']
    if digest is not None and (not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest)):
        raise ValueError('Invalid grade erasure request digest')
    entries, excluded, slots = details['entries'], details['excluded'], details['slots']
    if (not isinstance(entries, list) or not isinstance(excluded, list) or not isinstance(slots, list)
            or len(entries) + len(excluded) > 10000 or len(slots) > 10000):
        raise ValueError('Invalid grade erasure sources')
    if any(not isinstance(s, str) or not re.fullmatch(r'[a-f0-9]{32}', s) for s in slots) or len(set(slots)) != len(slots):
        raise ValueError('Invalid grade erasure slots')
    pairs = []
    for entry in entries + excluded:
        if (not isinstance(entry, dict) or set(entry) != {'import_id', 'entry_index'}
                or not isinstance(entry['import_id'], str) or not re.fullmatch(r'[a-f0-9]{32}', entry['import_id'])
                or type(entry['entry_index']) is not int or not 0 <= entry['entry_index'] < 1200):
            raise ValueError('Invalid grade erasure entry')
        pairs.append((entry['import_id'], entry['entry_index']))
    if len(set(pairs)) != len(pairs):
        raise ValueError('Duplicate grade erasure entry')


def request(db, scope, target, *, details=None):
    if scope not in SCOPES or not re.fullmatch(r"[a-f0-9]{32}", target):
        raise ValueError("Invalid erasure identifier")
    if scope == 'grade':
        validate_grade_details(details)
    elif details is not None:
        raise ValueError('Unexpected erasure details')
    _require_journal_owner(db)
    db.add(ErasureRequest(scope=scope, target=target, details=details))


def signed(record, key):
    payload = json.dumps(record, sort_keys=True, separators=(",", ":"))
    signature = hmac.new(key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return json.dumps({"record": record, "signature": signature}, separators=(",", ":"))


def verify(raw, key):
    value = json.loads(raw)
    record = value["record"]
    expected = json.loads(signed(record, key))["signature"]
    if not hmac.compare_digest(value["signature"], expected):
        raise ValueError("Erasure journal authentication failed")
    if record.get("resource_kind") not in (None, "assignment", "grade", "grade_import", "grade_slot", *VOCABULARY_SCOPES) or (
        record.get("resource_kind") and record["scope"] != "unit"
    ):
        raise ValueError("Invalid erasure resource kind")
    if record.get('resource_kind') == 'grade':
        validate_grade_details(record.get('details'))
    elif 'details' in record:
        raise ValueError('Unexpected erasure details')
    if record["scope"] not in SCOPES or record['scope'] in ('grade', 'grade_import', 'grade_slot', *VOCABULARY_SCOPES):
        raise ValueError("Invalid erasure scope")
    if not all(re.fullmatch(r"[a-f0-9]{32}", record[k]) for k in ("id", "target")):
        raise ValueError("Invalid erasure identifier")
    return record


@contextmanager
def journal_write_lock():
    """Serialize a deletion commit against an authenticated journal snapshot."""
    if _journal_owner.get() is not None:
        raise RuntimeError("Nested journal write locks are not supported")
    fd = os.open(settings.data_dir / ".erasure-ledger.lock", os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, "r+") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        token = {"active": True, "pid": os.getpid(), "thread": threading.get_ident()}
        context_token = _journal_owner.set(token)
        try:
            yield
        finally:
            token["active"] = False
            _journal_owner.reset(context_token)


def flush_journal():
    path = settings.data_dir / "erasure-ledger.jsonl"
    # Lock before opening the transaction: holding a database reader while
    # waiting for a writer with this lock can deadlock SQLite commits.
    with journal_write_lock(), DB.begin() as db:
        rows = list(db.scalars(select(ErasureRequest).where(ErasureRequest.published.is_(False))))
        if not rows:
            return
        if not settings.master_key:
            raise RuntimeError("An erasure journal requires the protected master key")
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(descriptor, "a") as output:
            fcntl.flock(output, fcntl.LOCK_EX)
            for row in rows:
                record = {k: getattr(row, k) for k in ("id", "scope", "target", "created")}
                if row.scope == "assignment":
                    record["scope"] = "unit"
                    record["resource_kind"] = "assignment"
                elif row.scope in ('grade', 'grade_import', 'grade_slot', *VOCABULARY_SCOPES):
                    if row.scope == 'grade':
                        validate_grade_details(row.details)
                        record['details'] = row.details
                    record['scope'] = 'unit'
                    record['resource_kind'] = row.scope
                output.write(signed(record, settings.master_key) + "\n")
                row.published = True
            output.flush()
            os.fsync(output.fileno())
        # A crash before commit may append duplicate signed IDs; replay is
        # idempotent and maintenance retries pending outbox rows.


def prune_journal():
    """35 days exceeds all allowed 14-day backups; never keep private names."""
    cutoff = int(now()) - 35 * 86400
    path = settings.data_dir / "erasure-ledger.jsonl"
    lock = os.open(settings.data_dir / ".erasure-ledger.lock", os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(lock, "r+") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        if path.exists():
            records = [verify(line, settings.master_key) for line in path.read_text().splitlines() if line]
            kept = {r["id"]: r for r in records if r["created"] >= cutoff}
            with tempfile.NamedTemporaryFile(
                mode="w", dir=settings.data_dir, prefix=".erasure-", delete=False
            ) as output:
                temporary = output.name
                for record in kept.values():
                    output.write(signed(record, settings.master_key) + "\n")
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
    with DB.begin() as db:
        db.execute(delete(ErasureRequest).where(ErasureRequest.published.is_(True), ErasureRequest.created < cutoff))


def reconcile(db, records):
    """Apply verified IDs in an isolated restore DB; return obsolete image paths."""
    from .families import remove_child, remove_family

    records = [
        {**record, "scope": record['resource_kind']}
        if record["scope"] == "unit" and record.get("resource_kind") in ('assignment', 'grade', 'grade_import', 'grade_slot', *VOCABULARY_SCOPES)
        else record for record in records
    ]
    paths = []
    # Collect image paths before user cascades can remove their Material rows.
    order = {"family": 0, "child": 1, "grade": 2, "grade_import": 3, "grade_slot": 4, "unit": 5,
             "assignment": 6, "vocab_item": 7, "vocab_import": 8, "vocab_set": 9,
             "material": 10, "membership": 11, "user": 12}
    for record in sorted(records, key=lambda record: order[record["scope"]]):
        scope, target = record["scope"], record["target"]
        if scope in VOCABULARY_SCOPES:
            from .db import VocabularyCollection, VocabularyImport, VocabularyItem

            model = {"vocab_item": VocabularyItem, "vocab_import": VocabularyImport,
                     "vocab_set": VocabularyCollection}[scope]
            row = db.get(model, target)
            if row is not None:
                db.delete(row)
                db.flush()
            continue
        if scope in ('grade_import', 'grade_slot'):
            from .db import GradeImport, GradeSourceSlot

            row = db.get(GradeImport if scope == 'grade_import' else GradeSourceSlot, target)
            if row is not None:
                db.delete(row)
                db.flush()
            continue
        if scope == 'grade':
            from .db import DeletedGradeRequest, SchoolGrade
            from .grade_erasure import redact_grade_sources

            details = record.get('details')
            validate_grade_details(details)
            child_id = details['child_id']
            if db.get(Child, child_id) is None:
                continue
            grade = db.get(SchoolGrade, target)
            if grade is not None and grade.child_id != child_id:
                raise ValueError('Grade erasure belongs to another child')
            redact_grade_sources(db, {'child_id': child_id, 'grade_id': target,
                                      'entries': details['entries'], 'slots': details['slots']}, allow_missing=True)
            digest = details['request_digest']
            if digest and not db.scalar(select(DeletedGradeRequest.id).where(
                DeletedGradeRequest.child_id == child_id, DeletedGradeRequest.request_key_digest == digest
            )):
                db.add(DeletedGradeRequest(child_id=child_id, request_key_digest=digest))
            if grade is not None:
                db.delete(grade)
            db.flush()
            continue
        model = {
            "family": Family,
            "child": Child,
            "user": User,
            "material": Material,
            "membership": Membership,
            "unit": LearningUnit,
            "assignment": Assignment,
        }[scope]
        row = db.get(model, target)
        if row is None:
            continue
        if scope == "family":
            paths.extend(remove_family(db, row, journal=False))
        elif scope == "child":
            paths.extend(remove_child(db, row, journal=False))
        elif scope == "user":
            from .profile_images import deletion_paths

            paths.extend(deletion_paths(db, target))
            db.execute(delete(User).where(User.id == target))
        elif scope == "membership":
            db.delete(row)
        elif scope == "assignment":
            from .source_cleanup import erase_assignments

            erase_assignments(db, row.child_id, [row.id], journal=False)
        elif scope == "unit":
            from .unit_erasure import remove

            remove(db, db.get(Child, row.child_id), [row.id], journal=False)
        else:
            from .school_preparation import sources_removed
            from .tutor import purge_source_turns
            from .unit_erasure import linked_ids, remove

            # Older journals only recorded the page. A restore must not revive
            # its rounds, follow-ups or evidence after replaying that deletion.
            remove(db, db.get(Child, row.child_id), linked_ids(db, row.child_id, [row.id]), journal=False)
            from .source_lineage import purge_diagnostic_outputs

            purge_diagnostic_outputs(db, [row.id], unlink_files=False)
            purge_source_turns(db, [row.id], child_id=row.child_id)
            if row.path:
                paths.append(row.path)
            day = db.get(SchoolDay, row.school_day_id) if row.school_day_id else None
            db.delete(row)
            db.flush()
            if day:
                day.revision += 1
                sources_removed(db, day)
        db.flush()
    return paths


def retained_image_names(db):
    """Current private file pointers, including own-account profile images."""
    from .db import UserAvatar
    from .profile_images import filename

    known = set(db.scalars(select(Material.path).where(Material.path.is_not(None))))
    known.update(
        filename(row.user_id, row.revision)
        for row in db.scalars(select(UserAvatar).where(UserAvatar.image_digest.is_not(None)))
    )
    return known


def valid_image_name(name):
    return bool(re.fullmatch(r"(?:[a-f0-9]{32}|avatar-[a-f0-9]{64}-[a-f0-9]{32})\.jpg", name))


def prune_orphan_images(db):
    """Remove interrupted upload writes after a grace period, within our directory."""
    known = retained_image_names(db)
    removed = 0
    for path in (settings.data_dir / "uploads").glob("*.jpg"):
        try:
            modified = path.lstat().st_mtime
        except FileNotFoundError:
            continue
        if valid_image_name(path.name) and path.name not in known and modified < now() - 3600:
            path.unlink(missing_ok=True)
            removed += 1
    return removed
