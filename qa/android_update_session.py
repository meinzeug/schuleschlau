"""Synthetic-family Direct-update test; use only a dedicated empty emulator.

The old Direct app must show its unauthenticated login screen. The higher
release must already be public. This test deletes its own synthetic household
and clears this emulator's app data; never use it on a real or shared device.
No deployment may run concurrently: the installed app fetches the public
manifest itself, after this driver's checks, without an atomic release lock.
"""
import argparse
import io
import json
import os
import re
import secrets
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from contextlib import redirect_stdout
from pathlib import Path

import httpx
import android_smoke as native
import android_update as update

PRIVATE = Path('/tmp/schulpilot-own-update-fixture.json')


def require(condition, error):
    if not condition:
        raise RuntimeError(error)


def validate_preflight(old, target, installed, public, emulator):
    require(target > old, 'target_version_must_be_higher')
    require(emulator == b'1', 'only_emulator_allowed')
    require(installed == old, 'unexpected_installed_version')
    require(public == target, 'unexpected_public_target')


def is_owned_demo(demo):
    user = demo.get('user') or {}
    families = user.get('families') or []
    credentials = demo.get('credentials') or {}
    return (user.get('role') == 'parent' and bool(families)
            and all(row.get('synthetic') is True for row in families)
            and bool(re.fullmatch(r'kind-[a-f0-9]{10}', credentials.get('child_username', '')))
            and bool(re.fullmatch(r'eltern-[a-f0-9]{10}', credentials.get('parent_username', '')))
            and credentials['parent_username'][7:] == credentials['child_username'][5:]
            and bool(demo.get('token')))


def clear_emulator_app():
    # adb can return exit status 0 for Android's own "Failed" response.
    require(native.adb('shell', 'pm', 'clear', native.PACKAGE).strip() == b'Success',
            'emulator_app_cleanup_failed')


def remote_exists(path):
    require(re.fullmatch(r'/sdcard/schulpilot-update-[a-f0-9]{32}\.xml', path) is not None,
            'invalid_temporary_path')
    # The generated name contains no shell metacharacters.
    result = native.adb('shell', f'if [ -e {path} ]; then echo yes; else echo no; fi').strip()
    require(result in (b'yes', b'no'), 'temporary_path_check_failed')
    return result == b'yes'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--from-code', type=int, required=True)
    parser.add_argument('--to-code', type=int, required=True)
    parser.add_argument('--clear-dedicated-emulator-app-data', action='store_true', required=True)
    args = parser.parse_args()
    require(not PRIVATE.exists(), 'previous_fixture_requires_cleanup')
    with httpx.Client(base_url=native.BASE, headers=native.HEADERS, timeout=40) as parent:
        public = parent.get('/app-release'); public.raise_for_status()
        validate_preflight(args.from_code, args.to_code, update.installed_code(),
                           public.json()['version_code'], native.adb('shell', 'getprop', 'ro.kernel.qemu').strip())
        path = '/sdcard/schulpilot-update-' + secrets.token_hex(16) + '.xml'
        require(not remote_exists(path), 'temporary_path_already_exists')
        original_nodes, original_update_nodes, original_artifacts = native.nodes, update.nodes, native.ARTIFACTS
        made_dump = False
        def private_nodes():
            nonlocal made_dump
            for _ in range(4):
                try:
                    # Unique name was checked before any dump. No standard UI
                    # hierarchy path is read, overwritten or removed.
                    made_dump = True
                    native.adb('shell', 'uiautomator', 'dump', path)
                    return list(ET.fromstring(native.adb('exec-out', 'cat', path)).iter('node'))
                except (ET.ParseError, RuntimeError):
                    time.sleep(.3)
            raise RuntimeError('native_window_snapshot_incomplete')
        native.nodes = update.nodes = private_nodes
        demo = None
        confirmed_owned = False
        recovery_created = False
        create_requested = False
        deleted = False
        own_login_attempted = False
        report = {'synthetic_only': True, 'provider_calls_measured': False, 'cleanup_complete': False}
        try:
            native.wait('Willkommen zurück', seconds=10)
            # Reserve recovery file before server mutation; exclusive creation
            # prevents both overwriting and silent cleanup of unrelated files.
            fd = os.open(PRIVATE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            recovery_created = True
            with os.fdopen(fd, 'w') as recovery:
                create_requested = True
                response = parent.post('/demo'); response.raise_for_status(); demo = response.json()
                confirmed_owned = is_owned_demo(demo)
                json.dump(demo, recovery); recovery.flush(); os.fsync(recovery.fileno())
                require(confirmed_owned, 'synthetic_fixture_validation_failed')
            creds = demo['credentials']
            parent.headers['Authorization'] = 'Bearer ' + demo['token']
            family = parent.get('/families/' + demo['user']['families'][0]['id']); family.raise_for_status()
            require(family.json().get('synthetic') is True, 'synthetic_family_required')
            profile = next(x for x in family.json()['children'] if x['id'] == demo['child_id'])
            name = 'Updatekind' + creds['child_username'][-6:]
            payload = {k: profile[k] for k in ('grade', 'subjects', 'school_type', 'region')}
            payload['display_name'] = name
            changed = parent.put('/children/' + demo['child_id'], json=payload,
                                 headers={'If-Match': profile['profile_revision']}); changed.raise_for_status()
            before = parent.get('/materials/' + demo['material_id']); before.raise_for_status(); before = before.json()
            require(before['id'] == demo['material_id'] and before['synthetic'] and 'content' in before,
                    'synthetic_material_required')
            response = parent.get('/children/' + demo['child_id'] + '/sessions'); response.raise_for_status()
            previous = {x['id'] for x in response.json()}
            own_login_attempted = True
            native.login(creds['child_username'], creds['child_password'])
            native.wait_any(('Jetzt lernen', 'Weiterlernen', 'Freiwillig üben', 'Heute'), seconds=60)
            native.press('Konto'); native.wait('Abmelden'); native.adb('shell', 'input', 'keyevent', '4')
            response = parent.get('/children/' + demo['child_id'] + '/sessions'); response.raise_for_status()
            own_sessions = {x['id'] for x in response.json()} - previous
            require(len(own_sessions) == 1 and update.installed_code() == args.from_code, 'initial_session_invalid')
            report['signed_in_before_update'] = True
            # Re-check target before invoking the actual mutating update.
            public = parent.get('/app-release'); public.raise_for_status()
            validate_preflight(args.from_code, args.to_code, update.installed_code(),
                               public.json()['version_code'], native.adb('shell', 'getprop', 'ro.kernel.qemu').strip())
            with tempfile.TemporaryDirectory(prefix='schulpilot-update-shots-') as tmp:
                native.ARTIFACTS = Path(tmp)
                old_argv = sys.argv
                try:
                    sys.argv = ['android_update.py', '--upgrade', '--expected-version-code', str(args.to_code)]
                    output = io.StringIO()
                    with redirect_stdout(output): update.main()
                finally:
                    sys.argv = old_argv
                    native.ARTIFACTS = original_artifacts
                upgrade = json.loads(output.getvalue())
            require(upgrade['previous_code'] == args.from_code and upgrade['installed_code'] == args.to_code
                    and upgrade['system_install_confirmed'] and not upgrade['adb_install_used_for_upgrade'],
                    'unexpected_update_result')
            native.wait_any(('Jetzt lernen', 'Weiterlernen', 'Freiwillig üben', 'Heute'), seconds=60)
            native.press('Konto'); native.wait('Abmelden')
            response = parent.get('/children/' + demo['child_id'] + '/sessions'); response.raise_for_status()
            require(own_sessions <= {x['id'] for x in response.json()}, 'prior_session_missing')
            report['same_synthetic_child_session_active_after_update'] = True
            report['client_session_id_independently_observed'] = False
            after = parent.get('/materials/' + demo['material_id']); after.raise_for_status(); after = after.json()
            require(after['id'] == before['id'] and after.get('content') == before.get('content'), 'material_changed')
            report['synthetic_material_unchanged_after_update'] = True
            report['material_visible_in_app_before_and_after'] = False
            report['upgrade'] = upgrade
        finally:
            # Never remove an unverified household. If creation failed before
            # a valid response, keep the reserved recovery file for inspection.
            cleanup_errors = []
            if confirmed_owned:
                try:
                    parent.headers['Authorization'] = 'Bearer ' + demo['token']
                    response = parent.request('DELETE', '/account', json={'password': demo['credentials']['parent_password']})
                    require(response.status_code == 200, 'synthetic_family_cleanup_failed')
                    deleted = True
                    if own_login_attempted: clear_emulator_app()
                except Exception:
                    cleanup_errors.append('family_or_emulator_cleanup_failed')
            elif create_requested:
                cleanup_errors.append('fixture_creation_outcome_requires_inspection')
            if recovery_created and (deleted and not cleanup_errors or not create_requested):
                try: PRIVATE.unlink()
                except OSError: cleanup_errors.append('recovery_file_cleanup_failed')
            if made_dump:
                try:
                    native.adb('shell', 'rm', '-f', path)
                    require(not remote_exists(path), 'temporary_ui_cleanup_failed')
                except Exception:
                    cleanup_errors.append('temporary_ui_cleanup_failed')
            report['cleanup_complete'] = confirmed_owned and deleted and not cleanup_errors
            report['recovery_file_retained'] = PRIVATE.exists()
            native.nodes, update.nodes, native.ARTIFACTS = original_nodes, original_update_nodes, original_artifacts
            print(json.dumps(report), flush=True)
            if cleanup_errors: raise RuntimeError(','.join(cleanup_errors))


if __name__ == '__main__':
    main()
