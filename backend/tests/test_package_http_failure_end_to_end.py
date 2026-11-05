"""Actual OpenRouter adapter failures through a persisted multi-part worker.

The first and explicit-retry outputs are artificial validated fixtures. The
failure itself crosses the real adapter and the worker; HTTP never leaves the
mock transport and no real key or family is used.
"""
import json

import httpx
import pytest
from schulpilot import providers, worker
from schulpilot.db import DB, Attempt, Job, LearningUnit, Usage
from sqlalchemy import func, select
from test_package_parts_worker import artificial_day, bounded_output, preparation, run_one, snapshot
from test_package_transport import config as adapter_config


@pytest.mark.parametrize(("fault", "expected", "billed"), [
    ("http400", "not_configured", False),
    ("http400_schema", "invalid_output", False),
    ("http429", "provider_busy", False),
    ("http408", "provider_timeout", False),
    ("http500", "provider_unavailable", False),
    ("http503", "provider_unavailable", False),
    ("http504", "provider_timeout", False),
    ("timeout", "provider_timeout", False),
    ("network", "provider_unavailable", False),
    ("truncated", "invalid_output", True),
    ("invalid_json", "invalid_output", True),
    ("invalid_envelope_json", "invalid_output", False),
    ("embedded_429", "provider_busy", True),
    ("empty", "invalid_output", True),
    ("schema", "invalid_output", True),
])
def test_http_error_is_settled_once_and_only_explicit_retry_continues(api, household, monkeypatch, fault, expected, billed):
    day_id, _, old = artificial_day(api, household)
    requests, calls = [], []
    real_client = httpx.Client
    marker = "SYNTHETIC-ECHO-NEVER-PERSIST"

    def handler(request):
        requests.append(request)
        if fault == "timeout":
            raise httpx.ReadTimeout("synthetic timeout", request=request)
        if fault == "network":
            raise httpx.ConnectError("synthetic network", request=request)
        if fault.startswith("http"):
            status = 400 if fault == "http400_schema" else int(fault[4:])
            metadata = {"raw": marker}
            if fault == "http400_schema":
                metadata["provider_error_code"] = "invalid_json_schema"
            return httpx.Response(status, json={"error": {"code": status, "message": marker, "metadata": metadata}})
        if fault == "invalid_envelope_json":
            return httpx.Response(200, content=b"{not-json")
        if fault == "embedded_429":
            return httpx.Response(200, json={"error": {"code": 429, "message": marker,
                "metadata": {"error_type": "rate_limit_exceeded", "raw": marker}},
                "usage": {"prompt_tokens": 5, "completion_tokens": 7, "cost": 0.000137}})
        content = {"truncated": "{}", "invalid_json": "not-json", "empty": "", "schema": "{}"}[fault]
        return httpx.Response(200, json={"choices": [{"finish_reason": "length" if fault == "truncated" else "stop",
            "message": {"content": content}}], "usage": {"prompt_tokens": 5, "completion_tokens": 7, "cost": 0.000137}})

    monkeypatch.setattr(providers.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(providers, "external_allowed", lambda *a, **kw: None)
    monkeypatch.setattr(providers, "decrypt", lambda _: "synthetic-key")
    monkeypatch.setattr("schulpilot.model_routing.selection", lambda cfg: {"route": {"upstreams": ["azure"]}, "region": "standard"} if cfg.provider == "openrouter" else None)
    def request(config, function, payload, image_bytes=None, *, synthetic_fixture=False):
        calls.append(payload["package_partition"])
        if len(calls) == 2:
            c = adapter_config()
            c.max_output_tokens = 8000
            return providers.request_provider(c, function, payload, image_bytes, synthetic_fixture=synthetic_fixture)
        return providers.Result(bounded_output(payload), 20, 40, 101, cost_source="reported")

    monkeypatch.setattr(worker, "request_provider", request)
    preparation(api, day_id, "http-matrix-first")
    assert run_one(), json.dumps(snapshot(day_id), ensure_ascii=False)
    assert calls == [0]
    first = snapshot(day_id)["package_outputs"]["0"]
    failed_job = run_one()
    assert failed_job and calls == [0, 1] and len(requests) == 1
    assert snapshot(day_id)["package_outputs"]["0"] == first
    state = api.get(f"/api/school-days/{day_id}").json()["preparation"]
    assert state["status"] == "failed" and state["error_code"] == expected
    assert state["completed_parts"] == 1 and state["total_parts"] == 3
    with DB() as db:
        job = db.get(Job, failed_job)
        usage = db.scalar(select(Usage).where(Usage.job_id == failed_job))
        assert job.error_code == expected and marker not in json.dumps({"error": job.error, "result": job.result})
        assert marker not in json.dumps(usage.telemetry)
        assert usage.settlement_version == 1
        if billed:
            assert usage.status == "failed_billed" and usage.cost_micros == 137
        else:
            assert usage.status == "failed_unknown" and usage.cost_micros is None and usage.reserved_micros > 0
        assert db.get(Attempt, old["attempt"]).answer == "Künstliche Altantwort"
        assert db.get(LearningUnit, old["unit"]).active_seconds == 17
        assert db.scalar(select(func.count()).select_from(Attempt)) == 1
    for _ in range(3):
        assert run_one() is None
        assert api.get(f"/api/school-days/{day_id}").json()["preparation"]["status"] == "failed"
    assert calls == [0, 1] and len(requests) == 1
    preparation(api, day_id, "http-matrix-explicit-retry")
    assert run_one() and run_one() and calls == [0, 1, 1, 2]
    ready = api.get(f"/api/school-days/{day_id}").json()
    assert ready["preparation"]["status"] == "ready" and len(ready["units"]) == 3
    with DB() as db:
        usage = db.scalar(select(Usage).where(Usage.job_id == failed_job))
        assert usage.settlement_version == 1
        assert db.scalar(select(func.count()).select_from(Attempt)) == 1
