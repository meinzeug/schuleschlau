"""Failure paths of the synthetic notebook UI runner; no Flutter or network."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PATH = Path(__file__).with_name("notebook_material_ui_test.py")
spec = importlib.util.spec_from_file_location("notebook_material_ui_runner", PATH)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class TempFile:
    def __init__(self, path, fail_write=False):
        self.name = str(path)
        self.fail_write = fail_write
        path.write_text("temporary synthetic test")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def write(self, _):
        if self.fail_write:
            raise OSError("synthetic write failure")


class RunnerCleanup(unittest.TestCase):
    def test_write_failure_removes_own_temporary_file(self):
        with tempfile.TemporaryDirectory(dir=runner.ROOT / "app/test") as directory:
            path = Path(directory) / "own-test.dart"
            fake = TempFile(path, fail_write=True)
            with (
                patch.object(runner.tempfile, "NamedTemporaryFile", return_value=fake),
                patch("sys.argv", ["runner"]),
                self.assertRaises(OSError),
            ):
                runner.main()
            self.assertFalse(path.exists())

    def test_flutter_failure_removes_own_temporary_file(self):
        with tempfile.TemporaryDirectory(dir=runner.ROOT / "app/test") as directory:
            path = Path(directory) / "own-test.dart"
            fake = TempFile(path)
            with (
                patch.object(runner.tempfile, "NamedTemporaryFile", return_value=fake),
                patch.object(runner.subprocess, "run", side_effect=RuntimeError("synthetic failure")),
                patch("sys.argv", ["runner"]),
                self.assertRaises(RuntimeError),
            ):
                runner.main()
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
