"""Synthetic multi-session integration using real authorization and worker paths."""

from conftest import create_child
from schulpilot import language_projects
from schulpilot.db import DB, Activity, Attempt, Job, LearningUnit, Usage
from schulpilot.providers import Result
from sqlalchemy import func, select
from test_language_jobs import notebook as notebook
from test_language_jobs import project_request, proposal, run_job
from test_vocabulary import child_login, import_words


def counts():
    with DB() as db:
        return tuple(db.scalar(select(func.count()).select_from(model))
                     for model in (Job, Usage, LearningUnit, Attempt, Activity))


def test_two_child_sessions_see_same_saved_job_and_other_child_is_denied(api, notebook, monkeypatch):
    parent, child, material_id = notebook
    import_words(api, child)
    create_child(api, parent, username='other-child')
    child_login(api)
    first_auth = api.headers['Authorization']
    response, _, item_id = project_request(api, child, material_id, mode='exam')
    assert response.status_code == 202, response.text
    row = response.json()
    api.headers.pop('Authorization')
    api.cookies.clear()
    child_login(api)
    second_auth = api.headers['Authorization']
    assert first_auth != second_auth
    api.headers.pop('Authorization')
    api.cookies.clear()
    child_login(api, username='other-child')
    stranger_auth = api.headers['Authorization']
    route = f"/api/children/{child['id']}/language-projects/{row['id']}"
    before_reads = counts()
    for token in (first_auth, second_auth, first_auth):
        response = api.get(route, headers={'Authorization': token})
        assert response.status_code == 200, response.text
        assert response.json()['status'] == 'queued'
    assert api.get(route, headers={'Authorization': stranger_auth}).status_code in (403, 404)
    assert counts() == before_reads
    calls = []

    def artificial_provider(*_args):
        calls.append('language_project')
        return Result(proposal(item_id), 10, 10, 1)

    monkeypatch.setattr(language_projects, 'request_provider', artificial_provider)
    run_job(row['job_id'])
    after_worker = counts()
    for token in (second_auth, first_auth, second_auth):
        response = api.get(route, headers={'Authorization': token})
        assert response.status_code == 200, response.text
        assert response.json()['status'] == 'ready'
        assert response.json()['unit_id']
    assert api.get(route, headers={'Authorization': stranger_auth}).status_code in (403, 404)
    assert counts() == after_worker
    assert calls == ['language_project']
    assert after_worker[0] == before_reads[0]
    assert after_worker[1] == before_reads[1]
    assert after_worker[2] == before_reads[2] + 1
    assert after_worker[3:] == before_reads[3:]
