"""Local-only guards; no emulator, account login or Firebase calls."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import android_push
import android_push_background
import android_push_foreground
import prepare_android_push_foreground


class AndroidPushGuardsTest(unittest.TestCase):
    def test_home_identity_requires_synthetic_marker_and_matching_greeting(self):
        def node(text):
            return {"text": text, "content-desc": ""}
        demo = node("Demo · nur Beispieldaten")
        greeting = node("Hallo, Mika (Beispiel)!")
        user = {"synthetic": True, "display_name": "Mika (Beispiel)"}
        self.assertTrue(android_push.synthetic_home_matches([demo, greeting], user))
        self.assertFalse(android_push.synthetic_home_matches([greeting], user))
        self.assertFalse(android_push.synthetic_home_matches([demo, greeting], {**user, "synthetic": False}))
        self.assertFalse(android_push.synthetic_home_matches([demo, greeting], {**user, "display_name": "Andere"}))

    def test_login_fields_wait_for_complete_semantics_tree(self):
        field = {"class": "android.widget.EditText"}
        with patch.object(android_push, "nodes", side_effect=[[], [field], [field, field]]), patch.object(
            android_push.time, "sleep"
        ):
            self.assertEqual(len(android_push.login_fields()), 2)

    def test_login_fields_fail_safely_if_form_never_appears(self):
        with patch.object(android_push, "nodes", return_value=[]), patch.object(
            android_push.time, "monotonic", side_effect=[0, 0, 2]
        ), patch.object(android_push.time, "sleep"):
            with self.assertRaisesRegex(android_push.PushQaError, "native_login_fields_not_ready"):
                android_push.login_fields(timeout=1)

    def test_credentials_accept_old_and_explicit_synthetic_wrapped_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            credentials = {"child_username": "synthetic_child", "child_password": "synthetic_only"}
            for fixture in (credentials, {"synthetic_only": True, "credentials": credentials}):
                android_push.safe_write(path, fixture)
                self.assertEqual(android_push.load_credentials(path), credentials)
            android_push.safe_write(path, {"synthetic_only": False, "credentials": credentials})
            with self.assertRaises(android_push.PushQaError):
                android_push.load_credentials(path)
            android_push.safe_write(path, credentials)
            os.chmod(path, 0o644)
            with self.assertRaises(android_push.PushQaError):
                android_push.load_credentials(path)

    def test_send_claim_survives_missing_summary_after_interruption(self):
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "summary.json"
            with patch.object(android_push, "CHECKPOINT", checkpoint):
                self.assertEqual(android_push.mark_send(84), 1)
                checkpoint.unlink()  # Simulated crash before the summary write.
                with self.assertRaisesRegex(android_push.PushQaError, "already_reserved"):
                    android_push.mark_send(84)

    def test_normal_send_limit_is_two_and_cannot_be_reset_by_new_instance(self):
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "summary.json"
            with patch.object(android_push, "CHECKPOINT", checkpoint):
                self.assertEqual(android_push.mark_send(84), 1)
                self.assertEqual(android_push.mark_send(84), 2)
                with self.assertRaisesRegex(android_push.PushQaError, "two_send_intents"):
                    android_push.mark_send(84)
                claims = list(Path(directory).glob(".android-push-*-send-*.json"))
                self.assertEqual(len(claims), 2)
                self.assertTrue(all(path.stat().st_mode & 0o777 == 0o600 for path in claims))

    def test_background_claim_survives_missing_legacy_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "artifacts").mkdir()
            with patch.object(android_push_background, "ROOT", root):
                android_push_background.reserve_one(84)
                (root / "artifacts/.android-push-background-84-checkpoint.json").unlink()
                with self.assertRaisesRegex(android_push.PushQaError, "already_reserved"):
                    android_push_background.reserve_one(84)

    def test_foreground_send_can_only_be_reserved_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(android_push_foreground, "ROOT", root):
                android_push_foreground.reserve_one(243)
                claims = list((root / "artifacts").glob(".android-push-foreground-*-reserved.json"))
                self.assertEqual(len(claims), 1)
                self.assertEqual(claims[0].stat().st_mode & 0o777, 0o600)
                with self.assertRaisesRegex(android_push.PushQaError, "already_reserved"):
                    android_push_foreground.reserve_one(243)

    def test_foreground_observer_rejects_ambiguous_or_changed_deliveries(self):
        progress = android_push_foreground.delivery_progress
        self.assertEqual(progress({"matching_deliveries": 0, "status": "missing"}, None), (None, False))
        self.assertEqual(progress({"matching_deliveries": 1, "status": "queued", "delivery_id": "first"}, None), ("first", False))
        self.assertEqual(progress({"matching_deliveries": 1, "status": "accepted", "delivery_id": "first"}, "first"), ("first", True))
        for state, previous in (
            ({"matching_deliveries": 2, "status": "accepted", "delivery_id": "first"}, None),
            ({"matching_deliveries": 1, "status": "accepted", "delivery_id": "second"}, "first"),
            ({"matching_deliveries": 0, "status": "missing"}, "first"),
            ({"matching_deliveries": 1, "status": "accepted"}, None),
            ({"matching_deliveries": 1, "status": "failed", "delivery_id": "first"}, None),
        ):
            with self.assertRaises(android_push.PushQaError):
                progress(state, previous)

    def test_fixture_credentials_survive_failed_identity_check(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            response = {"credentials": {"parent_username": "artificial", "parent_password": "test"},
                        "user": {"role": "parent", "families": []}}
            prepare_android_push_foreground.store_response(path, response)
            self.assertFalse(prepare_android_push_foreground.is_own_synthetic_parent(response["user"]))
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(path.read_text())["credentials"], response["credentials"])
            with self.assertRaises(FileExistsError):
                prepare_android_push_foreground.store_response(path, response)
            good = {"role": "parent", "families": [{"synthetic": True, "permission": "owner"}]}
            self.assertTrue(prepare_android_push_foreground.is_own_synthetic_parent(good))
            self.assertFalse(prepare_android_push_foreground.is_own_synthetic_parent(
                {"role": "parent", "families": [{"synthetic": False, "permission": "owner"}]}))

    def test_cold_process_requires_pid_absence_without_force_stop(self):
        gone = type("Result", (), {"returncode": 1, "stdout": b""})()
        with patch.object(android_push_background, "adb") as adb, patch.object(
            android_push_background.subprocess, "run", return_value=gone
        ) as run:
            android_push_background.stop_cached_process()
            adb.assert_called_once_with("shell", "am", "kill", android_push_background.PACKAGE)
            self.assertIn("pidof", run.call_args.args[0])

    def test_unreadable_device_state_does_not_allow_cold_send(self):
        error = type("Result", (), {"returncode": 2, "stdout": b""})()
        with patch.object(android_push_background, "adb"), patch.object(
            android_push_background.subprocess, "run", return_value=error
        ):
            with self.assertRaisesRegex(android_push.PushQaError, "no_message_sent"):
                android_push_background.stop_cached_process()


if __name__ == "__main__":
    unittest.main()
