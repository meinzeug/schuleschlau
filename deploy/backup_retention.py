"""Guarded retention for encrypted backups; no private contents are read.

A recent authenticated restore report and (when enabled) offsite acknowledgement
are prerequisites for deletion. An outage can delay deletion: the monitor must
alert instead of claiming that the 14-day maximum was met.
"""
import json
import os
import re
import stat
import time
from datetime import datetime, timezone
from pathlib import Path

from backup_storage import guarded_operation
from ledger_snapshot import backup_lock, status_path
from monitor import validate_restore_report

BACKUP_DIR = Path('/var/backups/schulpilot')
MONITOR_DIR = Path('/var/backups/schulpilot-monitor')
OFFSITE_ENABLED = Path('/etc/schulpilot/offsite-enabled')
RETENTION_SECONDS = 14 * 86400
# Five-minute timer plus safety margin. A machine or job outage can exceed this.
EARLY_SECONDS = 600
MAX_BACKUP_AGE = 30 * 3600


def _safe_read(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as source:
        meta = os.fstat(source.fileno())
        if not stat.S_ISREG(meta.st_mode) or meta.st_nlink != 1 or meta.st_uid != os.geteuid():
            raise RuntimeError('Untrusted backup metadata')
        data = source.read(limit + 1)
        if len(data) > limit:
            raise RuntimeError('Oversized backup metadata')
        return data


def _json(path):
    try:
        result = json.loads(_safe_read(path, 8192))
    except (OSError, ValueError, UnicodeError) as exc:
        raise RuntimeError('Invalid backup metadata') from exc
    if not isinstance(result, dict):
        raise RuntimeError('Invalid backup metadata')
    return result


def offsite_fresh(enabled, marker, now):
    try:
        info = enabled.lstat()
    except FileNotFoundError:
        return True
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1:
        return False
    try:
        checked = _json(marker).get('checked_at')
    except RuntimeError:
        return False
    return type(checked) is int and 0 < checked <= now and now - checked <= 3600


def _inspect(path, now):
    if not re.fullmatch(r'\d{8}T\d{6}Z\.tar\.enc', path.name):
        raise RuntimeError('Unexpected archive name')
    try:
        stamp = datetime.strptime(path.name[:16], '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc).timestamp()
        info = path.lstat()
    except (OSError, ValueError) as exc:
        raise RuntimeError('Invalid archive') from exc
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1
            or stamp > now or info.st_mtime > now or abs(stamp - info.st_mtime) > 3600):
        raise RuntimeError('Untrusted archive metadata')
    return stamp, info.st_mtime


def _valid_recovery_copy(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        with os.fdopen(fd, 'rb') as source:
            meta = os.fstat(source.fileno())
            if not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.geteuid() or meta.st_nlink != 1:
                raise RuntimeError('Untrusted recovery archive')
            if meta.st_size < 32 or source.read(4) != b'SPB1':
                raise RuntimeError('Invalid recovery archive')
        status = _json(status_path(path))
    except OSError as exc:
        raise RuntimeError('Missing recovery archive') from exc
    if status.get('backup') != path.name or status.get('journal') != 'present':
        raise RuntimeError('Missing recovery journal')


def prune(directory, now, report, *, dry_run):
    """Inspect all candidates, then prune. Caller holds exclusive backup_lock."""
    if validate_restore_report(report, now):
        raise RuntimeError('No recent verified restore')
    archives = sorted(directory.glob('*.tar.enc'))
    if not archives:
        raise RuntimeError('No backups')
    inspected = {path.name: _inspect(path, now) for path in archives}
    latest = archives[-1]
    verified_name = report['backup']
    if verified_name not in inspected:
        raise RuntimeError('Verified restore archive unavailable')
    verified = directory / verified_name
    if (now - inspected[latest.name][0] > MAX_BACKUP_AGE
            or now - inspected[verified_name][0] >= RETENTION_SECONDS - EARLY_SECONDS
            or inspected[verified_name][0] > report['checked_at']):
        raise RuntimeError('Recovery archive is stale')
    _valid_recovery_copy(latest)
    _valid_recovery_copy(verified)
    cutoff = now - RETENTION_SECONDS + EARLY_SECONDS
    candidates = []
    for archive in archives:
        stamp, modified = inspected[archive.name]
        if stamp <= cutoff and modified <= cutoff:
            if archive in (latest, verified):
                raise RuntimeError('Cannot remove recovery archive')
            sidecar = status_path(archive)
            try:
                meta = sidecar.lstat()
            except FileNotFoundError:
                pass  # Older backups predate sidecars.
            else:
                if not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.geteuid() or meta.st_nlink != 1:
                    raise RuntimeError('Untrusted archive sidecar')
            candidates.append((archive, sidecar))
    if not dry_run:
        for archive, sidecar in candidates:
            archive.unlink()
            sidecar.unlink(missing_ok=True)
    return len(candidates)


def main():
    os.umask(0o077)
    with guarded_operation(), backup_lock(BACKUP_DIR, exclusive=True):
        now = int(time.time())
        report = _json(MONITOR_DIR / 'restore-check.json')
        if not offsite_fresh(OFFSITE_ENABLED, MONITOR_DIR / 'offsite-last-success.json', now):
            raise RuntimeError('Offsite acknowledgement unavailable')
        count = prune(BACKUP_DIR, now, report, dry_run=False)
    print('SCHULPILOT backup retention: removed', count, 'expired archives')


if __name__ == '__main__':
    main()
