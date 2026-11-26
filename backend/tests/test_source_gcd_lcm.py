"""Bounded literal checks: originals remain untouched and unknown syntax stays unknown."""

from types import SimpleNamespace

import pytest
from schulpilot.material_review import _protected_readings
from schulpilot.source_lineage import false_gcd_lcm, learning_source


@pytest.mark.parametrize('text', [
    'kgV(20,80)=160', 'kgV(8,12)=96', 'ggT(24,36)=6',
    'KGV ( 8 ; 12 ) = 96.', 'Überschrift\nkgV(8,12)=96\nWeitere Zeile',
    'kgV(8,12)=96\n' + 'x' * 10000 + ' = 1',
])
def test_false_complete_integer_statements(text):
    assert false_gcd_lcm(text)


@pytest.mark.parametrize('text', [
    'kgV(20,80)=80', 'kgV(8,12)=24', 'ggT(24,36)=12',
    'kgV(0,12)=1', 'ggT(0,0)=2', 'kgV(-8,12)=96', 'kgV(8,12)=96?',
    'Ist kgV(8,12)=96 richtig?', 'kgV(8,12)=96 ist falsch',
    'kgV(8,12)=96+1', 'kgV(8,12)=9/6', 'kgV(a,12)=96',
    'kgV(1,000,12)=96', 'kgV(10000000,12)=96',
])
def test_valid_or_ambiguous_syntax_is_not_inferred(text):
    assert not false_gcd_lcm(text)


def test_source_preserves_original_and_quarantines_only_the_false_block():
    blocks = [{'kind': 'paragraph', 'text': 'Vielfache sind Ergebnisse des Malnehmens.'},
              {'kind': 'paragraph', 'text': 'kgV(20,80)=160'}]
    original = '\n\n'.join(block['text'] for block in blocks)
    material = SimpleNamespace(id='a' * 32, revision=1, purpose='notebook', confirmed=True,
                               legibility='readable', uncertainties=[], content=original, source_blocks=blocks)
    safe = learning_source(None, material)
    assert safe['policy_version'] == 'literal-safety-7'
    assert safe['content'] == blocks[0]['text']
    assert [row['reason'] for row in safe['exclusions']] == ['false_gcd_lcm']
    assert material.content == original and material.source_blocks == blocks


def test_countercheck_uses_recorded_policy_and_preserves_the_original():
    first = {'kind': 'paragraph', 'text': 'kgV(8,12)=96'}
    second = {'kind': 'paragraph', 'text': 'kgV(8,12)=24'}
    data = {'source_blocks': [second], 'content': '', 'legibility': 'readable', 'uncertainties': []}
    old = SimpleNamespace(snapshot={'source_blocks': [first]}, receipt={'policy_version': 'literal-safety-6'})
    new = SimpleNamespace(snapshot={'source_blocks': [first]}, receipt={'policy_version': 'literal-safety-7'})
    assert _protected_readings(data, old)['source_blocks'][0]['text'] == second['text']
    protected = _protected_readings(data, new)
    assert any(block['text'] == first['text'] for block in protected['source_blocks'])
    assert all(block['reading_uncertainties'] for block in protected['source_blocks'])
    assert protected['legibility'] == 'partial'


@pytest.mark.parametrize('statement,compatible', [('kgV(8,12)=96', False), ('kgV(8,12)=24', True)])
def test_existing_learning_path_only_survives_unchanged_safe_projection(monkeypatch, statement, compatible):
    from schulpilot import source_lineage, study_path

    block = {'kind': 'paragraph', 'text': statement}
    material = SimpleNamespace(id='b' * 32, revision=1, purpose='notebook', confirmed=True,
                               legibility='readable', uncertainties=[], content=statement, source_blocks=[block])
    with monkeypatch.context() as patch:
        patch.setattr(source_lineage, 'false_gcd_lcm', lambda _text: False)
        old_fingerprint = study_path.fingerprint([material])
    assert (old_fingerprint in study_path.compatible_fingerprints([material], None)) is compatible
