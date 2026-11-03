"""Regression tests for the isolated restoration upload boundary."""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("reconcile_restore", ROOT / "scripts/reconcile_restore.py")
reconcile_restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reconcile_restore)


@pytest.fixture
def upload_trees(tmp_path, monkeypatch):
    live = tmp_path / "live" / "uploads"
    child = live / "subdirectory"
    child.mkdir(parents=True)
    separate = tmp_path / "restore" / "uploads"
    separate.mkdir(parents=True)
    monkeypatch.setattr(reconcile_restore, "LIVE_UPLOADS", live)
    return live, child, separate


def test_separate_restore_copy_is_allowed(upload_trees):
    _, _, separate = upload_trees
    assert reconcile_restore.isolated_uploads(separate) == separate.resolve()


@pytest.mark.parametrize("path_name", ["live", "child", "parent"])
def test_live_upload_tree_and_ancestors_are_refused(upload_trees, path_name):
    live, child, _ = upload_trees
    target = {"live": live, "child": child, "parent": live.parent}[path_name]
    with pytest.raises(ValueError, match="live upload tree"):
        reconcile_restore.isolated_uploads(target)


def test_parent_symlink_cannot_hide_live_subdirectory(tmp_path, upload_trees):
    live, _, _ = upload_trees
    alias = tmp_path / "alias"
    alias.symlink_to(live, target_is_directory=True)
    with pytest.raises(ValueError, match="live upload tree"):
        reconcile_restore.isolated_uploads(alias / "subdirectory")


def test_final_symlink_is_refused_even_for_separate_copy(tmp_path, upload_trees):
    _, _, separate = upload_trees
    alias = tmp_path / "restore-alias"
    alias.symlink_to(separate, target_is_directory=True)
    with pytest.raises(ValueError, match="must not be a symlink"):
        reconcile_restore.isolated_uploads(alias)


def test_configured_data_directory_is_also_protected(tmp_path, upload_trees, monkeypatch):
    configured = tmp_path / "configured" / "uploads"
    configured.mkdir(parents=True)
    monkeypatch.setenv("DATA_DIR", str(configured.parent))
    with pytest.raises(ValueError, match="live upload tree"):
        reconcile_restore.isolated_uploads(configured)


def test_missing_and_non_directory_uploads_are_refused(tmp_path, upload_trees):
    with pytest.raises(ValueError, match="Cannot resolve"):
        reconcile_restore.isolated_uploads(tmp_path / "missing")
    regular_file = tmp_path / "file"
    regular_file.write_text("not a directory")
    with pytest.raises(ValueError, match="existing directory"):
        reconcile_restore.isolated_uploads(regular_file)


def test_cli_rejects_live_child_before_database_or_file_changes(monkeypatch, upload_trees):
    _, child, _ = upload_trees
    photo = child / "important.jpg"
    photo.write_bytes(b"not a real image")
    monkeypatch.setenv("DATABASE_URL", "untouched")
    monkeypatch.setattr(sys, "argv", [
        "reconcile_restore.py", "--database-url", "sqlite:///unsafe_restore_test",
        "--ledger", "missing-ledger", "--master-key-file", "missing-key", "--uploads", str(child),
    ])
    with pytest.raises(SystemExit) as error:
        reconcile_restore.main()
    assert error.value.code == 2
    assert photo.read_bytes() == b"not a real image"
    assert reconcile_restore.os.environ["DATABASE_URL"] == "untouched"
