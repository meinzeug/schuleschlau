"""Prepare and publish a verified release outside the prune-visible tree.

This does not serialize deployment, activation or pruning. Operators must
still coordinate those operations, especially with older installed scripts.
"""

import ctypes
import errno
import os
import re
import stat
import sys
from pathlib import Path

BASE = Path('/opt/schulpilot')
RELEASE_ID = re.compile(r'\d{8}T\d{6}Z-[0-9a-f]{7,40}\Z')


def _directory(parent, name, owner, *, mode=None):
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    info = os.fstat(fd)
    if info.st_uid != owner or info.st_mode & 0o022 or (mode is not None and stat.S_IMODE(info.st_mode) != mode):
        os.close(fd)
        raise ValueError('Unsafe release directory ownership or permissions')
    return fd


def _base(path, owner):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    info = os.fstat(fd)
    if info.st_uid != owner or info.st_mode & 0o022:
        os.close(fd)
        raise ValueError('Unsafe release root ownership or permissions')
    return fd


def _check_id(release_id):
    if not RELEASE_ID.fullmatch(release_id):
        raise ValueError('Invalid release identifier')


def prepare(base, release_id, owner=0):
    _check_id(release_id)
    base_fd = _base(base, owner)
    try:
        try:
            os.mkdir('staging', 0o700, dir_fd=base_fd)
            os.fsync(base_fd)
        except FileExistsError:
            pass
        staging_fd = _directory(base_fd, 'staging', owner, mode=0o700)
        try:
            os.mkdir(release_id, 0o700, dir_fd=staging_fd)
            os.fsync(staging_fd)
        finally:
            os.close(staging_fd)
    finally:
        os.close(base_fd)


def _rename_noreplace(source_fd, target_fd, name):
    # The Linux primitive performs collision detection and rename atomically.
    # Refuse unsupported kernels instead of falling back to a racy precheck.
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, 'renameat2', None)
    if rename is None:
        raise OSError(errno.ENOSYS, 'renameat2 is required')
    rename.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
    rename.restype = ctypes.c_int
    encoded = os.fsencode(name)
    if rename(source_fd, encoded, target_fd, encoded, 1) != 0:  # RENAME_NOREPLACE
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), name)


def publish(base, release_id, owner=0):
    _check_id(release_id)
    base_fd = _base(base, owner)
    try:
        staging_fd = _directory(base_fd, 'staging', owner, mode=0o700)
        try:
            releases_fd = _directory(base_fd, 'releases', owner)
            try:
                release_fd = _directory(staging_fd, release_id, owner, mode=0o700)
                try:
                    # Staging remains root-only via its parent. Once published,
                    # the unprivileged application must traverse the release.
                    os.fchmod(release_fd, 0o755)
                    os.fsync(release_fd)
                    try:
                        _rename_noreplace(staging_fd, releases_fd, release_id)
                    except OSError:
                        os.fchmod(release_fd, 0o700)
                        raise
                    os.fsync(releases_fd)
                    os.fsync(staging_fd)
                finally:
                    os.close(release_fd)
            finally:
                os.close(releases_fd)
        finally:
            os.close(staging_fd)
    finally:
        os.close(base_fd)


def main():
    if os.geteuid() != 0:
        raise SystemExit('Release staging requires root')
    if len(sys.argv) != 3 or sys.argv[1] not in ('prepare', 'publish'):
        raise SystemExit('Usage: stage_release.py prepare|publish RELEASE_ID')
    {'prepare': prepare, 'publish': publish}[sys.argv[1]](BASE, sys.argv[2])


if __name__ == '__main__':
    main()
