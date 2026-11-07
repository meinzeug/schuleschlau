import builtins
import fcntl
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url

MODULE = Path(__file__).resolve().parents[1] / "audit_erasure_journal.py"
spec = importlib.util.spec_from_file_location("audit_erasure_journal", MODULE)
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)

from schulpilot.db import ErasureRequest  # noqa: E402
from schulpilot.erasure import VOCABULARY_SCOPES, signed, verify  # noqa: E402

SCOPES = ("assignment", "grade", "grade_import", "grade_slot", *VOCABULARY_SCOPES)


def run_audit(path, key, engine, *, sqlite=False):
    return audit_module.audit(path, key, engine=engine, model=ErasureRequest, verify_record=verify,
                              extended_scopes=SCOPES, allow_test_sqlite=sqlite)


def row(scope="material", published=True, created=100, **kwargs):
    return SimpleNamespace(id="a" * 32, scope=scope, target="b" * 32, created=created,
                           published=published, details=kwargs.get("details"))


def record(item):
    return {"id": item.id, "scope": item.scope, "target": item.target, "created": item.created}


def test_clean_comparison_never_authorizes_restore():
    item = row()
    result = audit_module.compare([record(item)], [item], 50)
    assert result["outbox_recent_matched"] == 1
    assert result["outbox_recent_missing"] == result["outbox_recent_mismatched"] == 0
    assert result["writer_fence_verified"] is result["historical_completeness_verified"] is False
    assert result["restore_activation_authorized"] is False


def test_missing_mismatch_pending_and_retention_are_distinct():
    a = row()
    bad = {**record(a), "target": "c" * 32}
    result = audit_module.compare([bad], [a, row(published=False), row(created=10)], 50)
    assert (result["outbox_recent_missing"], result["outbox_recent_mismatched"], result["outbox_unpublished"]) == (0, 1, 1)
    result = audit_module.compare([], [a], 50)
    assert result["outbox_recent_missing"] == 1


def test_extended_scopes_and_grade_details_are_compared():
    grade = row("grade", details={"synthetic": "value"})
    grade_record = {**record(grade), "scope": "unit", "resource_kind": "grade", "details": grade.details}
    assert audit_module.compare([grade_record], [grade], 0)["outbox_recent_matched"] == 1
    grade_record["details"] = {"synthetic": "changed"}
    assert audit_module.compare([grade_record], [grade], 0)["outbox_recent_mismatched"] == 1
    vocab = row("vocab_set")
    vocab_record = {**record(vocab), "scope": "unit", "resource_kind": "vocab_set"}
    assert audit_module.compare([vocab_record], [vocab], 0)["outbox_recent_matched"] == 1


def test_duplicate_conflict_is_not_hidden_by_last_copy():
    item = row()
    good = record(item)
    result = audit_module.compare([good, {**good, "target": "c" * 32}, good], [item], 0)
    assert result["outbox_recent_matched"] == 1
    assert result["journal_duplicate_ids"] == result["journal_conflicting_duplicate_ids"] == 2


def test_recent_signed_record_missing_from_outbox_is_reported():
    item = row()
    result = audit_module.compare([record(item)], [], 50)
    assert result["journal_recent_missing_outbox"] == 1
    assert audit_module.compare([record(item)], [], 150)["journal_recent_missing_outbox"] == 0


def test_real_sqlite_read_and_signature_verification(tmp_path, monkeypatch):
    engine = create_engine("sqlite://")
    ErasureRequest.__table__.create(engine)
    item = row()
    with engine.begin() as con:
        con.execute(ErasureRequest.__table__.insert().values(id=item.id, scope=item.scope, target=item.target,
                                                             created=item.created, published=True))
    monkeypatch.setattr(audit_module.time, "time", lambda: 101)
    (tmp_path / ".erasure-ledger.lock").touch()
    ledger = tmp_path / "erasure-ledger.jsonl"
    ledger.write_text(signed(record(item), "synthetic-key") + "\n")
    result = run_audit(ledger, "synthetic-key", engine, sqlite=True)
    assert result["outbox_recent_matched"] == 1
    ledger.write_text(ledger.read_text().replace('"material"', '"unit"'))
    with pytest.raises(ValueError, match="authentication failed"):
        run_audit(ledger, "synthetic-key", engine, sqlite=True)
    with engine.connect() as con:
        assert con.exec_driver_sql("SELECT count(*) FROM erasure_requests").scalar_one() == 1


def test_missing_lock_or_key_fails_closed(tmp_path):
    engine = create_engine("sqlite://")
    with pytest.raises(RuntimeError):
        run_audit(tmp_path / "ledger", "", engine, sqlite=True)
    with pytest.raises(FileNotFoundError):
        run_audit(tmp_path / "ledger", "synthetic-key", engine, sqlite=True)


def test_missing_sqlite_database_is_never_created(tmp_path):
    path = tmp_path / "must-not-appear.sqlite"
    engine = create_engine(f"sqlite:///{path}")
    with pytest.raises(ValueError, match="PostgreSQL"):
        run_audit(tmp_path / "ledger", "synthetic-key", engine, sqlite=True)
    assert not path.exists()


def test_lock_timeout_does_not_leave_a_lock_held(tmp_path, monkeypatch):
    engine = create_engine("sqlite://")
    lock_path = tmp_path / ".erasure-ledger.lock"
    lock_path.touch()
    monkeypatch.setattr(audit_module, "LOCK_TIMEOUT_SECONDS", 0.1)
    with lock_path.open("rb") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        with pytest.raises(TimeoutError):
            run_audit(tmp_path / "ledger", "synthetic-key", engine, sqlite=True)
    with lock_path.open("rb") as check:
        fcntl.flock(check, fcntl.LOCK_EX | fcntl.LOCK_NB)


def test_connection_precedes_journal_lock_and_clock_is_read_under_lock(tmp_path, monkeypatch):
    engine = create_engine("sqlite://")
    ErasureRequest.__table__.create(engine)
    engine.dispose()  # the next in-memory connection is genuinely new
    order = []

    @event.listens_for(engine, "connect")
    def connected(_dbapi, _record):
        order.append("connect")

    # Prepare the table on the new connection; only test ordering from here.
    ErasureRequest.__table__.create(engine)
    order.clear()
    original = audit_module.bounded_journal

    def tracking(path):
        order.append("lock")
        return original(path)

    def clock():
        with (tmp_path / ".erasure-ledger.lock").open("rb") as probe:
            with pytest.raises(BlockingIOError):
                fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        order.append("clock")
        return 101

    monkeypatch.setattr(audit_module, "bounded_journal", tracking)
    monkeypatch.setattr(audit_module.time, "time", clock)
    (tmp_path / ".erasure-ledger.lock").touch()
    (tmp_path / "ledger").write_text("")
    # Existing in-memory connection is reused; connect() itself must occur
    # before bounded_journal and cutoff is obtained only while lock is held.
    original_connect = engine.connect

    def connect():
        order.append("acquire-db")
        return original_connect()

    monkeypatch.setattr(engine, "connect", connect)
    run_audit(tmp_path / "ledger", "synthetic-key", engine, sqlite=True)
    assert order == ["acquire-db", "lock", "clock"]


def test_import_failure_is_redacted(monkeypatch, capsys):
    original = builtins.__import__

    def failing(name, *args, **kwargs):
        if name == "schulpilot.config":
            raise RuntimeError("synthetic-secret-must-not-appear")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", failing)
    assert audit_module.main() == 1
    captured = capsys.readouterr()
    assert "synthetic-secret" not in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_hard_process_deadline_releases_lock(tmp_path):
    lock_path = tmp_path / ".erasure-ledger.lock"
    lock_path.touch()
    code = ("import importlib.util,fcntl,signal,sys,time; "
            "s=importlib.util.spec_from_file_location('audit',sys.argv[1]); "
            "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
            "f=open(sys.argv[2],'rb'); fcntl.flock(f,fcntl.LOCK_SH); "
            "signal.signal(signal.SIGALRM,m._deadline_expired); signal.alarm(1); time.sleep(30)")
    result = subprocess.run([sys.executable, "-c", code, str(MODULE), str(lock_path)],
                            capture_output=True, timeout=5, check=False)
    assert result.returncode == 2
    assert result.stdout == result.stderr == b""
    with lock_path.open("rb") as check:
        fcntl.flock(check, fcntl.LOCK_EX | fcntl.LOCK_NB)


def test_real_postgres_read_only_comparison(tmp_path, monkeypatch):
    url_string = os.getenv("TEST_DATABASE_URL")
    if not url_string:
        pytest.skip("Requires the isolated PostgreSQL test runner")
    url = make_url(url_string)
    socket = Path(url.query.get("host", ""))
    if (url.database != "schulpilot_isolated_test" or not socket.is_relative_to("/dev/shm")
            or not socket.parent.name.startswith("schulpilot-isolated-pg-")):
        pytest.fail("Refusing a non-isolated PostgreSQL endpoint")
    engine = create_engine(url)
    ErasureRequest.__table__.create(engine)
    try:
        item = row()
        with engine.begin() as con:
            con.execute(ErasureRequest.__table__.insert().values(id=item.id, scope=item.scope, target=item.target,
                                                                 created=item.created, published=True))
        monkeypatch.setattr(audit_module.time, "time", lambda: 101)
        (tmp_path / ".erasure-ledger.lock").touch()
        ledger = tmp_path / "erasure-ledger.jsonl"
        ledger.write_text(signed(record(item), "synthetic-key") + "\n")
        observed = []

        def capture_read_only(_conn, cursor, statement, _params, _context, _many):
            if "FROM erasure_requests" in statement:
                cursor.execute("SHOW transaction_read_only")
                observed.append(cursor.fetchone()[0])

        event.listen(Engine, "before_cursor_execute", capture_read_only)
        try:
            assert run_audit(ledger, "synthetic-key", engine)["outbox_recent_matched"] == 1
        finally:
            event.remove(Engine, "before_cursor_execute", capture_read_only)
        assert observed == ["on"]
        # Hold a real conflicting table lock. The audit's bounded SQL must
        # fail and release its journal lock even while the blocker remains.
        monkeypatch.setattr(audit_module, "STATEMENT_TIMEOUT_MS", 200)
        with engine.connect() as blocker, blocker.begin():
            blocker.exec_driver_sql("LOCK TABLE erasure_requests IN ACCESS EXCLUSIVE MODE")
            with pytest.raises(Exception):
                run_audit(ledger, "synthetic-key", engine)
            with (tmp_path / ".erasure-ledger.lock").open("rb") as check:
                fcntl.flock(check, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        ErasureRequest.__table__.drop(engine)
        engine.dispose()
