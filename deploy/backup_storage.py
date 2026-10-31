"""Coordination primitives for an explicitly configured backup-volume cutover.

The operation lock must be outside the mount being switched. This module does
not activate a volume or alter an existing installation on its own.
"""

import fcntl
import os
import stat
import subprocess
import uuid
from contextlib import contextmanager
from pathlib import Path

OPERATION_LOCK = Path("/run/lock/schulpilot-backup-operations.lock")
VOLUME_CONFIG = Path("/etc/schulpilot/backup-volume.uuid")
BACKUP_DIRECTORY = Path("/var/backups/schulpilot")


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
    try:
        parsed_uuid = uuid.UUID(expected_uuid)
    except (TypeError, ValueError, AttributeError):
        raise ValueError("Invalid volume UUID") from None
    if str(parsed_uuid) != expected_uuid:
        raise ValueError("Invalid volume UUID")
    result = subprocess.run(
        ["findmnt", "--noheadings", "--output", "UUID", "--mountpoint", str(mountpoint)],
        check=True, capture_output=True, text=True, timeout=10,
    )
    if result.stdout.strip() != expected_uuid:
        raise RuntimeError("Expected backup volume is not mounted")


@contextmanager
def guarded_operation(*, exclusive=False):
    """Coordinate with cutovers and, when configured, require the volume.

    An absent configuration preserves the existing directory-backed setup.
    Provision and remove the root-owned configuration only while holding the
    exclusive operation lock. Never store it on the volume being switched.
    """
    with operation_lock(OPERATION_LOCK, exclusive=exclusive):
        try:
            fd = os.open(VOLUME_CONFIG, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        except FileNotFoundError:
            pass
        else:
            with os.fdopen(fd, "r") as config:
                metadata = os.fstat(config.fileno())
                if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != 0
                        or metadata.st_nlink != 1 or metadata.st_mode & 0o022):
                    raise RuntimeError("Untrusted backup volume configuration")
                expected_uuid = config.read(128).strip()
            require_volume(BACKUP_DIRECTORY, expected_uuid)
        yield
