"""The preflight is an isolated test, never an alternate production DB client."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def run_preflight(tmp_path, **changes):
    env = {
        "PATH": os.defpath,
        "PYTHONPATH": str(ROOT / "backend"),
        "DATABASE_URL": "sqlite://",
        "ENVIRONMENT": "test",
        "MASTER_KEY": "synthetic-key-not-a-production-secret",
        "DATA_DIR": str(tmp_path),
    }
    env.update(changes)
    return subprocess.run([sys.executable, str(ROOT / "deploy/verify_restore_runtime.py")],
                          env=env, cwd=ROOT, capture_output=True, text=True, timeout=45)


def test_preflight_exercises_signed_deletions_without_creating_a_database(tmp_path):
    result = run_preflight(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "Synthetic signed vocabulary erasures: OK" in result.stdout
    assert "Synthetic signed visual-review erasures: OK" in result.stdout
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("changes", [
    {"DATABASE_URL": "postgresql://example.invalid/production"},
    {"DATABASE_URL": "sqlite:///real.sqlite"},
    {"ENVIRONMENT": "production"},
    {"MASTER_KEY": "not-the-synthetic-key"},
    {"DATA_DIR": ""},
])
def test_preflight_refuses_non_synthetic_environment_before_import(tmp_path, changes):
    result = run_preflight(tmp_path, **changes)
    assert result.returncode != 0
    assert "Explicit synthetic test environment is required" in result.stderr
    assert not list(tmp_path.iterdir())
