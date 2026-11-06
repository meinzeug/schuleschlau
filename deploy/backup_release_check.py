"""Validate the exact systemd backup invocation used to gate a release.

The record and sidecar only prove that the snapshot was captured, not its
signature, semantic completeness or the ability to restore the archive.
"""

import json
import os
import re
import stat
from pathlib import Path

_RECORD = re.compile(r"SCHULPILOT backup created: (\d{8}T\d{6}Z\.tar\.enc); deletion journal: (present|missing|unavailable)\Z")


def _open_regular(directory_fd, name, *, limit=None):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=directory_fd)
    try:
        info = os.fstat(fd)
        current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1
                or info.st_mode & 0o022 or (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino)
                or limit is not None and info.st_size > limit):
            raise RuntimeError("Untrusted backup evidence")
        return fd, info
    except BaseException:
        os.close(fd)
        raise


def verify_invocation_log(log, directory=Path('/var/backups/schulpilot')):
    """Verify one neutral completion record and its matching published files."""
    if not isinstance(log, str) or len(log) > 65536:
        raise RuntimeError("Backup invocation output unavailable")
    records = [_RECORD.fullmatch(line) for line in log.splitlines()
               if line.startswith("SCHULPILOT backup created:")]
    if len(records) != 1 or records[0] is None or records[0][2] != "present":
        raise RuntimeError("Backup invocation lacks a complete journal snapshot")
    name = records[0][1]
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        directory_fd = os.open(directory, flags)
        try:
            info = os.fstat(directory_fd)
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
                raise RuntimeError("Untrusted backup directory")
            archive_fd, archive_info = _open_regular(directory_fd, name)
            try:
                if archive_info.st_size < 32 or os.read(archive_fd, 4) != b"SPB1":
                    raise RuntimeError("Invalid backup archive")
            finally:
                os.close(archive_fd)
            sidecar_fd, _ = _open_regular(directory_fd, name + '.journal.json', limit=8192)
            try:
                with os.fdopen(sidecar_fd, 'rb', closefd=False) as source:
                    value = json.load(source)
            finally:
                os.close(sidecar_fd)
            if not isinstance(value, dict) or value.get('backup') != name or value.get('journal') != 'present':
                raise RuntimeError("Backup journal evidence does not match the invocation")
        finally:
            os.close(directory_fd)
    except (OSError, ValueError, UnicodeError) as exc:
        raise RuntimeError("Backup invocation evidence unavailable") from exc
    return name
