"""Synthetic direct-provider charges must not use an expired EUR conversion."""

import pytest
from fastapi import HTTPException
from schulpilot.child_cost_models import UsageCostBalance
from schulpilot.db import DB, Family, ProviderConfig, Usage, UsageBucket, now
from schulpilot.job_failures import generation_availability
from schulpilot.providers import settle
from sqlalchemy import func, select
from test_child_cost_controls import claim, configure
from test_codex_models import operator as operator_fixture


@pytest.fixture
def operator():
    yield from operator_fixture.__wrapped__()


@pytest.mark.parametrize('offset', [-32 * 86400, 600])
@pytest.mark.parametrize(('day', 'month'), [(1_000_000, None), (None, 2_000_000)])
def test_child_cost_control_rejects_stale_or_future_fx_for_direct_provider(api, household, operator, offset, day, month):
    parent, child = household
    family_id = parent['families'][0]['id']
    configure(api, household, operator, day=day, month=month)
    with DB.begin() as db:
        config = db.get(ProviderConfig, 1)
        # Direct providers bypass model routing's independent freshness guard.
        config.provider = 'openai'
        config.routing_policy = {**config.routing_policy, 'budget': {**config.routing_policy['budget'],
            'fx_checked_at': int(now()) + offset}}
    edited = configure(api, household, operator, day=day, month=month, revision=1,
                       key='stale-fx-limited-policy')
    assert edited['revision'] == 2
    with pytest.raises(HTTPException) as error:
        claim(family_id, child['id'])
    assert error.value.status_code == 503
    with DB() as db:
        blocker = generation_availability(db, db.get(Family, family_id), 'unit', child_id=child['id'])
        assert blocker and blocker['code'] == 'not_configured'
        assert db.scalar(select(func.count()).select_from(Usage)) == 0


def test_unlimited_child_limits_keep_unknown_hold_and_global_cap_with_stale_fx(api, household, operator):
    parent, child = household
    family_id = parent['families'][0]['id']
    configure(api, household, operator, day=None, month=None)
    with DB.begin() as db:
        config = db.get(ProviderConfig, 1)
        config.provider = 'openai'
        config.global_limit_micros = config.reserve_micros
        config.routing_policy = {**config.routing_policy, 'budget': {**config.routing_policy['budget'],
            'fx_checked_at': int(now()) - 32 * 86400}}
    edited = configure(api, household, operator, day=None, month=None, revision=1,
                       key='stale-fx-unlimited-policy')
    assert edited['day']['state'] == edited['month']['state'] == 'unlimited'
    ident = claim(family_id, child['id'])
    with DB.begin() as db:
        settle(db, db.get(Usage, ident), failed=True)
    with DB() as db:
        usage = db.get(Usage, ident)
        balance = db.get(UsageCostBalance, ident)
        assert usage.cost_micros is None and usage.status == 'failed_unknown'
        assert balance.held_eur_micros == 100_000 and balance.accounted_eur_micros == 108_000
        bucket = db.get(UsageBucket, usage.bucket_ids[0])
        assert bucket.encumbered_micros == 100_000 and bucket.unknown_calls == 1
    with pytest.raises(HTTPException) as error:
        claim(family_id, child['id'])
    assert error.value.status_code == 429
