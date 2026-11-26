"""Artificial arithmetic on mixed text pages; no provider inference or real material."""
from types import SimpleNamespace

from schulpilot.source_lineage import false_equality, learning_source


def test_embedded_wrong_calculations_are_detected():
    examples = [
        'Berechne. 3/10 mal 5/12 = 30/58',
        'Berechne: 3/10 mal 5/12 = 30/58',
        'Berechne. 1/2 mal 2/3 = 1/3  3/10 mal 5/12 = 30/58',
        'Aufgabe: 1/2 + 1/4 = 2/4.',
        'Rechnung: 2/3 · 3/4 = 6/12 = 1/3',
    ]
    for text in examples:
        assert false_equality(text, include_embedded=True), text


def test_unknown_or_correct_examples_are_not_invented_as_wrong():
    examples = [
        'Berechne. 1/2 mal 2/3 = 1/3  3/10 mal 5/12 = 1/8',
        'Bestimme x: x + 2 = 3',
        '1 m = 100 cm',
        'Anzahl: 1.000 = 1000',
        'Anzahl: 1,000 = 1000',
        'Zwei Aufgaben: 1==2 und 2**100000=1',
        'Temperatur: 3 = 4 Grad Celsius',
        'x-2=1',
        '12:3 = 4',
        '2^3 = 8',
        'Aufgabe: 1 2/3 = 5/3',
        'Aufgabe: 4/5 mal 5/8 = 4 mal 5/5 mal 8 = 1/2',
        'CO=Co',
        '1/0=0',
        ('1+' * 5000) + '=',
    ]
    for text in examples:
        assert not false_equality(text, include_embedded=True), text


def test_original_preserved_but_unsafe_block_not_in_learning_projection():
    blocks = [
        {'kind': 'paragraph', 'text': 'Ein Bruch beschreibt Teile eines Ganzen.'},
        {'kind': 'paragraph', 'text': 'Berechne. 3/10 mal 5/12 = 30/58'},
    ]
    original = '\n\n'.join(block['text'] for block in blocks)
    material = SimpleNamespace(id='a' * 32, revision=1, purpose='notebook', confirmed=True,
                               legibility='readable', uncertainties=[], content=original,
                               source_blocks=blocks)
    result = learning_source(None, material)
    assert result['content'] == blocks[0]['text']
    assert [item['reason'] for item in result['exclusions']] == ['false_equality']
    assert material.content == original and material.source_blocks == blocks


def test_new_receipt_protects_original_but_old_merge_stays_reproducible():
    from schulpilot.material_review import _protected_readings

    original = {'kind': 'paragraph', 'text': '1) Berechne. 3/10 mal 5/12 = 30/58'}
    second = {'kind': 'paragraph', 'text': '1) Berechne. 3/10 mal 5/12 = 1/8'}
    data = {'source_blocks': [second], 'content': '', 'legibility': 'readable', 'uncertainties': []}
    old = SimpleNamespace(snapshot={'source_blocks': [original]}, receipt={'policy_version': 'literal-safety-3'})
    new = SimpleNamespace(snapshot={'source_blocks': [original]}, receipt={'policy_version': 'literal-safety-4'})
    historical = _protected_readings(data, old)
    protected = _protected_readings(data, new)
    assert historical['source_blocks'][0]['text'] == second['text']
    assert historical['legibility'] == 'readable'
    assert protected['source_blocks'][0]['text'] == original['text']
    assert protected['source_blocks'][0]['reading_uncertainties']
    assert protected['legibility'] == 'partial'


def test_old_plan_fingerprint_is_kept_only_when_eligible_content_is_unchanged(monkeypatch):
    import hashlib
    import json

    from schulpilot import source_lineage, study_path

    block = {'kind': 'paragraph', 'text': 'Berechne. 3/10 mal 5/12 = 30/58'}
    material = SimpleNamespace(id='b' * 32, revision=1, purpose='notebook', confirmed=True,
                               legibility='readable', uncertainties=[], content=block['text'],
                               source_blocks=[block])
    current = source_lineage.false_equality
    with monkeypatch.context() as patch:
        patch.setattr(source_lineage, 'false_equality',
                      lambda text, **kwargs: current(text, include_embedded=False))
        old_projection = source_lineage.learning_source(None, material)
        old_projection['policy_version'] = 'literal-safety-3'
        old_hash = hashlib.sha256(json.dumps([(material.id, material.revision, old_projection)],
                                             sort_keys=True).encode()).hexdigest()
    assert old_hash not in study_path.compatible_fingerprints([material], None)
    assert source_lineage.learning_source(None, material)['content'] == ''
