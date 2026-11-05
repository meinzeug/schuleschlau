"""One synthetic ready-round Android push, from a real saved job to a tap.

Requires the current signed production APK and an already prepared, explicitly
synthetic fixture with a bounded push-test grant. No arbitrary content, FCM
recipient, retries or provider calls are used. This QA tool must not be run
until the requested release is actually deployed.
"""

import argparse
import json
import os
import re
import shlex
import subprocess
import time
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpx
from android_push import (
    BACKGROUND_BODY,
    ROOT,
    PushQaError,
    api_json,
    choose_hour,
    confirm_synthetic_home,
    labels,
    load_credentials,
    native_login,
    open_device_panel,
    own_notifications,
    quiet,
    safe_write,
    seek_label,
)
from android_push_background import activity_state
from android_smoke import BASE, HEADERS, PACKAGE, adb, nodes, press, tap_node, wait

REPORT = ROOT / 'artifacts/android-demo-ready-result.json'
REMOTE = r'''
import json, os, pwd, re, shlex, sys
from pathlib import Path
try:
    raw = sys.stdin.buffer.read(16385)
    if len(raw) > 16384 or os.geteuid() != 0:
        raise ValueError('input')
    p = json.loads(raw)
    if set(p) != {'username', 'password', 'device_id', 'registered_after', 'job_id', 'unit_id', 'mode'} or p['mode'] not in ('before', 'after'):
        raise ValueError('schema')
    if not re.fullmatch(r'[a-f0-9]{32}', p['device_id']):
        raise ValueError('identifier')
    if p['mode'] == 'after' and any(not re.fullmatch(r'[a-f0-9]{32}', p[k]) for k in ('job_id', 'unit_id')):
        raise ValueError('identifier')
    if p['mode'] == 'before' and (p['job_id'] or p['unit_id']):
        raise ValueError('identifier')
    environment = {'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'}
    for line in Path('/etc/schulpilot/environment').read_text().splitlines():
        if line.strip() and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            environment[key] = ' '.join(shlex.split(value)) if value else ''
    account = pwd.getpwnam('schulpilot')
    os.initgroups('schulpilot', account.pw_gid)
    os.setgid(account.pw_gid)
    os.setuid(account.pw_uid)
    os.environ.clear()
    os.environ.update(environment)
    os.chdir('/opt/schulpilot/current/backend')
    sys.path.insert(0, os.getcwd())
    from sqlalchemy import select
    from schulpilot.db import DB, Child, Family, Job, LearningUnit, PushDelivery, PushDevice, Session, User, now
    from schulpilot.notifications import due_kinds, test_allowed
    from schulpilot.ready_notifications import authority, delivery_key, events_for_child, unit_ids
    from schulpilot.security import verify_password
    with DB() as db:
        user = db.scalar(select(User).where(User.username == p['username'].lower()))
        if not user or user.role != 'child' or not user.verified or user.disabled or not verify_password(p['password'], user.password_hash):
            raise ValueError('fixture_authentication')
        child = db.scalar(select(Child).where(Child.user_id == user.id))
        family = db.get(Family, child.family_id) if child else None
        if not family or not family.synthetic or not test_allowed(db, user.id):
            raise ValueError('synthetic_test_grant')
        device = db.scalar(select(PushDevice).where(PushDevice.id == p['device_id'], PushDevice.user_id == user.id))
        if not device or device.platform != 'android' or device.updated < int(p['registered_after']):
            raise ValueError('exact_new_device')
        session = db.get(Session, device.session_id)
        if not session or session.user_id != user.id or session.revoked or session.expires <= now() or now() - session.seen > 7 * 86400:
            raise ValueError('device_session')
        units = list(db.scalars(select(LearningUnit.id).where(LearningUnit.child_id == child.id).limit(2)))
        all_deliveries = list(db.scalars(select(PushDelivery).where(PushDelivery.device_id == device.id).limit(2)))
        if p['mode'] == 'before':
            if (units or all_deliveries or due_kinds(db, device, int(now()))
                or due_kinds(db, device, int(now()) + 600)):
                raise ValueError('fixture_not_empty_or_another_notification_due')
            print(json.dumps({'ok': True, 'empty_before': True}))
            raise SystemExit(0)
        if units != [p['unit_id']]:
            raise ValueError('round_not_unique')
        if len(all_deliveries) > 1 or any(d.kind != 'round_ready' for d in all_deliveries):
            raise ValueError('other_or_multiple_deliveries')
        job = db.get(Job, p['job_id'])
        if not job or job.child_id != child.id or job.kind != 'unit' or job.status != 'completed' or unit_ids(job) != [p['unit_id']] or not authority(db, job, child):
            raise ValueError('job_binding')
        events = [event for event in events_for_child(db, child, int(now())) if event['route'] == '/unit/' + p['unit_id']]
        if len(events) > 1:
            raise ValueError('ambiguous_event')
        deliveries = [] if not events else list(db.scalars(select(PushDelivery).where(
            PushDelivery.device_id == device.id, PushDelivery.kind == 'round_ready',
            PushDelivery.dedup_key == delivery_key(device, events[0])).limit(2)))
        if all_deliveries and (not deliveries or deliveries[0].id != all_deliveries[0].id):
            raise ValueError('unexpected_delivery_identity')
        print(json.dumps({'ok': True, 'events': len(events), 'deliveries': len(deliveries),
                          'delivery_id': deliveries[0].id if len(deliveries) == 1 else None,
                          'status': deliveries[0].status if len(deliveries) == 1 else 'missing',
                          'error': deliveries[0].error_code if len(deliveries) == 1 else None}))
except Exception as error:
    code = 'guard_' + str(error) if isinstance(error, ValueError) else 'remote_' + type(error).__name__
    print(json.dumps({'ok': False, 'code': code}))
    raise SystemExit(1)
'''


def result_for(creds, device_id, registered_after, job_id='', unit_id='', *, mode='after'):
    payload = {'username': creds['child_username'], 'password': creds['child_password'],
               'device_id': device_id, 'registered_after': registered_after,
               'job_id': job_id, 'unit_id': unit_id, 'mode': mode}
    cmd = '/opt/schulpilot/current/venv/bin/python -c ' + shlex.quote(REMOTE)
    result = subprocess.run(['ssh', 'dorfspy', cmd], input=json.dumps(payload).encode(),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=35, check=False)
    try:
        value = json.loads(result.stdout)
    except (ValueError, UnicodeDecodeError):
        raise PushQaError('observer_unreadable_no_retry') from None
    if not value.get('ok'):
        raise PushQaError('observer_guard_failed_no_retry')
    return value


def reserve_one(version):
    day = datetime.now(timezone.utc).date().isoformat()
    path = ROOT / f'artifacts/.android-demo-ready-{version}-{day}-reserved.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise PushQaError('demo_ready_already_reserved_no_replay') from None
    with os.fdopen(fd, 'w') as target:
        json.dump({'date': day, 'installed_code': version, 'reserved': True}, target)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected-code', type=int, required=True)
    parser.add_argument('--expected-commit', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-f0-9]{40}', args.expected_commit):
        raise SystemExit('A full source commit is required')
    report = {'synthetic_child_verified': False, 'native_registration': False,
              'background_before_request': False, 'explicit_round_requests': 0,
              'unit_saved': False, 'unique_delivery': False, 'fcm_accepted': False,
              'system_notice_visible': False, 'opened_unique_demo_unit': False,
              'fixture_device_removed': False, 'app_logged_out': False}
    observer, device_id, logged_in = None, None, False
    try:
        creds = load_credentials()
        with httpx.Client(base_url=BASE, headers=HEADERS, timeout=25) as public:
            health = api_json(public, 'GET', '/health')
            release = api_json(public, 'GET', '/app-release')
        if health.get('source_commit') != args.expected_commit or release.get('version_code') != args.expected_code:
            raise PushQaError('active_release_or_apk_manifest_mismatch_no_request')
        package = adb('shell', 'dumpsys', 'package', PACKAGE).decode(errors='replace')
        version = re.search(r'\bversionCode=(\d+)', package)
        if not version or int(version[1]) != args.expected_code:
            raise PushQaError('installed_version_mismatch_no_request')
        paths = adb('shell', 'pm', 'path', PACKAGE).decode().splitlines()
        if len(paths) != 1 or not paths[0].startswith('package:'):
            raise PushQaError('installed_apk_path_ambiguous_no_request')
        digest = adb('shell', 'sha256sum', paths[0][len('package:'):]).decode().split()[0]
        if not re.fullmatch(r'[a-f0-9]{64}', digest) or digest != release.get('sha256'):
            raise PushQaError('installed_apk_hash_mismatch_no_request')
        report['installed_apk_matches_release_sha256'] = True
        if own_notifications():
            raise PushQaError('preexisting_native_notification_no_request')
        observer = httpx.Client(base_url=BASE, headers=HEADERS, timeout=25)
        login = api_json(observer, 'POST', '/auth/login', json={'username': creds['child_username'],
                          'password': creds['child_password'], 'device': 'Synthetic ready-push observer'})
        observer.headers['Authorization'] = 'Bearer ' + login['token']
        user = login['user']
        if user.get('role') != 'child' or not user.get('synthetic'):
            raise PushQaError('synthetic_child_required')
        report['synthetic_child_verified'] = True
        prefs = api_json(observer, 'GET', '/children/' + user['child_id'] + '/overview')['child']['preferences']
        if not prefs.get('push_consent') or quiet(datetime.now(ZoneInfo(prefs['timezone'])), prefs['quiet_start'], prefs['quiet_end']):
            raise PushQaError('consent_or_quiet_time_blocks_test')
        if not api_json(observer, 'GET', '/notifications/config').get('available') or not api_json(observer, 'GET', '/notifications/tests').get('allowed'):
            raise PushQaError('production_push_or_synthetic_grant_not_available')
        baseline_devices = {x['id'] for x in api_json(observer, 'GET', '/notifications/devices')}
        if baseline_devices:
            raise PushQaError('fresh_fixture_must_have_no_other_devices')
        current = [x for x in api_json(observer, 'GET', '/auth/sessions') if x.get('current') is True]
        if len(current) != 1:
            raise PushQaError('observer_session_missing')
        registered_after = current[0]['created']
        # This API is only used to inspect and confirm the single fixed demo
        # source. No other source or caller-provided content is accepted here.
        materials = api_json(observer, 'GET', '/children/' + user['child_id'] + '/materials')
        if isinstance(materials, dict):
            materials = materials.get('materials', materials.get('items', []))
        if not isinstance(materials, list) or len(materials) != 1:
            raise PushQaError('single_demo_source_required')
        source = api_json(observer, 'GET', '/materials/' + materials[0]['id'])
        from schulpilot.synthetic import CONTENT
        if not source.get('synthetic') or source.get('fixed_example') or source.get('has_image') or source.get('content') != CONTENT or source.get('confirmed'):
            raise PushQaError('fixed_local_demo_source_mismatch')
        confirmed = api_json(observer, 'PUT', '/materials/' + source['id'] + '/confirm', json={
            'subject': 'Mathematik', 'topic': 'Brüche', 'content': CONTENT,
            'homework': [], 'uncertainties_resolved': True})
        if not confirmed.get('confirmed'):
            raise PushQaError('source_confirmation_missing')
        report['phase'] = 'native_login'
        safe_write(REPORT, report)
        adb('shell', 'am', 'start', '-n', PACKAGE + '/.MainActivity')
        wait('Willkommen zurück')
        native_login(creds)
        logged_in = True
        confirm_synthetic_home(user)
        open_device_panel()
        tap_node(seek_label('Gerät einstellen'))
        if 'Ruhezeit: 20:00–08:00' not in labels(nodes()):
            raise PushQaError('default_quiet_hours_not_observed')
        tap_node(seek_label('Seitenoptionen'))
        tap_node(seek_label('Zeiten & Auswahl', prefix=True))
        choose_hour('Ruhe ab')
        choose_hour('Ruhe bis')
        tap_node(seek_label('Auf diesem Gerät einschalten'))
        deadline = time.monotonic() + 65
        while time.monotonic() < deadline:
            permission = [n for n in nodes() if n.get('resource-id', '').endswith(':id/permission_allow_button')]
            if permission:
                tap_node(permission[0])
            new = [x for x in api_json(observer, 'GET', '/notifications/devices')
                   if x['id'] not in baseline_devices and x.get('platform') == 'android']
            if len(new) == 1:
                device_id = new[0]['id']
                if (new[0]['quiet_start'], new[0]['quiet_end']) != (0, 0):
                    raise PushQaError('fixture_quiet_hours_not_saved')
                report['native_registration'] = True
                break
            time.sleep(.4)
        if not device_id:
            raise PushQaError('native_registration_timeout')
        if own_notifications():
            raise PushQaError('native_notice_already_present_no_request')
        preflight = result_for(creds, device_id, registered_after, mode='before')
        if not preflight.get('empty_before'):
            raise PushQaError('fixture_preflight_not_empty_no_request')
        report['no_other_units_deliveries_or_due_categories'] = True
        before_home = float(adb('shell', 'date', '+%s.%N').decode().strip())
        adb('shell', 'input', 'keyevent', '3')
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            foreground, stopped, stopped_at = activity_state()
            if not foreground and stopped and stopped_at > before_home:
                report['background_before_request'] = True
                break
            time.sleep(.5)
        if not report['background_before_request']:
            raise PushQaError('stopped_state_not_observed_no_request')
        report['phase'] = 'one_explicit_demo_round'
        safe_write(REPORT, report)
        reserve_one(args.expected_code)
        report['explicit_round_requests'] = 1
        safe_write(REPORT, report)
        # One conscious round request, no retry even if the response is lost.
        queued = api_json(observer, 'POST', '/children/' + user['child_id'] + '/units', expected=202,
                          headers={'Idempotency-Key': uuid.uuid4().hex}, json={'material_id': source['id']})
        job_id = queued['id']
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            job = api_json(observer, 'GET', '/jobs/' + job_id)
            if job['status'] == 'completed':
                break
            if job['status'] == 'failed':
                raise PushQaError('saved_demo_job_failed_no_retry')
            time.sleep(1)
        else:
            raise PushQaError('saved_demo_job_timeout_no_retry')
        unit_id = job['result']['unit_id']
        unit = api_json(observer, 'GET', '/units/' + unit_id)
        if not unit.get('synthetic') or unit.get('status') != 'not_started' or unit.get('topic') != 'Brüche':
            raise PushQaError('saved_demo_unit_mismatch')
        report['unit_saved'] = True
        deadline = time.monotonic() + 75
        delivery = None
        while time.monotonic() < deadline:
            result = result_for(creds, device_id, registered_after, job_id, unit_id)
            if result['deliveries'] > 1:
                raise PushQaError('ambiguous_delivery_no_retry')
            if result['deliveries'] == 1:
                if delivery and delivery != result['delivery_id']:
                    raise PushQaError('delivery_changed_no_retry')
                delivery = result['delivery_id']
                report['unique_delivery'] = bool(delivery)
                if result['status'] == 'accepted':
                    report['fcm_accepted'] = True
                if result['status'] in ('failed', 'suppressed'):
                    raise PushQaError('normal_delivery_' + result['status'] + '_no_retry')
            if report['fcm_accepted'] and own_notifications():
                break
            time.sleep(1)
        if not report['fcm_accepted'] or not report['unique_delivery']:
            raise PushQaError('acceptance_not_observed_no_retry')
        adb('shell', 'cmd', 'statusbar', 'expand-notifications')
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            values = labels(nodes())
            if 'SchuleSchlau' in values and BACKGROUND_BODY in values:
                report['system_notice_visible'] = True
                break
            time.sleep(.4)
        if not report['system_notice_visible']:
            raise PushQaError('system_notice_not_visible')
        # Recheck all deliveries immediately before tapping the only notice.
        last = result_for(creds, device_id, registered_after, job_id, unit_id)
        if last['deliveries'] != 1 or last['delivery_id'] != delivery or last['status'] != 'accepted':
            raise PushQaError('unique_delivery_changed_before_tap_no_retry')
        tap_node(seek_label(BACKGROUND_BODY))
        # The title alone may also occur in a list. The saved round's
        # introductory action proves that the notification opened its detail.
        wait('Brüche')
        wait('Einheit starten')
        report['opened_unique_demo_unit'] = True
        image_path = ROOT / 'artifacts/android-demo-ready-unit.png'
        image_path.write_bytes(adb('exec-out', 'screencap', '-p'))
        image_path.chmod(0o600)
    except Exception as error:
        report['blocker'] = str(error) if isinstance(error, PushQaError) else 'unexpected_' + type(error).__name__
    finally:
        if logged_in:
            try:
                adb('shell', 'cmd', 'statusbar', 'collapse')
                adb('shell', 'am', 'start', '-n', PACKAGE + '/.MainActivity')
                for _ in range(6):
                    screen = labels(nodes())
                    if 'Auf diesem Gerät ausschalten' in screen:
                        break
                    if 'Benachrichtigungen' in screen:
                        open_device_panel()
                        break
                    adb('shell', 'input', 'keyevent', '4')
                    time.sleep(.5)
                if device_id:
                    tap_node(seek_label('Auf diesem Gerät ausschalten'))
            except Exception:
                # The observer still removes this exact device below.
                report['cleanup_ui_incomplete'] = True
            try:
                # Android back from a deep-linked unit may leave the activity;
                # reopening the app restores the account's own home shell.
                adb('shell', 'am', 'start', '-n', PACKAGE + '/.MainActivity')
                wait('Konto öffnen')
                press('Konto öffnen')
                press('Abmelden')
                wait('Willkommen zurück')
                report['app_logged_out'] = True
            except Exception:
                report['logout_ui_incomplete'] = True
        if observer:
            try:
                if device_id:
                    remaining = api_json(observer, 'GET', '/notifications/devices')
                    if any(x['id'] == device_id for x in remaining):
                        api_json(observer, 'DELETE', '/notifications/devices/' + device_id)
                    report['fixture_device_removed'] = not any(x['id'] == device_id for x in api_json(observer, 'GET', '/notifications/devices'))
                api_json(observer, 'POST', '/auth/logout')
            except Exception:
                report['cleanup_observer_incomplete'] = True
            observer.close()
        try:
            adb('shell', 'rm', '-f', '/sdcard/schulpilot-window.xml')
        except Exception:
            pass
        report['phase'] = 'finished'
        safe_write(REPORT, report)
        print(json.dumps(report))
    return int(bool(report.get('blocker') or report.get('cleanup_ui_incomplete') or report.get('logout_ui_incomplete') or report.get('cleanup_observer_incomplete')))


if __name__ == '__main__':
    raise SystemExit(main())
