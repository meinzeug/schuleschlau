"""Integrity of the reviewed synthetic references, not an OCR accuracy test."""
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2] / 'testdata' / 'ocr_synthetic'


def test_reviewed_synthetic_pages_and_reference_integrity():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    assert manifest['version'] == 1 and manifest['synthetic'] is True
    assert len(manifest['cases']) == 4
    names = set()
    for case in manifest['cases']:
        name = case['file']
        assert Path(name).name == name and name not in names
        names.add(name)
        path = ROOT / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == case['sha256']
        with Image.open(path) as img:
            img.verify()
        assert case['readable_in_order'] and case['visual_reference']
        assert isinstance(case['uncertainties'], list)
    assert len(manifest['cases'][1]['uncertainties']) == 1
