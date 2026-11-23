"""Source-scoped routing for the observed artificial two-page truncation."""

import pytest
from conftest import create_child
from schulpilot.db import DB, Family, Job, Material, ProviderConfig, uid
from schulpilot.model_routing import choose_tier, features_for
from schulpilot.providers import reserve
from test_model_routing import setup_policy


@pytest.mark.parametrize('case', ['supported', 'unconfirmed', 'foreign', 'other_subject', 'other_topic', 'unit'])
def test_only_own_confirmed_multi_page_fraction_packages_use_teaching_route(api, household, case):
    owner, child = household
    sibling = create_child(api, owner, username='fraction-route-sibling') if case == 'foreign' else None
    setup_policy(owner['families'][0]['id'])
    with DB.begin() as db:
        config = db.get(ProviderConfig, 1)
        config.routing_policy = {**config.routing_policy, 'economy_mode': True}
        pages = [Material(child_id=child['id'], title='Künstliche Seite', subject='Mathematik',
                          topic='Brüche', content='Brüche kürzen.', confirmed=True) for _ in range(2)]
        if case == 'unconfirmed':
            pages[1].confirmed = False
        if case == 'foreign':
            pages[1].child_id = sibling['id']
        if case == 'other_subject':
            pages[1].subject = 'Deutsch'
        if case == 'other_topic':
            for page in pages:
                page.topic, page.content = 'Zahlen', 'Addiere zwei Zahlen.'
        db.add_all(pages)
        db.flush()
        job = Job(child_id=child['id'], kind='unit' if case == 'unit' else 'package',
                  payload={'sources': [{'id': page.id, 'revision': page.revision} for page in pages]}, idempotency=uid())
        db.add(job)
        db.flush()
        facts = features_for(db, child['id'], job.id)
        assert facts['package_multi_fraction'] is (case == 'supported')
        if case == 'supported':
            assert choose_tier('package', facts, economy=True) == ('sol', 'multi_source_fraction_teaching')
            usage = reserve(db, db.get(Family, owner['families'][0]['id']), child['id'], job.id, 'package')
            assert usage.model == 'openai/gpt-6.1-sol'
            assert usage.route_snapshot['reason'] == 'multi_source_fraction_teaching'
        else:
            assert choose_tier('package', facts, economy=True)[1] != 'multi_source_fraction_teaching'
