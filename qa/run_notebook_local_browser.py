#!/usr/bin/env python3
"""Run the notebook browser regression in a fresh, local-only pytest sandbox."""

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
            [sys.executable, "-m", "pytest", "-q", "backend/tests/test_notebook_local_browser.py", "--tb=short"],
            cwd=ROOT,
            env=test_environment(web_dir, Path(scratch), str(Path(shutil_node()).parent) + ":" + os.defpath),
            check=True,
        )


def shutil_node():
    import shutil

    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js 20+ is required for Playwright")
    return node


if __name__ == "__main__":
    main()
