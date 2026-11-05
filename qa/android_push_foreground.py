"""One foreground-only neutral FCM test on a dedicated synthetic emulator.

The test uses the existing child UI and exactly one atomic send reservation.
FCM acceptance, the in-app callback and the native notification are separate
observations. The fixed server-side observer binds the result to the exact new
Android device and its session; it never returns a token or notification payload.
Unknown send outcomes are not retried.
"""

import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpx
from android_push import (
    BACKGROUND_BODY,
    NEUTRAL,
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
from android_push_background import activity_state, protected_request
from android_smoke import BASE, HEADERS, PACKAGE, adb, nodes, press, tap_node, wait

REPORT = ROOT / 'artifacts/android-push-foreground-result.json'


def reserve_one(version):
    day = datetime.now(timezone.utc).date().isoformat()
    path = ROOT / f'artifacts/.android-push-foreground-{version}-{day}-reserved.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise PushQaError('foreground_send_already_reserved_no_replay') from None
    with os.fdopen(fd, 'w') as target:
        json.dump({'date': day, 'installed_code': version, 'reserved': True}, target)


def delivery_progress(result, previous_id):
    """Keep acceptance bound to one unchanged delivery of this new device."""
    if result.get('matching_deliveries', 0) > 1:
        raise PushQaError('multiple_device_deliveries_ambiguous_no_retry')
    if result.get('matching_deliveries') != 1:
        if previous_id:
            raise PushQaError('delivery_disappeared_no_retry')
        return previous_id, False
    delivery_id = result.get('delivery_id')
    if not delivery_id or previous_id and delivery_id != previous_id:
        raise PushQaError('delivery_identity_changed_no_retry')
    if result.get('status') in ('failed', 'suppressed'):
        raise PushQaError('delivery_' + result['status'] + '_no_retry')
    return delivery_id, result.get('status') == 'accepted'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected-code', type=int, required=True)
    args = parser.parse_args()
    report = {'installed_code': None, 'synthetic_child_verified': False,
              'native_registration': False, 'foreground_before_tap': False,
              'queue_attempts': 0, 'unique_delivery': False, 'fcm_accepted': False,
              'foreground_in_app_visible': False, 'foreground_android_visible': False,
              'resumed_after_delivery': False, 'fixture_device_removed': False,
              'app_logged_out': False}
    observer = None
    native_logged_in = False
    device_id = None
    try:
        creds = load_credentials()
        package = adb('shell', 'dumpsys', 'package', PACKAGE).decode(errors='replace')
        version = re.search(r'\bversionCode=(\d+)', package)
        if not version or int(version[1]) != args.expected_code:
            raise PushQaError('installed_version_mismatch_no_send')
        report['installed_code'] = int(version[1])
        observer = httpx.Client(base_url=BASE, headers=HEADERS, timeout=25)
        session = api_json(observer, 'POST', '/auth/login', json={
            'username': creds['child_username'], 'password': creds['child_password'],
            'device': 'Isolated foreground push QA observer'})
        observer.headers['Authorization'] = 'Bearer ' + session['token']
        user = session['user']
        if user.get('role') != 'child' or not user.get('synthetic'):
            raise PushQaError('artificial_child_required_no_send')
        report['synthetic_child_verified'] = True
        prefs = api_json(observer, 'GET', '/children/' + user['child_id'] + '/overview')['child']['preferences']
        if not prefs.get('push_consent') or quiet(datetime.now(ZoneInfo(prefs['timezone'])), prefs['quiet_start'], prefs['quiet_end']):
            raise PushQaError('fixture_consent_or_quiet_policy_blocks_test')
        if not api_json(observer, 'GET', '/notifications/config').get('available') or not api_json(observer, 'GET', '/notifications/tests').get('allowed'):
            raise PushQaError('fixture_push_test_not_enabled')
        baseline_devices = {x['id'] for x in api_json(observer, 'GET', '/notifications/devices')}
        sessions = api_json(observer, 'GET', '/auth/sessions')
        current = [x for x in sessions if x.get('current') is True]
        if len(current) != 1:
            raise PushQaError('server_observer_session_anchor_missing')
        registered_after = current[0]['created']
        if own_notifications():
            raise PushQaError('preexisting_native_notifications_no_send')
        report['phase'] = 'native_login'
        safe_write(REPORT, report)
        adb('shell', 'am', 'start', '-n', PACKAGE + '/.MainActivity')
        wait('Willkommen zurück')
        native_login(creds)
        native_logged_in = True
        confirm_synthetic_home(user)
        open_device_panel()
        report['phase'] = 'native_opt_in'
        safe_write(REPORT, report)
        tap_node(seek_label('Gerät einstellen'))
        if 'Ruhezeit: 20:00–08:00' not in labels(nodes()):
            raise PushQaError('default_device_quiet_hours_not_observed')
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
                    raise PushQaError('fixture_device_quiet_hours_not_saved')
                report['native_registration'] = True
                break
            time.sleep(.4)
        if not device_id:
            raise PushQaError('native_registration_timeout')
        initial = protected_request(creds, device_id, registered_after, 'status')
        if initial.get('status') != 'missing' or initial.get('matching_deliveries') != 0:
            raise PushQaError('new_device_already_has_test_delivery_no_send')
        if own_notifications():
            raise PushQaError('native_notification_appeared_before_send')
        button = seek_label('Test an dieses Gerät senden')
        if not activity_state()[0]:
            raise PushQaError('activity_not_resumed_before_send')
        report['foreground_before_tap'] = True
        report['phase'] = 'one_foreground_send'
        safe_write(REPORT, report)
        reserve_one(report['installed_code'])
        report['queue_attempts'] = 1
        safe_write(REPORT, report)
        tap_node(button)
        deadline = time.monotonic() + 55
        delivery = None
        while time.monotonic() < deadline:
            report['foreground_in_app_visible'] |= NEUTRAL in labels(nodes())
            result = protected_request(creds, device_id, registered_after, 'status')
            delivery, accepted = delivery_progress(result, delivery)
            report['unique_delivery'] = bool(delivery)
            report['fcm_accepted'] |= accepted
            if report['fcm_accepted'] and own_notifications():
                break
            time.sleep(.4)
        report['resumed_after_delivery'] = activity_state()[0]
        if not report['fcm_accepted'] or not report['unique_delivery']:
            raise PushQaError('unique_fcm_acceptance_not_observed_no_retry')
        adb('shell', 'cmd', 'statusbar', 'expand-notifications')
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            values = labels(nodes())
            if 'SchuleSchlau' in values and BACKGROUND_BODY in values:
                report['foreground_android_visible'] = True
                break
            time.sleep(.4)
        if report['foreground_android_visible']:
            image_path = ROOT / 'artifacts/android-foreground-push-evidence.png'
            image_path.write_bytes(adb('exec-out', 'screencap', '-p'))
            image_path.chmod(0o600)
        if not (report['foreground_android_visible'] and report['foreground_in_app_visible']
                and report['resumed_after_delivery']):
            raise PushQaError('foreground_native_delivery_not_fully_observed')
    except Exception as error:
        report['blocker'] = str(error) if isinstance(error, PushQaError) else 'unexpected_' + type(error).__name__
    finally:
        if native_logged_in:
            try:
                adb('shell', 'cmd', 'statusbar', 'collapse')
                adb('shell', 'am', 'start', '-n', PACKAGE + '/.MainActivity')
                open_device_panel()
                if device_id:
                    tap_node(seek_label('Auf diesem Gerät ausschalten'))
                press('Konto öffnen')
                press('Abmelden')
                wait('Willkommen zurück')
                report['app_logged_out'] = True
            except Exception:
                report['cleanup_ui_incomplete'] = True
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
    return int(bool(report.get('blocker') or report.get('cleanup_ui_incomplete') or report.get('cleanup_observer_incomplete')))


if __name__ == '__main__':
    raise SystemExit(main())
