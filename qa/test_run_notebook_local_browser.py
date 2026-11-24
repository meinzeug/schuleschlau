"""The opt-in notebook runner must not inherit provider or database settings."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

path = Path(__file__).with_name("run_notebook_local_browser.py")
spec = importlib.util.spec_from_file_location("notebook_local_runner", path)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class LocalRunnerSafety(unittest.TestCase):
    def test_environment_is_allowlisted_and_points_to_fresh_scratch(self):
        with patch.dict(
            "os.environ",
            {
                "TEST_DATABASE_URL": "must-not-cross",
                "OPENROUTER_API_KEY": "must-not-cross",
                "CODEX_SOCKET": "must-not-cross",
            },
            clear=False,
        ):
            env = runner.test_environment(Path("/local/web"), Path("/local/scratch"), "/local/node:/bin")
        self.assertNotIn("TEST_DATABASE_URL", env)
        self.assertNotIn("OPENROUTER_API_KEY", env)
        self.assertNotIn("CODEX_SOCKET", env)
        self.assertEqual(env["TMPDIR"], "/local/scratch")
        self.assertEqual(env["NOTEBOOK_LOCAL_BROWSER"], "1")
        self.assertEqual(env["RECALL_MOBILE_BROWSER"], "1")
        self.assertEqual(env["PARENT_PREFS_CAS_BROWSER"], "1")
        self.assertEqual(env["NOTIFICATION_LOCAL_BROWSER"], "1")
        self.assertEqual(env["SCHULBUDDY_LOCAL_BROWSER"], "1")
        self.assertEqual(env["PARENT_MULTICHILD_BROWSER"], "1")
        self.assertEqual(env["PARENT_MULTICHILD_PDF_BROWSER"], "1")
        self.assertEqual(env["AUTH_LOCAL_BROWSER"], "1")
        self.assertEqual(env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"], "1")

    def test_workflow_runs_browser_contract_against_fresh_web_build(self):
        workflow = (path.parents[1] / ".github/workflows/checks.yml").read_text()
        build = workflow.index("flutter build web --release --no-pub --no-web-resources-cdn --csp")
        install = workflow.index("npm ci --ignore-scripts --no-audit --no-fund", build)
        contract = workflow.index("python -m unittest discover -s qa -p test_run_notebook_local_browser.py", install)
        run = workflow.index("python qa/run_notebook_local_browser.py --web-dir app/build/web", contract)
        self.assertLess(build, install)
        self.assertLess(install, contract)
        self.assertLess(contract, run)

    def test_required_results_are_present_passed_and_unique(self):
        cases = (
            ("test_notebook_local_browser", "test_notebook_local_browser"),
            ("test_notebook_local_browser", "test_notebook_browser_rejects_external_database_before_import"),
            ("test_recall_mobile_browser", "test_synthetic_recall_journey_in_390px_browser"),
            ("test_recall_mobile_browser", "test_recall_browser_rejects_external_database_before_import"),
            ("test_preferences_browser_cas", "test_real_browser_preferences_cas"),
            ("test_preferences_browser_cas", "test_browser_cas_refuses_external_test_database_before_import"),
            ("test_notification_cross_device_browser", "test_browser_cross_device_notice_reads_and_round_link"),
            ("test_notification_cross_device_browser", "test_notification_browser_rejects_external_database_before_import"),
            ("test_schulbuddy_local_browser", "test_schulbuddy_source_and_saved_reply_in_mobile_browser"),
            ("test_schulbuddy_local_browser", "test_schulbuddy_browser_rejects_external_database_before_import"),
            ("test_photo_local_browser", "test_photo_picker_and_crop_in_mobile_browser"),
            ("test_parent_multichild_acceptance", "test_parent_reads_multiple_children_facts_without_creating_learning_or_provider_calls"),
            ("test_parent_multichild_acceptance", "test_parent_multichild_local_flutter_browser"),
            ("test_parent_multichild_acceptance", "test_parent_multichild_pdf_local_flutter_browser"),
            ("test_parent_multichild_acceptance", "test_browser_harness_rejects_external_test_database_before_import"),
            ("test_auth_local_browser", "test_cold_start_links_and_logout_in_two_web_sizes"),
            ("test_auth_local_browser", "test_auth_browser_rejects_external_database_before_import"),
        )
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / "results.xml"
            for defect in (None, "missing", "duplicate", "skipped", "failure", "error", "unexpected"):
                with self.subTest(defect=defect):
                    root = ElementTree.Element("testsuites")
                    suite = ElementTree.SubElement(root, "testsuite")
                    for group, name in cases[:-1] if defect == "missing" else cases:
                        case = ElementTree.SubElement(suite, "testcase", classname=group, name=name)
                    if defect in ("skipped", "failure", "error"):
                        ElementTree.SubElement(case, defect)
                    if defect == "duplicate":
                        ElementTree.SubElement(suite, "testcase", classname=cases[0][0], name=cases[0][1])
                    if defect == "unexpected":
                        ElementTree.SubElement(suite, "testcase", classname="other", name="unexpected")
                    ElementTree.ElementTree(root).write(path)
                    if defect is None:
                        runner.check_results(path)
                    else:
                        with self.assertRaises(RuntimeError):
                            runner.check_results(path)


if __name__ == "__main__":
    unittest.main()
