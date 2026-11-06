"""The configuration gate is not a substitute for a real restore rehearsal."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("restore_release_guard", ROOT / "deploy/restore_release_guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def tree(root):
    for name in ("backend/schulpilot/db.py", "backend/schulpilot/erasure.py", "backend/schulpilot/restore_push.py",
                 "backend/migrations/env.py", "backend/migrations/versions/0047.py", "backend/alembic.ini",
                 "backend/requirements.lock", "deploy/restore_check.py"):
        file = root / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("synthetic " + name)
    (root / "deploy/schulpilot-restore-check.service").write_text(
        "ExecStart=/opt/schulpilot/current/venv/bin/python /opt/schulpilot/current/deploy/restore_check.py\n"
    )
    interpreter = root / "venv/bin/python"
    interpreter.parent.mkdir(parents=True, exist_ok=True)
    interpreter.write_text("synthetic")


def output(runtime, *, user="root", reload="no", suffix=""):
    interpreter = str(runtime / "venv/bin/python")
    return ("LoadState=loaded\nNeedDaemonReload=" + reload + "\nUser=" + user + "\nExecStart={ path="
            + interpreter + " ; argv[]=" + interpreter + " " + str(runtime / "deploy/restore_check.py")
            + suffix + " ; ignore_errors=no ; start_time=[n/a] ; stop_time=[n/a] ; pid=0 ; code=(null) ; status=0/0 }\n")


def test_current_command_is_runtime_relative(tmp_path):
    target = tmp_path / "target"
    tree(target)
    guard.inspect(output(Path("/opt/schulpilot/current")), target)


def test_override_requires_complete_matching_sources(tmp_path):
    target, base = tmp_path / "target", tmp_path / "runtimes"
    runtime = base / ("a" * 40)
    tree(target)
    tree(runtime)
    guard.inspect(output(runtime), target, runtime_base=base)
    (runtime / "backend/schulpilot/db.py").write_text("old restore source")
    with pytest.raises(guard.RestoreConfigurationError, match="does not match"):
        guard.inspect(output(runtime), target, runtime_base=base)


@pytest.mark.parametrize("kind", ("missing", "symlink", "extra", "user", "reload", "args", "duplicate", "interpreter"))
def test_configuration_problems_fail_closed(tmp_path, kind):
    target, base = tmp_path / "target", tmp_path / "runtimes"
    runtime = base / ("b" * 40)
    tree(target)
    tree(runtime)
    line = output(runtime)
    item = runtime / "backend/schulpilot/db.py"
    if kind == "missing":
        item.unlink()
    elif kind == "symlink":
        item.unlink()
        item.symlink_to(target / "backend/schulpilot/db.py")
    elif kind == "extra":
        (runtime / "backend/schulpilot/old.py").write_text("old")
    elif kind == "user":
        line = output(runtime, user="nobody")
    elif kind == "reload":
        line = output(runtime, reload="yes")
    elif kind == "args":
        line = output(runtime, suffix=" --unsafe")
    elif kind == "interpreter":
        (runtime / "venv/bin/python").unlink()
    else:
        line += "User=root\n"
    with pytest.raises(guard.RestoreConfigurationError):
        guard.inspect(line, target, runtime_base=base)


def test_unrecognized_runtime_refused(tmp_path):
    target = tmp_path / "target"
    tree(target)
    with pytest.raises(guard.RestoreConfigurationError):
        guard.inspect(output(Path("/tmp/untrusted")), target)


def test_target_unit_change_does_not_pass_using_old_current(tmp_path):
    target = tmp_path / "target"
    tree(target)
    (target / "deploy/schulpilot-restore-check.service").write_text("ExecStart=/bin/true\n")
    with pytest.raises(guard.RestoreConfigurationError):
        guard.inspect(output(Path("/opt/schulpilot/current")), target)


def test_rollback_never_silently_switches_current_restore_reader(tmp_path):
    target, active = tmp_path / "older", tmp_path / "active"
    tree(target)
    tree(active)
    with pytest.raises(guard.RestoreConfigurationError, match="independent restore runtime"):
        guard.inspect(output(Path("/opt/schulpilot/current")), target, rollback=True, active=active)


def test_rollback_keeps_independent_reader_for_active_source(tmp_path):
    target, active, base = tmp_path / "older", tmp_path / "active", tmp_path / "runtimes"
    runtime = base / ("c" * 40)
    tree(target)
    tree(active)
    tree(runtime)
    (target / "backend/schulpilot/db.py").write_text("older incompatible reader")
    (target / "backend/schulpilot/restore_push.py").unlink()
    (target / "deploy/restore_check.py").unlink()
    guard.inspect(output(runtime), target, rollback=True, active=active, runtime_base=base)
    # A reader matching only the rollback target must not cover newer data.
    (runtime / "backend/schulpilot/db.py").write_text("older incompatible reader")
    with pytest.raises(guard.RestoreConfigurationError, match="does not match"):
        guard.inspect(output(runtime), target, rollback=True, active=active, runtime_base=base)


def test_rollback_requires_active_source(tmp_path):
    target = tmp_path / "older"
    tree(target)
    with pytest.raises(guard.RestoreConfigurationError, match="active source"):
        guard.inspect(output(Path("/opt/schulpilot/current")), target, rollback=True)


@pytest.mark.parametrize("missing", ("backend/schulpilot/erasure.py", "backend/schulpilot/restore_push.py",
                                     "backend/migrations/env.py", "deploy/restore_check.py"))
def test_current_reader_requires_complete_target_sources(tmp_path, missing):
    target = tmp_path / "target"
    tree(target)
    (target / missing).unlink()
    with pytest.raises(guard.RestoreConfigurationError):
        guard.inspect(output(Path("/opt/schulpilot/current")), target)


def test_target_interpreter_only_required_after_environment_installation(tmp_path):
    target = tmp_path / "target"
    tree(target)
    (target / "venv/bin/python").unlink()
    guard.inspect(output(Path("/opt/schulpilot/current")), target)
    with pytest.raises(guard.RestoreConfigurationError, match="Target interpreter"):
        guard.inspect(output(Path("/opt/schulpilot/current")), target, check_interpreter=True)


def test_preflight_checks_existing_before_service_changes(tmp_path, monkeypatch):
    target, current, active = tmp_path / "target", tmp_path / "current", tmp_path / "active"
    active.mkdir()
    current.symlink_to(active)
    checked = []
    monkeypatch.setattr(guard, "verify", checked.append)
    guard.verify_deploy_preflight(target, current)
    assert checked == [target]


def test_preflight_refuses_broken_or_non_symlink_current(tmp_path, monkeypatch):
    target, current = tmp_path / "target", tmp_path / "current"
    monkeypatch.setattr(guard, "verify", lambda _: pytest.fail("invalid current was checked"))
    current.symlink_to(tmp_path / "absent")
    with pytest.raises(FileNotFoundError):
        guard.verify_deploy_preflight(target, current)
    current.unlink()
    current.mkdir()
    with pytest.raises(guard.RestoreConfigurationError, match="not a symlink"):
        guard.verify_deploy_preflight(target, current)
