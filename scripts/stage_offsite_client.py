#!/usr/bin/env python3
"""Stage three Git-pinned offsite files without installing or starting anything.

This tool does not fence writers, upgrade a service, validate a backup, or
authorize a cutover. The operator must independently trust the repository,
commit and local account. A stage is a candidate, not a release attestation.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import stat
import subprocess
import time
from pathlib import Path

FILES = {
    'scripts/offsite_backup.py': 'offsite_backup.py',
    'deploy/schulpilot-offsite.service': 'schulpilot-offsite.service',
    'deploy/schulpilot-offsite.timer': 'schulpilot-offsite.timer',
}
LIMIT = 1024 * 1024
GIT = '/usr/bin/git'
ENV = {'PATH': '/usr/bin:/bin', 'HOME': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_NO_REPLACE_OBJECTS': '1', 'LC_ALL': 'C'}


def _git(repo: Path, *args: str) -> bytes:
    result = subprocess.run([GIT, '--no-replace-objects', '-C', str(repo), *args],
                            env=ENV, capture_output=True, timeout=15, check=True)
    if len(result.stdout) > LIMIT:
        raise ValueError('Git output exceeds staging limit')
    return result.stdout


def _candidate(repo: Path, revision: str) -> tuple[dict[str, bytes], bytes]:
    if not repo.is_absolute() or not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('absolute repository and full commit required')
    if _git(repo, 'rev-parse', '--verify', '--end-of-options', revision + '^{commit}').strip() != revision.encode():
        raise ValueError('revision is not an exact commit')
    result = {}
    for source, name in FILES.items():
        line = _git(repo, 'ls-tree', '-z', revision, '--', source)
        match = re.fullmatch(rb'100644 blob ([0-9a-f]{40})\t' + re.escape(source.encode()) + rb'\x00', line)
        if not match:
            raise ValueError('candidate must contain exact regular Git blobs')
        object_id = match.group(1).decode('ascii')
        size = _git(repo, 'cat-file', '-s', object_id).strip()
        if not size.isdigit() or int(size) > LIMIT:
            raise ValueError('candidate blob exceeds staging limit')
        result[name] = _git(repo, 'cat-file', 'blob', object_id)
    manifest = {'format': 1, 'revision': revision,
                'files': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(result.items())},
                'activation_authorized': False}
    return result, (json.dumps(manifest, sort_keys=True, separators=(',', ':')) + '\n').encode('ascii')


def _open_directory(path: Path, owner: int) -> int:
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('absolute staging directory required')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        for part in path.parts[1:]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = next_fd
            item = os.fstat(fd)
            sticky_root = item.st_uid == 0 and bool(item.st_mode & stat.S_ISVTX)
            if item.st_uid not in (0, owner) or (item.st_mode & 0o022 and not sticky_root):
                raise ValueError('untrusted staging directory chain')
        item = os.fstat(fd)
        if item.st_uid != owner or item.st_mode & 0o077:
            raise ValueError('staging directory must be owner-private')
        return fd
    except BaseException:
        os.close(fd)
        raise


def _write(directory: int, name: str, data: bytes) -> None:
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                 0o600, dir_fd=directory)
    try:
        view = memoryview(data)
        while view:
            n = os.write(fd, view)
            if n <= 0:
                raise OSError('incomplete staging write')
            view = view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _read(directory: int, name: str, owner: int) -> bytes:
    fd = os.open(name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
    try:
        info = os.fstat(fd)
        named = os.stat(name, dir_fd=directory, follow_symlinks=False)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != owner or info.st_mode & 0o077
                or info.st_nlink != 1 or info.st_size > LIMIT or (info.st_dev, info.st_ino) != (named.st_dev, named.st_ino)):
            raise ValueError('untrusted staged file')
        data = b''
        while len(data) < info.st_size:
            part = os.read(fd, min(65536, info.st_size - len(data)))
            if not part:
                raise ValueError('staged file truncated')
            data += part
        after = os.fstat(fd)
        named = os.stat(name, dir_fd=directory, follow_symlinks=False)
        def identity(s):
            return (s.st_dev, s.st_ino, s.st_uid, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if identity(info) != identity(after) or identity(after) != identity(named):
            raise ValueError('staged file changed during verification')
        # A previous producer may have died after its last file fsync but
        # before syncing the directory. A successful verifier re-establishes
        # durability rather than mistaking visible names for a completed run.
        os.fsync(fd)
        return data
    finally:
        os.close(fd)


def _lock(base: int, owner: int, *, create: bool, timeout: float) -> int:
    if not 0 <= timeout <= 60:
        raise ValueError('invalid stage lock timeout')
    flags = os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC | (os.O_CREAT if create else 0)
    fd = os.open('.stage.lock', flags, 0o600, dir_fd=base)
    try:
        info = os.fstat(fd)
        named = os.stat('.stage.lock', dir_fd=base, follow_symlinks=False)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != owner or info.st_nlink != 1 or info.st_mode & 0o077
                or (info.st_dev, info.st_ino) != (named.st_dev, named.st_ino)):
            raise ValueError('untrusted stage lock')
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, (fcntl.LOCK_EX if create else fcntl.LOCK_SH) | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError('stage lock busy') from None
                time.sleep(.025)
        named = os.stat('.stage.lock', dir_fd=base, follow_symlinks=False)
        if (info.st_dev, info.st_ino) != (named.st_dev, named.st_ino):
            raise ValueError('stage lock replaced')
        return fd
    except BaseException:
        os.close(fd)
        raise


def stage(repo: Path, destination: Path, revision: str, *, timeout: float = 5) -> None:
    """Create an exclusive candidate directory. Failures never replace a stage."""
    owner = os.geteuid()
    files, manifest = _candidate(repo, revision)
    base = _open_directory(destination, owner)
    lock = None
    try:
        lock = _lock(base, owner, create=True, timeout=timeout)
        # A failed/interrupted directory remains present and cannot be reused.
        os.mkdir(revision, 0o700, dir_fd=base)
        os.fsync(base)
        candidate = os.open(revision, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=base)
        try:
            for name, data in files.items():
                _write(candidate, name, data)
            _write(candidate, 'manifest.json', manifest)
            os.fsync(candidate)
        finally:
            os.close(candidate)
        os.fsync(base)
    finally:
        if lock is not None:
            os.close(lock)
        os.close(base)


def verify(repo: Path, destination: Path, revision: str, *, timeout: float = 5) -> None:
    files, manifest = _candidate(repo, revision)
    base = _open_directory(destination, os.geteuid())
    lock = None
    try:
        lock = _lock(base, os.geteuid(), create=False, timeout=timeout)
        fd = os.open(revision, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=base)
        try:
            info = os.fstat(fd)
            if info.st_uid != os.geteuid() or info.st_mode & 0o077:
                raise ValueError('untrusted candidate directory')
            if set(os.listdir(fd)) != set(files) | {'manifest.json'}:
                raise ValueError('incomplete or unexpected stage files')
            for name, expected in {**files, 'manifest.json': manifest}.items():
                if _read(fd, name, os.geteuid()) != expected:
                    raise ValueError('staged bytes differ from Git revision')
            os.fsync(fd)
            os.fsync(base)
            named = os.stat(revision, dir_fd=base, follow_symlinks=False)
            if (info.st_dev, info.st_ino) != (named.st_dev, named.st_ino):
                raise ValueError('candidate directory changed during verification')
            held = os.fstat(lock)
            named_lock = os.stat('.stage.lock', dir_fd=base, follow_symlinks=False)
            if (held.st_dev, held.st_ino) != (named_lock.st_dev, named_lock.st_ino):
                raise ValueError('stage lock replaced during verification')
        finally:
            os.close(fd)
    finally:
        if lock is not None:
            os.close(lock)
        os.close(base)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'verify'))
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    (stage if args.action == 'stage' else verify)(args.repo, args.destination, args.revision)
    print('Candidate staged; run verify before use.' if args.action == 'stage' else 'Candidate bytes match Git revision.')
    print('No installation, process fence or cutover is authorized.')


if __name__ == '__main__':
    main()
