"""Rotated artificial photos: bounding-box overlap cannot erase literal blocks."""
from types import SimpleNamespace

import pytest

from schulpilot.material_review import _protected_readings


def block(text, role='student_work', region=None, annotations=None):
    return {'kind': 'paragraph', 'text': text, 'literal_role': role,
            'image_region': region or {'left': 100, 'top': 100, 'right': 800, 'bottom': 800},
            'annotations': annotations or []}


def test_overlapping_changed_and_exact_protected_blocks_all_survive_in_order():
    old = [block('Titel', 'unknown'), block('1) 2/3 Minute = 60 40 Sekunden'),
           block('2) 1 km = 1000 m'), block('3) 27 t = 27000 kg'),
           block('4) Drei von sieben: 3/7'), block('5) 7/4 = 1 3/4')]
    new = [block('Titel', 'unknown'), block('1) 2/3 Minute = 60 Sekunden\n40', 'unknown'),
           block('2) 1 km = 1000 m', 'unknown'), block('3) 27 t = 27000 kg', 'unknown'),
           block('4) Drei von sieben: 3/7', 'unknown'), block('5) 7/4 =\n1 3/4', 'unknown')]
    result = _protected_readings({'source_blocks': new, 'content': '', 'legibility': 'readable', 'uncertainties': []},
                                SimpleNamespace(snapshot={'source_blocks': old}))
    assert [b['text'] for b in result['source_blocks']] == [b['text'] for b in old]
    assert result['legibility'] == 'partial' and result['uncertainties']
    assert result['source_blocks'][1]['reading_uncertainties']
    assert not result['source_blocks'][3].get('reading_uncertainties')


def test_normal_ink_does_not_freeze_an_uncorrected_first_reading():
    old = block('Der Nemer bezeichnet die Teile.', 'unknown', annotations=[{'kind': 'ink', 'quote': 'Nemer', 'color': 'blue'}])
    corrected = block('Der Nenner bezeichnet die Teile.', 'unknown')
    result = _protected_readings({'source_blocks': [corrected], 'content': '', 'legibility': 'readable', 'uncertainties': []},
                                SimpleNamespace(snapshot={'source_blocks': [old]}))
    assert result['content'] == corrected['text']


def _correction(region):
    return {'kind': 'correction', 'quote': '11/15', 'color': 'red', 'image_region': region}


def test_disjoint_correction_locations_remain_visible_as_uncertainty():
    first = _correction({'left': 624, 'top': 585, 'right': 661, 'bottom': 625})
    second = _correction({'left': 623, 'top': 654, 'right': 662, 'bottom': 734})
    original = block('2/5 + 1/3 = 11/15', 'unknown', annotations=[first])
    checked = block('2/5 + 1/3 = 11/15', 'unknown', annotations=[second])
    result = _protected_readings({'source_blocks': [checked], 'content': '', 'legibility': 'readable', 'uncertainties': []},
                                SimpleNamespace(snapshot={'source_blocks': [original]}))
    assert result['content'] == original['text']
    assert result['legibility'] == 'partial'
    assert result['source_blocks'][0]['annotations'] == [first, second]
    assert 'Bildbereiche einer Korrektur unterscheiden' in result['source_blocks'][0]['reading_uncertainties'][0]


def test_overlapping_correction_locations_are_not_flagged_as_a_conflict():
    first = _correction({'left': 624, 'top': 654, 'right': 661, 'bottom': 734})
    second = _correction({'left': 620, 'top': 660, 'right': 665, 'bottom': 740})
    original = block('2/5 + 1/3 = 11/15', 'unknown', annotations=[first])
    checked = block('2/5 + 1/3 = 11/15', 'unknown', annotations=[second])
    result = _protected_readings({'source_blocks': [checked], 'content': '', 'legibility': 'readable', 'uncertainties': []},
                                SimpleNamespace(snapshot={'source_blocks': [original]}))
    assert result['legibility'] == 'readable'
    assert not result['source_blocks'][0].get('reading_uncertainties')


def test_repeated_identical_corrections_are_not_arbitrarily_paired():
    first = _correction({'left': 100, 'top': 100, 'right': 140, 'bottom': 140})
    other = _correction({'left': 600, 'top': 600, 'right': 640, 'bottom': 640})
    original = block('11/15 und 11/15', 'unknown', annotations=[first, other])
    checked = block('11/15 und 11/15', 'unknown', annotations=[other, first])
    result = _protected_readings({'source_blocks': [checked], 'content': '', 'legibility': 'readable', 'uncertainties': []},
                                SimpleNamespace(snapshot={'source_blocks': [original]}))
    assert result['legibility'] == 'readable'
    assert not result['source_blocks'][0].get('reading_uncertainties')


def test_changed_repeated_corrections_stay_uncertain_without_guessing_pairs():
    first = _correction({'left': 100, 'top': 100, 'right': 140, 'bottom': 140})
    other = _correction({'left': 600, 'top': 600, 'right': 640, 'bottom': 640})
    shifted = _correction({'left': 610, 'top': 610, 'right': 650, 'bottom': 650})
    original = block('11/15 und 11/15', 'unknown', annotations=[first, other])
    checked = block('11/15 und 11/15', 'unknown', annotations=[first, shifted])
    result = _protected_readings({'source_blocks': [checked], 'content': '', 'legibility': 'readable', 'uncertainties': []},
                                SimpleNamespace(snapshot={'source_blocks': [original]}))
    assert result['legibility'] == 'partial'
    assert result['source_blocks'][0]['reading_uncertainties']
    assert result['source_blocks'][0]['annotations'] == [first, other, shifted]


def test_uncertain_location_stays_ineligible_but_unrelated_text_remains_usable():
    from schulpilot.source_lineage import learning_source
    from schulpilot.subject_content import SourceBlock

    first = _correction({'left': 624, 'top': 585, 'right': 661, 'bottom': 625})
    second = _correction({'left': 623, 'top': 654, 'right': 662, 'bottom': 734})
    safe = block('Ein Bruch beschreibt Teile eines Ganzen.', 'unknown')
    original = block('2/5 + 1/3 = 11/15', 'unknown', annotations=[first])
    checked = block('2/5 + 1/3 = 11/15', 'unknown', annotations=[second])
    result = _protected_readings({'source_blocks': [safe, checked], 'content': '', 'legibility': 'readable', 'uncertainties': []},
                                SimpleNamespace(snapshot={'source_blocks': [safe, original]}))
    for value in result['source_blocks']:
        SourceBlock.model_validate(value)
    material = SimpleNamespace(id='a' * 32, revision=1, purpose='notebook', confirmed=True,
                               legibility=result['legibility'], uncertainties=result['uncertainties'],
                               content=result['content'], source_blocks=result['source_blocks'])
    source = learning_source(None, material)
    assert source['content'] == safe['text']
    assert [item['reason'] for item in source['exclusions']] == ['reading_uncertain']


@pytest.mark.parametrize('count', [1, 30])
def test_full_whitespace_page_notices_cannot_hide_local_conflict_or_break_validation(count):
    from schulpilot.extraction import validate_material
    from schulpilot.source_lineage import learning_source

    first = _correction({'left': 10, 'top': 10, 'right': 20, 'bottom': 20})
    second = _correction({'left': 50, 'top': 50, 'right': 60, 'bottom': 60})
    safe = block('Ein sicherer Satz.', 'unknown')
    old = block('Ergebnis 11/15', 'unknown', annotations=[first])
    new = block('Ergebnis 11/15', 'unknown', annotations=[second])
    data = {'subject': 'Mathematik', 'topic': 'Brüche', 'homework': [],
            'source_blocks': [safe, new], 'content': '', 'legibility': 'readable',
            'uncertainties': [' ' * n for n in range(1, count + 1)]}
    result = validate_material(_protected_readings(data, SimpleNamespace(snapshot={'source_blocks': [safe, old]})))
    assert result['legibility'] == 'partial' and len(result['uncertainties']) <= 30
    assert any(notice.strip() for notice in result['uncertainties'])
    assert any(not notice.strip() for notice in result['uncertainties'])
    material = SimpleNamespace(id='a' * 32, revision=1, purpose='notebook', confirmed=True,
                               legibility=result['legibility'], uncertainties=result['uncertainties'],
                               content=result['content'], source_blocks=result['source_blocks'])
    assert learning_source(None, material)['content'] == ''


def test_full_block_warning_list_still_surfaces_conflicting_correction():
    from schulpilot.extraction import validate_material
    from schulpilot.source_lineage import learning_source

    first = _correction({'left': 10, 'top': 10, 'right': 20, 'bottom': 20})
    second = _correction({'left': 50, 'top': 50, 'right': 60, 'bottom': 60})
    safe = block('Ein sicherer Satz.', 'unknown')
    old = block('Ergebnis 11/15', 'unknown', annotations=[first])
    old['reading_uncertainties'] = [f'Alte Unsicherheit {n}' for n in range(8)]
    new = block('Ergebnis 11/15', 'unknown', annotations=[second])
    data = {'subject': 'Mathematik', 'topic': 'Brüche', 'homework': [],
            'source_blocks': [safe, new], 'content': '', 'legibility': 'readable', 'uncertainties': []}
    result = validate_material(_protected_readings(data, SimpleNamespace(snapshot={'source_blocks': [safe, old]})))
    assert result['source_blocks'][1]['reading_uncertainties'] == old['reading_uncertainties']
    assert any('Bildbereiche einer Korrektur unterscheiden' in notice for notice in result['uncertainties'])
    material = SimpleNamespace(id='a' * 32, revision=1, purpose='notebook', confirmed=True,
                               legibility=result['legibility'], uncertainties=result['uncertainties'],
                               content=result['content'], source_blocks=result['source_blocks'])
    assert learning_source(None, material)['content'] == ''  # page-wide overflow warning


def test_full_page_and_block_limits_keep_a_page_wide_overflow_even_if_conflict_text_is_local_elsewhere():
    from schulpilot.extraction import validate_material
    from schulpilot.source_lineage import learning_source

    first = _correction({'left': 10, 'top': 10, 'right': 20, 'bottom': 20})
    second = _correction({'left': 50, 'top': 50, 'right': 60, 'bottom': 60})
    safe = block('Ein sicherer Satz.', 'unknown')
    old = block('Ergebnis 11/15', 'unknown', annotations=[first])
    old['reading_uncertainties'] = [f'Alte Unsicherheit {n}' for n in range(8)]
    new = block('Ergebnis 11/15', 'unknown', annotations=[second])
    helpers = []
    for i in range(3):
        item = block(f'Weiterer Abschnitt {i}', 'unknown')
        item['reading_uncertainties'] = [f'Andere Unsicherheit {i}-{j}' for j in range(8)]
        helpers.append(item)
    conflict = 'Die Bildbereiche einer Korrektur unterscheiden sich. Bitte die Markierung im ganzen Foto prüfen.'
    helpers[0]['reading_uncertainties'][0] = conflict
    local = [*old['reading_uncertainties'], *(notice for item in helpers for notice in item['reading_uncertainties'])]
    page = [*local[:29], 'Bisher nicht zuordenbare Seitenwarnung']
    data = {'subject': 'Mathematik', 'topic': 'Brüche', 'homework': [],
            'source_blocks': [safe, new, *helpers], 'content': '', 'legibility': 'readable', 'uncertainties': page}
    result = validate_material(_protected_readings(data, SimpleNamespace(snapshot={'source_blocks': [safe, old, *helpers]})))
    assert len(result['uncertainties']) <= 30
    all_local = {notice for item in result['source_blocks'] for notice in item.get('reading_uncertainties', [])}
    assert any('Weitere Hinweise konnten nicht einzeln' in notice and notice not in all_local
               for notice in result['uncertainties'])
    material = SimpleNamespace(id='a' * 32, revision=1, purpose='notebook', confirmed=True,
                               legibility=result['legibility'], uncertainties=result['uncertainties'],
                               content=result['content'], source_blocks=result['source_blocks'])
    assert learning_source(None, material)['content'] == ''
