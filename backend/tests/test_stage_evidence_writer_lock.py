"""Actual evidence endpoints serialize against automatic-stage publication."""
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from schulpilot import learning, learning_evidence_marker, school_preparation, worker
from schulpilot.db import DB, Activity, Attempt, Job, LearningUnit, engine
from schulpilot.main import app
from sqlalchemy import event, select, text
from test_automatic_evidence_guard import add_attempt, make_practice
from test_study_path import arm_automatic_rounds

pytest_plugins = ["test_study_path"]
pytestmark = pytest.mark.skipif(engine.dialect.name != "postgresql", reason="PostgreSQL row lock ordering")


def start(study):
    with DB.begin() as db:
        unit_id = make_practice(db, study["child"]["id"])
        unit = db.get(LearningUnit, unit_id)
        unit.status = "active"
        unit.questions = [{**unit.questions[0], "hints": ["Lies den ersten Satz."]}]
        add_attempt(db, unit_id)
    arm_automatic_rounds(study)
    assert school_preparation.advance_auto_rounds(study["day_id"])
    with DB() as db:
        job_id = worker.claim(db)
    assert job_id
    return unit_id, job_id


def call(study, unit_id, kind):
    with TestClient(app, headers=dict(study["client"].headers)) as client:
        path = f"/api/units/{unit_id}"
        if kind == "answer":
            return client.post(path + "/questions/evidence/answer", json={"answer": "nein"})
        if kind == "hint":
            return client.post(path + "/questions/evidence/hint")
        return client.post(path + "/explanation", json={"question_id": "evidence"})


def wait_for_db_lock(pid):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        with DB() as db:
            result = db.execute(text("select wait_event_type, cardinality(pg_blocking_pids(:pid)) "
                                     "from pg_stat_activity where pid=:pid"), {"pid": pid}).first()
        if result and result[0] == "Lock" and result[1] > 0:
            return
        threading.Event().wait(.02)
    pytest.fail("The concurrent transaction did not wait on a PostgreSQL lock")


@pytest.mark.parametrize("kind", ["answer", "hint", "explanation"])
def test_publication_first_keeps_writer_waiting_and_later_start_warns(study, stage_transport, monkeypatch, kind):
    unit_id, job_id = start(study)
    reached, release, writer_update = threading.Event(), threading.Event(), threading.Event()
    actual_snapshot = learning_evidence_marker.snapshot
    writer_pid = []

    def observe(db, *args, **kwargs):
        marker = actual_snapshot(db, *args, **kwargs)
        if threading.current_thread().name.startswith("stage-publish") and stage_transport["calls"]:
            reached.set()
            assert release.wait(15)
        return marker

    def sql_gate(_conn, cursor, statement, _parameters, _context, _executemany):
        if reached.is_set() and statement.lstrip().lower().startswith("update children"):
            writer_pid.append(cursor.connection.info.backend_pid)
            writer_update.set()

    monkeypatch.setattr(learning_evidence_marker, "snapshot", observe)
    event.listen(engine, "before_cursor_execute", sql_gate)
    try:
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="stage-publish") as pool, \
             ThreadPoolExecutor(max_workers=1, thread_name_prefix="evidence-writer") as writers:
            stage = pool.submit(worker.process, job_id)
            assert reached.wait(15)
            result = writers.submit(call, study, unit_id, kind)
            try:
                assert writer_update.wait(15)
                wait_for_db_lock(writer_pid[0])
            finally:
                release.set()
            stage.result(timeout=15)
            response = result.result(timeout=15)
    finally:
        release.set()
        event.remove(engine, "before_cursor_execute", sql_gate)
    assert response.status_code == 200, response.text
    with DB() as db:
        job = db.get(Job, job_id)
        assert job.status == "completed", job.error
        prepared = job.result["unit_id"]
    detail = study["client"].get(f"/api/units/{prepared}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["practice_evidence_may_have_changed"] is True
    assert len(stage_transport["calls"]) == 1


@pytest.mark.parametrize("kind", ["answer", "hint", "explanation"])
def test_writer_first_changes_marker_before_publication(study, stage_transport, monkeypatch, kind):
    unit_id, job_id = start(study)
    reached, release, publisher_update = threading.Event(), threading.Event(), threading.Event()
    actual_record = learning.record
    stage_pid = []
    def record(db, child_id, event_kind, detail=None, unit_id=None):
        actual_record(db, child_id, event_kind, detail, unit_id)
        if event_kind == kind:
            reached.set()
            assert release.wait(15)
    def sql_gate(_conn, cursor, statement, _parameters, _context, _executemany):
        if (threading.current_thread().name.startswith("stage-publish") and stage_transport["calls"]
                and statement.lstrip().lower().startswith("update children")):
            stage_pid.append(cursor.connection.info.backend_pid)
            publisher_update.set()
    monkeypatch.setattr(learning, "record", record)
    event.listen(engine, "before_cursor_execute", sql_gate)
    try:
        # Start generation first and pause its provider so its initial marker
        # predates the evidence write; release it after the writer holds Child.
        in_provider, provider_release = threading.Event(), threading.Event()
        def provider_hold():
            in_provider.set()
            assert provider_release.wait(15)
        stage_transport["effect"] = provider_hold
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="stage-publish") as pool, \
             ThreadPoolExecutor(max_workers=1, thread_name_prefix="evidence-writer") as writers:
            stage = pool.submit(worker.process, job_id)
            assert in_provider.wait(15)
            result = writers.submit(call, study, unit_id, kind)
            try:
                assert reached.wait(15)
                provider_release.set()
                assert publisher_update.wait(15)
                wait_for_db_lock(stage_pid[0])
            finally:
                provider_release.set()
                release.set()
            response = result.result(timeout=15)
            stage.result(timeout=15)
    finally:
        release.set()
        provider_release.set()
        event.remove(engine, "before_cursor_execute", sql_gate)
    assert response.status_code == 200, response.text
    with DB() as db:
        job = db.get(Job, job_id)
        assert job.status == "failed" and "Lernstand" in job.error
        assert db.scalar(select(LearningUnit.id).where(LearningUnit.id == unit_id))
        if kind == "answer":
            assert len(list(db.scalars(select(Attempt).where(Attempt.unit_id == unit_id)))) == 2
        else:
            assert db.scalar(select(Activity.id).where(Activity.unit_id == unit_id, Activity.kind == kind))
    assert len(stage_transport["calls"]) == 1


@pytest.mark.parametrize("kind", ["answer", "hint", "explanation"])
def test_waiting_evidence_action_rechecks_revoked_session(study, kind):
    from schulpilot.db import Child, Session, User
    from sqlalchemy import update

    unit_id, _job_id = start(study)
    waiting, writer_pid = threading.Event(), []
    def sql_gate(_conn, cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().lower().startswith("update children"):
            writer_pid.append(cursor.connection.info.backend_pid)
            waiting.set()
    with DB() as holder:
        holder.execute(update(Child).where(Child.id == study["child"]["id"]).values(grade=Child.grade))
        event.listen(engine, "before_cursor_execute", sql_gate)
        try:
            with ThreadPoolExecutor(max_workers=1) as writers:
                result = writers.submit(call, study, unit_id, kind)
                try:
                    assert waiting.wait(15)
                    wait_for_db_lock(writer_pid[0])
                    with DB.begin() as db:
                        user = db.scalar(select(User).where(User.username == "test-child"))
                        db.execute(update(Session).where(Session.user_id == user.id).values(revoked=True))
                finally:
                    holder.rollback()
                response = result.result(timeout=15)
        finally:
            event.remove(engine, "before_cursor_execute", sql_gate)
            holder.rollback()
    assert response.status_code == 401, response.text
    with DB() as db:
        assert len(list(db.scalars(select(Attempt).where(Attempt.unit_id == unit_id)))) == 1
        assert not list(db.scalars(select(Activity).where(Activity.unit_id == unit_id,
            Activity.kind.in_(("answer", "hint", "explanation")))))


@pytest.mark.parametrize("kind", ["answer", "hint"])
@pytest.mark.parametrize("access", ["valid", "revoked", "expired"])
def test_replay_rechecks_session_after_waiting_for_unit(study, kind, access):
    from schulpilot.db import Family, Session, User, now
    from sqlalchemy import update

    unit_id, _job_id = start(study)
    path = f"/api/units/{unit_id}/questions/evidence/{kind}"
    headers = {"Idempotency-Key": "synthetic-replay-key-123"}
    payload = {"answer": "nein", "request_id": "synthetic-replay-key-123"} if kind == "answer" else None
    first = study["client"].post(path, json=payload, headers=headers)
    assert first.status_code == 200, first.text
    waiting, writer_pid = threading.Event(), []
    def sql_gate(_conn, cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().lower().startswith("update learning_units"):
            writer_pid.append(cursor.connection.info.backend_pid)
            waiting.set()
    with DB() as holder:
        holder.execute(update(LearningUnit).where(LearningUnit.id == unit_id).values(status=LearningUnit.status))
        event.listen(engine, "before_cursor_execute", sql_gate)
        try:
            with ThreadPoolExecutor(max_workers=1) as writers:
                def replay():
                    with TestClient(app, headers=dict(study["client"].headers)) as client:
                        return client.post(path, json=payload, headers=headers)
                task = writers.submit(replay)
                try:
                    assert waiting.wait(15)
                    wait_for_db_lock(writer_pid[0])
                    if access != "valid":
                        with DB.begin() as db:
                            if access == "revoked":
                                user = db.scalar(select(User).where(User.username == "test-child"))
                                db.execute(update(Session).where(Session.user_id == user.id).values(revoked=True))
                            else:
                                family = db.get(Family, study["parent"]["families"][0]["id"])
                                family.expires = int(now()) - 1
                finally:
                    holder.rollback()
                response = task.result(timeout=15)
        finally:
            event.remove(engine, "before_cursor_execute", sql_gate)
            holder.rollback()
    if access == "valid":
        assert response.status_code == 200, response.text
        assert response.json() == first.json()
    else:
        assert response.status_code == (401 if access == "revoked" else 410), response.text
    with DB() as db:
        if kind == "answer":
            assert len(list(db.scalars(select(Attempt).where(Attempt.unit_id == unit_id)))) == 2
        else:
            assert len(list(db.scalars(select(Activity).where(Activity.unit_id == unit_id,
                                                               Activity.kind == "hint")))) == 1


def test_waiting_answer_rechecks_expired_family(study):
    from schulpilot.db import Child, Family, now
    from sqlalchemy import update

    unit_id, _job_id = start(study)
    waiting, writer_pid = threading.Event(), []
    def sql_gate(_conn, cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().lower().startswith("update children"):
            writer_pid.append(cursor.connection.info.backend_pid)
            waiting.set()
    with DB() as holder:
        holder.execute(update(Child).where(Child.id == study["child"]["id"]).values(grade=Child.grade))
        event.listen(engine, "before_cursor_execute", sql_gate)
        try:
            with ThreadPoolExecutor(max_workers=1) as writers:
                task = writers.submit(call, study, unit_id, "answer")
                try:
                    assert waiting.wait(15)
                    wait_for_db_lock(writer_pid[0])
                    with DB.begin() as db:
                        family = db.get(Family, study["parent"]["families"][0]["id"])
                        family.expires = int(now()) - 1
                finally:
                    holder.rollback()
                response = task.result(timeout=15)
        finally:
            event.remove(engine, "before_cursor_execute", sql_gate)
            holder.rollback()
    assert response.status_code == 410, response.text
    with DB() as db:
        assert len(list(db.scalars(select(Attempt).where(Attempt.unit_id == unit_id)))) == 1


def test_waiting_answer_rechecks_child_role(study):
    from schulpilot.db import Child, User
    from sqlalchemy import update

    unit_id, _job_id = start(study)
    waiting, writer_pid = threading.Event(), []
    def sql_gate(_conn, cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().lower().startswith("update children"):
            writer_pid.append(cursor.connection.info.backend_pid)
            waiting.set()
    with DB() as holder:
        holder.execute(update(Child).where(Child.id == study["child"]["id"]).values(grade=Child.grade))
        event.listen(engine, "before_cursor_execute", sql_gate)
        try:
            with ThreadPoolExecutor(max_workers=1) as writers:
                task = writers.submit(call, study, unit_id, "answer")
                try:
                    assert waiting.wait(15)
                    wait_for_db_lock(writer_pid[0])
                    with DB.begin() as db:
                        user = db.scalar(select(User).where(User.username == "test-child"))
                        user.role = "parent"
                finally:
                    holder.rollback()
                response = task.result(timeout=15)
        finally:
            event.remove(engine, "before_cursor_execute", sql_gate)
            holder.rollback()
    assert response.status_code == 403, response.text
    with DB() as db:
        assert len(list(db.scalars(select(Attempt).where(Attempt.unit_id == unit_id)))) == 1


def test_busy_session_never_deadlocks_evidence_write(study):
    from schulpilot.db import Session, User

    unit_id, _job_id = start(study)
    with DB() as holder:
        user = holder.scalar(select(User).where(User.username == "test-child"))
        holder.scalar(select(Session).where(Session.user_id == user.id, Session.revoked.is_(False)).with_for_update())
        with ThreadPoolExecutor(max_workers=1) as writers:
            task = writers.submit(call, study, unit_id, "answer")
            try:
                response = task.result(timeout=8)
            finally:
                holder.rollback()
    assert response.status_code == 409, response.text
    with DB() as db:
        assert len(list(db.scalars(select(Attempt).where(Attempt.unit_id == unit_id)))) == 1
