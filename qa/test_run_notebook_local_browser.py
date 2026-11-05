"""The opt-in notebook runner must not inherit provider or database settings."""

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

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
        self.assertEqual(env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"], "1")


if __name__ == "__main__":
    unittest.main()
