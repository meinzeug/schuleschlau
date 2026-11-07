"""Bounded read-only outbox/journal comparison; never authorizes a restore.

The CLI accepts PostgreSQL only. SQLite is supported solely through an
explicit injected in-memory test engine. Output is aggregate metadata only.
"""

import fcntl
import json
import os
import signal
import sys
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

RETENTION_SECONDS = 35 * 86400
MAX_JOURNAL_BYTES = 64 * 1024 * 1024
MAX_OUTBOX_ROWS = 10000
MAX_OUTBOX_DETAIL_BYTES = 8192
LOCK_TIMEOUT_SECONDS = 2
STATEMENT_TIMEOUT_MS = 3000
CLI_TIMEOUT_SECONDS = 12


def compare(records, rows, cutoff, extended_scopes=None):
    """Compare authenticated records with a read-only outbox snapshot."""
    if extended_scopes is None:
        from schulpilot.erasure import VOCABULARY_SCOPES
        extended_scopes = ("assignment", "grade", "grade_import", "grade_slot", *VOCABULARY_SCOPES)
    indexed = {}
    duplicates = conflicting_duplicates = 0
    for record in records:
        previous = indexed.get(record["id"])
        if previous is not None:
            duplicates += 1
            conflicting_duplicates += int(previous != record)
        indexed[record["id"]] = record

    pending = matched = missing = mismatched = 0
    outbox_ids = set()
    for row in rows:
        outbox_ids.add(row.id)
        if not row.published:
            pending += 1
            continue
        if row.created < cutoff:
            continue
        actual = indexed.get(row.id)
        if actual is None:
            missing += 1
            continue
        expected = {"id": row.id, "scope": row.scope, "target": row.target, "created": row.created}
        if row.scope in extended_scopes:
            expected["scope"] = "unit"
            expected["resource_kind"] = row.scope
        if row.scope == "grade":
            expected["details"] = row.details
        if actual == expected:
            matched += 1
        else:
            mismatched += 1

    unmatched = sum(item["created"] >= cutoff and ident not in outbox_ids for ident, item in indexed.items())
    return {"authenticated_journal_unique": len(indexed), "journal_duplicate_ids": duplicates,
            "journal_conflicting_duplicate_ids": conflicting_duplicates, "outbox_unpublished": pending,
            "outbox_recent_matched": matched, "outbox_recent_missing": missing,
            "outbox_recent_mismatched": mismatched, "journal_recent_missing_outbox": unmatched,
            "retention_window_days": 35, "installation_identity_verified": False,
            "historical_completeness_verified": False, "writer_fence_verified": False,
            "restore_activation_authorized": False}


@contextmanager
def bounded_journal(path):
    # Reuse the app's stable rotation lock. Never create a missing lock.
    with path.with_name(".erasure-ledger.lock").open("rb") as lock:
        deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Journal lock timeout") from None
                time.sleep(0.02)
        try:
            with path.open("rb") as journal:
                yield journal
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def audit(path, key, *, engine, model, verify_record, extended_scopes, allow_test_sqlite=False):
    if not key:
        raise RuntimeError("A configured master key is required")
    from sqlalchemy import LargeBinary, Text, case, cast, create_engine, func, or_, select
    from sqlalchemy.pool import NullPool

    if engine.dialect.name == "postgresql":
        # An existing application's pool can have an unbounded queue or connect
        # timeout. Use a dedicated short-lived, bounded PostgreSQL connection.
        bind = create_engine(engine.url, connect_args={"connect_timeout": 3}, poolclass=NullPool)
        dispose = True
    elif allow_test_sqlite and engine.dialect.name == "sqlite" and engine.url.database in (None, ":memory:"):
        bind, dispose = engine, False
    else:
        raise ValueError("Only PostgreSQL is accepted")
    try:
        # Connect before taking the lock: a slow or unavailable DB must not
        # block deletion writers. No transaction is opened while awaiting it.
        with bind.connect() as connection:
            with bounded_journal(path) as source:
                cutoff = int(time.time()) - RETENTION_SECONDS
                journal = source.read(MAX_JOURNAL_BYTES + 1)
                if len(journal) > MAX_JOURNAL_BYTES:
                    raise ValueError("Journal exceeds bounded audit size")
                with connection.begin():
                    if connection.dialect.name == "postgresql":
                        connection.exec_driver_sql("SET TRANSACTION READ ONLY")
                        connection.exec_driver_sql(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}")
                        connection.exec_driver_sql("SET LOCAL lock_timeout = 1000")
                    details_text = cast(model.details, Text)
                    size = (func.octet_length(details_text) if connection.dialect.name == "postgresql"
                            else func.length(cast(details_text, LargeBinary)))
                    size = func.coalesce(size, 0)
                    safe_details = case((size <= MAX_OUTBOX_DETAIL_BYTES, model.details), else_=None).label("details")
                    statement = select(model.id, model.scope, model.target, safe_details, model.created,
                                       model.published, size.label("details_size"))
                    statement = statement.where(or_(model.published.is_(False), model.created >= cutoff))
                    statement = statement.limit(MAX_OUTBOX_ROWS + 1)
                    rows = []
                    # PostgreSQL uses a server-side cursor, so a large outbox
                    # cannot be buffered completely by the database driver.
                    with connection.execution_options(stream_results=True).execute(statement) as result:
                        for row in result.yield_per(256):
                            if len(rows) >= MAX_OUTBOX_ROWS or row.details_size > MAX_OUTBOX_DETAIL_BYTES:
                                raise ValueError("Outbox exceeds bounded audit size")
                            rows.append(row)
        # Crypto and comparison do not hold the journal lock or DB session.
        records = [verify_record(line, key) for line in journal.decode("utf-8").splitlines() if line]
        return compare(records, rows, cutoff, extended_scopes)
    finally:
        if dispose:
            bind.dispose()


def _deadline_expired(_signum, _frame):
    # A stuck OS call must release the shared file lock, even if the driver
    # cannot cleanly roll back. Process exit closes its file descriptors.
    os._exit(2)


def main():
    signal.signal(signal.SIGALRM, _deadline_expired)
    signal.alarm(CLI_TIMEOUT_SECONDS)
    try:
        # Configuration, dependencies and engine setup can fail too: never
        # expose their exception strings, database URLs, IDs or secrets.
        from schulpilot.config import settings
        from schulpilot.db import ErasureRequest, engine
        from schulpilot.erasure import VOCABULARY_SCOPES, verify

        scopes = ("assignment", "grade", "grade_import", "grade_slot", *VOCABULARY_SCOPES)
        result = audit(settings.data_dir / "erasure-ledger.jsonl", settings.master_key, engine=engine,
                       model=ErasureRequest, verify_record=verify, extended_scopes=scopes)
        print(json.dumps(result, sort_keys=True))
        return int(bool(result["journal_conflicting_duplicate_ids"] or result["outbox_unpublished"]
                        or result["outbox_recent_missing"] or result["outbox_recent_mismatched"]
                        or result["journal_recent_missing_outbox"]))
    except Exception as exc:
        print("Journal audit failed: " + type(exc).__name__, file=sys.stderr)
        return 1
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    raise SystemExit(main())
