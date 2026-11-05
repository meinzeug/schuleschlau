"""Offline tests; mocks never access devices, accounts or a provider."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import android_update_session as subject


class Response:
    status_code = 200
    def __init__(self, body=None): self.body = body or {}
    def raise_for_status(self): pass
    def json(self): return self.body


class FakeApi:
    def __init__(self, *args, **kwargs): self.headers = {}; self.deleted = False
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def get(self, path):
        if path == '/app-release': return Response({'version_code': 250})
        if path.startswith('/families/'):
            return Response({'synthetic': True, 'children': [{'id': 'child', 'grade': 6, 'subjects': [], 'school_type': 'x', 'region': 'x', 'profile_revision': 'rev'}]})
        if path.startswith('/materials/'):
            return Response({'id': 'material', 'synthetic': True, 'content': 'synthetic'})
        if path.endswith('/sessions'):
            return Response([] if not hasattr(self, 'seen') else [{'id': 'session'}])
        raise AssertionError(path)
    def post(self, path):
        if path != '/demo': raise AssertionError(path)
        return Response({'user': {'role': 'parent', 'families': [{'id': 'family', 'synthetic': True}]},
                         'credentials': {'child_username': 'kind-0123456789', 'child_password': 'synthetic', 'parent_username': 'eltern-0123456789', 'parent_password': 'synthetic'},
                         'token': 'synthetic-token', 'child_id': 'child', 'material_id': 'material'})
    def put(self, *args, **kwargs): return Response()
    def request(self, method, path, **kwargs):
        if method != 'DELETE' or path != '/account': raise AssertionError(path)
        self.deleted = True
        return Response()


class TestUpdateSession(unittest.TestCase):
    def test_safety_preconditions_survive_optimized_python(self):
        script = "import android_update_session as s; s.validate_preflight(249,250,249,250,b'0')"
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).parent.resolve()))
        result = subprocess.run([sys.executable, '-O', '-c', script], env=env, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        script = "import android_update_session as s; s.validate_preflight(249,250,249,251,b'1')"
        result = subprocess.run([sys.executable, '-O', '-c', script], env=env, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        script = "import android_update_session as s; raise SystemExit(1 if s.is_owned_demo({'user':{'role':'parent','families':[{'synthetic':False}]}}) else 0)"
        self.assertEqual(subprocess.run([sys.executable, '-O', '-c', script], env=env).returncode, 0)

    def test_update_driver_refuses_changed_target_before_device_action(self):
        with patch.object(subject.update.httpx, 'get', return_value=Response({'version_code': 251})) as request, \
                patch.object(subject.update, 'adb') as adb, \
                patch.object(sys, 'argv', ['update', '--upgrade', '--expected-version-code', '250']):
            # Real httpx.Response.raise_for_status returns itself.
            request.return_value.raise_for_status = lambda: request.return_value
            with self.assertRaisesRegex(RuntimeError, 'version changed'):
                subject.update.main()
            adb.assert_not_called()

    def run_case(self, pm_result, *, file_failure=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); originals = root / 'original'; originals.mkdir()
            names = ['android-update-permission-explanation.png', 'android-update-source-consent.png', 'android-update-system-confirmation.png', 'android-updated-current-version.png']
            for name in names: (originals / name).write_bytes(b'keep')
            state = {'xml': False, 'screens': None, 'clears': 0}
            api = FakeApi()
            def adb(*args):
                if args[:2] == ('shell', 'getprop'): return b'1\n'
                if args[:2] == ('shell', 'pm'): state['clears'] += 1; return pm_result
                if args[:2] == ('shell', 'input'): return b''
                if args[:2] == ('shell', 'uiautomator'): state['xml'] = True; return b'dumped'
                if args[:2] == ('exec-out', 'cat'): return b'<hierarchy><node /></hierarchy>'
                if args[:2] == ('shell', 'rm'): state['xml'] = False; return b''
                if args[0] == 'shell' and args[1].startswith('if [ -e '): return b'yes\n' if state['xml'] else b'no\n'
                raise AssertionError(args)
            def wait(*args, **kwargs): subject.native.nodes()
            def login(*args): api.seen = True
            def upgrade():
                state['screens'] = subject.native.ARTIFACTS
                for name in names: (state['screens'] / name).write_bytes(b'created')
                print(json.dumps({'previous_code': 249, 'installed_code': 250, 'system_install_confirmed': True, 'adb_install_used_for_upgrade': False}))
            argv = ['test', '--from-code', '249', '--to-code', '250', '--clear-dedicated-emulator-app-data']
            with patch.object(subject, 'PRIVATE', root / 'fixture'), patch.object(subject.httpx, 'Client', return_value=api), \
                    patch.object(subject.native, 'ARTIFACTS', originals), patch.object(subject.native, 'adb', side_effect=adb), \
                    patch.object(subject.native, 'wait', side_effect=wait), patch.object(subject.native, 'wait_any'), \
                    patch.object(subject.native, 'press'), patch.object(subject.native, 'login', side_effect=login), \
                    patch.object(subject.update, 'installed_code', return_value=249), patch.object(subject.update, 'main', side_effect=upgrade), \
                    patch.object(sys, 'argv', argv):
                if file_failure:
                    with patch.object(subject.json, 'dump', side_effect=OSError('synthetic file failure')):
                        with self.assertRaises(OSError): subject.main()
                elif pm_result.strip() == b'Success': subject.main()
                else:
                    with self.assertRaisesRegex(RuntimeError, 'cleanup_failed'): subject.main()
            self.assertTrue(api.deleted)
            self.assertFalse(state['xml'])
            if state['screens'] is not None: self.assertFalse(state['screens'].exists())
            for name in names: self.assertEqual((originals / name).read_bytes(), b'keep')
            self.assertEqual((root / 'fixture').exists(), pm_result.strip() != b'Success')
            if file_failure: self.assertEqual(state['clears'], 0)

    def test_screens_and_ui_dump_are_isolated_and_cleaned(self): self.run_case(b'Success\n')
    def test_pm_failure_cannot_claim_cleanup(self): self.run_case(b'Failed\n')
    def test_fixture_write_failure_cleans_only_verified_household(self): self.run_case(b'Success\n', file_failure=True)

    def test_unknown_creation_outcome_keeps_recovery_without_deleting(self):
        with tempfile.TemporaryDirectory() as tmp:
            api = FakeApi()
            def adb(*args):
                if args[:2] == ('shell', 'getprop'): return b'1\n'
                if args[0] == 'shell' and args[1].startswith('if [ -e '): return b'no\n'
                raise AssertionError(args)
            argv = ['test', '--from-code', '249', '--to-code', '250', '--clear-dedicated-emulator-app-data']
            with patch.object(subject, 'PRIVATE', Path(tmp) / 'fixture'), \
                    patch.object(subject.httpx, 'Client', return_value=api), \
                    patch.object(api, 'post', side_effect=TimeoutError('synthetic timeout')), \
                    patch.object(subject.native, 'adb', side_effect=adb), \
                    patch.object(subject.native, 'wait'), \
                    patch.object(subject.update, 'installed_code', return_value=249), \
                    patch.object(sys, 'argv', argv):
                with self.assertRaisesRegex(RuntimeError, 'requires_inspection'): subject.main()
            self.assertTrue((Path(tmp) / 'fixture').exists())
            self.assertFalse(api.deleted)


if __name__ == '__main__': unittest.main()
