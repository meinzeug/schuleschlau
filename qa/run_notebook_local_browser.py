#!/usr/bin/env python3
"""Run the synthetic notebook and learning journeys in a local pytest sandbox."""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_environment(web_dir, scratch, path):
    """An allowlist excludes inherited DB/provider/credential settings."""
    return {
        "PATH": path,
        "LANG": "C.UTF-8",
        "TMPDIR": str(scratch),
        "WEB_DIR": str(web_dir),
        "NOTEBOOK_LOCAL_BROWSER": "1",
        "RECALL_MOBILE_BROWSER": "1",
        "PYTHONPATH": str(ROOT / "backend"),
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web-dir", required=True, type=Path, help="Locally built Flutter web release directory")
    parser.add_argument("--scratch-root", type=Path, help="Optional parent for disposable test directory")
    args = parser.parse_args()
    web_dir = args.web_dir.resolve(strict=True)
    if not (web_dir / "main.dart.js").is_file():
        parser.error("web directory needs a local main.dart.js")
    with tempfile.TemporaryDirectory(prefix="notebook-browser-", dir=args.scratch_root) as scratch:
        subprocess.run(
            [
                sys.executable, "-m", "pytest", "-q",
                "backend/tests/test_notebook_local_browser.py",
                "backend/tests/test_recall_mobile_browser.py",
                "--tb=short", "-ra", "--junitxml", str(Path(scratch) / "browser-results.xml"),
            ],
            cwd=ROOT,
            env=test_environment(web_dir, Path(scratch), str(Path(shutil_node()).parent) + ":" + os.defpath),
            check=True,
        )
        check_results(Path(scratch) / "browser-results.xml")


def check_results(path):
    """Refuse a successful process that omitted or skipped a required journey."""
    from xml.etree import ElementTree

    required = {
        ("test_notebook_local_browser", "test_notebook_local_browser"),
        ("test_notebook_local_browser", "test_notebook_browser_rejects_external_database_before_import"),
        ("test_recall_mobile_browser", "test_synthetic_recall_journey_in_390px_browser"),
        ("test_recall_mobile_browser", "test_recall_browser_rejects_external_database_before_import"),
    }
    root = ElementTree.parse(path).getroot()
    seen = set()
    for case in root.iter("testcase"):
        key = (case.get("classname", "").split(".")[-1], case.get("name"))
        if key not in required or key in seen or any(case.find(tag) is not None for tag in ("skipped", "failure", "error")):
            raise RuntimeError(f"Incomplete or unexpected browser test result: {key}")
        seen.add(key)
    if seen != required:
        raise RuntimeError(f"Missing browser test results: {sorted(required - seen)}")


def shutil_node():
    import shutil

    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js 20+ is required for Playwright")
    return node


if __name__ == "__main__":
    main()
