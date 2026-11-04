"""Bounded, private access to flat upload files.

The database normally stores generated filenames; it is still not a filesystem
capability. A damaged or restored row must not escape uploads, follow a link,
read a device or hand an arbitrary path to an archive or a provider.
"""

import os
import re
import stat

from .config import settings

MAX_IMAGE_BYTES = 10 * 1024 * 1024
_NAME = re.compile(r"[A-Za-z0-9_-]{1,150}\.jpg", re.ASCII)


def valid_name(name):
    return isinstance(name, str) and _NAME.fullmatch(name) is not None


def read(name, max_bytes=MAX_IMAGE_BYTES):
    """Return bytes for a regular bounded upload, otherwise None.

    Open relative to an independently opened directory and never follow the
    final symlink. O_NONBLOCK prevents a corrupted FIFO from blocking a worker.
    """
    if not valid_name(name) or type(max_bytes) is not int or not 0 < max_bytes <= MAX_IMAGE_BYTES:
        return None
    try:
        directory = os.open(settings.data_dir / "uploads", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError:
        return None
    try:
        try:
            descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        except OSError:
            return None
        with os.fdopen(descriptor, "rb") as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > max_bytes:
                return None
            data = source.read(max_bytes + 1)
            return data if len(data) <= max_bytes else None
    finally:
        os.close(directory)


def remove(name):
    """Unlink a single upload entry; invalid paths never escape its directory."""
    if not valid_name(name):
        raise ValueError("Invalid private upload name")
    try:
        directory = os.open(settings.data_dir / "uploads", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return
    try:
        try:
            os.unlink(name, dir_fd=directory)
        except FileNotFoundError:
            pass
    finally:
        os.close(directory)
