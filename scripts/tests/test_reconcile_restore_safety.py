"""Regression tests for the isolated restoration upload boundary."""

import importlib.util
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("reconcile_restore", ROOT / "scripts/reconcile_restore.py")
reconcile_restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reconcile_restore)


@pytest.fixture
def upload_trees(tmp_path, monkeypatch):
    live = tmp_path / "live" / "uploads"
    child = live / "subdirectory"
    child.mkdir(parents=True)
    separate = tmp_path / "restore" / "uploads"
    separate.mkdir(parents=True)
    monkeypatch.setattr(reconcile_restore, "LIVE_UPLOADS", live)
    return live, child, separate


def test_separate_restore_copy_is_allowed(upload_trees):
    _, _, separate = upload_trees
    assert reconcile_restore.isolated_uploads(separate) == separate.resolve()


@pytest.mark.parametrize("path_name", ["live", "child", "parent"])
def test_live_upload_tree_and_ancestors_are_refused(upload_trees, path_name):
    live, child, _ = upload_trees
    target = {"live": live, "child": child, "parent": live.parent}[path_name]
    with pytest.raises(ValueError, match="live upload tree"):
        reconcile_restore.isolated_uploads(target)


def test_parent_symlink_cannot_hide_live_subdirectory(tmp_path, upload_trees):
    live, _, _ = upload_trees
    alias = tmp_path / "alias"
    alias.symlink_to(live, target_is_directory=True)
    with pytest.raises(ValueError, match="live upload tree"):
        reconcile_restore.isolated_uploads(alias / "subdirectory")


def test_final_symlink_is_refused_even_for_separate_copy(tmp_path, upload_trees):
    _, _, separate = upload_trees
    alias = tmp_path / "restore-alias"
    alias.symlink_to(separate, target_is_directory=True)
    with pytest.raises(ValueError, match="must not be a symlink"):
        reconcile_restore.isolated_uploads(alias)


def test_configured_data_directory_is_also_protected(tmp_path, upload_trees, monkeypatch):
    configured = tmp_path / "configured" / "uploads"
    configured.mkdir(parents=True)
    monkeypatch.setenv("DATA_DIR", str(configured.parent))
    with pytest.raises(ValueError, match="live upload tree"):
        reconcile_restore.isolated_uploads(configured)


def test_missing_and_non_directory_uploads_are_refused(tmp_path, upload_trees):
    with pytest.raises(ValueError, match="Cannot resolve"):
        reconcile_restore.isolated_uploads(tmp_path / "missing")
    regular_file = tmp_path / "file"
    regular_file.write_text("not a directory")
    with pytest.raises(ValueError, match="existing directory"):
        reconcile_restore.isolated_uploads(regular_file)


def test_cli_rejects_live_child_before_database_or_file_changes(monkeypatch, upload_trees):
    _, child, _ = upload_trees
    photo = child / "important.jpg"
    photo.write_bytes(b"not a real image")
    monkeypatch.setenv("DATABASE_URL", "untouched")
    monkeypatch.setattr(sys, "argv", [
        "reconcile_restore.py", "--diagnostic-only", "--database-url", "sqlite:///unsafe_restore_test",
        "--ledger", "missing-ledger", "--master-key-file", "missing-key", "--uploads", str(child),
        "--retention-as-of", str(int(time.time())),
    ])
    with pytest.raises(SystemExit) as error:
        reconcile_restore.main()
    assert error.value.code == 2
    assert photo.read_bytes() == b"not a real image"
    assert reconcile_restore.os.environ["DATABASE_URL"] == "untouched"


@pytest.mark.parametrize("query", [
    "dbname=production", "database=production", "DbNaMe=production", "db%6eame=production",
    "dbname=safe_restore_test&dbname=production", "service=production", "servicefile=/tmp/service",
    "host=production", "host=/var/run/postgresql&host=production",
    "host=/tmp/other", "host=/var/run/postgresql&dbname=production",
    "options=-csearch_path%3Dpublic", "sslmode=require",
])
def test_restore_url_rejects_all_connection_parameters(query):
    with pytest.raises(ValueError, match="query parameters"):
        reconcile_restore.isolated_database(f"postgresql+psycopg://localhost/safe_restore_test?{query}")


def test_psycopg_query_really_overrides_checked_database_name():
    from sqlalchemy.dialects.postgresql.psycopg import PGDialect_psycopg
    from sqlalchemy.engine import make_url

    url = make_url("postgresql+psycopg://localhost/safe_restore_test?dbname=production")
    assert url.database == "safe_restore_test"
    assert PGDialect_psycopg().create_connect_args(url)[1]["dbname"] == "production"
    with pytest.raises(ValueError, match="query parameters"):
        reconcile_restore.isolated_database(str(url))


def test_cli_rejects_overridden_target_before_environment_or_files_change(monkeypatch, upload_trees):
    _, _, separate = upload_trees
    photo = separate / "synthetic.jpg"
    photo.write_bytes(b"synthetic")
    monkeypatch.setenv("DATABASE_URL", "untouched")
    monkeypatch.setattr(sys, "argv", [
        "reconcile_restore.py", "--diagnostic-only", "--database-url",
        "postgresql+psycopg://localhost/safe_restore_test?dbname=production",
        "--ledger", "missing-ledger", "--master-key-file", "missing-key", "--uploads", str(separate),
        "--retention-as-of", str(int(time.time())),
    ])
    with pytest.raises(SystemExit) as error:
        reconcile_restore.main()
    assert error.value.code == 2
    assert reconcile_restore.os.environ["DATABASE_URL"] == "untouched"
    assert photo.read_bytes() == b"synthetic"


def test_postgres_simple_restore_name_is_allowed_and_overlong_rejected():
    assert reconcile_restore.isolated_database("postgresql+psycopg://localhost/safe_restore_test") == (
        "postgresql", "safe_restore_test"
    )
    with pytest.raises(ValueError, match="PostgreSQL"):
        reconcile_restore.isolated_database("postgresql://localhost/" + "a" * 60 + "_restore_test")


def test_only_documented_local_postgresql_socket_query_is_allowed():
    from sqlalchemy.dialects.postgresql.psycopg import PGDialect_psycopg
    from sqlalchemy.engine import make_url

    raw = "postgresql+psycopg:///safe_restore_test?host=/var/run/postgresql"
    assert reconcile_restore.isolated_database(raw) == ("postgresql", "safe_restore_test")
    args = PGDialect_psycopg().create_connect_args(make_url(raw))[1]
    assert args["host"] == "/var/run/postgresql"
    assert args["dbname"] == "safe_restore_test"


def test_sqlite_rejects_symlink_and_hardlinked_database(tmp_path):
    target = tmp_path / "production_restore_test"
    target.write_bytes(b"synthetic")
    alias = tmp_path / "alias_restore_test"
    alias.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        reconcile_restore.isolated_database(f"sqlite:///{alias}")
    alias.unlink()
    alias.hardlink_to(target)
    with pytest.raises(ValueError, match="single-link"):
        reconcile_restore.isolated_database(f"sqlite:///{alias}")


def test_sqlite_existing_single_link_restore_file_is_allowed(tmp_path):
    database = tmp_path / "copy_restore_test"
    database.write_bytes(b"synthetic")
    assert reconcile_restore.isolated_database(f"sqlite:///{database}") == ("sqlite", str(database.resolve()))


def test_connected_postgres_name_is_checked_before_reconciliation():
    class Result:
        def scalar_one(self):
            return "production"

    class Session:
        def execute(self, _statement):
            return Result()

    with pytest.raises(ValueError, match="does not match"):
        reconcile_restore.verify_connected_database(Session(), "postgresql", "safe_restore_test")


def test_connected_sqlite_path_is_checked_against_copy(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    target = tmp_path / "actual_restore_test"
    engine = create_engine(f"sqlite:///{target}")
    with Session(engine) as session:
        reconcile_restore.verify_connected_database(session, "sqlite", str(target))
        with pytest.raises(ValueError, match="does not match"):
            reconcile_restore.verify_connected_database(session, "sqlite", str(tmp_path / "other_restore_test"))
    engine.dispose()


@pytest.mark.parametrize("journal_kind", ["missing", "empty", "older-authenticated"])
def test_default_cli_refuses_unproven_journal_before_touching_isolated_copy(tmp_path, journal_kind):
    """Even authentic individual records cannot establish a complete journal."""
    import hashlib
    import hmac
    import json
    import sqlite3
    import subprocess

    database = tmp_path / "sample_restore_test"
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE synthetic_objects (name text)")
        db.execute("INSERT INTO synthetic_objects VALUES ('synthetic-row')")
    uploads = tmp_path / "isolated_uploads"
    uploads.mkdir()
    photo = uploads / ("a" * 32 + ".jpg")
    photo.write_bytes(b"synthetic image")
    key = tmp_path / "key"
    key.write_text("synthetic-secret")
    ledger = tmp_path / "ledger"
    if journal_kind != "missing":
        ledger.write_text("")
    if journal_kind == "older-authenticated":
        record = {"id": "b" * 32, "scope": "family", "target": "c" * 32}
        payload = json.dumps(record, sort_keys=True, separators=(",", ":"))
        signature = hmac.new(b"synthetic-secret", payload.encode(), hashlib.sha256).hexdigest()
        ledger.write_text(json.dumps({"record": record, "signature": signature}) + "\n")
    original = database.read_bytes()
    command = [sys.executable, str(ROOT / "scripts/reconcile_restore.py"),
               "--database-url", "sqlite:///" + str(database), "--ledger", str(ledger),
               "--master-key-file", str(key), "--uploads", str(uploads),
               "--retention-as-of", str(int(time.time()))]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert "only --diagnostic-only" in result.stderr
    assert "synthetic-secret" not in result.stdout + result.stderr
    assert database.read_bytes() == original
    assert photo.read_bytes() == b"synthetic image"
