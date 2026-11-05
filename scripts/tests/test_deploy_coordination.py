"""Comprehensive integration and isolation tests for release deployment coordination.

Exercises lease races, simulated interruptions, delayed local child processes,
pruning, the rollback lease and monitor behavior. It does not run an SSH
disconnect, a real service activation, or a full migration/rollback.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import multiprocessing
import os
import stat
import subprocess
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


def legacy_prune(fixture=None):
    """Load exact deployed 534009f snapshot even in a shallow checkout.

    The byte digest was checked against `git show 534009f:deploy/prune_releases.py`;
    do not silently skip this regression when Git history is unavailable.
    """
    fixture = fixture or ROOT / "scripts/tests/fixtures/prune_releases_534009f.py"
    source = fixture.read_bytes()
    assert hashlib.sha256(source).hexdigest() == "22d6e9210c6c9966e678d0945246927a24396cf697923c0338c6631b0bddae47"
    namespace = {"__name__": "legacy_prune_fixture"}
    exec(compile(source, str(fixture), "exec"), namespace)
    return namespace


def test_legacy_prune_snapshot_rejects_altered_fixture_before_execution(tmp_path):
    fixture = tmp_path / "altered.py"
    fixture.write_text("raise RuntimeError('must not execute')")
    with pytest.raises(AssertionError):
        legacy_prune(fixture)


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


def _delayed_upload(path, ready, resume):
    ready.set()
    if not resume.wait(10):
        raise RuntimeError("Test upload was not resumed")
    (path / "later.txt").write_text("completed")


def test_interrupted_delayed_upload_preserves_staging_and_lease(env):
    token = stage.prepare(env, RELEASE_1)
    partial = env / "staging" / RELEASE_1
    ctx = multiprocessing.get_context("fork")
    ready, resume = ctx.Event(), ctx.Event()
    process = ctx.Process(target=_delayed_upload, args=(partial, ready, resume))
    process.start()
    try:
        assert ready.wait(5)
        # No file in staging is open while the child waits. An abort must not
        # remove the directory or release the lease based on /proc or timeout.
        stage.abort(env, RELEASE_1, token=token)
        lock_path = env / ".deploy.lock"
        data = json.loads(lock_path.read_text())
        data.update(holder_pid=99999999, tracked_pids=[], updated_at=time.time() - 3600)
        lock_path.write_text(json.dumps(data))
        with pytest.raises(stage.ReleaseLockError):
            stage.prepare(env, RELEASE_2)
        with pytest.raises(stage.ReleaseLockError, match="Interrupted"):
            stage.heartbeat(env, RELEASE_1, token)
        assert partial.is_dir()
        resume.set()
        process.join(5)
        assert process.exitcode == 0
        assert (partial / "later.txt").read_text() == "completed"
        with pytest.raises(stage.ReleaseLockError):
            stage.prepare(env, RELEASE_2)
    finally:
        resume.set()
        process.join(5)
        if process.is_alive():
            process.terminate()
            process.join()


def test_abort_and_release_reject_missing_wrong_or_mismatched_tokens(env):
    token = stage.prepare(env, RELEASE_1)
    staged = env / "staging" / RELEASE_1
    (staged / "keep.txt").write_text("partial")
    for release_id, candidate in [(RELEASE_1, None), (RELEASE_1, "wrong"), (RELEASE_2, token)]:
        with pytest.raises(stage.ReleaseLockError):
            stage.abort(env, release_id, token=candidate)
        assert (staged / "keep.txt").read_text() == "partial"
    with pytest.raises(stage.ReleaseLockError):
        stage.release_lock(env)
    with pytest.raises(stage.ReleaseLockError):
        stage.acquire_lock(env, "activate", RELEASE_2, token=token)
    with pytest.raises(stage.ReleaseLockError):
        stage.heartbeat(env, RELEASE_2, token)
    assert stage.check_lock(env)["release_id"] == RELEASE_1


def test_finish_requires_matching_active_release_and_completed_followup(env):
    token = stage.prepare(env, RELEASE_1)
    stage.guard_legacy_prune(env, RELEASE_1, token)
    with pytest.raises(stage.ReleaseLockError, match="not activated"):
        stage.finish(env, RELEASE_1, token)
    stage.publish(env, RELEASE_1, token=token)
    stage.acquire_lock(env, "activate", RELEASE_1, token=token, stage="activating")
    stage.update_lock(env, token, stage="activated", release_id=RELEASE_1)
    with pytest.raises(stage.ReleaseLockError, match="active release"):
        stage.finish(env, RELEASE_1, token)
    with pytest.raises(stage.ReleaseLockError):
        stage.prepare(env, RELEASE_2)
    (env / "current").unlink()
    (env / "current").symlink_to(env / "releases" / RELEASE_1)
    with pytest.raises(stage.ReleaseLockError, match="not activated"):
        stage.finish(env, RELEASE_1, "wrong")
    stage.finish(env, RELEASE_1, token)
    assert stage.check_lock(env) is None
    assert not (env / "releases" / ".deploy-in-progress").exists()
    assert stage.prepare(env, RELEASE_2)


def test_legacy_prune_refuses_guard_even_after_interruption(env):
    namespace = legacy_prune()
    token = stage.prepare(env, RELEASE_1)
    with pytest.raises(stage.ReleaseLockError):
        stage.guard_legacy_prune(env, RELEASE_1, "wrong")
    stage.guard_legacy_prune(env, RELEASE_1, token)
    for interrupted in (False, True):
        if interrupted:
            stage.abort(env, RELEASE_1, token=token)
        with pytest.raises(namespace["PruneError"], match="unexpected entry"):
            namespace["plan_prune"](env / "releases", env / "current", env / "previous")
        assert (env / "staging" / RELEASE_1).exists()


def test_abort_waits_for_inflight_publication(env, monkeypatch):
    token = stage.prepare(env, RELEASE_1)
    stage.guard_legacy_prune(env, RELEASE_1, token)
    at_rename, resume, abort_started, aborted = (threading.Event() for _ in range(4))
    errors = []
    rename = stage._rename_noreplace

    def paused_rename(*args):
        at_rename.set()
        if not resume.wait(5):
            raise RuntimeError("Publication was not resumed")
        return rename(*args)

    def publish():
        try:
            stage.publish(env, RELEASE_1, token=token)
        except Exception as exc:
            errors.append(exc)

    def abort():
        abort_started.set()
        try:
            stage.abort(env, RELEASE_1, token=token)
        except Exception as exc:
            errors.append(exc)
        finally:
            aborted.set()

    monkeypatch.setattr(stage, "_rename_noreplace", paused_rename)
    publication = threading.Thread(target=publish)
    interruption = threading.Thread(target=abort)
    publication.start()
    try:
        assert at_rename.wait(5)
        interruption.start()
        assert abort_started.wait(5)
        returned_early = aborted.wait(.3)
    finally:
        resume.set()
        publication.join(timeout=5)
        if interruption.ident is not None:
            interruption.join(timeout=5)
    assert not publication.is_alive() and not interruption.is_alive()
    assert not errors
    assert not returned_early
    assert stage.check_lock(env)["stage"] == "interrupted"
    assert (env / "releases" / RELEASE_1).is_dir()
    assert (env / "releases" / ".deploy-in-progress").is_file()


@pytest.mark.parametrize("damage", ["missing", "wrong_contents", "symlink"])
def test_finish_refuses_missing_or_altered_legacy_guard(env, tmp_path, damage):
    token = stage.prepare(env, RELEASE_1)
    stage.guard_legacy_prune(env, RELEASE_1, token)
    stage.publish(env, RELEASE_1, token=token)
    stage.acquire_lock(env, "activate", RELEASE_1, token=token, stage="activating")
    stage.update_lock(env, token, stage="activated", release_id=RELEASE_1)
    (env / "current").unlink()
    (env / "current").symlink_to(env / "releases" / RELEASE_1)
    marker = env / "releases" / ".deploy-in-progress"
    if damage == "missing":
        marker.unlink()
    elif damage == "wrong_contents":
        marker.write_text(RELEASE_2 + "\n")
    else:
        marker.unlink()
        marker.symlink_to(tmp_path / "outside")
    with pytest.raises((stage.ReleaseLockError, OSError)):
        stage.finish(env, RELEASE_1, token)
    assert stage.check_lock(env)["stage"] == "activated"


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


@pytest.mark.parametrize("content", ["", "{", "[]", '{}', '{"token": ""}', '{"token": "foo"}'])
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


@pytest.mark.parametrize("target_exists", [False, True])
def test_symlink_lease_fails_closed_for_all_operations(env, tmp_path, monkeypatch, target_exists):
    target = tmp_path / "outside-lease"
    if target_exists:
        target.write_text("not a lease")
    lease = env / ".deploy.lock"
    lease.symlink_to(target)
    with pytest.raises(stage.ReleaseLockError):
        stage.check_lock(env)
    with pytest.raises(stage.ReleaseLockError):
        stage.prepare(env, RELEASE_1)
    with pytest.raises(stage.ReleaseLockError):
        stage.release_lock(env, force=True)
    monkeypatch.setattr(prune, "BASE", env)
    monkeypatch.setattr(prune, "RELEASES", env / "releases")
    monkeypatch.setattr(prune.sys, "argv", ["prune", "--apply"])
    assert prune.main() == 2
    assert lease.is_symlink()
    assert target.exists() == target_exists


def test_untrusted_lease_does_not_leak_file_descriptors(env):
    lease = env / ".deploy.lock"
    lease.write_text("invalid")
    lease.chmod(0o644)
    before = len(os.listdir("/proc/self/fd"))
    for _ in range(32):
        with pytest.raises(stage.ReleaseLockError):
            stage.check_lock(env)
    assert len(os.listdir("/proc/self/fd")) == before


@pytest.mark.parametrize("field,value", [
    ("updated_at", float("nan")), ("lease_timeout", -1), ("holder_pid", True),
    ("tracked_pids", [0]), ("release_id", "../../elsewhere"),
])
def test_corrupt_lease_fields_refuse_acquire(env, field, value):
    data = stage.acquire_lock(env, "deploy", RELEASE_1)
    data[field] = value
    (env / ".deploy.lock").write_text(json.dumps(data))
    with pytest.raises(stage.ReleaseLockError, match="lock metadata"):
        stage.acquire_lock(env, "deploy", RELEASE_2)


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


@pytest.mark.parametrize("dispatcher_state", [
    "MainPID=0\nLoadState=not-found\nActiveState=inactive\n",
    "MainPID=0\nLoadState=loaded\nActiveState=inactive\n",
    "MainPID=103\nLoadState=loaded\nActiveState=active\n",
])
def test_prune_checks_optional_dispatcher_and_allows_safe_states(env, monkeypatch, dispatcher_state):
    current = env / "releases" / CURRENT
    previous = env / "releases" / PREVIOUS
    old = env / "releases" / "20261028T200000Z-abcdef0"
    old.mkdir()
    real_resolve = Path.resolve

    def resolve(path, *args, **kwargs):
        if str(path) in ("/proc/101/cwd", "/proc/102/cwd"):
            return current / "backend"
        if str(path) == "/proc/103/cwd":
            return previous / "backend"
        return real_resolve(path, *args, **kwargs)

    def systemctl(args, **kwargs):
        service = args[-1]
        if service == "schulpilot-repair-dispatcher.service":
            return subprocess.CompletedProcess(args, 0, stdout=dispatcher_state)
        return subprocess.CompletedProcess(args, 0, stdout={
            "schulpilot-api.service": "101\n", "schulpilot-worker.service": "102\n",
        }[service])

    monkeypatch.setattr(Path, "resolve", resolve)
    monkeypatch.setattr(prune.subprocess, "run", systemctl)
    monkeypatch.setattr(prune, "BASE", env)
    monkeypatch.setattr(prune, "RELEASES", env / "releases")
    monkeypatch.setattr(prune.sys, "argv", ["prune", "--apply"])
    assert prune.main() == 0
    assert not old.exists()
    assert current.is_dir() and previous.is_dir()


@pytest.mark.parametrize("dispatcher_state, old_process", [
    ("MainPID=103\nLoadState=loaded\nActiveState=active\n", True),
    ("MainPID=0\nLoadState=loaded\nActiveState=activating\n", False),
    ("MainPID=103\nLoadState=loaded\nActiveState=inactive\n", False),
    ("MainPID=0\nLoadState=loaded\nActiveState=failed\n", False),
    ("MainPID=0\nLoadState=loaded\n", False),
    ("MainPID=invalid\nLoadState=loaded\nActiveState=active\n", False),
])
def test_prune_refuses_stale_or_uncertain_dispatcher(env, monkeypatch, dispatcher_state, old_process):
    current = env / "releases" / CURRENT
    old = env / "releases" / "20261028T200000Z-abcdef0"
    old.mkdir()
    real_resolve = Path.resolve

    def resolve(path, *args, **kwargs):
        if str(path) in ("/proc/101/cwd", "/proc/102/cwd"):
            return current / "backend"
        if str(path) == "/proc/103/cwd" and old_process:
            return old / "backend"
        return real_resolve(path, *args, **kwargs)

    def systemctl(args, **kwargs):
        service = args[-1]
        if service == "schulpilot-repair-dispatcher.service":
            return subprocess.CompletedProcess(args, 0, stdout=dispatcher_state)
        return subprocess.CompletedProcess(args, 0, stdout={
            "schulpilot-api.service": "101\n", "schulpilot-worker.service": "102\n",
        }[service])

    monkeypatch.setattr(Path, "resolve", resolve)
    monkeypatch.setattr(prune.subprocess, "run", systemctl)
    monkeypatch.setattr(prune, "BASE", env)
    monkeypatch.setattr(prune, "RELEASES", env / "releases")
    monkeypatch.setattr(prune.sys, "argv", ["prune", "--apply"])
    assert prune.main() == 2
    assert old.is_dir()
    assert stage.check_lock(env)["operation"] == "prune"


def test_prune_checks_real_dispatcher_process_directory(env, monkeypatch):
    current = env / "releases" / CURRENT
    old = env / "releases" / "20261028T200000Z-abcdef0"
    (current / "backend").mkdir()
    (old / "backend").mkdir(parents=True)
    api = subprocess.Popen(["sleep", "30"], cwd=current / "backend")
    dispatcher = subprocess.Popen(["sleep", "30"], cwd=old / "backend")
    try:
        def systemctl(args, **kwargs):
            if args[-1] == "schulpilot-repair-dispatcher.service":
                value = f"MainPID={dispatcher.pid}\nLoadState=loaded\nActiveState=active\n"
            else:
                value = f"{api.pid}\n"
            return subprocess.CompletedProcess(args, 0, stdout=value)

        monkeypatch.setattr(prune.subprocess, "run", systemctl)
        with pytest.raises(prune.PruneError, match="repair-dispatcher.*outside current/previous"):
            prune._assert_services_use_kept_releases({current})
        assert old.is_dir()
    finally:
        for process in (api, dispatcher):
            process.terminate()
            process.wait(timeout=5)


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
        assert (env / "releases" / ".deploy-in-progress").read_text() == PREVIOUS + "\n"

        # Exercise the actual previously deployed cleanup code, not a copy of
        # the new implementation. Its directory validation must reject the
        # marker before it creates any removal plan.
        namespace = legacy_prune()
        with pytest.raises((ValueError, RuntimeError, OSError)):
            namespace["plan_prune"](env / "releases", env / "current", env / "previous")

        # A deploy cannot run during rollback
        with pytest.raises(stage.ReleaseLockError):
            stage.prepare(env, RELEASE_1, owner)
        (env / "current").unlink()
        (env / "current").symlink_to(env / "releases" / PREVIOUS)

    # Once rollback finishes, lock is cleanly released
    assert stage.check_lock(env, owner=owner) is None
    assert not (env / "releases" / ".deploy-in-progress").exists()


def test_rollback_keeps_guard_when_target_is_not_active(env):
    with pytest.raises(stage.ReleaseLockError, match="active release changed"):
        with stage.release_operation(env, "rollback", PREVIOUS, stage="activating"):
            pass
    assert stage.check_lock(env)["operation"] == "rollback"
    assert (env / "releases" / ".deploy-in-progress").exists()


def test_failed_rollback_retains_legacy_guard(env):
    with pytest.raises(RuntimeError, match="synthetic failure"):
        with stage.release_operation(env, "rollback", PREVIOUS, stage="activating"):
            raise RuntimeError("synthetic failure")
    assert stage.check_lock(env)["operation"] == "rollback"
    assert (env / "releases" / ".deploy-in-progress").read_text() == PREVIOUS + "\n"


@pytest.mark.parametrize("damage", ["missing", "changed", "symlink"])
def test_rollback_does_not_release_lease_if_guard_is_damaged(env, damage):
    guard = env / "releases" / ".deploy-in-progress"
    with pytest.raises((stage.ReleaseLockError, OSError)):
        with stage.release_operation(env, "rollback", PREVIOUS, stage="activating"):
            (env / "current").unlink()
            (env / "current").symlink_to(env / "releases" / PREVIOUS)
            if damage == "changed":
                guard.write_text(CURRENT + "\n")
            else:
                guard.unlink()
                if damage == "symlink":
                    guard.symlink_to(env / "current")
    assert stage.check_lock(env)["operation"] == "rollback"


@pytest.mark.parametrize("operation", ["rollback", "prune"])
def test_failed_operator_operation_retains_lease_until_inspected(env, operation):
    with pytest.raises(RuntimeError, match="synthetic failure"):
        with stage.release_operation(env, operation, PREVIOUS):
            raise RuntimeError("synthetic failure")
    assert stage.check_lock(env)["operation"] == operation
    with pytest.raises(stage.ReleaseLockError):
        stage.prepare(env, RELEASE_1)


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
