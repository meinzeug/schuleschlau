"""Read-only outbox/journal comparison; never authorizes a restore.

Run as the application user with its normal environment. Output contains
aggregate counts only. A clean comparison cannot prove historical completeness
or exclude an old/non-cooperating writer.
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "deploy"))

from ledger_snapshot import locked_journal  # noqa: E402
from schulpilot.config import settings  # noqa: E402
from schulpilot.db import ErasureRequest, engine  # noqa: E402
from schulpilot.erasure import VOCABULARY_SCOPES, verify  # noqa: E402
from sqlalchemy import or_, select  # noqa: E402

RETENTION_SECONDS = 35 * 86400
EXTENDED_SCOPES = ("assignment", "grade", "grade_import", "grade_slot", *VOCABULARY_SCOPES)


def compare(records, rows, cutoff):
    """Compare authenticated records with a read-only outbox snapshot."""
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
        if row.scope in EXTENDED_SCOPES:
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
            "retention_window_days": 35,
            "historical_completeness_verified": False, "writer_fence_verified": False,
            "restore_activation_authorized": False}


def audit(path, key, *, now):
    if not key:
        raise RuntimeError("A configured master key is required")
    with locked_journal(path) as source:
        records = [verify(line, key) for line in source.read().decode("utf-8").splitlines() if line]
        with engine.connect() as connection, connection.begin():
            if connection.dialect.name == "postgresql":
                connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            cutoff = now - RETENTION_SECONDS
            statement = select(ErasureRequest.id, ErasureRequest.scope, ErasureRequest.target,
                               ErasureRequest.details, ErasureRequest.created, ErasureRequest.published)
            rows = connection.execute(statement.where(or_(ErasureRequest.published.is_(False),
                                                           ErasureRequest.created >= cutoff))).all()
            return compare(records, rows, cutoff)


def main():
    try:
        result = audit(settings.data_dir / "erasure-ledger.jsonl", settings.master_key, now=int(time.time()))
    except Exception as exc:
        # Never print SQL, URLs, journal records, keys or exception payloads.
        print("Journal audit failed: " + type(exc).__name__, file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return int(bool(result["journal_conflicting_duplicate_ids"] or result["outbox_unpublished"]
                    or result["outbox_recent_missing"] or result["outbox_recent_mismatched"]
                    or result["journal_recent_missing_outbox"]))


if __name__ == "__main__":
    raise SystemExit(main())
