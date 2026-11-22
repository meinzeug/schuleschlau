"""Bounded ECB/OpenRouter metadata refresh; never sends learning content.

A refreshed quote is a conservative planning bound, not a settled EUR bill.
No inference, provider switch, route evaluation or change to spending limits.
"""
import copy
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from urllib.parse import quote
from xml.etree import ElementTree

import httpx
from sqlalchemy import select

from .config import settings
from .db import DB, Job, OperatorJob, ProviderConfig, ServiceState, now
from .model_routing import RoutingPolicy, enabled
from .security import audit, decrypt, insert_ignore

log = logging.getLogger("schulpilot.market_data")
ECB = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
HOSTS = {"standard": "https://openrouter.ai", "eu": "https://eu.openrouter.ai", "us": "https://us.openrouter.ai"}
INTERVAL = 6 * 3600
ATTEMPT = "market-data-attempt"
NEXT = "market-data-next"
SUCCESS = "market-data-success"
ECB_SUCCESS = "market-data-ecb"
MAX_BYTES = 1_000_000


def parse_ecb(body, timestamp):
    if len(body) > MAX_BYTES or b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        raise ValueError("Invalid ECB document")
    root = ElementTree.fromstring(body)
    dated = [e for e in root.iter() if "time" in e.attrib]
    if len(dated) != 1:
        raise ValueError("Invalid ECB reference date")
    day = datetime.strptime(dated[0].attrib["time"], "%Y-%m-%d").date()
    today = datetime.fromtimestamp(timestamp, timezone.utc).date()
    if not 0 <= (today - day).days <= 7:
        raise ValueError("ECB reference is stale or in the future")
    usd = [e.attrib.get("rate") for e in dated[0].iter() if e.attrib.get("currency") == "USD"]
    if len(usd) != 1:
        raise ValueError("Missing or ambiguous USD quote")
    try:
        dollars_per_euro = Decimal(usd[0])
        if not dollars_per_euro.is_finite() or not Decimal("0.1") <= dollars_per_euro <= Decimal("10"):
            raise ValueError("Invalid USD quote")
        euro_per_dollar = (Decimal(1) / dollars_per_euro).quantize(Decimal("0.000001"), rounding=ROUND_CEILING)
    except (InvalidOperation, TypeError, ZeroDivisionError):
        raise ValueError("Invalid USD quote") from None
    return day.isoformat(), str(dollars_per_euro), str(euro_per_dollar)


def parse_prices(payload, model, upstreams):
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict) or data.get("id") != model or not isinstance(data.get("endpoints"), list):
        raise ValueError("Invalid provider metadata")
    matched = []
    for upstream in upstreams:
        endpoints = [e for e in data["endpoints"] if isinstance(e, dict) and e.get("tag") == upstream and e.get("status") == 0]
        if len(endpoints) != 1:
            raise ValueError("Configured provider endpoint unavailable")
        pricing = endpoints[0].get("pricing")
        if not isinstance(pricing, dict) or "prompt" not in pricing or "completion" not in pricing:
            raise ValueError("Missing provider prices")
        try:
            if any(Decimal(str(pricing.get(key) or 0)) != 0 for key in ("request", "image")):
                raise ValueError("Unsupported extra provider charge")
            prices = [pricing, *(pricing.get("overrides") or [])]
            if any(not isinstance(p, dict) for p in prices):
                raise ValueError("Invalid price override")
            for key in ("prompt", "completion"):
                values = [Decimal(str(p[key])) for p in prices if key in p]
                if not values or not all(v.is_finite() and v >= 0 for v in values):
                    raise ValueError("Invalid provider price")
                matched.append((key, int((max(values) * 1_000_000_000_000).to_integral_value(rounding=ROUND_CEILING))))
        except (InvalidOperation, TypeError, KeyError):
            raise ValueError("Invalid provider price") from None
    result = {key: max(v for k, v in matched if k == key) for key in ("prompt", "completion")}
    if result["prompt"] > 100_000_000 or result["completion"] > 500_000_000:
        raise ValueError("Provider price exceeds supported bounds")
    return result


def parse_image_prices(payload, model, upstreams):
    """Current Image API token rates, rejecting unpriced billing dimensions."""
    if not isinstance(payload, dict) or payload.get("id") != model or len(upstreams) != 1:
        raise ValueError("Invalid image metadata")
    endpoints = payload.get("endpoints")
    matches = [e for e in endpoints or [] if isinstance(e, dict) and e.get("provider_tag") == upstreams[0]]
    if len(matches) != 1 or not isinstance(matches[0].get("pricing"), list):
        raise ValueError("Configured image endpoint unavailable")
    result = {}
    for row in matches[0]["pricing"]:
        if not isinstance(row, dict):
            raise ValueError("Invalid image rate")
        kind, unit = row.get("billable"), row.get("unit")
        try:
            amount = Decimal(str(row["cost_usd"]))
            if not amount.is_finite() or amount < 0:
                raise ValueError("Invalid image rate")
        except (InvalidOperation, KeyError, TypeError):
            raise ValueError("Invalid image rate") from None
        if kind == "input_image":
            continue  # The public prompt never includes input images.
        if kind not in ("input_text", "output_image") or unit != "token" or kind in result:
            raise ValueError("Unsupported image billing dimension")
        result[kind] = int((amount * 1_000_000_000_000).to_integral_value(rounding=ROUND_CEILING))
    if set(result) != {"input_text", "output_image"}:
        raise ValueError("Missing image rates")
    return {"prompt": result["input_text"], "completion": result["output_image"]}


def get_limited(client, url, *, headers=None):
    with client.stream("GET", url, headers=headers) as response:
        response.raise_for_status()
        chunks, size = [], 0
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > MAX_BYTES:
                raise ValueError("Metadata response too large")
            chunks.append(chunk)
        return b"".join(chunks)


def refresh_if_due(*, force=False):
    """At most one periodic metadata attempt; every accepted change is audited.

    Network calls happen outside database transactions. The final row lock is
    shared with new reservations and operator probes; active work is not
    invalidated. Failed or inconsistent metadata leaves the last quote intact.
    """
    if settings.environment != "production" and not force:
        return False
    tick = int(now())
    with DB.begin() as db:
        config = db.get(ProviderConfig, 1)
        if not config or not enabled(config):
            return False
        if db.scalar(select(Job.id).where(Job.status.in_(["queued", "running"]))):
            return False
        if db.scalar(select(OperatorJob.id).where(OperatorJob.status.in_(["queued", "running"]))):
            return False
        insert_ignore(db, ServiceState, {"name": ATTEMPT, "updated": 0}, key="name")
        state = db.scalar(select(ServiceState).where(ServiceState.name == ATTEMPT).with_for_update())
        next_attempt = db.get(ServiceState, NEXT)
        if not force and ((next_attempt and tick < next_attempt.updated) or
                          (not next_attempt and tick - state.updated < INTERVAL)):
            return False
        state.updated = tick
        insert_ignore(db, ServiceState, {"name": NEXT, "updated": tick + INTERVAL}, key="name")
        db.get(ServiceState, NEXT).updated = tick + INTERVAL
        revision, policy = config.revision, copy.deepcopy(config.routing_policy)
        try:
            secret = settings.openrouter_api_key or (decrypt(config.encrypted_key) if config.encrypted_key else "")
        except Exception:
            # A bad provider credential must not prevent refreshing ECB data.
            log.warning("market_data_key_unavailable")
            secret = ""
    fx = None
    price_updates = {}
    try:
        policy = RoutingPolicy.model_validate(policy).model_dump()
        with httpx.Client(timeout=httpx.Timeout(8, connect=4), follow_redirects=False) as client:
            try:
                fx = parse_ecb(get_limited(client, ECB), tick)
            except (ValueError, httpx.HTTPError, ElementTree.ParseError):
                log.warning("market_data_ecb_unavailable")
            if secret:
                import json
                host = HOSTS[policy["region"]]
                for tier, route in policy["routes"].items():
                    url = host + ("/api/v1/images/models/" if tier == "image" else "/api/v1/models/") + quote(route["model"], safe="/") + "/endpoints"
                    try:
                        data = json.loads(get_limited(client, url, headers={"Authorization": "Bearer " + secret}))
                        parser = parse_image_prices if tier == "image" else parse_prices
                        price_updates[tier] = (parser(data, route["model"], route["upstreams"]), url)
                    except (ValueError, httpx.HTTPError, KeyError):
                        log.warning("market_data_price_unavailable tier=%s", tier)
    except (ValueError, httpx.HTTPError):
        log.warning("market_data_refresh_unavailable")
        return False
    if fx is None and not price_updates:
        return False
    with DB.begin() as db:
        current = db.scalar(select(ProviderConfig).where(ProviderConfig.id == 1).with_for_update())
        if not current or not enabled(current):
            return False
        if (current.revision != revision or
                db.scalar(select(Job.id).where(Job.status.in_(["queued", "running"]))) or
                db.scalar(select(OperatorJob.id).where(OperatorJob.status.in_(["queued", "running"])) )):
            state = db.get(ServiceState, NEXT)
            if state:
                state.updated = tick + 60
            return False
        new_policy = copy.deepcopy(current.routing_policy)
        if fx is not None:
            day, usd, eur = fx
            new_policy["budget"].update(eur_per_usd=eur, fx_checked_at=tick,
                fx_evidence=f"ECB {day} {ECB}; 1 EUR = {usd} USD; inverse rounded upward")
            insert_ignore(db, ServiceState, {"name": ECB_SUCCESS, "updated": tick}, key="name")
            db.get(ServiceState, ECB_SUCCESS).updated = tick
        changed_tiers = []
        for tier, (prices, url) in price_updates.items():
            route = new_policy["routes"][tier]
            route["input_per_million_micros"] = prices["prompt"]
            route["output_per_million_micros"] = prices["completion"]
            route["pricing_evidence"] = f"{datetime.fromtimestamp(tick, timezone.utc).date()} {url}; maximum published token tier, rounded upward"
            changed_tiers.append(tier)
            name = "market-data-route-" + tier
            insert_ignore(db, ServiceState, {"name": name, "updated": tick}, key="name")
            db.get(ServiceState, name).updated = tick
        # Never refresh route.verified_at, operator approvals, limits, upstreams,
        # reservations or past usage; metadata is not a capability test.
        RoutingPolicy.model_validate(new_policy)
        current.routing_policy = new_policy
        current.revision += 1
        audit(db, "market-data", "ai.market_data_refresh", f"ECB:{fx[0] if fx else 'unchanged'};routes:{','.join(sorted(changed_tiers))}")
        insert_ignore(db, ServiceState, {"name": SUCCESS, "updated": tick}, key="name")
        db.get(ServiceState, SUCCESS).updated = tick
    return True
