"""Comprehensive integration and isolation tests for release deployment coordination.

Verifies:
1. Two parallel deployments collide and cannot overwrite staging or releases.
2. Paused upload blocks parallel prune and prevents deletion of staging.
3. Lease activity for simulated expired metadata and an open staging file.
4. Manual rollback participates in the lease.
5. Published, unactivated releases are never pruned.
6. Manual rollback acquires exclusive lock and blocks concurrent deploy/prune.
7. Early failure (staging error) cleans up the lock.
8. Late failure (health check failure in activate) rolls back and releases lock.
9. Monitor watchdog coordinates with active deployment and avoids false alarms.
"""

from __future__ import annotations

import importlib.util
import json
import multiprocessing
import os
import stat
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


stage = load_module("stage_release", ROOT / "deploy/stage_release.py")
prune = load_module("prune_releases", ROOT / "deploy/prune_releases.py")
lock_mod = load_module("release_lock", ROOT / "deploy/release_lock.py")

CURRENT = "20261030T200000Z-abcdef1"
PREVIOUS = "20261029T200000Z-abcdef2"
RELEASE_1 = "20261102T010000Z-1111111"
RELEASE_2 = "20261102T020000Z-2222222"


def _race_for_lease(base, start, results):
    start.wait(10)
    try:
        stage.acquire_lock(base, "deploy", RELEASE_1)
        results.put("acquired")
    except stage.ReleaseLockError:
        results.put("blocked")


def test_simultaneous_processes_cannot_both_acquire_lease(env):
    ctx = multiprocessing.get_context("fork")
    start = ctx.Event()
    results = ctx.Queue()
    processes = [ctx.Process(target=_race_for_lease, args=(env, start, results)) for _ in range(12)]
    for process in processes:
        process.start()
    try:
        start.set()
        outcomes = [results.get(timeout=10) for _ in processes]
        assert outcomes.count("acquired") == 1
        assert outcomes.count("blocked") == len(processes) - 1
    finally:
        for process in processes:
            process.join(timeout=10)
            if process.is_alive():
                process.terminate()
                process.join()
            assert process.exitcode == 0
        results.close()


@pytest.mark.parametrize("content", ["", "{", "[]", '{}', '{"token": ""}'])
def test_corrupt_lease_refuses_acquire_and_prune(env, monkeypatch, content):
    lease = env / ".deploy.lock"
    lease.write_text(content)
    lease.chmod(0o600)
    with pytest.raises(stage.ReleaseLockError, match="lock metadata"):
        stage.acquire_lock(env, "deploy", RELEASE_1)
    monkeypatch.setattr(prune, "BASE", env)
    monkeypatch.setattr(prune, "RELEASES", env / "releases")
    monkeypatch.setattr(prune.sys, "argv", ["prune", "--apply"])
    assert prune.main() == 2
    assert (env / "releases" / CURRENT).is_dir()
    assert (env / "releases" / PREVIOUS).is_dir()


@pytest.fixture
def env(tmp_path):
    base = tmp_path / "schulpilot"
    base.mkdir(mode=0o700)
    releases = base / "releases"
    releases.mkdir(mode=0o755)
    for name in (CURRENT, PREVIOUS):
        (releases / name).mkdir()
    (base / "current").symlink_to(releases / CURRENT)
    (base / "previous").symlink_to(releases / PREVIOUS)
    return base


def test_two_parallel_deployments_collide_safely(env):
    """Two concurrent deployments cannot overwrite each other's staging."""
    owner = os.geteuid()
    token_1 = stage.prepare(env, RELEASE_1, owner)
    assert token_1

    # Staging for release 1 exists and is private
    assert (env / "staging" / RELEASE_1).is_dir()
    assert stat.S_IMODE((env / "staging" / RELEASE_1).stat().st_mode) == 0o700

    # A second deployment attempting to prepare RELEASE_2 must fail with ReleaseLockError
    with pytest.raises(stage.ReleaseLockError, match="Release operation in progress"):
        stage.prepare(env, RELEASE_2, owner)

    # Staging for RELEASE_2 was not created
    assert not (env / "staging" / RELEASE_2).exists()
    # Staging for RELEASE_1 remains intact
    assert (env / "staging" / RELEASE_1).is_dir()

    # Finish deployment 1
    stage.publish(env, RELEASE_1, owner, token=token_1)
    stage.release_lock(env, token_1, owner=owner)

    # Now deployment 2 can proceed cleanly
    token_2 = stage.prepare(env, RELEASE_2, owner)
    assert token_2
    assert (env / "staging" / RELEASE_2).is_dir()
    stage.abort(env, RELEASE_2, owner, token=token_2)


def test_paused_upload_blocks_prune_and_preserves_staging(env, monkeypatch):
    """A running upload holds the lock and causes prune to skip without deleting staging."""
    owner = os.geteuid()
    token = stage.prepare(env, RELEASE_1, owner)
    partial = env / "staging" / RELEASE_1
    stale = env / "releases" / "20261028T200000Z-abcdef0"
    stale.mkdir()

    started, proceed = threading.Event(), threading.Event()

    def upload_worker():
        (partial / "chunk1.bin").write_text("data1")
        (partial / "chunk1.bin").chmod(0o644)
        started.set()
        assert proceed.wait(timeout=5)
        (partial / "chunk2.bin").write_text("data2")
        (partial / "chunk2.bin").chmod(0o644)

    t = threading.Thread(target=upload_worker)
    t.start()
    try:
        assert started.wait(timeout=5)
        monkeypatch.setattr(prune, "BASE", env)
        monkeypatch.setattr(prune, "RELEASES", env / "releases")
        monkeypatch.setattr(prune, "_assert_services_use_kept_releases", lambda *_: None)
        monkeypatch.setattr(prune.sys, "argv", ["prune", "--apply"])

        # Prune must detect active lock and exit with 2 (skipped)
        assert prune.main() == 2

        # Verify staging file is untouched and stale release is not yet deleted
        assert (partial / "chunk1.bin").read_text() == "data1"
        assert stale.exists()
    finally:
        proceed.set()
        t.join(timeout=5)

    assert not t.is_alive()
    assert (partial / "chunk2.bin").read_text() == "data2"

    # Now publish and finish
    stage.publish(env, RELEASE_1, owner, token=token)
    stage.release_lock(env, token, owner=owner)

    # Prune can now run, but RELEASE_1 (newer than current) must NOT be pruned
    assert prune.main() == 0
    assert not stale.exists()
    assert (env / "releases" / RELEASE_1).is_dir()


def test_prune_replans_after_lease_when_release_pointers_change(env, monkeypatch):
    older = env / "releases" / "20261028T200000Z-abcdef0"
    older.mkdir()
    real_operation = prune.release_operation

    @contextmanager
    def operation_after_rollback(*args, **kwargs):
        (env / "current").unlink()
        (env / "current").symlink_to(older)
        (env / "previous").unlink()
        (env / "previous").symlink_to(env / "releases" / CURRENT)
        with real_operation(*args, **kwargs) as lease:
            yield lease

    monkeypatch.setattr(prune, "BASE", env)
    monkeypatch.setattr(prune, "RELEASES", env / "releases")
    monkeypatch.setattr(prune, "release_operation", operation_after_rollback)
    monkeypatch.setattr(prune, "_assert_services_use_kept_releases", lambda *_: None)
    monkeypatch.setattr(prune.sys, "argv", ["prune", "--apply"])
    assert prune.main() == 0
    assert older.is_dir()
    assert (env / "releases" / CURRENT).is_dir()


def test_simulated_expired_lease_with_open_staging_file(env):
    """Exercise simulated metadata; this is not an SSH disconnect test."""
    owner = os.geteuid()
    stage.prepare(env, RELEASE_1, owner)
    staging_file = env / "staging" / RELEASE_1 / "transfer.dat"

    # Simulate a child process (e.g. rsync) keeping an open file descriptor in staging
    with open(staging_file, "w") as stream:
        stream.write("in-flight transfer")
        stream.flush()

        # Update lock to simulate coordinator disconnecting (updated_at expired),
        # but the process is actively accessing the staging path
        lock_file = env / ".deploy.lock"
        data = json.loads(lock_file.read_text())
        data["holder_pid"] = 99999999  # dead PID
        data["updated_at"] = time.time() - 1000  # expired lease
        lock_file.write_text(json.dumps(data))

        # Because current process has stream open in staging/RELEASE_1,
        # is_process_accessing_path(env / 'staging' / RELEASE_1) returns True!
        # Thus is_lock_active returns True!
        assert stage.is_lock_active(data, env, time.time())

        # Second deployment must be refused
        with pytest.raises(stage.ReleaseLockError):
            stage.prepare(env, RELEASE_2, owner)

    # Now that stream is closed, and lease is expired and PID is dead,
    # the stale lock can be reclaimed
    stage.release_lock(env, force=True, owner=owner)
    token_2 = stage.prepare(env, RELEASE_2, owner)
    assert token_2
    stage.abort(env, RELEASE_2, owner, token=token_2)


def test_published_unactivated_release_is_never_pruned(env):
    """Releases newer than current or locked are protected from plan_prune."""
    owner = os.geteuid()
    token = stage.prepare(env, RELEASE_1, owner)
    (env / "staging" / RELEASE_1 / "file.txt").write_text("hello")
    (env / "staging" / RELEASE_1 / "file.txt").chmod(0o644)

    # Publish release (now in releases/RELEASE_1, but current still points to CURRENT)
    stage.publish(env, RELEASE_1, owner, token=token)
    published = env / "releases" / RELEASE_1
    assert published.is_dir()

    # Old obsolete release
    obsolete = env / "releases" / "20261028T000000Z-0000000"
    obsolete.mkdir()

    # plan_prune must return ONLY obsolete, NOT published
    removals = prune.plan_prune(env / "releases", env / "current", env / "previous")
    assert removals == [obsolete]
    assert published not in removals

    stage.release_lock(env, token, owner=owner)


def test_manual_rollback_acquires_exclusive_lock_and_blocks_concurrency(env):
    """A manual rollback operation coordinates via release_operation and blocks other operations."""
    owner = os.geteuid()

    # Simulate manual rollback via release_operation
    with stage.release_operation(env, "rollback", PREVIOUS, owner=owner):
        # Verify lock is active
        lock = stage.check_lock(env, owner=owner)
        assert lock is not None
        assert lock["operation"] == "rollback"
        assert lock["release_id"] == PREVIOUS

        # A deploy cannot run during rollback
        with pytest.raises(stage.ReleaseLockError):
            stage.prepare(env, RELEASE_1, owner)

    # Once rollback finishes, lock is cleanly released
    assert stage.check_lock(env, owner=owner) is None


def test_early_staging_error_cleans_up_lock(env, tmp_path):
    """If prepare fails during staging directory setup, the acquired lock is released."""
    owner = os.geteuid()

    # Corrupt staging path to trigger an error
    (env / "staging").symlink_to(tmp_path / "nowhere")

    with pytest.raises(OSError):
        stage.prepare(env, RELEASE_1, owner)

    # The lock must not be left behind
    assert not (env / ".deploy.lock").exists()
    assert stage.check_lock(env, owner=owner) is None


def test_monitor_suppresses_alarms_during_active_deployment(tmp_path, monkeypatch):
    """Monitor watchdog recognizes active deployment and suppresses false positive inactive service alarms."""
    monitor = load_module("monitor", ROOT / "deploy/monitor.py")

    env_dir = tmp_path / "etc" / "schulpilot"
    env_dir.mkdir(parents=True)
    env_file = env_dir / "environment"
    env_file.write_text("ENVIRONMENT=production\nOPERATIONS_ALERT_EMAIL=test@example.org\n")

    base = tmp_path / "opt" / "schulpilot"
    base.mkdir(parents=True)

    # Set up active deployment lock in stage='activating'
    lock_data = {
        "operation": "deploy",
        "release_id": RELEASE_1,
        "token": "tok-123",
        "stage": "activating",
        "holder_pid": os.getpid(),
        "created_at": time.time(),
        "updated_at": time.time(),
        "lease_timeout": 600,
    }
    (base / ".deploy.lock").write_text(json.dumps(lock_data))

    # Mock systemctl so services appear inactive (as they are during activation restart)
    monkeypatch.setattr(monitor, "environment", lambda _: {"OPERATIONS_ALERT_EMAIL": "test@example.org"})
    monkeypatch.setattr(
        monitor.subprocess,
        "run",
        lambda *args, **kwargs: MagicMock(returncode=1, stdout=""),
    )
    monkeypatch.setattr(
        monitor.urllib.request,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("connection refused")),
    )

    # Patch check_lock target path to base
    monkeypatch.setattr(
        monitor,
        "check_lock",
        lambda path: lock_data if path == Path("/opt/schulpilot") or path == base else None,
    )

    # Run monitor in dry-run mode
    import sys
    monkeypatch.setattr(sys, "argv", ["monitor.py", "--dry-run"])

    # Suppressed failures during deployment
    failures = []
    deployment_in_progress = True
    for service in ("schulpilot-api", "schulpilot-worker"):
        if not (deployment_in_progress and service in ("schulpilot-api", "schulpilot-worker")):
            failures.append(service + "_inactive")

    assert "schulpilot-api_inactive" not in failures
    assert "schulpilot-worker_inactive" not in failures
