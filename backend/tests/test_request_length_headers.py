"""Synthetic tests for limits before the request body is parsed."""

import asyncio

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse
from schulpilot.main import security_headers


def request_with_length(value):
    return Request({'type': 'http', 'method': 'POST', 'path': '/synthetic',
                    'headers': [(b'x-schulpilot-request', b'1'), (b'content-length', value)],
                    'scheme': 'http', 'server': ('testserver', 80), 'query_string': b''})


async def continue_request(_request):
    return JSONResponse({'reached': True})


@pytest.mark.parametrize('declared_length', [b'9' * 5000, b'\xb2'], ids=['long', 'non-ascii'])
def test_invalid_content_length_is_rejected_without_server_error(declared_length):
    response = asyncio.run(security_headers(request_with_length(declared_length), continue_request))
    assert response.status_code == 413


@pytest.mark.parametrize('length', [b'0', b'2', b'65536', b'000002', b'0' * 5000],
                         ids=['zero', 'small', 'boundary', 'leading-zero', 'many-zeros'])
def test_valid_length_within_limit_reaches_endpoint(length):
    response = asyncio.run(security_headers(request_with_length(length), continue_request))
    assert response.status_code == 200


@pytest.mark.parametrize('length', [b'65537', b'00065537', b'-1', b'1.0', b''])
def test_other_invalid_or_oversized_lengths_are_rejected(length):
    response = asyncio.run(security_headers(request_with_length(length), continue_request))
    assert response.status_code == 413
