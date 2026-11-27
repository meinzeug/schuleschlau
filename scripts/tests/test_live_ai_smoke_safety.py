"""Safety boundaries for the explicitly synthetic live provider probe."""

import copy
import json
import sys

import pytest

from scripts import live_ai_smoke as smoke


@pytest.fixture
def metadata():
    return {
        'architecture': {'input_modalities': ['text', 'image']},
        'endpoints': [{
            'tag': 'example/us', 'status': 0,
            'pricing': {'prompt': '0', 'completion': '0', 'request': '0', 'discount': 0},
            'supported_parameters': ['response_format', 'structured_outputs', 'max_tokens'],
        }],
    }


def test_fixed_pages_are_checksum_bound(monkeypatch, tmp_path):
    for fixture in smoke.OCR_FIXTURES:
        data, mime = smoke.fixed_ocr_fixture(fixture)
        assert data and mime in {'image/png', 'image/jpeg'}
    filename, _, _ = smoke.OCR_FIXTURES['fraction']
    (tmp_path / filename).write_bytes(b'not the synthetic image')
    monkeypatch.setattr(smoke, 'OCR_ROOT', tmp_path)
    with pytest.raises(ValueError, match='checksum'):
        smoke.fixed_ocr_fixture('fraction')
    with pytest.raises(KeyError):
        smoke.fixed_ocr_fixture('../../private')


def test_routing_never_allows_collection_or_fallback():
    for strict in (False, True):
        options = smoke.provider_options('example/us', strict_privacy=strict)
        assert options['data_collection'] == 'deny'
        assert options['only'] == ['example/us']
        assert options['allow_fallbacks'] is False
        assert options['max_price'] == {'prompt': 0, 'completion': 0, 'request': 0}
        assert options['zdr'] is strict


def test_verified_free_image_endpoint_rejects_unsafe_metadata(metadata):
    assert smoke.verified_free_endpoint(metadata, 'example/us', image=True)['tag'] == 'example/us'
    for change in ('missing_price', 'paid_image', 'unavailable', 'no_image', 'missing_parameter', 'nan'):
        item = copy.deepcopy(metadata)
        endpoint = item['endpoints'][0]
        if change == 'missing_price':
            del endpoint['pricing']['prompt']
        elif change == 'paid_image':
            endpoint['pricing']['image'] = '0.01'
        elif change == 'unavailable':
            endpoint['status'] = -1
        elif change == 'no_image':
            item['architecture']['input_modalities'] = ['text']
        elif change == 'missing_parameter':
            endpoint['supported_parameters'].remove('structured_outputs')
        else:
            endpoint['pricing']['prompt'] = 'NaN'
        with pytest.raises(ValueError):
            smoke.verified_free_endpoint(item, 'example/us', image=True)
    with pytest.raises(ValueError):
        smoke.verified_free_endpoint(metadata, 'other/us', image=True)


def test_request_contains_only_approved_fixture_and_routing(monkeypatch, tmp_path, metadata, capsys):
    requests = []
    keyfile = tmp_path / 'key'
    keyfile.write_text('synthetic-test-key')

    class Response:
        status_code = 429

        def raise_for_status(self):
            pass

        def json(self):
            return {'data': metadata} if not requests else {'error': {'code': 429}}

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url):
            return Response()

        def post(self, url, **kwargs):
            requests.append(kwargs['json'])
            return Response()

    monkeypatch.setattr(smoke.httpx, 'Client', Client)
    monkeypatch.setattr(sys, 'argv', ['probe', '--model', 'example/model:free', '--upstream', 'example/us',
                                    '--key-file', str(keyfile), '--ocr-fixture', 'fraction'])
    with pytest.raises(SystemExit):
        smoke.main()
    assert len(requests) == 1
    request = requests[0]
    assert request['provider'] == smoke.provider_options('example/us', strict_privacy=False)
    image = request['messages'][1]['content'][1]['image_url']['url']
    import base64
    assert base64.b64decode(image.split(',', 1)[1]) == smoke.fixed_ocr_fixture('fraction')[0]
    assert json.loads(capsys.readouterr().out)['http_status'] == 429


def test_changed_fixture_fails_before_network_or_key_read(monkeypatch, tmp_path):
    filename, _, _ = smoke.OCR_FIXTURES['fraction']
    (tmp_path / filename).write_bytes(b'not the approved fixture')
    monkeypatch.setattr(smoke, 'OCR_ROOT', tmp_path)
    monkeypatch.setattr(smoke.httpx, 'Client', lambda **kwargs: pytest.fail('network must not start'))
    monkeypatch.setattr(sys, 'argv', ['probe', '--model', 'example/model:free', '--upstream', 'example/us',
                                    '--key-file', str(tmp_path / 'missing-key'), '--ocr-fixture', 'fraction'])
    with pytest.raises(ValueError, match='checksum'):
        smoke.main()
