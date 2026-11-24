"""DACH source inventory is explicitly not a complete or selectable curriculum."""
import json

import pytest
from schulpilot import dach_scope
from schulpilot.db import DB, Activity, Job, Usage
from sqlalchemy import func, select


def test_dach_scope_is_authenticated_read_only_and_preserves_legacy_states(api, household):
    # The normal catalogue keeps the existing 16 German state contract.
    before = api.get('/api/curriculum/catalog').json()
    with DB() as db:
        counts = [db.scalar(select(func.count()).select_from(model)) for model in (Activity, Job, Usage)]
    response = api.get('/api/curriculum/dach-scope')
    assert response.status_code == 200
    result = response.json()
    assert result['complete'] is False
    countries = {country['code']: country for country in result['countries']}
    assert set(countries) == {'DE', 'AT', 'CH'}
    assert [len(countries[code]['regions']) for code in ('DE', 'AT', 'CH')] == [16, 9, 26]
    all_regions = [region['code'] for country in countries.values() for region in country['regions']]
    assert len(all_regions) == len(set(all_regions)) == 51
    assert countries['DE']['profile_supported'] is True
    assert all(countries[code]['profile_supported'] is False
               and countries[code]['curriculum_coverage'] == 'source_index_only' for code in ('AT', 'CH'))
    assert result['higher_education']['profile_supported'] is False
    assert len(before['states']) == 16
    assert api.get('/api/curriculum/catalog').json()['states'] == before['states']
    with DB() as db:
        assert counts == [db.scalar(select(func.count()).select_from(model)) for model in (Activity, Job, Usage)]


def test_invalid_or_duplicate_region_data_is_rejected(tmp_path, monkeypatch):
    data = json.loads(dach_scope.REFERENCE.read_text())
    data['countries'][1]['regions'][1]['code'] = data['countries'][1]['regions'][0]['code']
    bad = tmp_path / 'invalid.json'
    bad.write_text(json.dumps(data))
    monkeypatch.setattr(dach_scope, 'REFERENCE', bad)
    with pytest.raises(ValueError):
        dach_scope.scope()


def test_unknown_region_code_cannot_replace_a_canton(tmp_path, monkeypatch):
    data = json.loads(dach_scope.REFERENCE.read_text())
    data['countries'][1]['regions'][0]['code'] = 'CH-ZZ'
    bad = tmp_path / 'unknown.json'
    bad.write_text(json.dumps(data))
    monkeypatch.setattr(dach_scope, 'REFERENCE', bad)
    with pytest.raises(ValueError):
        dach_scope.scope()
