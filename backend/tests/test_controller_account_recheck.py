"""Artificial support-check jobs must recheck their child account before and after inference."""

import pytest
from schulpilot import controller_jobs
from schulpilot.db import DB, Child, Job, LearningUnit, Usage, User
from schulpilot.providers import Result
from schulpilot.synthetic import sample_unit
from sqlalchemy import func, select
from test_coaching import process_next
from test_controller_media import ask_check, returned
from test_controller_media import media_unit as controller_media_unit  # noqa: F401


@pytest.mark.parametrize("account_change", ["disabled", "unverified"])
@pytest.mark.parametrize("change_at", ["before", "during"])
def test_support_check_rechecks_child_account(request, monkeypatch, account_change, change_at):
    client, unit_id, _, _, child = request.getfixturevalue("controller_media_unit")
    returned(client, unit_id, child["id"])
    job_id = ask_check(client, unit_id)
    calls = []

    def change_account():
        with DB.begin() as db:
            user = db.get(User, db.get(Child, child["id"]).user_id)
            if account_change == "disabled":
                user.disabled = True
            else:
                user.verified = False

    def generate(config, function, payload):
        calls.append(function)
        if change_at == "during":
            change_account()
        data = sample_unit()
        data["topic"] = "Brüche addieren"
        data["questions"] = [
            dict(data["questions"][2], id="new1", learning_goal_id=payload["focus_goal_ids"][0]),
            dict(data["questions"][3], id="new2", learning_goal_id=payload["focus_goal_ids"][-1]),
        ]
        data["questions"][0].update(type="short", options=[], accepted=[],
            prompt="Wie heißt die Zahl unter dem Bruchstrich bei 2/7?", answer="Nenner")
        data["questions"][1].update(type="short", options=[], accepted=[],
            prompt="Berechne 1/6 + 2/6.", answer="3/6")
        return Result(data, 100, 200, 1)

    monkeypatch.setattr(controller_jobs, "request_provider", generate)
    if change_at == "before":
        change_account()
    process_next()
    with DB() as db:
        job = db.get(Job, job_id)
        usage = db.scalar(select(Usage).where(Usage.job_id == job_id))
        assert job.status == "failed"
        assert "Anmeldung" in job.error
        assert usage.status == ("failed_not_sent" if change_at == "before" else "failed_billed")
        assert usage.cost_micros == (0 if change_at == "before" else 1)
        assert db.scalar(select(func.count()).select_from(LearningUnit)) == 1
    assert calls == ([] if change_at == "before" else ["unit"])
