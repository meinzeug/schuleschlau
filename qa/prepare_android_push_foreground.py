"""Create or remove only this test's synthetic family and short-lived grant.

Credentials are persisted before validating the returned account or invoking
an operator command, so those later failures remain recoverable. A transport
failure before the create response arrives is ambiguous and never retried.
"""

import argparse
import json
import os
import subprocess
from pathlib import Path

import httpx
from android_smoke import BASE, HEADERS

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = Path(os.environ.get('SCHULPILOT_QA_PUSH_CREDENTIALS', str(ROOT / 'artifacts/.push-foreground-fixture.json'))).expanduser()
REMOTE = "sudo sh -c 'set -a; . /etc/schulpilot/environment; cd /opt/schulpilot/current/backend; exec sudo -E -u schulpilot /opt/schulpilot/current/venv/bin/python -m schulpilot.firebase_ops grant-synthetic-test'"


def is_own_synthetic_parent(user):
    families = user.get('families')
    return bool(user.get('role') == 'parent' and isinstance(families, list) and len(families) == 1
                and families[0].get('synthetic') is True and families[0].get('permission') == 'owner')


def store_response(path, response):
    """O_EXCL also prevents replacing an earlier recoverable fixture."""
    credentials = response.get('credentials')
    if not isinstance(credentials, dict):
        raise RuntimeError('demo_credentials_missing_cannot_cleanup_automatically')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w') as target:
        json.dump({'synthetic_only': True, 'credentials': credentials}, target)
        target.flush()
        os.fsync(target.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cleanup', action='store_true')
    args = parser.parse_args()
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=30) as client:
        if args.cleanup:
            data = json.loads(PRIVATE.read_text())
            if data.get('synthetic_only') is not True:
                raise RuntimeError('not_an_explicit_synthetic_fixture')
            credentials = data['credentials']
            result = client.post('/auth/login', json={'username': credentials['parent_username'],
                                                      'password': credentials['parent_password']})
            result.raise_for_status()
            session = result.json()
            if not is_own_synthetic_parent(session['user']):
                raise RuntimeError('only_own_synthetic_parent_can_be_cleaned')
            client.headers['Authorization'] = 'Bearer ' + session['token']
            result = client.request('DELETE', '/account', json={'password': credentials['parent_password']})
            result.raise_for_status()
            PRIVATE.unlink()
            print(json.dumps({'synthetic_test_family_deleted': True, 'fixture_credentials_removed': True}))
            return
        if PRIVATE.exists():
            raise RuntimeError('existing_fixture_must_be_cleaned_before_new_account')
        result = client.post('/demo')  # Exactly once. No retry after ambiguous transport failure.
        result.raise_for_status()
        data = result.json()
        store_response(PRIVATE, data)
        if not is_own_synthetic_parent(data.get('user', {})):
            raise RuntimeError('demo_identity_unexpected_credentials_retained_for_manual_cleanup')
        request = json.dumps({'username': data['credentials']['parent_username']}).encode()
        grant = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'dorfspy', REMOTE],
                               input=request, capture_output=True, timeout=35, check=False)
        if grant.returncode:
            raise RuntimeError('test_grant_failed_credentials_retained_for_cleanup')
        result = json.loads(grant.stdout)
        if result.get('synthetic_test_accounts_granted') != 2 or result.get('production_push_approval_changed') is not False:
            raise RuntimeError('test_grant_unexpected_credentials_retained_for_cleanup')
        print(json.dumps({'synthetic_test_family_created': True, 'bounded_test_grant': True}))


if __name__ == '__main__':
    main()
