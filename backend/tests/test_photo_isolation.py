import io
import subprocess

import pytest
from fastapi import HTTPException
from PIL import Image, ImageFilter, ImageOps, ImageStat
from schulpilot import main
from schulpilot.db import DB, Material
from schulpilot.photo_isolation import normalize_photo
from sqlalchemy import func, select
from test_school_day import allow_synthetic_test_transport


def original_normalize(raw):
    with Image.open(io.BytesIO(raw)) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
        image.thumbnail((3200, 3200))
        warnings = []
        if min(image.size) < 600:
            warnings.append('Das Foto ist klein. Bitte prüfen, ob der Text gut lesbar ist.')
        probe = image.copy()
        probe.thumbnail((320, 320))
        probe = probe.convert('L').filter(ImageFilter.FIND_EDGES)
        if min(probe.size) > 4 and ImageStat.Stat(probe.crop((2, 2, probe.width - 2, probe.height - 2))).var[0] < 70:
            warnings.append('Das Foto enthält wenig erkennbare Details und könnte unscharf oder leer sein. Bitte prüfen.')
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=95)
        return output.getvalue(), warnings


def fixture(fmt, *, orientation=1):
    image = Image.new('RGBA' if fmt == 'PNG' else 'RGB', (733, 501), 'green')
    for x in range(0, image.width, 17):
        for y in range(0, image.height, 19):
            image.putpixel((x, y), (x % 255, y % 255, 128, 70) if fmt == 'PNG' else (x % 255, y % 255, 128))
    output = io.BytesIO()
    exif = Image.Exif()
    exif[274] = orientation
    exif[270] = 'SYNTHETIC PRIVATE METADATA'
    image.save(output, format=fmt, exif=exif)
    return output.getvalue()


@pytest.mark.parametrize('fmt,orientation', [('JPEG', 1), ('JPEG', 3), ('JPEG', 6), ('PNG', 1), ('WEBP', 1)])
def test_photo_decoder_preserves_original_pixels_orientation_and_warning(fmt, orientation):
    raw = fixture(fmt, orientation=orientation)
    expected, warnings = original_normalize(raw)
    actual, geometry, actual_warnings = normalize_photo(raw)
    assert actual.getvalue() == expected
    assert actual_warnings == warnings
    assert geometry['input_width'] == 733 and geometry['input_height'] == 501
    assert geometry['output_bytes'] == len(expected)
    with Image.open(io.BytesIO(expected)) as result:
        assert result.size == ((501, 733) if orientation == 6 else (733, 501))
        assert not result.getexif()


def test_decompression_bomb_is_rejected_by_decoder():
    image = Image.new('RGB', (4001, 4000), 'white')
    output = io.BytesIO()
    image.save(output, format='PNG')
    with pytest.raises(HTTPException) as exc:
        normalize_photo(output.getvalue())
    assert exc.value.status_code == 422


def test_invalid_photo_and_decoder_failure_are_safe(monkeypatch):
    with pytest.raises(HTTPException) as exc:
        normalize_photo(b'not an image')
    assert exc.value.status_code == 422
    def timed_out(*args, **kwargs):
        assert kwargs['env'] == {'LANG': 'C.UTF-8', 'PATH': '/usr/bin:/bin'}
        assert kwargs['close_fds'] is True
        raise subprocess.TimeoutExpired('synthetic-command', 30)
    monkeypatch.setattr(subprocess, 'run', timed_out)
    with pytest.raises(HTTPException) as exc:
        normalize_photo(b'synthetic')
    assert exc.value.status_code == 503 and exc.value.headers['Retry-After'] == '2'


def test_busy_intake_preserves_upload_and_idempotent_retry(api, household):
    allow_synthetic_test_transport()
    _, child = household
    path = f"/api/children/{child['id']}/materials"
    headers = {'Idempotency-Key': 'photo-capacity-test-0001'}
    image = fixture('JPEG')
    assert main._PHOTO_REQUEST_SLOT.acquire(blocking=False)
    try:
        refused = api.post(path, files={'file': ('test.jpg', image, 'image/jpeg')}, headers=headers)
        assert refused.status_code == 503 and refused.headers['Retry-After'] == '2'
        with DB() as db:
            assert db.scalar(select(func.count()).select_from(Material)) == 0
    finally:
        main._PHOTO_REQUEST_SLOT.release()
    first = api.post(path, files={'file': ('test.jpg', image, 'image/jpeg')}, headers=headers)
    second = api.post(path, files={'file': ('test.jpg', image, 'image/jpeg')}, headers=headers)
    assert first.status_code == second.status_code == 201
    assert first.json()['id'] == second.json()['id']
    with DB() as db:
        assert db.scalar(select(func.count()).select_from(Material)) == 1
