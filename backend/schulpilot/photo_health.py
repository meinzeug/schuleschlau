"""Verify the local decoder socket uses this release's exact decoder code."""
import hashlib
import os
import pwd
import socket
import struct
import sys
from pathlib import Path


def main(path, expected_uid, timeout=5):
    base = Path(__file__).resolve().parent
    digest = hashlib.sha256((base / 'photo_decoder.py').read_bytes() + (base / 'photo_service.py').read_bytes()
                            + (base.parent / 'requirements.lock').read_bytes()).digest()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        client.connect(path)
        _pid, uid, _gid = struct.unpack('3i', client.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        if uid != expected_uid:
            raise RuntimeError('Photo service user mismatch')
        client.sendall(digest + bytes(4))
        response = b''
        while len(response) < 4:
            chunk = client.recv(4 - len(response))
            if not chunk:
                raise RuntimeError('Photo service identity or health mismatch')
            response += chunk
        if response != bytes(4):
            raise RuntimeError('Invalid photo service health response')


if __name__ == '__main__':
    if len(sys.argv) == 3 and os.environ.get('ENVIRONMENT') == 'test':
        main(sys.argv[1], int(sys.argv[2]))
    elif sys.argv[1:] in ([], ['--monitor']):
        # A monitor can arrive behind an upload being read and decoded.  The
        # service is deliberately single-flight; give that request time to end.
        timeout = 75 if sys.argv[1:] else 5
        main('/run/schulpilot-photo/decoder.sock', pwd.getpwnam('schulpilot-photo').pw_uid, timeout)
    else:
        raise SystemExit('Invalid arguments')
