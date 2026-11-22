"""Public source inventory; it does not invent learner profiles or curricula."""
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends

from .security import authenticated

router = APIRouter(tags=['Bildungssysteme'])
REFERENCE = Path(__file__).with_name('reference') / 'dach-regions-v1.json'
EXPECTED_CODES = {
    'AT': {f'AT-{number}' for number in range(1, 10)},
    'CH': {f'CH-{suffix}' for suffix in (
        'AG', 'AI', 'AR', 'BE', 'BL', 'BS', 'FR', 'GE', 'GL', 'GR', 'JU', 'LU', 'NE',
        'NW', 'OW', 'SG', 'SH', 'SO', 'SZ', 'TG', 'TI', 'UR', 'VD', 'VS', 'ZG', 'ZH')},
}
OFFICIAL_HOSTS = {
    'www.bmb.gv.at', 'www.statistik.at', 'www.edk.ch',
    'www.lehrplan21.ch', 'pianodistudio.edu.ti.ch',
}


def scope():
    # Import lazily to avoid a module cycle and reuse the established German
    # inventory without changing the legacy curriculum/profile API.
    from .curriculum import inventory

    data = json.loads(REFERENCE.read_text())
    if data.get('version') != 1:
        raise ValueError('Ungültige Version des Quellenverzeichnisses.')
    countries = data.get('countries')
    if not isinstance(countries, list) or {c.get('code') for c in countries} != {'AT', 'CH'} or len(countries) != 2:
        raise ValueError('Das Quellenverzeichnis benötigt Österreich und die Schweiz.')
    all_codes = set()
    for country in countries:
        code = country['code']
        regions = country.get('regions')
        urls = country.get('source_urls')
        if not isinstance(regions, list) or len(regions) != (9 if code == 'AT' else 26):
            raise ValueError('Die regionale Übersicht ist unvollständig.')
        if not isinstance(urls, list) or not urls or any(
            not isinstance(url, str) or urlsplit(url).scheme != 'https' or not urlsplit(url).hostname
            or urlsplit(url).username or urlsplit(url).password
            or urlsplit(url).hostname.lower() not in OFFICIAL_HOSTS for url in urls
        ):
            raise ValueError('Ein Quellenverweis ist ungültig.')
        for region in regions:
            pattern = r'AT-[1-9]' if code == 'AT' else r'CH-[A-Z]{2}'
            if (not isinstance(region, dict) or not isinstance(region.get('code'), str)
                    or not re.fullmatch(pattern, region['code']) or not isinstance(region.get('name'), str)
                    or not region['name'].strip() or region['code'] in all_codes):
                raise ValueError('Eine Region im Quellenverzeichnis ist ungültig.')
            all_codes.add(region['code'])
        if {region['code'] for region in regions} != EXPECTED_CODES[code]:
            raise ValueError('Das Quellenverzeichnis enthält unbekannte Regionen.')
    germany = inventory()
    result = [{'code': 'DE', 'name': 'Deutschland',
               'regions': [{'code': code, 'name': item['label']} for code, item in sorted(germany.items())],
               'source_urls': ['https://www.kmk.org/downloads-dokumente/rechtsvorschriften-/-lehrplaene/uebersicht-lehrplaene.html'],
               'profile_supported': True, 'curriculum_coverage': 'partial'}]
    for country in countries:
        result.append({**country, 'profile_supported': False, 'curriculum_coverage': 'source_index_only'})
    return {'version': 1, 'retrieved': data['retrieved'], 'countries': result,
            'higher_education': {'profile_supported': False, 'curriculum_coverage': 'not_integrated'},
            'complete': False, 'notice': data['notice']}


@router.get('/curriculum/dach-scope')
def dach_scope(p=Depends(authenticated)):
    """Read-only; no import, learner-data mutation, provider call or progress."""
    return scope()
