"""Conservatively retain at most three unreferenced-safe restore runtimes.

The default is a dry run. The release and backup locks are held for mutations.
Interrupted preparations are removed only after a day and only when unreferenced.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

try:
    from backup_storage import guarded_operation
    from prune_releases import _assert_no_nested_mounts, _pointer_target
    from release_lock import ReleaseLockError, release_operation
    from restore_release_guard import verify as verify_restore
except ImportError:
    from deploy.backup_storage import guarded_operation
    from deploy.prune_releases import _assert_no_nested_mounts, _pointer_target
    from deploy.release_lock import ReleaseLockError, release_operation
    from deploy.restore_release_guard import verify as verify_restore

BASE = Path('/opt/schulpilot')
RUNTIMES = BASE / 'restore-runtimes'
HEX = re.compile(r'[a-f0-9]{40}\Z')
PREP = re.compile(r'\.prepare-[a-f0-9]{40}\Z')
LEGACY = re.compile(r'[a-f0-9]{7}-\d{8}\Z')


class RetentionError(RuntimeError):
    pass


def require_root():
    if os.geteuid() != 0:
        raise SystemExit('Root access required')


def _commit(release):
    path = release / 'release.json'
    if path.is_symlink() or not path.is_file():
        raise RetentionError('Release metadata unavailable')
    value = json.loads(path.read_text())
    commit = value.get('source_commit') if isinstance(value, dict) else None
    if not isinstance(commit, str) or not HEX.fullmatch(commit):
        raise RetentionError('Invalid release source commit')
    return commit


def _reference_names(text):
    return set(re.findall(r'/opt/schulpilot/restore-runtimes/([^/\x00\s;{}\]\["\']+)', text))


def systemd_references():
    # Loaded commands and operator-installed definitions both matter. Never
    # silently drop a runtime referenced by a disabled service or drop-in.
    result = subprocess.run(['systemctl', 'show', '--all', '-p', 'ExecStart', '-p', 'ExecStartPre',
                             '-p', 'ExecStartPost', '-p', 'WorkingDirectory'],
                            check=True, capture_output=True, text=True, timeout=30)
    names = _reference_names(result.stdout)
    root = Path('/etc/systemd/system')
    for path in root.rglob('*'):
        if path.is_symlink() or not path.is_file() or path.suffix not in ('.service', '.conf', '.timer', '.socket'):
            continue
        if path.stat().st_size > 1024 * 1024:
            raise RetentionError('Systemd definition too large to inspect')
        names.update(_reference_names(path.read_text(errors='strict')))
    return names


def process_references(proc=Path('/proc')):
    """Inspect paths without logging command lines, environment, or file names."""
    if not proc.is_dir():
        raise RetentionError('Process inspection unavailable')
    names = set()
    for process in proc.iterdir():
        if not process.name.isdigit():
            continue
        try:
            try:
                names.update(_reference_names((process / 'cmdline').read_bytes().decode('utf-8', 'replace')))
            except FileNotFoundError:
                pass
            try:
                with (process / 'maps').open('r', encoding='utf-8', errors='replace') as mappings:
                    for line in mappings:
                        names.update(_reference_names(line))
            except FileNotFoundError:
                pass
            for path in (process / 'cwd', process / 'exe', process / 'root'):
                try:
                    names.update(_reference_names(os.readlink(path)))
                except FileNotFoundError:
                    pass
            try:
                for fd in (process / 'fd').iterdir():
                    try:
                        names.update(_reference_names(os.readlink(fd)))
                    except FileNotFoundError:
                        pass
            except FileNotFoundError:
                pass
        except ProcessLookupError:
            pass  # A process that exited cannot retain the directory.
        except PermissionError as exc:
            raise RetentionError('A running process cannot be inspected') from exc
    return names


def plan(root, protected, *, limit=3, now=None):
    if limit not in (2, 3) or root.is_symlink() or not root.is_dir():
        raise RetentionError('Invalid runtime root or retention limit')
    meta = root.stat()
    if meta.st_uid != os.geteuid() or meta.st_mode & 0o022:
        raise RetentionError('Untrusted runtime root')
    now = time.time() if now is None else now
    runtimes, stale, recent = [], [], set()
    for path in root.iterdir():
        matched = HEX.fullmatch(path.name) or PREP.fullmatch(path.name) or LEGACY.fullmatch(path.name)
        if not matched:
            continue  # Other operator files are not runtime candidates.
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
            raise RetentionError('Untrusted runtime entry')
        if HEX.fullmatch(path.name):
            runtimes.append(path)
            # A provisioner may still be populating a newly named runtime.
            # ctime cannot be backdated by the copying process like mtime.
            if info.st_ctime > now - 3600:
                recent.add(path.name)
        elif (path.name not in protected and info.st_mtime <= now - 86400
              and info.st_ctime <= now - 3600):
            stale.append(path)
    names = {p.name for p in runtimes}
    keep = (set(protected) & names) | recent
    if len(keep) > limit:
        raise RetentionError('More runtimes are in use than the allowed limit')
    for path in sorted(runtimes, key=lambda p: (p.stat().st_mtime_ns, p.name), reverse=True):
        if len(keep) >= limit:
            break
        keep.add(path.name)
    return sorted((p for p in runtimes if p.name not in keep), key=lambda p: p.name) + sorted(stale)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--reserve-slot', action='store_true', help='leave one slot for a new runtime')
    parser.add_argument('--keep-commit', help='protect a prepared runtime for the next release')
    args = parser.parse_args()
    require_root()
    if args.keep_commit and not HEX.fullmatch(args.keep_commit):
        raise SystemExit('Invalid protected commit')
    limit = 2 if args.reserve_slot else 3

    def calculate():
        releases = (BASE / 'releases').resolve(strict=True)
        current = _pointer_target(BASE / 'current', releases, required=True)
        previous = _pointer_target(BASE / 'previous', releases, required=False)
        verify_restore(current)
        protected = {_commit(current), *([_commit(previous)] if previous else [])}
        protected.update(systemd_references())
        protected.update(process_references())
        if args.keep_commit:
            protected.add(args.keep_commit)
        if not (RUNTIMES / _commit(current)).is_dir():
            raise RetentionError('Current release runtime unavailable')
        if previous and not (RUNTIMES / _commit(previous)).is_dir():
            raise RetentionError('Previous release runtime unavailable')
        return plan(RUNTIMES, protected, limit=limit)

    try:
        # Check first so a normal defer (for example a release currently being
        # prepared) never leaves behind a persistent maintenance lease.
        removals = calculate()
        if not args.apply:
            print(f'Dry run: {len(removals)} alte Runtime-Verzeichnisse; Limit {limit}.')
            for item in removals:
                print(item.name)
            return 0
        with release_operation(BASE, 'prune_restore_runtimes', None, stage='pruning'):
            deletion_started = False
            try:
                with guarded_operation(exclusive=True):
                    removals = calculate()
                    for item in removals:
                        _assert_no_nested_mounts(item)
                    for item in removals:
                        deletion_started = True
                        shutil.rmtree(item)
            except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
                if deletion_started:
                    raise  # Preserve the lease when cleanup may be incomplete.
                # Before any deletion, release the lease on a normal defer.
                print(f'Runtime-Bereinigung gestoppt: {exc}', file=sys.stderr)
                return 2
        print(f'{len(removals)} alte Runtime-Verzeichnisse entfernt; geschützte Versionen bleiben erhalten.')
        return 0
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError, ReleaseLockError) as exc:
        print(f'Runtime-Bereinigung gestoppt: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
