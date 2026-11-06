"""Private local photo normalizer, confined by the deployment service unit."""
import errno
import hashlib
import os
import pwd
import socket
import stat
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

MAX_IMAGE = 10 * 1024 * 1024
MAX_RESPONSE = 11 * 1024 * 1024
# Pin the decoder to this immutable release, even if current changes later.
DECODER = Path(__file__).resolve().with_name('photo_decoder.py')
DECODER_DIGEST = hashlib.sha256(
    DECODER.read_bytes() + Path(__file__).resolve().read_bytes() + DECODER.parent.parent.joinpath('requirements.lock').read_bytes()
).digest()
# Resolve only the venv directory, never the final python symlink: resolving
# the executable itself would bypass its virtualenv and its installed packages.
_source_root = DECODER.parent.parent.parent
if str(DECODER).startswith('/opt/schulpilot/releases/') or (_source_root / 'release.json').is_file():
    # Both decoder and venv derive from the very same resolved release root.
    PINNED_INTERPRETER = _source_root / 'venv' / 'bin' / 'python'
    if not PINNED_INTERPRETER.is_file():
        raise RuntimeError('Release-bound interpreter missing')
else:
    # Synthetic local tests have no packaged release/venv tree.
    PINNED_INTERPRETER = Path(sys.executable).parent.resolve() / Path(sys.executable).name


def recv_exact(connection, size):
    result = bytearray()
    while len(result) < size:
        chunk = connection.recv(min(65536, size - len(result)))
        if not chunk:
            raise EOFError('Incomplete local photo request')
        result.extend(chunk)
    return bytes(result)


def normalize(raw):
    with tempfile.TemporaryFile() as output:
        process = subprocess.run(
            [str(PINNED_INTERPRETER), '-I', str(DECODER)],
            input=raw, stdout=output, stderr=subprocess.DEVNULL,
            timeout=30, check=False, env={'LANG': 'C.UTF-8', 'PATH': '/usr/bin:/bin'}, close_fds=True,
        )
        size = output.tell()
        if process.returncode or not 4 <= size <= MAX_RESPONSE:
            raise RuntimeError('Bounded decoder failed')
        output.seek(0)
        return output.read(MAX_RESPONSE + 1)


def serve(path, api_uid):
    directory = path.parent
    metadata = directory.stat()
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o027:
        raise RuntimeError('Private decoder directory required')
    if path.exists() or path.is_symlink():
        metadata = path.lstat()
        if not stat.S_ISSOCK(metadata.st_mode) or metadata.st_uid != os.getuid():
            raise RuntimeError('Decoder socket path is not safe')
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
            probe.settimeout(1)
            try:
                probe.connect(str(path))
            except OSError as error:
                if error.errno != errno.ECONNREFUSED:
                    raise RuntimeError('Cannot verify existing decoder socket') from None
            else:
                raise RuntimeError('Decoder socket is already active')
        # Do not remove a replacement installed while the old socket was probed.
        current = path.lstat()
        if (current.st_dev, current.st_ino) != (metadata.st_dev, metadata.st_ino):
            raise RuntimeError('Decoder socket changed during startup')
        path.unlink()
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    previous = os.umask(0o077)
    try:
        server.bind(str(path))
    finally:
        os.umask(previous)
    os.chmod(path, 0o660)
    own_socket = path.lstat()
    server.listen(8)
    try:
        while True:
            connection, _ = server.accept()
            with connection:
                connection.settimeout(35)
                try:
                    _pid, uid, _gid = struct.unpack('3i', connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                    if uid != api_uid:
                        continue
                    if recv_exact(connection, 32) != DECODER_DIGEST:
                        continue
                    size = int.from_bytes(recv_exact(connection, 4), 'big')
                    if size == 0:
                        connection.sendall(bytes(4))
                        continue
                    if size > MAX_IMAGE:
                        continue
                    raw = recv_exact(connection, size)
                    result = normalize(raw)
                    connection.sendall(len(result).to_bytes(4, 'big'))
                    connection.sendall(result)
                except (EOFError, OSError, subprocess.TimeoutExpired, RuntimeError):
                    # No source bytes, user info or exception details in logs.
                    continue
    finally:
        server.close()
        try:
            current = path.lstat()
            if (current.st_dev, current.st_ino) == (own_socket.st_dev, own_socket.st_ino):
                path.unlink()
        except FileNotFoundError:
            pass


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('A private socket path and API user are required')
    serve(Path(sys.argv[1]), pwd.getpwnam(sys.argv[2]).pw_uid)
