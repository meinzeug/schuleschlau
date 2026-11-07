"""Apply a current authenticated deletion journal to an isolated restore DB.

Production databases are deliberately refused. Reconcile and inspect an offline
restore first, then activate it through a separately planned recovery procedure.
"""

import argparse
import os
import re
import stat
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

LIVE_UPLOADS = Path("/var/lib/schulpilot/uploads")


def isolated_uploads(path: Path) -> Path:
    """Reject the live tree and its parents, including through path aliases."""
    if path.is_symlink():
        raise ValueError("The restore upload directory must not be a symlink")
    try:
        resolved = path.resolve(strict=True)
        live_paths = {LIVE_UPLOADS.resolve()}
        if os.environ.get("DATA_DIR"):
            live_paths.add((Path(os.environ["DATA_DIR"]) / "uploads").resolve())
    except (OSError, RuntimeError) as exc:
        raise ValueError("Cannot resolve restore upload directory") from exc
    if not resolved.is_dir():
        raise ValueError("Restore uploads must be an existing directory")
    for live in live_paths:
        if resolved == live or live in resolved.parents or resolved in live.parents:
            raise ValueError("The live upload tree is not accepted; use a separate restore copy")
    return resolved


def isolated_database(database_url: str):
    """Reject URL parameters that can override the checked database name.

    This is a guardrail, not proof that an independently operated database or
    filesystem is separate from production.
    """
    from sqlalchemy.engine import make_url
    from sqlalchemy.exc import ArgumentError

    try:
        url = make_url(database_url)
    except ArgumentError as exc:
        raise ValueError("Invalid restore database URL") from exc
    database = url.database or ""
    if url.drivername in {"postgresql", "postgresql+psycopg", "postgresql+psycopg2"}:
        if url.query and dict(url.query) != {"host": "/var/run/postgresql"}:
            raise ValueError("Restore database URL query parameters are not permitted")
        if len(database.encode("utf-8")) > 63 or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*_restore_test", database):
            raise ValueError("Restore PostgreSQL database must end in _restore_test")
        return "postgresql", database
    if url.drivername in {"sqlite", "sqlite+pysqlite"}:
        if url.query:
            raise ValueError("Restore database URL query parameters are not permitted")
        path = Path(database)
        try:
            if path.is_symlink():
                raise ValueError("Restore SQLite database must not be a symlink")
            resolved = path.resolve(strict=True)
            info = resolved.stat()
        except (OSError, RuntimeError) as exc:
            raise ValueError("Restore SQLite database must already exist") from exc
        if not resolved.name.endswith("_restore_test") or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("Restore SQLite database must be a single-link regular copy ending in _restore_test")
        return "sqlite", str(resolved)
    raise ValueError("Unsupported restore database driver")


def verify_connected_database(db, kind: str, expected: str):
    """Recheck the backend-reported target before changing any data."""
    from sqlalchemy import text

    if kind == "postgresql":
        actual = db.execute(text("SELECT current_database()")).scalar_one()
        if actual != expected:
            raise ValueError("Connected PostgreSQL database does not match the requested restore database")
    else:
        rows = db.execute(text("PRAGMA database_list")).all()
        paths = [row[2] for row in rows if row[1] == "main"]
        if len(paths) != 1 or not paths[0] or Path(paths[0]).resolve(strict=True) != Path(expected):
            raise ValueError("Connected SQLite database does not match the requested restore database")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--master-key-file", type=Path, required=True)
    parser.add_argument("--uploads", type=Path, required=True)
    parser.add_argument("--retention-as-of", type=int, required=True,
                        help="Verified UTC Unix time from a trusted clock, not an unchecked offline host")
    args = parser.parse_args()
    local_now = int(time.time())
    # This bound catches obviously stale or future operator input. It does not
    # certify the local clock or replace the required independent verification.
    if not local_now - 86400 <= args.retention_as_of <= local_now + 300:
        parser.error("Retention time must be independently verified and close to the local clock")
    try:
        args.uploads = isolated_uploads(args.uploads)
    except ValueError as exc:
        parser.error(str(exc))
    try:
        database_kind, database_target = isolated_database(args.database_url)
    except ValueError as exc:
        parser.error(str(exc))
    os.environ["DATABASE_URL"] = args.database_url
    from schulpilot.conversation_retention import purge_expired as purge_expired_conversations
    from schulpilot.db import DB, ProviderConfig, Session, Token
    from schulpilot.erasure import reconcile, retained_image_names, valid_image_name, verify
    from schulpilot.message_retention import purge_expired as purge_expired_messages
    from schulpilot.restore_push import clear_restored_push
    from sqlalchemy import update

    key = args.master_key_file.read_text().strip()
    records = [verify(line, key) for line in args.ledger.read_text().splitlines() if line]
    with DB.begin() as db:
        verify_connected_database(db, database_kind, database_target)
        paths = reconcile(db, records)
        clear_restored_push(db)
        # A snapshot can contain messages that expired after it was taken.
        # The journal does not currently contain per-message retention events.
        purge_expired_messages(db, args.retention_as_of)
        # These directly expired records are not represented by individual
        # journal events either. Reapply precisely the live retention cutoff.
        purge_expired_conversations(db, args.retention_as_of)
        # A backup must never resurrect sessions or device push authorizations.
        db.execute(update(Session).values(revoked=True))
        db.execute(update(Token).values(used=True))
        db.execute(update(ProviderConfig).values(emergency_stop=True))
        retained = retained_image_names(db)
    for name in paths:
        if not valid_image_name(name):
            raise RuntimeError("Unexpected private image path")
        (args.uploads / name).unlink(missing_ok=True)
    for photo in args.uploads.glob("*.jpg"):
        if photo.name not in retained:
            photo.unlink()
    print("Isolated deletion reconciliation completed; all restored sessions revoked. "
          "Journal completeness and freshness were not verified; do not activate this database.")


if __name__ == "__main__":
    main()
