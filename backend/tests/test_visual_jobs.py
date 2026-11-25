"""Explicit sidecars over artificial begun rounds, with zero real provider calls."""
import copy
from uuid import uuid4

import pytest
from schulpilot.db import DB, Activity, Attempt, Job, LearningUnit, Material, Session
from schulpilot.providers import Result
from schulpilot.visual_jobs import context, process
from schulpilot.visual_reference_models import UnitVisualSnapshot
from schulpilot.visual_references import projection
from sqlalchemy import select
from test_visual_references import SOURCE, step
from test_visual_references import generated_visual_unit as original_generated_visual_unit


@pytest.fixture
def generated_visual_unit(household):
    return original_generated_visual_unit.__wrapped__(household)

@pytest.fixture
def legacy(api, household, generated_visual_unit, monkeypatch):
    from schulpilot import providers

    uid, mid, cid = generated_visual_unit
    with DB.begin() as db:
        db.delete(db.get(UnitVisualSnapshot, uid))
        unit = db.get(LearningUnit, uid)
        unit.questions = [{key: value for key, value in question.items() if key != "explanation_steps"} for question in unit.questions]
        db.add(Attempt(unit_id=uid, question_id="q1", answer="1/3", outcome="incorrect", assisted=False, evaluation={"attempt_number": 1}))
    calls = {"reserve": [], "provider": [], "settle": []}
    monkeypatch.setattr(providers, "reserve", lambda db, family, child, job, function: calls["reserve"].append((child, job, function)))
    monkeypatch.setattr(providers, "external_allowed", lambda *args, **kwargs: None)
    monkeypatch.setattr(providers, "settle", lambda *args, **kwargs: calls["settle"].append({**kwargs, "result": args[2] if len(args) > 2 else None}))

    def generate(config, function, payload, **kwargs):
        calls["provider"].append((function, copy.deepcopy(payload)))
        return Result({"subject": "Mathematik", "topic": "Brüche", "explanation_steps": [step()],
                       "questions": [{"id": "q1", "explanation_steps": [step("solution")]}]}, 1, 1, 0)

    monkeypatch.setattr(providers, "request_provider", generate)
    return uid, mid, cid, calls


def start(api, uid, key=None):
    return api.post(f"/api/units/{uid}/visual-explanation", headers={"Idempotency-Key": key or uuid4().hex})


def test_parent_prepares_legacy_graphics_without_child_activity_or_modifying_saved_round(api, legacy):
    uid, mid, _, calls = legacy
    with DB() as db:
        old = copy.deepcopy(db.get(LearningUnit, uid).questions)
        before = db.query(Attempt).count(), db.query(Activity).count()
        assert projection(db, db.get(LearningUnit, uid))["explanation_visual_status"] == "legacy_text"
    key = uuid4().hex
    response = start(api, uid, key)
    assert response.status_code == 202, response.text
    jid = response.json()["id"]
    assert api.get(f"/api/jobs/{jid}/trace").json()["sources"] == [
        {"id": mid, "revision": 1, "current_revision": 1}
    ]
    assert calls["reserve"][0][2] == "unit"
    assert start(api, uid, key).json() == response.json()
    assert len(calls["reserve"]) == 1
    with DB.begin() as db:
        db.get(Job, jid).status = "running"
    process(jid)
    with DB() as db:
        job, unit = db.get(Job, jid), db.get(LearningUnit, uid)
        assert job.status == "completed", job.error
        assert unit.questions == old
        assert unit.explanation == SOURCE
        assert unit.status == "paused"
        assert before == (db.query(Attempt).count(), db.query(Activity).count())
        visible = projection(db, unit)
        assert visible["explanation_visual_status"] == "ready"
        assert visible["visual_preparation"]["status"] == "completed"
        assert db.get(UnitVisualSnapshot, uid).question_steps["q1"][0]["disclosure"] == "solution"
    assert len(calls["provider"]) == 1
    with DB() as db:
        from schulpilot.visual_reference_models import VisualReference
        from schulpilot.visual_references import digest

        refs = calls["provider"][0][1]["visual_context"]["references"]
        selected = next(ref for ref in refs if ref["id"] == "math.fraction.part_whole")
        stored = db.get(VisualReference, (selected["id"], selected["version"]))
        assert selected["subject"] == "Mathematik"
        assert selected["digest"] == stored.digest == digest(stored.recipe)
    assert start(api, uid).status_code == 409
    assert len(calls["reserve"]) == 1


@pytest.mark.parametrize("fault", ["schema", "factual"])
def test_invalid_visual_result_has_safe_trace_and_keeps_round_and_attempt(api, legacy, monkeypatch, fault):
    from schulpilot import providers
    from schulpilot.db import Mastery, Usage

    uid, mid, _, calls = legacy
    with DB() as db:
        old = copy.deepcopy(db.get(LearningUnit, uid).questions)
    response = start(api, uid)
    assert response.status_code == 202
    jid = response.json()["id"]
    original = providers.request_provider

    def invalid(*args, **kwargs):
        result = original(*args, **kwargs)
        if fault == "schema":
            result.data["questions"] = []
        else:
            # Text/source describe 1/2, but the diagram claims 1/3.
            result.data["explanation_steps"][0]["presentation"]["blocks"][0]["numbers"] = [1, 3]
        return result

    monkeypatch.setattr(providers, "request_provider", invalid)
    with DB.begin() as db:
        db.get(Job, jid).status = "running"
    process(jid)
    with DB() as db:
        assert db.get(Job, jid).status == "failed"
        assert db.get(Job, jid).error_code == "invalid_output"
        assert db.get(UnitVisualSnapshot, uid) is None
        assert db.get(LearningUnit, uid).questions == old
        before = tuple(db.query(model).count() for model in (Job, Usage, Attempt, Activity, Mastery))
    for _ in range(2):
        trace = api.get(f"/api/jobs/{jid}/trace")
        assert trace.status_code == 200
        assert trace.json()["phase"] == "visual"
        assert trace.json()["error_code"] == "invalid_output"
        assert trace.json()["units"] == []
        assert trace.json()["sources"] == [{"id": mid, "revision": 1, "current_revision": 1}]
        assert SOURCE not in trace.text
    with DB() as db:
        assert tuple(db.query(model).count() for model in (Job, Usage, Attempt, Activity, Mastery)) == before
    assert len(calls["provider"]) == 1
    assert calls["settle"][0]["failed"] is True


def test_legacy_visual_job_without_trace_sources_keeps_idempotency(api, legacy):
    uid, _, _, calls = legacy
    key = uuid4().hex
    response = start(api, uid, key)
    assert response.status_code == 202
    jid = response.json()["id"]
    with DB.begin() as db:
        job = db.get(Job, jid)
        job.payload = {key: value for key, value in job.payload.items() if key != "sources"}
    assert start(api, uid, key).json() == response.json()
    assert api.get(f"/api/jobs/{jid}/trace").json()["sources"] == []
    assert len(calls["reserve"]) == 1


@pytest.mark.parametrize("change", ["source", "unit", "logout", "membership"])
def test_late_graphic_result_is_rejected_after_context_or_authority_change(api, legacy, monkeypatch, change):
    from schulpilot import providers
    from schulpilot.db import Membership

    uid, mid, _, calls = legacy
    response = start(api, uid)
    assert response.status_code == 202
    jid = response.json()["id"]
    with DB.begin() as db:
        db.get(Job, jid).status = "running"
    original = providers.request_provider

    def stale(config, function, payload, **kwargs):
        result = original(config, function, payload, **kwargs)
        with DB.begin() as db:
            if change == "source":
                db.get(Material, mid).revision += 1
            elif change == "unit":
                db.get(LearningUnit, uid).topic = "Anderes Thema"
            elif change == "logout":
                db.get(Session, db.get(Job, jid).payload["session_id"]).revoked = True
            else:
                job = db.get(Job, jid)
                member = db.scalar(select(Membership).where(Membership.user_id == job.payload["user_id"], Membership.family_id == job.payload["family_id"]))
                member.permission = "view"
        return result

    monkeypatch.setattr(providers, "request_provider", stale)
    process(jid)
    with DB() as db:
        assert db.get(Job, jid).status == "failed"
        assert db.get(UnitVisualSnapshot, uid) is None
        assert db.query(Attempt).count() == 1
        assert db.query(Activity).count() == 0
    assert len(calls["provider"]) == 1


def test_another_pending_child_job_prevents_a_second_paid_sidecar(api, legacy):
    uid, _, cid, calls = legacy
    with DB.begin() as db:
        db.add(Job(child_id=cid, kind="unit", payload={}, status="queued", idempotency=uuid4().hex))
    assert start(api, uid).status_code == 409
    assert calls["reserve"] == []


def test_read_only_parent_cannot_reserve_or_change_graphic_sidecar(api, legacy):
    from schulpilot.db import Membership

    uid, _, _, calls = legacy
    with DB.begin() as db:
        job_owner = db.scalar(select(Membership).limit(1))
        job_owner.permission = "view"
    assert start(api, uid).status_code == 403
    assert calls["reserve"] == []


def test_missing_idempotency_key_never_reserves(api, legacy):
    uid, _, _, calls = legacy
    assert api.post(f"/api/units/{uid}/visual-explanation").status_code == 422
    assert calls["reserve"] == []


def test_scene_without_source_arrow_is_rejected_before_reservation(api, legacy, monkeypatch):
    from schulpilot import visual_jobs

    uid, _, _, calls = legacy
    original = visual_jobs.with_visual_context

    def no_scene_evidence(*args, **kwargs):
        value = original(*args, **kwargs)
        value["visual_context"]["references"] = [{"id": "general.source_relation.phases", "kind": "scene"}]
        assert all("→" not in row["content"] and "->" not in row["content"]
                   for row in value["visual_context"]["sources"])
        return value

    monkeypatch.setattr(visual_jobs, "with_visual_context", no_scene_evidence)
    response = start(api, uid)
    assert response.status_code == 409
    assert calls["reserve"] == []
    assert calls["provider"] == []


def test_unit_view_does_not_offer_impossible_graphic_or_start_a_job(api, legacy, monkeypatch):
    from schulpilot import visual_jobs

    uid, _, _, calls = legacy
    original = visual_jobs.with_visual_context

    def no_scene_evidence(*args, **kwargs):
        value = original(*args, **kwargs)
        value["visual_context"]["references"] = [{"id": "general.source_relation.phases", "kind": "scene"}]
        assert all("→" not in row["content"] and "->" not in row["content"]
                   for row in value["visual_context"]["sources"])
        return value

    monkeypatch.setattr(visual_jobs, "with_visual_context", no_scene_evidence)
    with DB() as db:
        before = db.query(Job).count(), db.query(Attempt).count(), db.query(Activity).count()
    response = api.get(f"/api/units/{uid}")
    assert response.status_code == 200, response.text
    assert response.json()["can_prepare_visual"] is False
    assert response.json()["visual_prepare_unavailable"] is True
    with DB() as db:
        assert before == (db.query(Job).count(), db.query(Attempt).count(), db.query(Activity).count())
    assert not calls["reserve"] and not calls["provider"]
    assert start(api, uid).status_code == 409


def test_unit_view_keeps_available_graphic_action_without_reserving(api, legacy):
    uid, _, _, calls = legacy
    response = api.get(f"/api/units/{uid}")
    assert response.status_code == 200, response.text
    assert response.json()["can_prepare_visual"] is True
    assert "visual_prepare_unavailable" not in response.json()
    assert not calls["reserve"] and not calls["provider"]


@pytest.mark.parametrize("states", [("failed", "failed"), ("completed",)])
def test_unit_view_hides_exhausted_graphic_attempts_for_current_context(api, legacy, states):
    uid, _, cid, calls = legacy
    with DB.begin() as db:
        unit = db.get(LearningUnit, uid)
        signature, _ = context(db, unit)
        for state in states:
            db.add(Job(child_id=cid, kind="unit_visuals", status=state,
                       payload={"unit_id": uid, "signature": signature}, idempotency=uuid4().hex))
    response = api.get(f"/api/units/{uid}")
    assert response.status_code == 200, response.text
    assert response.json()["can_prepare_visual"] is False
    assert response.json()["visual_prepare_reason"] == "attempts_exhausted"
    assert not calls["reserve"] and not calls["provider"]
    assert start(api, uid).status_code == 409
    # A genuinely changed round gets its own existing source-bound contract.
    with DB.begin() as db:
        db.get(LearningUnit, uid).topic = "Brüche neu betrachtet"
    response = api.get(f"/api/units/{uid}")
    assert response.status_code == 200 and response.json()["can_prepare_visual"] is True


def test_unit_view_prefers_active_graphic_job_over_other_old_failures(api, legacy):
    uid, _, cid, calls = legacy
    with DB.begin() as db:
        signature, _ = context(db, db.get(LearningUnit, uid))
        old = Job(child_id=cid, kind="unit_visuals", status="failed", created=10,
                  payload={"unit_id": uid, "signature": signature}, idempotency=uuid4().hex)
        running = Job(child_id=cid, kind="unit_visuals", status="running", created=10,
                      payload={"unit_id": uid, "signature": signature}, idempotency=uuid4().hex)
        db.add_all([old, running])
        db.flush()
        running_id = running.id
    response = api.get(f"/api/units/{uid}")
    assert response.status_code == 200, response.text
    assert response.json()["visual_preparation"]["id"] == running_id
    assert response.json()["visual_preparation"]["status"] == "running"
    assert response.json()["can_prepare_visual"] is False
    assert not calls["reserve"] and not calls["provider"]


def test_sidecar_context_is_derived_from_existing_source_revision_and_saved_question(api, legacy):
    uid, mid, _, _ = legacy
    with DB() as db:
        signature, value = context(db, db.get(LearningUnit, uid))
    assert len(signature) == 64
    assert value["visual_context"]["sources"][0]["material_id"] == mid
    assert value["saved_questions"][0]["id"] == "q1"
    assert "answer" not in value["saved_questions"][0]
    assert value["visual_only"] is True


def test_source_gate_before_provider_entry_settles_as_provably_not_sent(api, legacy):
    uid, mid, _, calls = legacy
    jid = start(api, uid).json()["id"]
    with DB.begin() as db:
        db.get(Job, jid).status = "running"
        db.get(Material, mid).revision += 1
    process(jid)
    assert calls["provider"] == []
    receipt = calls["settle"][0]["result"]
    assert receipt.cost_source == "cancelled"
    assert (receipt.input_tokens, receipt.output_tokens, receipt.cost_micros) == (0, 0, 0)


def test_error_after_provider_function_entry_is_not_falsely_reported_free(api, legacy, monkeypatch):
    from schulpilot import providers

    uid, _, _, calls = legacy
    jid = start(api, uid).json()["id"]
    with DB.begin() as db:
        db.get(Job, jid).status = "running"
    def failure(*args, **kwargs):
        raise providers.ProviderError("Künstlicher unbekannter Transportfehler")
    monkeypatch.setattr(providers, "request_provider", failure)
    process(jid)
    assert calls["settle"][0]["result"] is None
    assert calls["settle"][0]["failed"] is True


def test_legacy_graphics_do_not_certify_old_questions_were_generated_from_filtered_blocks(api, legacy):
    from schulpilot.visual_references import source_bindings_current

    uid, _, _, _ = legacy
    jid = start(api, uid).json()['id']
    with DB.begin() as db:
        db.get(Job, jid).status = 'running'
    process(jid)
    with DB() as db:
        unit = db.get(LearningUnit, uid)
        assert source_bindings_current(db, unit)
        assert not source_bindings_current(db, unit, require_question_binding=True)
