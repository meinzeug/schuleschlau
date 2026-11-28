"""Synthetic automatic notebook jobs after revoking their submitting authority."""

import pytest
from schulpilot import notebook_auto, notifications, study_path, worker
from schulpilot.db import DB, Job, Material, Membership, Message, Session, Usage
from schulpilot.notebook_auto_models import NotebookAutoIntent
from sqlalchemy import func, select
from test_notebook_auto import prepare
from test_notebook_practice import process, stored_learning_evidence

pytest_plugins = ["test_notebook_practice"]


@pytest.mark.parametrize("authority", ["child_session", "parent_membership"])
@pytest.mark.parametrize("when", ["before", "during"])
def test_revoked_authority_stops_automatic_notebook_round_without_retry(notebook, monkeypatch, authority, when):
    # The transport below is a local scripted response; never send FCM or call
    # another provider route while exercising the regular reservation path.
    def forbidden(*_args, **_kwargs):
        pytest.fail("Unexpected provider or FCM call")
    monkeypatch.setattr(study_path, "request_provider", forbidden)
    monkeypatch.setattr(notifications, "send_fcm", forbidden)
    intent_id, child_session_id = prepare(notebook)
    if authority == "parent_membership":
        with DB.begin() as db:
            intent = db.get(NotebookAutoIntent, intent_id)
            session = db.scalar(select(Session).where(Session.user_id == notebook.parent["id"]))
            intent.user_id, intent.session_id = notebook.parent["id"], session.id
    notebook_auto.advance_one()
    with DB() as db:
        intent = db.get(NotebookAutoIntent, intent_id)
        assert intent.status == "queued"
        job_id, material_id = intent.job_id, intent.material_id
        page = db.get(Material, material_id)
        source_before = (page.revision, page.confirmed, page.subject, page.topic, page.content)
        counts_before = tuple(db.scalar(select(func.count()).select_from(model)) for model in (Job, Usage))
    saved_before = stored_learning_evidence()

    def revoke():
        with DB.begin() as db:
            if authority == "child_session":
                db.get(Session, child_session_id).revoked = True
            else:
                membership = db.scalar(select(Membership).where(
                    Membership.user_id == notebook.parent["id"],
                    Membership.family_id == notebook.parent["families"][0]["id"]))
                assert membership is not None
                db.delete(membership)
    if when == "before":
        revoke()
    result, calls = process(notebook, monkeypatch, job_id, 3, callback=revoke if when == "during" else None)
    assert result["status"] == "failed", result
    assert len(calls) == (0 if when == "before" else 1)
    assert result["usage_status"] == ("failed_not_sent" if when == "before" else "failed_billed")
    assert result["cost"] == (0 if when == "before" else 200)
    assert stored_learning_evidence() == saved_before
    for _ in range(3):
        notebook_auto.advance_one()
        worker.process(job_id)
    with DB() as db:
        page = db.get(Material, material_id)
        assert (page.revision, page.confirmed, page.subject, page.topic, page.content) == source_before
        assert db.get(NotebookAutoIntent, intent_id).status == "blocked"
        assert db.get(Job, job_id).status == "failed"
        assert tuple(db.scalar(select(func.count()).select_from(model)) for model in (Job, Usage)) == counts_before
        assert db.scalar(select(func.count()).select_from(Message).where(Message.kind == "round_ready")) == 0
    assert len(calls) == (0 if when == "before" else 1)
    assert stored_learning_evidence() == saved_before
