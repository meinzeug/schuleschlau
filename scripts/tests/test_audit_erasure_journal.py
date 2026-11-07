import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

MODULE = Path(__file__).resolve().parents[1] / "audit_erasure_journal.py"
spec = importlib.util.spec_from_file_location("audit_erasure_journal", MODULE)
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)

from schulpilot.db import ErasureRequest  # noqa: E402
from schulpilot.erasure import signed  # noqa: E402


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
    monkeypatch.setattr(audit_module, "engine", engine)
    (tmp_path / ".erasure-ledger.lock").touch()
    ledger = tmp_path / "erasure-ledger.jsonl"
    ledger.write_text(signed(record(item), "synthetic-key") + "\n")
    result = audit_module.audit(ledger, "synthetic-key", now=101)
    assert result["outbox_recent_matched"] == 1
    ledger.write_text(ledger.read_text().replace('"material"', '"unit"'))
    with pytest.raises(ValueError, match="authentication failed"):
        audit_module.audit(ledger, "synthetic-key", now=101)
    with engine.connect() as con:
        assert con.exec_driver_sql("SELECT count(*) FROM erasure_requests").scalar_one() == 1


def test_missing_lock_or_key_fails_closed(tmp_path):
    with pytest.raises(RuntimeError):
        audit_module.audit(tmp_path / "ledger", "", now=1)
    with pytest.raises(FileNotFoundError):
        audit_module.audit(tmp_path / "ledger", "synthetic-key", now=1)


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
        monkeypatch.setattr(audit_module, "engine", engine)
        (tmp_path / ".erasure-ledger.lock").touch()
        ledger = tmp_path / "erasure-ledger.jsonl"
        ledger.write_text(signed(record(item), "synthetic-key") + "\n")
        assert audit_module.audit(ledger, "synthetic-key", now=101)["outbox_recent_matched"] == 1
    finally:
        ErasureRequest.__table__.drop(engine)
        engine.dispose()
