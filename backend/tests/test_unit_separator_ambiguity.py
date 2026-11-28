"""Synthetic unit examples: do not choose a decimal/thousands meaning."""
from types import SimpleNamespace

import pytest
from schulpilot.material_review import _protected_readings
from schulpilot.source_lineage import learning_source


def material(text):
    return SimpleNamespace(id='a' * 32, revision=1, purpose='notebook', confirmed=True,
                           legibility='readable', uncertainties=[], content=text,
                           source_blocks=[{'kind': 'paragraph', 'text': text}])


@pytest.mark.parametrize('text', [
    '1.000 m = 1 km', '1,000 m = 1000 mm', '1 km = 1.000 m',
    '2.000 g = 2 kg', '1.000 s = 1.000 s',
])
def test_ambiguous_complete_unit_equation_does_not_become_safe_learning(text):
    item = material(text)
    value = learning_source(None, item)
    assert value['content'] == ''
    assert [row['reason'] for row in value['exclusions']] == ['ambiguous_numeric']
    assert item.content == text


@pytest.mark.parametrize('text', [
    '1 km = 1000 m', '0,125 h = 7,5 min', '1.000 Euro = 1.000 Euro',
    '1.000 m = 1 kg', 'Strecke: 1.000 m = 1 km', '1.000 m + x = 1 km',
])
def test_unsupported_or_unambiguous_units_are_not_inferred(text):
    assert learning_source(None, material(text))['content'] == text


def test_countercheck_keeps_older_policy_reproducible():
    first = {'kind': 'paragraph', 'text': '1.000 m = 1 km'}
    second = {'kind': 'paragraph', 'text': '1000 m = 1 km'}
    data = {'source_blocks': [second], 'content': '', 'legibility': 'readable', 'uncertainties': []}
    old = SimpleNamespace(snapshot={'source_blocks': [first]}, receipt={'policy_version': 'literal-safety-9'})
    new = SimpleNamespace(snapshot={'source_blocks': [first]}, receipt={'policy_version': 'literal-safety-10'})
    assert _protected_readings(data, old)['source_blocks'][0]['text'] == second['text']
    result = _protected_readings(data, new)
    assert any(block['text'] == first['text'] for block in result['source_blocks'])
    assert result['legibility'] == 'partial'


def test_unit_ambiguity_does_not_reuse_previously_unsafe_plan(monkeypatch):
    from schulpilot import source_lineage, study_path

    item = material('1.000 m = 1 km')
    with monkeypatch.context() as patch:
        patch.setattr(source_lineage, 'ambiguous_unit_conversion', lambda _text: False)
        previous = study_path.fingerprint([item])
    assert previous not in study_path.compatible_fingerprints([item], None)
