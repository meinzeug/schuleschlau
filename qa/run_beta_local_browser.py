#!/usr/bin/env python3
"""Repeat the synthetic beta browser journey with a disposable database.

This is not an acceptance of SMTP delivery, a live AI provider or production
beta enrollment. The only mailbox and learning unit are local test fixtures.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {"test_beta_browser_journey", "test_beta_browser_rejects_external_database_before_import"}


def validate_results(path):
    found = set()
    for case in ElementTree.parse(path).getroot().iter("testcase"):
        name = case.get("name")
        if (
            name not in REQUIRED
            or name in found
            or any(case.find(x) is not None for x in ("skipped", "failure", "error"))
        ):
            raise RuntimeError("Beta browser test incomplete or unexpected: " + str(name))
        found.add(name)
    if found != REQUIRED:
        raise RuntimeError("Missing beta browser checks: " + ", ".join(sorted(REQUIRED - found)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web-dir", type=Path, required=True)
    parser.add_argument("--scratch-root", type=Path)
    args = parser.parse_args()
    web = args.web_dir.resolve(strict=True)
    if not (web / "main.dart.js").is_file():
        parser.error("web directory needs a locally built main.dart.js")
    node = shutil.which("node")
    if not node:
        parser.error("Node.js and the locked qa dependencies are required")
    with tempfile.TemporaryDirectory(prefix="beta-browser-", dir=args.scratch_root) as scratch:
        report = Path(scratch) / "results.xml"
        env = {
            "PATH": str(Path(node).parent) + ":" + os.defpath,
            "LANG": "C.UTF-8",
            "TMPDIR": scratch,
            "WEB_DIR": str(web),
            "BETA_LOCAL_BROWSER": "1",
            "PYTHONPATH": str(ROOT / "backend"),
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        }
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "backend/tests/test_beta_browser_journey.py",
                "--tb=short",
                "--junitxml",
                str(report),
            ],
            cwd=ROOT,
            env=env,
            check=True,
        )
        validate_results(report)


if __name__ == "__main__":
    main()
