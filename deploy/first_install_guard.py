"""Fail closed before treating a missing current link as an empty installation.

This verifies concrete local prerequisites, not a fence against future starts,
non-systemd writers, another host, or privileged concurrent changes.
"""
import os
import subprocess
from pathlib import Path

UNITS = ('schulpilot-api.service', 'schulpilot-worker.service', 'schulpilot-photo.service',
         'schulpilot-repair.service', 'schulpilot-repair-dispatcher.service',
         'schulpilot-backup.service', 'schulpilot-backup.timer', 'schulpilot-backup-retention.service',
         'schulpilot-backup-retention.timer', 'schulpilot-restore-check.service',
         'schulpilot-restore-check.timer', 'schulpilot-monitor.service', 'schulpilot-monitor.timer',
         'schulpilot-codex.service', 'schulpilot-turn.service', 'schulpilot-turn-cert.service',
         'schulpilot-turn-cert.timer')
FIELDS = {'LoadState', 'ActiveState', 'SubState', 'MainPID', 'ControlGroup', 'Job'}


class FirstInstallError(RuntimeError):
    pass


def previous_release(current: Path) -> Path | None:
    if current.is_symlink():
        try:
            previous = current.resolve(strict=True)
        except OSError as exc:
            raise FirstInstallError('Existing current release is inaccessible') from exc
        if not previous.is_dir():
            raise FirstInstallError('Existing current release is not a directory')
        return previous
    if os.path.lexists(current):
        raise FirstInstallError('Existing current release is not a symlink')
    return None


def _unit_is_absent(output: str, *, timer: bool) -> bool:
    values = {}
    for line in output.splitlines():
        key, sep, value = line.partition('=')
        if not sep or key in values:
            raise FirstInstallError('Unknown service state')
        values[key] = value
    expected = {'LoadState': 'not-found', 'ActiveState': 'inactive', 'SubState': 'dead', 'Job': ''}
    if not timer:
        expected.update({'MainPID': '0', 'ControlGroup': ''})
    if set(values) != set(expected):
        raise FirstInstallError('Incomplete service state')
    return values == expected


def verify_first_install(*, data_dir: Path = Path('/var/lib/schulpilot'), run=subprocess.run) -> None:
    for unit in UNITS:
        result = run(['systemctl', 'show', unit, '--no-pager', *(item for field in sorted(FIELDS)
                     for item in ('-p', field))], capture_output=True, text=True, check=True, timeout=10)
        if not _unit_is_absent(result.stdout, timer=unit.endswith('.timer')):
            raise FirstInstallError('Missing current release with existing service; manual recovery required')
    # bootstrap_host.py creates exactly this empty data directory and uploads
    # subdirectory. Existing content is evidence of a previous installation.
    if (data_dir.is_symlink() or not data_dir.is_dir()
            or (data_dir / 'uploads').is_symlink() or not (data_dir / 'uploads').is_dir()
            or {entry.name for entry in data_dir.iterdir()} != {'uploads'}
            or any((data_dir / 'uploads').iterdir())):
        raise FirstInstallError('Missing current release with existing private data; manual recovery required')
    query = """SELECT current_database(),
 (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE left(n.nspname,3) <> 'pg_' AND n.nspname <> 'information_schema' AND c.relkind IN ('r','p','v','m','S','f')),
 (SELECT count(*) FROM pg_stat_activity WHERE pid <> pg_backend_pid() AND backend_type='client backend'
  AND (datname='schulpilot' OR usename='schulpilot')),
 (SELECT count(*) FROM pg_prepared_xacts WHERE database='schulpilot');"""
    result = run(['runuser', '-u', 'postgres', '--', '/usr/bin/env', '-i', 'PATH=/usr/bin:/bin',
                  'PGHOST=/var/run/postgresql', 'PGPORT=5432', '/usr/bin/psql', '-X', '-A', '-t', '-F', '|',
                  '-v', 'ON_ERROR_STOP=1', '-d', 'schulpilot', '-c', query],
                 capture_output=True, text=True, check=True, timeout=15)
    if result.stdout.strip() != 'schulpilot|0|0|0':
        raise FirstInstallError('Missing current release with existing database state; manual recovery required')
