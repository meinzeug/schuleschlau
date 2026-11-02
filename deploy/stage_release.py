"""Prepare and publish a verified release outside the prune-visible tree.

Guarantees coordination and mutual exclusion across deployment, rollback,
activation, and pruning operations.
"""

from __future__ import annotations

import ctypes
import errno
import fcntl
import functools
import grp
import inspect
import json
import os
import re
import shutil
import stat
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

BASE = Path('/opt/schulpilot')
RELEASE_ID = re.compile(r'\d{8}T\d{6}Z-[0-9a-f]{7,40}\Z')


class ReleaseLockError(RuntimeError):
    """Raised when a release operation lock cannot be acquired or validated."""


def _resolve_owner(base: Path, owner: int | None) -> int:
    if owner is not None:
        return owner
    try:
        return base.stat().st_uid
    except OSError:
        return os.geteuid()


def _check_trusted_file(fd: int, path: Path, expected_owner: int) -> None:
    current = os.fstat(fd)
    actual = os.lstat(path)
    if (
        not stat.S_ISREG(current.st_mode)
        or current.st_uid != expected_owner
        or current.st_nlink != 1
        or (current.st_dev, current.st_ino) != (actual.st_dev, actual.st_ino)
        or current.st_mode & 0o077
    ):
        raise ReleaseLockError(f"Untrusted release lock file: {path}")


def is_pid_alive(pid: int) -> bool:
    """Return True if pid exists on the system."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def is_process_accessing_path(target_path: Path) -> bool:
    """Check if any relevant process on the system is reading/writing in target_path.

    Inspects /proc on Linux. Fails open (returns False) if /proc is not available.
    """
    proc = Path('/proc')
    if not proc.is_dir():
        return False

    try:
        resolved_target = str(target_path.resolve())
    except OSError:
        return False

    try:
        entries = os.listdir(proc)
    except OSError:
        return False

    for entry in entries:
        if not entry.isdigit():
            continue
        pid_dir = proc / entry

        # Fast filter: skip kernel threads and unrelated processes
        try:
            with open(pid_dir / 'cmdline', 'rb') as cmd_file:
                cmd = cmd_file.read()
                if not cmd:
                    continue
                # Only inspect processes that might touch schulpilot or rsync or python
                if b'rsync' not in cmd and b'python' not in cmd and b'schulpilot' not in cmd:
                    continue
        except (OSError, ProcessLookupError):
            continue

        # Check cwd
        try:
            cwd = os.readlink(pid_dir / 'cwd')
            if cwd == resolved_target or cwd.startswith(resolved_target + '/'):
                return True
        except (OSError, ProcessLookupError):
            pass

        # Check open file descriptors
        fd_dir = pid_dir / 'fd'
        try:
            fd_entries = os.listdir(fd_dir)
        except (OSError, ProcessLookupError):
            continue

        for fd_name in fd_entries:
            try:
                link = os.readlink(fd_dir / fd_name)
                if link == resolved_target or link.startswith(resolved_target + '/'):
                    return True
            except (OSError, ProcessLookupError):
                continue

    return False


def is_lock_active(data: dict, base: Path, now: float) -> bool:
    """Determine whether an existing lock is actively held or stale."""
    if not isinstance(data, dict):
        return False

    # Check holder PID
    holder_pid = data.get('holder_pid')
    if isinstance(holder_pid, int) and is_pid_alive(holder_pid):
        return True

    # Check tracked PIDs
    tracked = data.get('tracked_pids', [])
    if isinstance(tracked, list):
        for pid in tracked:
            if isinstance(pid, int) and is_pid_alive(pid):
                return True

    # Check lease timeout
    updated_at = data.get('updated_at', 0)
    timeout = data.get('lease_timeout', 600)
    if isinstance(updated_at, (int, float)) and isinstance(timeout, (int, float)):
        if now - updated_at < timeout:
            return True

    # Check if any process is accessing staging directory of the release even after timeout
    release_id = data.get('release_id')
    if release_id and isinstance(release_id, str):
        staging_dir = base / 'staging' / release_id
        if staging_dir.is_dir() and is_process_accessing_path(staging_dir):
            return True

    return False


def _read_lock_file(lock_file: Path, owner: int) -> dict | None:
    if not lock_file.exists():
        return None
    try:
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
        fd = os.open(lock_file, flags)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ReleaseLockError(f"Cannot open release lock: {exc}") from exc

    try:
        _check_trusted_file(fd, lock_file, owner)
        with os.fdopen(fd, 'r', encoding='utf-8') as stream:
            content = stream.read()
            if not content.strip():
                raise ReleaseLockError("Empty release lock metadata")
            data = json.loads(content)
            if not isinstance(data, dict) or not isinstance(data.get('token'), str) or not data['token']:
                raise ReleaseLockError("Invalid release lock metadata")
            return data
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ReleaseLockError("Invalid release lock metadata") from exc


def check_lock(base: Path, *, owner: int | None = None) -> dict | None:
    """Return active lock metadata or None if lock is absent or stale."""
    owner = _resolve_owner(base, owner)
    lock_file = base / '.deploy.lock'
    data = _read_lock_file(lock_file, owner)
    if data and is_lock_active(data, base, time.time()):
        return data
    return None


def _write_lock_file(lock_file: Path, data: dict, owner: int) -> None:
    """Atomically write lock data to lock_file with 0600 mode and verification."""
    temp_file = lock_file.with_name(f".deploy.lock.{os.getpid()}.{time.time_ns()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open(temp_file, flags, 0o600)
    try:
        payload = json.dumps(data, indent=2) + "\n"
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fchmod(stream.fileno(), 0o600)
            os.fchown(stream.fileno(), owner, os.getegid())
        os.replace(temp_file, lock_file)
    finally:
        temp_file.unlink(missing_ok=True)


def _serialize_lock_mutation(function):
    """Serialize read/modify/write of the lease across independent processes."""
    signature = inspect.signature(function)

    @functools.wraps(function)
    def guarded(*args, **kwargs):
        bound = signature.bind(*args, **kwargs)
        base = bound.arguments['base']
        owner = _resolve_owner(base, bound.arguments.get('owner'))
        base_fd = _base(base, owner)
        try:
            fd = os.open('.deploy.guard', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC,
                         0o600, dir_fd=base_fd)
            try:
                _check_trusted_file(fd, base / '.deploy.guard', owner)
                fcntl.flock(fd, fcntl.LOCK_EX)
                try:
                    return function(*args, **kwargs)
                finally:
                    fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)
        finally:
            os.close(base_fd)

    return guarded


@_serialize_lock_mutation
def acquire_lock(
    base: Path,
    operation: str,
    release_id: str | None,
    *,
    token: str | None = None,
    lease_timeout: float = 600.0,
    stage: str = "preparing",
    owner: int | None = None,
) -> dict:
    """Acquire or renew the release operation lock.

    Raises ReleaseLockError if another operation is active.
    """
    owner = _resolve_owner(base, owner)
    lock_file = base / '.deploy.lock'
    now = time.time()

    existing = _read_lock_file(lock_file, owner)
    if existing:
        if token and existing.get('token') == token:
            existing['updated_at'] = now
            existing['holder_pid'] = os.getpid()
            existing['stage'] = stage
            if release_id:
                existing['release_id'] = release_id
            _write_lock_file(lock_file, existing, owner)
            return existing

        if is_lock_active(existing, base, now):
            op = existing.get('operation', 'unknown')
            rel = existing.get('release_id', 'none')
            stg = existing.get('stage', 'unknown')
            raise ReleaseLockError(
                f"Release operation in progress: operation='{op}', release_id='{rel}', stage='{stg}'"
            )

    new_token = token or str(uuid.uuid4())
    lock_data = {
        'operation': operation,
        'release_id': release_id,
        'token': new_token,
        'stage': stage,
        'holder_pid': os.getpid(),
        'created_at': now,
        'updated_at': now,
        'lease_timeout': lease_timeout,
        'tracked_pids': [os.getpid()],
    }
    _write_lock_file(lock_file, lock_data, owner)
    return lock_data


@_serialize_lock_mutation
def update_lock(
    base: Path,
    token: str,
    *,
    stage: str | None = None,
    release_id: str | None = None,
    tracked_pids: list[int] | None = None,
    lease_timeout: float | None = None,
    owner: int | None = None,
) -> dict:
    """Update an active lock held by the given token."""
    owner = _resolve_owner(base, owner)
    lock_file = base / '.deploy.lock'
    existing = _read_lock_file(lock_file, owner)
    if not existing or existing.get('token') != token:
        raise ReleaseLockError("Cannot update lock: token mismatch or lock not found")

    now = time.time()
    existing['updated_at'] = now
    existing['holder_pid'] = os.getpid()
    if stage is not None:
        existing['stage'] = stage
    if release_id is not None:
        existing['release_id'] = release_id
    if lease_timeout is not None:
        existing['lease_timeout'] = lease_timeout
    if tracked_pids is not None:
        existing['tracked_pids'] = list(set(existing.get('tracked_pids', []) + tracked_pids))

    _write_lock_file(lock_file, existing, owner)
    return existing


@_serialize_lock_mutation
def release_lock(base: Path, token: str | None = None, *, owner: int | None = None, force: bool = False) -> None:
    """Release the lock if token matches or force is True."""
    owner = _resolve_owner(base, owner)
    lock_file = base / '.deploy.lock'
    if not lock_file.exists():
        return

    existing = _read_lock_file(lock_file, owner)
    if existing and not force:
        if token and existing.get('token') != token:
            raise ReleaseLockError("Cannot release lock: token mismatch")

    try:
        lock_file.unlink(missing_ok=True)
    except OSError as exc:
        raise ReleaseLockError(f"Cannot delete release lock: {exc}") from exc


@contextmanager
def release_operation(
    base: Path,
    operation: str,
    release_id: str | None,
    *,
    token: str | None = None,
    lease_timeout: float = 600.0,
    stage: str = "active",
    owner: int | None = None,
):
    """Context manager acquiring the release operation lock or reusing an existing token session."""
    owner = _resolve_owner(base, owner)
    lock_data = acquire_lock(
        base,
        operation,
        release_id,
        token=token,
        lease_timeout=lease_timeout,
        stage=stage,
        owner=owner,
    )
    managed_token = lock_data['token']
    is_session_owner = token is None
    try:
        yield lock_data
    finally:
        if is_session_owner:
            try:
                release_lock(base, managed_token, owner=owner)
            except Exception:
                pass


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


def prepare(base: Path, release_id: str, owner: int | None = None, *, token: str | None = None) -> str:
    _check_id(release_id)
    owner = _resolve_owner(base, owner)
    lock_data = acquire_lock(base, 'deploy', release_id, token=token, stage='staging', owner=owner)

    try:
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
    except Exception:
        release_lock(base, lock_data['token'], owner=owner)
        raise

    return lock_data['token']


def _rename_noreplace(source_fd, target_fd, name):
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


def _check_contents(directory_fd, owner, repair_gid, public_gid, prefix=''):
    with os.scandir(directory_fd) as entries:
        for entry in entries:
            path = f'{prefix}/{entry.name}' if prefix else entry.name
            info = entry.stat(follow_symlinks=False)
            mode = stat.S_IMODE(info.st_mode)
            if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
                raise ValueError(f'Non-regular release entry: {path}')
            if info.st_uid != owner or mode & 0o7022:
                raise ValueError(f'Unsafe release owner or permissions: {path}')
            if path != 'repair-source.tar.gz' and info.st_gid != public_gid:
                raise ValueError(f'Unsafe release group: {path}')
            if stat.S_ISDIR(info.st_mode):
                if mode & 0o005 != 0o005:
                    raise ValueError(f'Release directory is not publicly traversable: {path}')
                fd = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory_fd)
                try:
                    _check_contents(fd, owner, repair_gid, public_gid, path)
                finally:
                    os.close(fd)
            elif stat.S_ISREG(info.st_mode):
                if info.st_nlink != 1:
                    raise ValueError(f'Hard-linked release file: {path}')
                if path == 'repair-source.tar.gz':
                    if repair_gid is None or info.st_gid != repair_gid or mode != 0o640:
                        raise ValueError('Unsafe private repair archive permissions')
                elif not mode & 0o004:
                    raise ValueError(f'Release file is not publicly readable: {path}')


def publish(
    base: Path,
    release_id: str,
    owner: int | None = None,
    *,
    token: str | None = None,
    repair_gid: int | None = None,
    public_gid: int | None = None,
) -> None:
    _check_id(release_id)
    owner = _resolve_owner(base, owner)
    if token:
        update_lock(base, token, stage='published', release_id=release_id, owner=owner)

    if public_gid is None:
        public_gid = os.getegid()
    base_fd = _base(base, owner)
    try:
        staging_fd = _directory(base_fd, 'staging', owner, mode=0o700)
        try:
            releases_fd = _directory(base_fd, 'releases', owner)
            try:
                release_fd = _directory(staging_fd, release_id, owner, mode=0o700)
                try:
                    _check_contents(release_fd, owner, repair_gid, public_gid)
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


def abort(base: Path, release_id: str, owner: int | None = None, *, token: str | None = None) -> None:
    """Abort a staging release, cleanup files, and release the operation lock."""
    _check_id(release_id)
    owner = _resolve_owner(base, owner)
    staged_path = base / 'staging' / release_id
    if staged_path.is_dir():
        shutil.rmtree(staged_path, ignore_errors=True)
    try:
        release_lock(base, token, owner=owner)
    except ReleaseLockError:
        pass


def heartbeat(base: Path, release_id: str, token: str, owner: int | None = None) -> None:
    _check_id(release_id)
    owner = _resolve_owner(base, owner)
    update_lock(base, token, release_id=release_id, owner=owner)


def main():
    if os.geteuid() != 0:
        raise SystemExit('Release staging requires root')
    if len(sys.argv) < 3 or sys.argv[1] not in ('prepare', 'publish', 'abort', 'heartbeat'):
        raise SystemExit('Usage: stage_release.py prepare|publish|abort|heartbeat RELEASE_ID [TOKEN]')
    action = sys.argv[1]
    release_id = sys.argv[2]
    token = sys.argv[3] if len(sys.argv) > 3 else None

    if action == 'prepare':
        print(prepare(BASE, release_id, token=token))
    elif action == 'publish':
        publish(BASE, release_id, token=token, repair_gid=grp.getgrnam('schulpilot').gr_gid, public_gid=0)
    elif action == 'abort':
        abort(BASE, release_id, token=token)
    elif action == 'heartbeat':
        if not token:
            raise SystemExit('Heartbeat requires TOKEN')
        heartbeat(BASE, release_id, token)


if __name__ == '__main__':
    main()
