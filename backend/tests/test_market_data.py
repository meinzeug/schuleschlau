"""Public, artificial market metadata only; no external inference."""
import copy
from dataclasses import replace
from datetime import datetime, timezone

import httpx
import pytest
from sqlalchemy import select

from schulpilot import market_data
from schulpilot.db import DB, Audit, Job, ProviderConfig, ServiceState
from schulpilot.model_routing import BudgetPolicy
from test_model_routing import setup_policy


def xml_for(timestamp, rate="1.1000"):
    day = datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()
    return (f'<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01" '
            f'xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref"><Cube><Cube time="{day}">'
            f'<Cube currency="USD" rate="{rate}"/></Cube></Cube></gesmes:Envelope>').encode()


def test_ecb_quote_is_fresh_conservative_and_rejects_bad_documents():
    tick = 1795334400
    assert market_data.parse_ecb(xml_for(tick), tick)[2] == "0.909091"
    with pytest.raises(ValueError, match="stale"):
        market_data.parse_ecb(xml_for(tick - 9 * 86400), tick)
    with pytest.raises(ValueError):
        market_data.parse_ecb(xml_for(tick, "NaN"), tick)
    with pytest.raises(ValueError):
        market_data.parse_ecb(b'<!DOCTYPE x [<!ENTITY x "x">]><x/>', tick)


def test_price_parser_uses_highest_published_tier_and_exact_provider():
    metadata = {"data": {"id": "vendor/model", "endpoints": [{"tag": "azure/eu", "status": 0,
        "pricing": {"prompt": "0.0000024", "completion": "0.000012", "request": "0",
            "overrides": [{"prompt": "0.0000048", "completion": "0.000018"}]}}]}}
    assert market_data.parse_prices(metadata, "vendor/model", ["azure/eu"]) == {"prompt": 4800000, "completion": 18000000}
    with pytest.raises(ValueError):
        market_data.parse_prices(metadata, "vendor/model", ["azure"])
    metadata["data"]["endpoints"][0]["pricing"]["image"] = "0.05"
    with pytest.raises(ValueError, match="extra"):
        market_data.parse_prices(metadata, "vendor/model", ["azure/eu"])


def configure(household):
    parent, child = household
    setup_policy(parent["families"][0]["id"])
    with DB() as db:
        config = db.get(ProviderConfig, 1)
        return child, config.revision, copy.deepcopy(config.routing_policy)


def install_fake_client(monkeypatch, policy, tick, on_request=None, failed_hosts=()):
    real_client = httpx.Client
    def handle(request):
        if on_request:
            on_request(request)
        if request.url.host in failed_hosts:
            return httpx.Response(503, request=request)
        if request.url.host == "www.ecb.europa.eu":
            return httpx.Response(200, content=xml_for(tick), request=request)
        model = str(request.url.path).split('/models/', 1)[1].removesuffix('/endpoints')
        routes = [r for r in policy["routes"].values() if r["model"] == model]
        assert routes
        return httpx.Response(200, json={"data": {"id": model, "endpoints": [
            {"tag": tag, "status": 0, "pricing": {"prompt": "0.000001", "completion": "0.000005"}}
            for tag in routes[0]["upstreams"]]}}, request=request)
    monkeypatch.setattr(market_data.httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(handle)))
    monkeypatch.setattr(market_data, "settings", replace(market_data.settings, environment="test", openrouter_api_key="synthetic-key"))
    monkeypatch.setattr(market_data, "now", lambda: tick)


def test_refresh_updates_quotes_only_and_respects_active_job(api, household, monkeypatch):
    child, revision, policy = configure(household)
    tick = 1795334400
    install_fake_client(monkeypatch, policy, tick)
    assert market_data.refresh_if_due(force=True)
    with DB() as db:
        config = db.get(ProviderConfig, 1)
        updated = config.routing_policy
        assert config.revision == revision + 1
        assert updated["budget"]["eur_per_usd"] == "0.909091"
        assert updated["budget"]["fx_checked_at"] == tick
        for tier in policy["routes"]:
            assert updated["routes"][tier]["verified_at"] == policy["routes"][tier]["verified_at"]
            assert updated["routes"][tier]["upstreams"] == policy["routes"][tier]["upstreams"]
            assert updated["routes"][tier]["reserve_micros"] == policy["routes"][tier]["reserve_micros"]
            assert updated["routes"][tier]["input_per_million_micros"] == 1000000
            assert updated["routes"][tier]["output_per_million_micros"] == 5000000
        assert BudgetPolicy.model_validate(updated["budget"]).hard_eur_micros == BudgetPolicy.model_validate(policy["budget"]).hard_eur_micros
        assert db.scalar(select(Audit.id).where(Audit.action == "ai.market_data_refresh"))
        from schulpilot.routing_admin import routing
        status = routing(p=None, db=db)["metadata_refresh"]
        assert status["last_attempt"] == status["last_update"] == status["ecb_updated"] == tick
        assert all(status["prices_updated"][tier] == tick for tier in policy["routes"])
    with DB.begin() as db:
        db.add(Job(child_id=child["id"], kind="unit", payload={}, status="queued", idempotency="market-active-test"))
    assert not market_data.refresh_if_due(force=True)
    with DB() as db:
        assert db.get(ProviderConfig, 1).revision == revision + 1


def test_job_created_during_fetch_prevents_configuration_change(api, household, monkeypatch):
    child, revision, policy = configure(household)
    tick = 1795334400
    created = False
    def concurrent_request(_):
        nonlocal created
        if not created:
            created = True
            with DB.begin() as db:
                db.add(Job(child_id=child["id"], kind="unit", payload={}, status="queued", idempotency="market-race-test"))
    install_fake_client(monkeypatch, policy, tick, concurrent_request)
    assert not market_data.refresh_if_due(force=True)
    with DB() as db:
        assert db.get(ProviderConfig, 1).revision == revision
        assert db.get(ServiceState, market_data.ATTEMPT).updated == tick
        assert db.get(ServiceState, market_data.NEXT).updated == tick + 60


@pytest.mark.parametrize("failed_host", ["www.ecb.europa.eu", "openrouter.ai"])
def test_one_unavailable_source_does_not_forge_its_data(api, household, monkeypatch, failed_host):
    _, revision, policy = configure(household)
    tick = 1795334400
    install_fake_client(monkeypatch, policy, tick, failed_hosts=(failed_host,))
    assert market_data.refresh_if_due(force=True)
    with DB() as db:
        config = db.get(ProviderConfig, 1)
        assert config.revision == revision + 1
        if failed_host == "www.ecb.europa.eu":
            assert config.routing_policy["budget"] == policy["budget"]
        else:
            assert config.routing_policy["budget"]["fx_checked_at"] == tick
            assert config.routing_policy["routes"] == policy["routes"]


def test_postgres_reservation_blocks_concurrent_quote_commit(api, household, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from schulpilot.db import Family, uid
    from schulpilot.providers import reserve

    child, revision, policy = configure(household)
    with DB() as db:
        if db.bind.dialect.name != "postgresql":
            pytest.skip("Requires real PostgreSQL row locking")
    parent, _ = household
    family_id = parent["families"][0]["id"]
    reserved, fetched, release = Event(), Event(), Event()
    tick = 1795334400
    install_fake_client(monkeypatch, policy, tick, lambda _: fetched.set())

    def reserve_before_commit():
        with DB.begin() as db:
            job = Job(id=uid(), child_id=child["id"], kind="unit", payload={}, status="queued", idempotency="market-pg-race")
            db.add(job)
            db.flush()
            usage = reserve(db, db.get(Family, family_id), child["id"], job.id, "unit")
            assert usage.config_revision == revision
            reserved.set()
            assert release.wait(20)

    with ThreadPoolExecutor(max_workers=2) as executor:
        writer = executor.submit(reserve_before_commit)
        assert reserved.wait(20)
        sync = executor.submit(market_data.refresh_if_due, force=True)
        try:
            assert fetched.wait(20)
            assert not sync.done()
        finally:
            release.set()
        writer.result(timeout=20)
        assert sync.result(timeout=20) is False
    with DB() as db:
        assert db.get(ProviderConfig, 1).revision == revision
def test_image_rates_use_exact_endpoint_and_reject_unpriced_dimensions():
    from schulpilot.market_data import parse_image_prices

    sample = {"id": "test/image", "endpoints": [{"provider_tag": "azure", "pricing": [
        {"billable": "input_text", "unit": "token", "cost_usd": 0.00000175},
        {"billable": "input_image", "unit": "token", "cost_usd": 0.0000025},
        {"billable": "output_image", "unit": "token", "cost_usd": 0.00001}]}]}
    assert parse_image_prices(sample, "test/image", ["azure"]) == {"prompt": 1750000, "completion": 10000000}
    import copy
    bad = copy.deepcopy(sample)
    bad["endpoints"][0]["pricing"].append({"billable": "request", "unit": "request", "cost_usd": 0.1})
    import pytest
    with pytest.raises(ValueError):
        parse_image_prices(bad, "test/image", ["azure"])
    with pytest.raises(ValueError):
        parse_image_prices(sample, "test/image", ["other"])


def test_refresh_reads_image_api_rates_without_changing_approval(api, household, monkeypatch):
    from schulpilot.db import now

    _, _, policy = configure(household)
    image = copy.deepcopy(policy['routes']['sol'])
    image.update(model='test/image-model', upstreams=['azure'],
        image_output_budget={'version': 1, 'basis': 'operator_estimate', 'model': 'test/image-model',
            'upstream': 'azure', 'input_tokens': 500, 'output_tokens': 3000,
            'evidence': 'Synthetic test reservation evidence', 'approved_at': int(now())})
    policy['routes']['image'] = image
    with DB.begin() as db:
        db.get(ProviderConfig, 1).routing_policy = policy
    tick = 1795334400
    real_client = httpx.Client
    requested = []
    def handle(request):
        requested.append(str(request.url))
        if request.url.host == 'www.ecb.europa.eu':
            return httpx.Response(200, content=xml_for(tick), request=request)
        if '/images/models/' in request.url.path:
            return httpx.Response(200, json={'id': 'test/image-model', 'endpoints': [{'provider_tag': 'azure',
                'pricing': [{'billable': 'input_text', 'unit': 'token', 'cost_usd': 0.00000175},
                            {'billable': 'output_image', 'unit': 'token', 'cost_usd': 0.00001}]}]}, request=request)
        model = str(request.url.path).split('/models/', 1)[1].removesuffix('/endpoints')
        return httpx.Response(200, json={'data': {'id': model, 'endpoints': [{'tag': 'azure', 'status': 0,
            'pricing': {'prompt': '0.000001', 'completion': '0.000005'}}]}}, request=request)
    monkeypatch.setattr(market_data.httpx, 'Client', lambda **kwargs: real_client(transport=httpx.MockTransport(handle)))
    monkeypatch.setattr(market_data, 'settings', replace(market_data.settings, environment='test', openrouter_api_key='synthetic-key'))
    monkeypatch.setattr(market_data, 'now', lambda: tick)
    assert market_data.refresh_if_due(force=True)
    with DB() as db:
        route = db.get(ProviderConfig, 1).routing_policy['routes']['image']
        assert route['input_per_million_micros'] == 1750000
        assert route['output_per_million_micros'] == 10000000
        assert route['verified_at'] == image['verified_at']
        assert route['image_output_budget'] == image['image_output_budget']
    assert any('/images/models/test/image-model/endpoints' in url for url in requested)
