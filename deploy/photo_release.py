"""Release-bound lifecycle for the isolated local photo decoder service."""
from __future__ import annotations

import grp
import os
import pwd
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PreviousPhoto:
    loaded: bool
    active: bool
    enabled: bool


def inspect_photo(run=subprocess.run):
    result = run(['systemctl', 'show', 'schulpilot-photo.service', '--property=LoadState',
                  '--property=ActiveState', '--property=UnitFileState'],
                 check=True, capture_output=True, text=True, timeout=15)
    values = {}
    for line in result.stdout.splitlines():
        key, sep, value = line.partition('=')
        if not sep or key in values:
            raise RuntimeError('Ungültiger Fotodienstzustand')
        values[key] = value
    if set(values) != {'LoadState', 'ActiveState', 'UnitFileState'}:
        raise RuntimeError('Unvollständiger Fotodienstzustand')
    loaded, active, enabled = values['LoadState'], values['ActiveState'], values['UnitFileState']
    if loaded == 'not-found' and active == 'inactive' and enabled == '':
        return PreviousPhoto(False, False, False)
    if loaded != 'loaded' or active not in {'active', 'inactive'} or enabled not in {'enabled', 'disabled'}:
        raise RuntimeError('Fotodienst ist nicht in einem stabilen Zustand')
    return PreviousPhoto(True, active == 'active', enabled == 'enabled')


def verify_photo_definition(previous: PreviousPhoto, release: Path | None, *,
                            unit=Path('/etc/systemd/system/schulpilot-photo.service'), run=subprocess.run):
    """Refuse foreign definitions or systemd overrides before changing the service."""
    result = run(['systemctl', 'show', 'schulpilot-photo.service', '--property=FragmentPath',
                  '--property=DropInPaths', '--property=NeedDaemonReload'],
                 check=True, capture_output=True, text=True, timeout=15)
    values = {}
    for line in result.stdout.splitlines():
        key, sep, value = line.partition('=')
        if not sep or key in values:
            raise RuntimeError('Ungültige Fotodienstdefinition')
        values[key] = value
    if (set(values) != {'FragmentPath', 'DropInPaths', 'NeedDaemonReload'}
            or values['DropInPaths'] or values['NeedDaemonReload'] != 'no'):
        raise RuntimeError('Fotodienstdefinition hat unbekannte Overrides')
    if not previous.loaded:
        if values['FragmentPath'] or unit.exists() or unit.is_symlink():
            raise RuntimeError('Fremde Fotodienstdefinition vorhanden')
        return
    source = release / 'deploy/schulpilot-photo.service' if release else None
    if (values['FragmentPath'] != str(unit) or unit.is_symlink() or not unit.is_file()
            or not source or not source.is_file() or unit.read_bytes() != source.read_bytes()):
        raise RuntimeError('Fotodienstdefinition stimmt nicht mit dem Release überein')


def ensure_isolated_identity(release: Path, run=subprocess.run):
    spec = release / 'deploy/schulpilot-photo.sysusers'
    if not spec.is_file():
        raise RuntimeError('Fotodienstidentität fehlt im Release')
    run(['systemd-sysusers', str(spec)], check=True, timeout=30)
    api = pwd.getpwnam('schulpilot')
    photo = pwd.getpwnam('schulpilot-photo')
    group = grp.getgrnam('schulpilot-photo')
    group_ids = set(os.getgrouplist(photo.pw_name, photo.pw_gid))
    if (photo.pw_uid in {0, api.pw_uid} or photo.pw_gid != group.gr_gid or group.gr_gid in {0, api.pw_gid}
            or [entry.gr_name for entry in grp.getgrall() if entry.gr_gid == group.gr_gid] != [group.gr_name]
            or set(group.gr_mem) - {'schulpilot'}
            or group_ids != {group.gr_gid} or [entry.pw_name for entry in pwd.getpwall() if entry.pw_uid == photo.pw_uid] != [photo.pw_name]
            or photo.pw_shell != '/usr/sbin/nologin'
            or photo.pw_dir != '/nonexistent'):
        raise RuntimeError('Fotodienstidentität ist nicht ausreichend isoliert')


def stop_old_photo(previous: PreviousPhoto, run=subprocess.run):
    if previous.active:
        run(['systemctl', 'stop', 'schulpilot-photo.service'], check=True, timeout=40)


def start_candidate(release: Path, *, run=subprocess.run, sleep=time.sleep):
    run(['systemctl', 'restart', 'schulpilot-photo.service'], check=True, timeout=40)
    probe = release / 'backend/schulpilot/photo_health.py'
    if not probe.is_file():
        raise RuntimeError('Revisionsprüfung des Fotodiensts fehlt')
    for _ in range(30):
        result = run(['runuser', '-u', 'schulpilot', '-g', 'schulpilot-photo', '--',
                      str(release / 'venv/bin/python'), '-I', str(probe)],
                     check=False, capture_output=True, timeout=6)
        if result.returncode == 0:
            return
        sleep(1)
    raise RuntimeError('Fotodienst: Identität oder Socketprüfung fehlgeschlagen')


def undo_candidate_enable(previous: PreviousPhoto, run=subprocess.run):
    run(['systemctl', 'stop', 'schulpilot-photo.service'], check=True, timeout=40)
    if not previous.enabled:
        run(['systemctl', 'disable', 'schulpilot-photo.service'], check=True, timeout=40)


def restore_previous_photo(previous: PreviousPhoto, run=subprocess.run):
    if previous.loaded and previous.enabled:
        run(['systemctl', 'enable', 'schulpilot-photo.service'], check=True, timeout=40)
    if previous.loaded and previous.active:
        run(['systemctl', 'start', 'schulpilot-photo.service'], check=True, timeout=40)
