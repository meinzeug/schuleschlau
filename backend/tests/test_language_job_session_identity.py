"""Synthetic jobs must bind the actor to their actual session on both sides of inference."""

import pytest
from schulpilot import language_projects, vocabulary
from schulpilot.db import DB, Child, Job, LanguageProject, LearningUnit, Usage, VocabularyImport, VocabularyItem
from schulpilot.providers import Result
from sqlalchemy import select
from test_language_jobs import notebook as language_notebook  # noqa: F401
from test_language_jobs import project_request, proposal, run_job
from test_vocabulary import child_login, import_words


@pytest.mark.parametrize("kind", ["import", "project"])
@pytest.mark.parametrize("change_at", ["before", "during"])
def test_language_jobs_reject_session_belonging_to_other_family_member(api, request, monkeypatch, kind, change_at):
    parent, child, material_id = request.getfixturevalue("language_notebook")
    if kind == "import":
        response = api.post(
            f"/api/children/{child['id']}/vocabulary/imports",
            json={"target_locale": "en-GB", "title": "Meine Wörter", "language_confirmed": True,
                  "material_id": material_id},
            headers={"Idempotency-Key": "import-user-session-mismatch"},
        )
        assert response.status_code == 201, response.text
        model, module = VocabularyImport, vocabulary
        with DB() as db:
            alternate_id = db.get(Child, child["id"]).user_id
        output = {"pairs": [{"word": "apple", "meaning": "Apfel"}]}
    else:
        import_words(api, child)
        child_login(api)
        response, _, item_id = project_request(api, child, material_id)
        assert response.status_code == 202, response.text
        model, module, alternate_id = LanguageProject, language_projects, parent["id"]
        output = proposal(item_id)

    row_id, job_id = response.json()["id"], response.json()["job_id"]
    calls = []

    def mismatch():
        with DB.begin() as db:
            row = db.get(model, row_id)
            assert row.user_id != alternate_id
            row.user_id = alternate_id

    def transport(*args):
        calls.append(True)
        if change_at == "during":
            mismatch()
        return Result(output, 10, 10, 1)

    monkeypatch.setattr(module, "request_provider", transport)
    if change_at == "before":
        mismatch()
    run_job(job_id)
    with DB() as db:
        row, job = db.get(model, row_id), db.get(Job, job_id)
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        assert row.status == job.status == "failed"
        assert usage.status == ("failed_not_sent" if change_at == "before" else "failed_billed")
        assert usage.cost_micros == (0 if change_at == "before" else 1)
        if kind == "import":
            assert not row.pairs
            assert not list(db.scalars(select(VocabularyItem)))
        else:
            assert row.unit_id is None
            assert not list(db.scalars(select(LearningUnit)))
    assert len(calls) == (0 if change_at == "before" else 1)
