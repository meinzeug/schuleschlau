"""Synthetic automatic notebook job, interrupted by a source revision change."""

import pytest
from schulpilot import notebook_auto, worker
from schulpilot.db import DB, Job, Material, Message, Usage
from schulpilot.notebook_auto_models import NotebookAutoIntent
from sqlalchemy import func, select
from test_notebook_auto import prepare
from test_notebook_practice import process, stored_learning_evidence

pytest_plugins = ["test_notebook_practice"]


@pytest.mark.parametrize("when", ["before", "during"])
def test_revision_change_aborts_auto_round_without_retry_or_lost_answers(notebook, monkeypatch, when):
    intent_id, _ = prepare(notebook)
    notebook_auto.advance_one()
    with DB() as db:
        intent = db.get(NotebookAutoIntent, intent_id)
        assert intent.status == "queued"
        job_id, source_id = intent.job_id, intent.material_id
        assert db.get(Job, job_id).payload["material_revision"] == intent.revision
        jobs_before = db.scalar(select(func.count()).select_from(Job))
        usage_before = db.scalar(select(func.count()).select_from(Usage))
    evidence_before = stored_learning_evidence()
    def mutate_source():
        with DB.begin() as db:
            db.get(Material, source_id).revision += 1
    if when == "before":
        mutate_source()
    result, calls = process(notebook, monkeypatch, job_id, count=3,
                            callback=mutate_source if when == "during" else None)
    assert result["status"] == "failed", result
    assert len(calls) == (0 if when == "before" else 1)
    assert result["usage_status"] == ("failed_not_sent" if when == "before" else "failed_billed")
    assert result["cost"] == (0 if when == "before" else 200)
    assert stored_learning_evidence() == evidence_before
    for _ in range(3):
        notebook_auto.advance_one()
        worker.process(job_id)
    with DB() as db:
        assert db.get(NotebookAutoIntent, intent_id).status == "blocked"
        assert db.get(Job, job_id).status == "failed"
        assert db.scalar(select(func.count()).select_from(Job)) == jobs_before
        assert db.scalar(select(func.count()).select_from(Usage)) == usage_before
        assert db.scalar(select(func.count()).select_from(Message).where(Message.kind == "round_ready")) == 0
    assert len(calls) == (0 if when == "before" else 1)
    assert stored_learning_evidence() == evidence_before
