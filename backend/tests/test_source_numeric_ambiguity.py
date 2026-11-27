"""Synthetic literals: separator ambiguity is not a proven arithmetic error."""
from types import SimpleNamespace

import pytest
from schulpilot.material_review import _protected_readings
from schulpilot.source_lineage import learning_source


def _material(text):
    return SimpleNamespace(id='a' * 32, revision=1, purpose='notebook', confirmed=True,
                           legibility='readable', uncertainties=[], content=text,
                           source_blocks=[{'kind': 'paragraph', 'text': text}])


@pytest.mark.parametrize('text', ['1.000 = 1000', '1,000 = 1', '2.345 = 2.345'])
def test_separator_ambiguity_is_quarantined_without_asserting_error(text):
    material = _material(text)
    projected = learning_source(None, material)
    assert projected['content'] == ''
    assert [row['reason'] for row in projected['exclusions']] == ['ambiguous_numeric']
    assert material.content == text
    assert material.source_blocks[0]['text'] == text


@pytest.mark.parametrize('text', ['2,5 = 2.5', '1000 = 1000', '3/4 = 0,75', '0,125 = 1/8'])
def test_unambiguous_correct_arithmetic_remains_available(text):
    assert learning_source(None, _material(text))['content'] == text


def test_obvious_error_is_still_excluded_as_error():
    assert learning_source(None, _material('1/2 = 2/3'))['exclusions'][0]['reason'] == 'false_equality'


def test_new_countercheck_protects_uncertain_original_but_old_receipt_is_reproducible():
    first = {'kind': 'paragraph', 'text': '1,000 = 1'}
    second = {'kind': 'paragraph', 'text': '1 = 1'}
    data = {'source_blocks': [second], 'content': '', 'legibility': 'readable', 'uncertainties': []}
    old = SimpleNamespace(snapshot={'source_blocks': [first]}, receipt={'policy_version': 'literal-safety-7'})
    new = SimpleNamespace(snapshot={'source_blocks': [first]}, receipt={'policy_version': 'literal-safety-8'})
    assert _protected_readings(data, old)['source_blocks'][0]['text'] == second['text']
    result = _protected_readings(data, new)
    assert any(block['text'] == first['text'] for block in result['source_blocks'])
    assert result['legibility'] == 'partial'


def test_changed_source_exclusion_invalidates_the_old_plan_fingerprint(monkeypatch):
    from schulpilot import source_lineage, study_path

    material = _material('1,000 = 1')
    with monkeypatch.context() as patch:
        patch.setattr(source_lineage, 'ambiguous_numeric_equality', lambda _text: False)
        previous = study_path.fingerprint([material])
    assert previous not in study_path.compatible_fingerprints([material], None)


def test_unchanged_source_keeps_its_plan_fingerprint(monkeypatch):
    from schulpilot import source_lineage, study_path

    material = _material('1/2 = 2/4')
    with monkeypatch.context() as patch:
        patch.setattr(source_lineage, 'ambiguous_numeric_equality', lambda _text: False)
        previous = study_path.fingerprint([material])
    assert previous in study_path.compatible_fingerprints([material], None)
