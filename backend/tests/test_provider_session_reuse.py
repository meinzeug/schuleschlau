"""Provider approval reads remain fresh without a nested database session."""
import json

import pytest
from schulpilot.config import runtime_settings
from schulpilot.db import DB, Child, Installation, ProviderConfig
from schulpilot.providers import ProviderError, external_allowed
from schulpilot.security import encrypt
from test_school_day import allow_synthetic_test_transport


def test_provider_approval_does_not_open_a_second_session(household, monkeypatch):
    from schulpilot import db as database

    allow_synthetic_test_transport()
    with DB() as reader:
        config = reader.get(ProviderConfig, 1)

        def forbidden_nested_session(*_args, **_kwargs):
            raise AssertionError('Provider approval must reuse the current session')

        monkeypatch.setattr(database, 'DB', forbidden_nested_session)
        external_allowed(config, db=reader)


@pytest.mark.parametrize('revocation', [
    {'real_data_approved': False, 'privacy_evidence': 'Synthetic initial evidence'},
    {'real_data_approved': True, 'privacy_evidence': ''},
])
def test_existing_session_observes_committed_privacy_revocation_without_flushing_dirty_child(household, revocation):
    allow_synthetic_test_transport()
    _, child = household
    initial = {'real_data_approved': True, 'privacy_evidence': 'Synthetic initial evidence',
               'synthetic_ai_daily_limit': 40}
    with DB.begin() as writer:
        writer.get(Installation, 1).encrypted_settings = encrypt(json.dumps(initial))
    with DB() as reader:
        cached_installation = reader.get(Installation, 1)
        original_ciphertext = cached_installation.encrypted_settings
        local_child = reader.get(Child, child['id'])
        original_grade = local_child.grade
        config = reader.get(ProviderConfig, 1)
        external_allowed(config, db=reader)
        local_child.grade = original_grade + 1
        with DB.begin() as writer:
            writer.get(Installation, 1).encrypted_settings = encrypt(json.dumps({**initial, **revocation,
                                                                                'synthetic_ai_daily_limit': 9}))
        assert cached_installation.encrypted_settings == original_ciphertext  # intentionally stale ORM object
        with pytest.raises(ProviderError, match='Datenschutz'):
            external_allowed(config, db=reader)
        assert runtime_settings(reader, fresh=True).synthetic_ai_daily_limit == 9
        assert reader.is_modified(local_child)
        with DB() as observer:
            assert observer.get(Child, child['id']).grade == original_grade
        reader.rollback()
