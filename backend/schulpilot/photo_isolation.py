"""Call the private bounded photo service without passing credentials or metadata."""
import hashlib
import io
import json
import os
import pwd
import socket
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from fastapi import HTTPException

from .config import settings

_DECODER_DIGEST = hashlib.sha256(
    Path(__file__).with_name('photo_decoder.py').read_bytes() + Path(__file__).with_name('photo_service.py').read_bytes()
    + Path(__file__).resolve().parent.parent.joinpath('requirements.lock').read_bytes()
).digest()


class DecoderUnavailable(Exception):
    pass


def _recv_exact(connection, length):
    result = bytearray()
    while len(result) < length:
        part = connection.recv(min(65536, length - len(result)))
        if not part:
            raise DecoderUnavailable()
        result.extend(part)
    return bytes(result)


def _result_from_private_socket(raw, path, expected_uid):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(35)
        client.connect(path)
        _pid, uid, _gid = struct.unpack('3i', client.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        if uid != expected_uid:
            raise DecoderUnavailable()
        client.sendall(_DECODER_DIGEST + len(raw).to_bytes(4, 'big'))
        client.sendall(raw)
        length = int.from_bytes(_recv_exact(client, 4), 'big')
        if not 4 <= length <= 11 * 1024 * 1024:
            raise DecoderUnavailable()
        return _recv_exact(client, length)


def _isolated_test_result(raw):
    # Only isolated pytest fixtures use this compatibility mode. Deployed
    # installations fail closed unless their own separate service is available.
    with tempfile.TemporaryFile() as result:
        process = subprocess.run(
            [sys.executable, '-I', str(Path(__file__).with_name('photo_decoder.py'))],
            input=raw, stdout=result, stderr=subprocess.DEVNULL, timeout=30, check=False,
            env={'LANG': 'C.UTF-8', 'PATH': '/usr/bin:/bin'}, close_fds=True,
        )
        if process.returncode or not 4 <= result.tell() <= 11 * 1024 * 1024:
            raise DecoderUnavailable()
        result.seek(0)
        return result.read(11 * 1024 * 1024 + 1)


def normalize_photo(raw):
    if not raw:
        raise HTTPException(422, 'Bitte ein gültiges JPEG-, PNG- oder WebP-Bild mit höchstens 16 Megapixeln wählen.')
    try:
        test_socket = os.environ.get('PHOTO_TEST_SOCKET') if settings.environment == 'test' else None
        payload = (_isolated_test_result(raw) if settings.environment == 'test' and not test_socket
                   else _result_from_private_socket(
                       raw, test_socket or '/run/schulpilot-photo/decoder.sock',
                       os.getuid() if test_socket else pwd.getpwnam('schulpilot-photo').pw_uid))
        length = len(payload)
        if not 4 <= length <= 11 * 1024 * 1024:
            raise DecoderUnavailable()
        size = int.from_bytes(payload[:4], 'big')
        if not 2 <= size <= 4096 or 4 + size > length:
            raise DecoderUnavailable()
        meta = json.loads(payload[4:4 + size])
        if not isinstance(meta, dict):
            raise DecoderUnavailable()
        status = meta.get('status')
        if status == 'invalid':
            raise HTTPException(422, 'Bitte ein gültiges JPEG-, PNG- oder WebP-Bild mit höchstens 16 Megapixeln wählen.')
        if status in ('input_too_large', 'output_too_large'):
            raise HTTPException(413, 'Das Foto ist zu groß. Bitte einen kleineren gut lesbaren Ausschnitt abgeben.')
        geometry = meta.get('geometry')
        warnings = meta.get('warnings')
        if (status != 'ok' or not isinstance(geometry, dict) or not isinstance(warnings, list)
                or not all(isinstance(item, str) and len(item) <= 200 for item in warnings)
                or type(geometry.get('width')) is not int or type(geometry.get('height')) is not int
                or type(geometry.get('output_bytes')) is not int or geometry['output_bytes'] != length - 4 - size
                or type(geometry.get('input_width')) is not int or type(geometry.get('input_height')) is not int
                or geometry.get('input_bytes') != len(raw) or geometry.get('orientation') != 'baked'
                or not 1 <= geometry['width'] <= 3200 or not 1 <= geometry['height'] <= 3200
                or geometry['input_width'] < 1 or geometry['input_height'] < 1
                or geometry['input_width'] * geometry['input_height'] > 16_000_000):
            raise DecoderUnavailable()
        content = payload[4 + size:]
        if len(content) != geometry['output_bytes'] or not content.startswith(b'\xff\xd8\xff'):
            raise DecoderUnavailable()
        return io.BytesIO(content), geometry, warnings
    except HTTPException:
        raise
    except (OSError, KeyError, ValueError, subprocess.TimeoutExpired, DecoderUnavailable):
        raise HTTPException(503, 'Das Foto konnte gerade nicht verarbeitet werden. Bitte versuche es erneut.',
                            headers={'Retry-After': '2'}) from None
