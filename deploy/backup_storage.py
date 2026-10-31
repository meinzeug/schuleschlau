"""Coordination primitives for an explicitly configured backup-volume cutover.

The operation lock must be outside the mount being switched. This module does
not activate a volume or alter an existing installation on its own.
"""

import fcntl
import os
import stat
import subprocess
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def operation_lock(path: Path, *, exclusive: bool):
    flags = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open(path, flags, 0o600)
    try:
        current = os.fstat(fd)
        actual = os.lstat(path)
        if (not stat.S_ISREG(current.st_mode) or current.st_uid != os.geteuid()
                or current.st_nlink != 1 or (current.st_dev, current.st_ino) != (actual.st_dev, actual.st_ino)
                or current.st_mode & 0o077):
            raise RuntimeError("Untrusted backup operation lock")
        fcntl.flock(fd, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        # Detect replacement while waiting for another holder.
        actual = os.lstat(path)
        if (current.st_dev, current.st_ino) != (actual.st_dev, actual.st_ino):
            raise RuntimeError("Backup operation lock was replaced")
        yield
    finally:
        os.close(fd)


def require_volume(mountpoint: Path, expected_uuid: str):
    """Fail closed when the exact mountpoint is absent or has the wrong UUID."""
    if not expected_uuid or any(c not in "0123456789abcdef-" for c in expected_uuid):
        raise ValueError("Invalid volume UUID")
    result = subprocess.run(
        ["findmnt", "--noheadings", "--output", "UUID", "--mountpoint", str(mountpoint)],
        check=True, capture_output=True, text=True, timeout=10,
    )
    if result.stdout.strip() != expected_uuid:
        raise RuntimeError("Expected backup volume is not mounted")
