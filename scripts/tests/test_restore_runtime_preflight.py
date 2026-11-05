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
    assert "Synthetic restored-conversation retention: OK" in result.stdout
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("fault", ["no_delete", "boundary", "wrong_period"])
def test_preflight_rejects_broken_conversation_expiry(tmp_path, fault):
    if fault == "no_delete":
        replacement = "def broken(db, current):\n return {m.__tablename__: 1 for m in (retention.TutorTurn, retention.SchulbuddyTurn, retention.ParentLearningReview)}\n"
    elif fault == "boundary":
        replacement = "original = retention.purge_expired\ndef broken(db, current):\n return original(db, current + 1)\n"
    else:
        replacement = "retention.RETENTION_SECONDS = 364 * 86400\n"
    (tmp_path / "sitecustomize.py").write_text(
        "import schulpilot.conversation_retention as retention\n" + replacement
        + ("retention.purge_expired = broken\n" if fault != "wrong_period" else "")
    )
    result = run_preflight(tmp_path, PYTHONPATH=os.pathsep.join((str(tmp_path), str(ROOT / "backend"))))
    assert result.returncode != 0
    assert any(message in result.stderr for message in (
        "Synthetic tutor_turns retention failed", "Synthetic conversation expiry counts failed",
        "Unexpected synthetic conversation retention period"))


def test_preflight_does_not_import_pytest(tmp_path):
    (tmp_path / "sitecustomize.py").write_text(
        "import sys\n"
        "class BlockTestPackages:\n"
        " def find_spec(self, fullname, path=None, target=None):\n"
        "  if fullname == 'pytest' or fullname.startswith('_pytest'):\n"
        "   raise RuntimeError('pytest is not available in the runtime')\n"
        "sys.meta_path.insert(0, BlockTestPackages())\n"
    )
    result = run_preflight(tmp_path, PYTHONPATH=os.pathsep.join((str(tmp_path), str(ROOT / "backend"))))
    assert result.returncode == 0, result.stderr
    assert "Synthetic restored-conversation retention: OK" in result.stdout


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
