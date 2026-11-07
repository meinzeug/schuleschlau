"""Run the real activation script against temporary files and offline OS mocks."""

import builtins
import os
import runpy
import subprocess
import sys
from functools import partial
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).parents[2] / "deploy/activate.py"
WRITERS = ["schulpilot-api", "schulpilot-worker"]
OLDER = "20261028T200000Z-abcdef0"
OLD = "20261029T200000Z-abcdef1"
NEW = "20261030T200000Z-abcdef2"


class Activation:
    def __init__(self, root, failure=None, *, changed_schema=False):
        self.root, self.failure, self.changed_schema = root, failure, changed_schema
        self.commands, self.command_releases, self.schema_reads, self.restarts, self.backup_checks = [], [], 0, [], 0
        self.clock_reads = 0
        self.restore_checks = 0
        self.backup_starts = 0
        self.photo_active = False
        self.photo_enabled = False
        self.base = root / "opt/schulpilot"
        self.old = self.base / "releases" / OLD
        self.new = self.base / "releases" / NEW
        for release in (self.old, self.new):
            for name, content in {
                "web/index.html": "synthetic web",
                "backend/requirements.lock": "synthetic requirements",
                "venv/bin/pip": "synthetic existing venv",
                "deploy/Caddyfile.schulpilot": "old fragment" if release == self.old else "new fragment",
                "deploy/schulpilot-api.service": "old service" if release == self.old else "new service",
            }.items():
                path = release / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
        self.base.chmod(0o755)
        (self.base / "releases").chmod(0o755)
        self.current = self.base / "current"
        self.current.symlink_to(self.old)
        self.prior = self.base / "previous"
        self.prior.symlink_to(self.base / "releases" / OLDER)
        self.caddy = root / "etc/caddy/Caddyfile"
        self.caddy.parent.mkdir(parents=True)
        self.caddy.write_text("import /etc/caddy/schulpilot.caddy\n")
        self.fragment = self.caddy.parent / "schulpilot.caddy"
        self.fragment.write_text("old fragment")
        environment = root / "etc/schulpilot/environment"
        environment.parent.mkdir(parents=True)
        environment.write_text("DATABASE_URL=synthetic-no-connection\n")
        systemd = root / "etc/systemd/system"
        systemd.mkdir(parents=True)
        (systemd / "schulpilot-api.service").write_text("operator service")
        (systemd / "schulpilot-monitor.timer").write_text("operator timer")
        (self.new / "deploy/turn_certificate.py").write_text("new certificate helper")
        turn = root / "etc/schulpilot-turn"
        turn.mkdir()
        (turn / "turnserver.conf").write_text("synthetic operator config")
        (turn / "refresh_certificate.py").write_text("operator certificate helper")

    def path(self, *parts):
        path = Path(*parts)
        if str(path).startswith(("/opt/schulpilot", "/etc/")):
            return self.root / str(path).lstrip("/")
        return path

    def run(self, command, **kwargs):
        command = list(map(str, command))
        self.commands.append(command)
        self.command_releases.append(self.current.resolve())
        if command[:3] == ['systemctl', 'show', 'schulpilot-photo.service']:
            unit = self.root / 'etc/systemd/system/schulpilot-photo.service'
            if '--property=LoadState' in command:
                load = 'loaded' if unit.exists() else 'not-found'
                active = 'active' if self.photo_active else 'inactive'
                enabled = ('enabled' if self.photo_enabled else 'disabled') if unit.exists() else ''
                return subprocess.CompletedProcess(command, 0, stdout=f'LoadState={load}\nActiveState={active}\nUnitFileState={enabled}\n')
            fragment = str(unit) if unit.exists() else ''
            return subprocess.CompletedProcess(command, 0, stdout=f'FragmentPath={fragment}\nDropInPaths=\nNeedDaemonReload=no\n')
        if command[:2] == ['systemctl', 'restart'] and command[-1] == 'schulpilot-photo.service':
            self.photo_active = True
        if command[:2] == ['systemctl', 'start'] and command[-1] == 'schulpilot-photo.service':
            self.photo_active = True
        if command[:2] == ['systemctl', 'stop'] and command[-1] == 'schulpilot-photo.service':
            self.photo_active = False
        if command[:2] == ['systemctl', 'enable'] and 'schulpilot-photo.service' in command:
            self.photo_enabled = True
        if command[:2] == ['systemctl', 'disable'] and command[-1] == 'schulpilot-photo.service':
            self.photo_enabled = False
        if command and command[0] == 'runuser' and command[-1].endswith('photo_health.py'):
            return subprocess.CompletedProcess(command, 1 if self.failure == 'photo_health' else 0, stdout='')
        if command[0] == "runuser" and "-c" in command:
            self.schema_reads += 1
            schema = "0032" if self.changed_schema and self.schema_reads > 1 else "0031"
            return subprocess.CompletedProcess(command, 0, stdout=schema + "\n")
        if command == ["systemctl", "start", "schulpilot-backup.service"]:
            self.backup_starts += 1
            if self.failure == "unknown_start_drained" and self.backup_starts == 2:
                raise subprocess.CalledProcessError(1, command)
        if command == ["systemctl", "show", "schulpilot-backup.service", "--value", "-p", "InvocationID"]:
            changed = self.failure == "invocation_changed_drained" and self.backup_checks == 2
            return subprocess.CompletedProcess(command, 0, stdout=("b" if changed else "a") * 32 + "\n")
        if command and command[0] == "journalctl":
            assert command == ["journalctl", "--no-pager", "--quiet", "--output=cat",
                               "_SYSTEMD_INVOCATION_ID=" + "a" * 32]
            if self.failure == "journal_unavailable_drained" and self.backup_checks == 2:
                raise subprocess.CalledProcessError(1, command)
            return subprocess.CompletedProcess(command, 0, stdout="synthetic invocation log")
        if command[:3] == ["systemctl", "show", "schulpilot-backup.service"]:
            self.backup_checks += 1
            result = "failed" if self.failure == "second_backup" and self.backup_checks == 2 else "success"
            stale = self.failure == "stale_drained" and self.backup_checks == 2 or (
                self.failure == "stale_drained_exhausted" and self.backup_checks in (2, 3))
            if stale:
                start = getattr(self, "stale_start", self.clock_reads * 1_000_000 - 10)
                self.stale_start = start
            else:
                start = self.clock_reads * 1_000_000 + 10
            end = start + 1
            fields = {"Result": result, "ActiveState": "inactive", "SubState": "dead", "Job": "",
                "ExecMainStartTimestampMonotonic": str(start), "ExecMainExitTimestampMonotonic": str(end),
                "ExecMainCode": "1", "ExecMainStatus": "0", "InvocationID": "a" * 32}
            if self.failure == "active_drained" and self.backup_checks == 2:
                fields["ActiveState"] = "activating"
            if self.failure == "job_drained" and self.backup_checks == 2:
                fields["Job"] = "751"
            if self.failure == "future_drained" and self.backup_checks == 2:
                fields["ExecMainExitTimestampMonotonic"] = str((self.clock_reads + 2) * 1_000_000)
            if self.failure == "malformed_drained" and self.backup_checks == 2:
                fields["ExecMainStartTimestampMonotonic"] = "not-an-integer"
            if self.failure == "backwards_drained" and self.backup_checks == 2:
                fields["ExecMainExitTimestampMonotonic"] = str(start - 1)
            if self.failure == "missing_drained" and self.backup_checks == 2:
                del fields["Job"]
            if self.failure == "invalid_invocation_drained" and self.backup_checks == 2:
                fields["InvocationID"] = "not-an-invocation"
            return subprocess.CompletedProcess(command, 0, stdout="".join(f"{key}={value}\n" for key, value in fields.items()))
        if command == ["systemctl", "restart", *WRITERS]:
            self.restarts.append((self.current.resolve(), kwargs.get("check")))
        failed = (
            (self.failure == "validate" and command[:2] == ["caddy", "validate"])
            or (self.failure == "drain" and command == ["systemctl", "stop", *WRITERS] and kwargs.get("check"))
            or (self.failure == "enable" and command[:2] == ["systemctl", "enable"])
            or (self.failure == "migration" and "schulpilot.migrate" in command)
            or (self.failure == "restart" and command == ["systemctl", "restart", *WRITERS] and kwargs.get("check"))
            or (self.failure == "timer" and command[:3] == ["systemctl", "start", "schulpilot-backup.timer"])
            or (self.failure == "caddy" and command == ["systemctl", "reload", "caddy"] and kwargs.get("check"))
        )
        if failed:
            raise subprocess.CalledProcessError(1, command)
        return subprocess.CompletedProcess(command, 0, stdout="")

    def monotonic_ns(self):
        self.clock_reads += 1
        return self.clock_reads * 1_000_000_000

    def health(self, *_args, **_kwargs):
        self.commands.append(["health"])
        if self.failure == "health":
            raise OSError("synthetic health unavailable")
        return SimpleNamespace(__enter__=lambda self: self, __exit__=lambda *_: None, status=200)

    def execute(self, monkeypatch, rollback_compatible=False, token=None):
        from deploy import photo_release
        real_import = builtins.__import__

        class Health:
            def __enter__(self):
                return SimpleNamespace(status=200)
            def __exit__(self, *_):
                return None

        def urlopen(*args, **kwargs):
            self.health(*args, **kwargs)
            return Health()

        replacements = {
            "backup_release_check": SimpleNamespace(verify_invocation_log=self.verify_backup_log),
            "restore_release_guard": SimpleNamespace(verify=self.verify_restore),
            "photo_release": SimpleNamespace(
                ensure_isolated_identity=lambda release: self.run(['synthetic-sysusers', str(release)]),
                inspect_photo=partial(photo_release.inspect_photo, run=self.run),
                restore_previous_photo=partial(photo_release.restore_previous_photo, run=self.run),
                start_candidate=partial(photo_release.start_candidate, run=self.run, sleep=lambda _: None),
                stop_old_photo=partial(photo_release.stop_old_photo, run=self.run),
                undo_candidate_enable=partial(photo_release.undo_candidate_enable, run=self.run),
                verify_photo_definition=partial(photo_release.verify_photo_definition, run=self.run,
                    unit=self.root / 'etc/systemd/system/schulpilot-photo.service'),
            ),
            "pathlib": SimpleNamespace(Path=self.path),
            "subprocess": SimpleNamespace(run=self.run),
            "time": SimpleNamespace(sleep=lambda _: None, monotonic_ns=self.monotonic_ns),
            "urllib.request": SimpleNamespace(request=SimpleNamespace(urlopen=urlopen)),
        }

        def imports(name, globals=None, locals=None, fromlist=(), level=0):
            return replacements.get(name) or real_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(sys, "argv", [str(SCRIPT), NEW, *(["--rollback-compatible"] if rollback_compatible else []),
                                         *(["--token", token] if token else [])])
        return runpy.run_path(str(SCRIPT), init_globals={"__builtins__": {**vars(builtins), "__import__": imports}})

    def verify_backup_log(self, output):
        assert output == "synthetic invocation log"
        if self.failure == "journal_missing_drained" and self.backup_checks == 2:
            raise RuntimeError("backup invocation lacks a complete journal snapshot")

    def verify_restore(self, release, *, rollback=False, active=None, check_interpreter=False):
        assert release == self.new
        assert active == self.old
        self.restore_checks += 1
        assert check_interpreter == (self.restore_checks == 2)
        if self.failure == f"restore_guard_{self.restore_checks}":
            raise RuntimeError("incompatible restore runtime")


@pytest.mark.parametrize("rollback_compatible", [False, True])
def test_incompatible_restore_aborts_before_any_release_side_effect(tmp_path, monkeypatch, rollback_compatible):
    activation = Activation(tmp_path, "restore_guard_1")
    with pytest.raises(RuntimeError, match="incompatible restore runtime"):
        activation.execute(monkeypatch, rollback_compatible)
    assert activation.current.resolve() == activation.old
    assert activation.commands == []
    assert activation.fragment.read_text() == "old fragment"


@pytest.mark.parametrize('fail_health', [False, True])
def test_photo_activation_checks_revision_before_writers_and_preserves_failed_candidate(tmp_path, monkeypatch, fail_health):
    activation = Activation(tmp_path, 'photo_health' if fail_health else None)
    unit = activation.root / 'etc/systemd/system/schulpilot-photo.service'
    for release, content in ((activation.old, 'old photo unit'), (activation.new, 'new photo unit')):
        (release / 'deploy/schulpilot-photo.service').write_text(content)
        probe = release / 'backend/schulpilot/photo_health.py'
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_text('synthetic health')
    unit.write_text('old photo unit')
    activation.photo_active = activation.photo_enabled = True
    if fail_health:
        with pytest.raises(RuntimeError, match='Socketprüfung'):
            activation.execute(monkeypatch)
        assert activation.current.resolve() == activation.new
        assert unit.read_text() == 'new photo unit'
        assert not activation.photo_active and activation.photo_enabled
        assert activation.restarts == []
        assert any('schulpilot.migrate' in command for command in activation.commands)
        assert ['systemctl', 'stop', *WRITERS] in activation.commands
    else:
        activation.execute(monkeypatch)
        assert activation.current.resolve() == activation.new
        assert unit.read_text() == 'new photo unit'
        health_index = next(i for i, command in enumerate(activation.commands)
                            if command[0] == 'runuser' and command[-1].endswith('photo_health.py'))
        restart_index = activation.commands.index(['systemctl', 'restart', *WRITERS])
        assert health_index < restart_index


@pytest.mark.parametrize("rollback_compatible", [False, True])
def test_restore_rechecked_after_reload_before_migration(tmp_path, monkeypatch, rollback_compatible):
    activation = Activation(tmp_path, "restore_guard_2")
    with pytest.raises(RuntimeError, match="incompatible restore runtime"):
        activation.execute(monkeypatch, rollback_compatible)
    assert activation.current.resolve() == activation.new
    assert activation.restarts == []
    assert ["systemctl", "stop", *WRITERS] in activation.commands
    assert activation.restore_checks == 2
    assert not any("schulpilot.migrate" in command for command in activation.commands)


@pytest.mark.parametrize("rollback_compatible", [False, True])
@pytest.mark.parametrize("failure", ["validate", "drain"])
def test_failure_before_new_writers_retains_existing_release_without_restart(tmp_path, monkeypatch, capsys, rollback_compatible, failure):
    activation = Activation(tmp_path, failure)
    with pytest.raises(subprocess.CalledProcessError):
        activation.execute(monkeypatch, rollback_compatible)
    assert activation.current.resolve() == activation.old
    assert activation.restarts == []
    stop = ["systemctl", "stop", *WRITERS]
    assert activation.commands.count(stop) == (0 if failure == "validate" else 2)
    assert not any("schulpilot.migrate" in command for command in activation.commands)
    assert activation.fragment.read_text() == "old fragment"
    assert (activation.root / "etc/systemd/system/schulpilot-api.service").read_text() == "operator service"
    assert "Current release and units are retained" in capsys.readouterr().err


@pytest.mark.parametrize("changed_schema", [False, True])
def test_migration_failure_retains_candidate_without_schema_guess_or_restart(tmp_path, monkeypatch, capsys, changed_schema):
    activation = Activation(tmp_path, "migration", changed_schema=changed_schema)
    with pytest.raises(subprocess.CalledProcessError):
        activation.execute(monkeypatch)
    # Equal revision markers do not prove no data migration was committed.
    assert activation.schema_reads == 0
    assert activation.current.resolve() == activation.new
    assert activation.restarts == []
    assert ["systemctl", "stop", *WRITERS] in activation.commands
    assert (activation.root / "etc/systemd/system/schulpilot-api.service").read_text() == "new service"
    assert (activation.root / "etc/systemd/system/schulpilot-monitor.timer").read_text() == "operator timer"
    assert (activation.root / "etc/schulpilot-turn/refresh_certificate.py").read_text() == "new certificate helper"
    assert ["systemctl", "stop", "schulpilot-monitor.timer"] not in activation.commands
    assert "verify writers, schema, data, timers and recovery" in capsys.readouterr().err


@pytest.mark.parametrize("rollback_compatible", [False, True])
@pytest.mark.parametrize("failure", ["restart", "enable", "timer", "health", "caddy"])
def test_possible_new_writer_always_stops_and_retains_new_reader(tmp_path, monkeypatch, capsys, rollback_compatible, failure):
    activation = Activation(tmp_path, failure)
    expected = RuntimeError if failure == "health" else subprocess.CalledProcessError
    with pytest.raises(expected):
        activation.execute(monkeypatch, rollback_compatible)
    assert activation.current.resolve() == activation.new
    assert activation.restarts == [(activation.new, True)]  # Partial restart may already have written.
    assert activation.schema_reads == 0  # Schema equality cannot establish JSON or data compatibility.
    stop = ["systemctl", "stop", *WRITERS]
    failure_index = (max(i for i, cmd in enumerate(activation.commands) if cmd == ["health"])
                     if failure == "health" else next(i for i, cmd in enumerate(activation.commands)
                     if (cmd == ["systemctl", "restart", *WRITERS] if failure == "restart"
                         else cmd[:2] == ["systemctl", "enable"] if failure == "enable"
                         else cmd[:3] == ["systemctl", "start", "schulpilot-backup.timer"] if failure == "timer"
                         else cmd == ["systemctl", "reload", "caddy"])))
    assert activation.commands[failure_index + 1] == stop
    assert activation.fragment.read_text() == "old fragment"
    assert activation.prior.readlink() == activation.base / "releases" / OLDER
    message = capsys.readouterr().err
    assert "Current release and units are retained" in message
    assert "verify writers, schema, data, timers and recovery" in message


@pytest.mark.parametrize("rollback_compatible", [False, True])
def test_success_activates_new_release_and_preserves_previous_pointer(tmp_path, monkeypatch, capsys, rollback_compatible):
    activation = Activation(tmp_path)
    activation.execute(monkeypatch, rollback_compatible)
    assert activation.current.resolve() == activation.new and activation.prior.resolve() == activation.old
    assert activation.restarts == [(activation.new, True)]
    assert activation.fragment.read_text() == "new fragment"
    assert activation.schema_reads == 0
    assert any("schulpilot.migrate" in command for command in activation.commands) is (not rollback_compatible)
    assert activation.commands[-1] == ["systemctl", "reload", "caddy"]
    assert f"SCHULPILOT activated: {NEW}" in capsys.readouterr().out


def test_deployment_activation_retains_lease_until_followup_finishes(tmp_path, monkeypatch):
    from deploy.stage_release import acquire_lock, check_lock, finish, guard_legacy_prune

    activation = Activation(tmp_path)
    token = acquire_lock(activation.base, "deploy", NEW, stage="staging")["token"]
    guard_legacy_prune(activation.base, NEW, token)
    activation.execute(monkeypatch, token=token)
    assert check_lock(activation.base)["stage"] == "activated"
    finish(activation.base, NEW, token)
    assert check_lock(activation.base) is None


def test_failed_deployment_activation_keeps_existing_lease(tmp_path, monkeypatch):
    from deploy.stage_release import acquire_lock, check_lock

    activation = Activation(tmp_path, "validate")
    token = acquire_lock(activation.base, "deploy", NEW)["token"]
    with pytest.raises(subprocess.CalledProcessError):
        activation.execute(monkeypatch, token=token)
    assert check_lock(activation.base)["stage"] == "activating"
    assert activation.current.resolve() == activation.old


def test_failed_manual_activation_also_retains_lease(tmp_path, monkeypatch):
    from deploy.stage_release import ReleaseLockError, check_lock, prepare

    activation = Activation(tmp_path, "validate")
    with pytest.raises(subprocess.CalledProcessError):
        activation.execute(monkeypatch)
    assert check_lock(activation.base)["operation"] == "rollback"
    with pytest.raises(ReleaseLockError):
        prepare(activation.base, "20261031T200000Z-abcdef3")


@pytest.mark.parametrize("rollback_compatible", [False, True])
def test_writers_are_drained_and_last_backup_uses_old_release_before_switch(tmp_path, monkeypatch, rollback_compatible):
    activation = Activation(tmp_path)
    activation.execute(monkeypatch, rollback_compatible)
    stop = activation.commands.index(["systemctl", "stop", *WRITERS])
    restart = activation.commands.index(["systemctl", "restart", *WRITERS])
    backups = [i for i, cmd in enumerate(activation.commands)
               if cmd == ["systemctl", "start", "schulpilot-backup.service"]]
    assert len(backups) == 2 and backups[0] < stop < backups[1] < restart
    assert all(activation.command_releases[i] == activation.old for i in [*backups, stop])
    assert activation.command_releases[restart] == activation.new


def test_symlinked_service_refuses_activation_without_modifying_target(tmp_path, monkeypatch):
    activation = Activation(tmp_path)
    unit = activation.root / "etc/systemd/system/schulpilot-api.service"
    unit.unlink()
    target = activation.root / "unit-owner-file"
    target.write_text("keep operator file")
    unit.symlink_to(target)
    with pytest.raises(RuntimeError, match="symlink"):
        activation.execute(monkeypatch)
    assert target.read_text() == "keep operator file"
    assert unit.is_symlink() and activation.current.resolve() == activation.old


def test_migration_failure_does_not_attempt_unit_restore_or_restart(tmp_path, monkeypatch, capsys):
    activation = Activation(tmp_path, "migration")
    original_replace = os.replace

    def replace(source, destination, *args, **kwargs):
        if Path(source).name.startswith(".schulpilot-restore-"):
            raise AssertionError("automatic unit restoration must not occur")
        return original_replace(source, destination, *args, **kwargs)

    monkeypatch.setattr(os, "replace", replace)
    with pytest.raises(subprocess.CalledProcessError):
        activation.execute(monkeypatch)
    assert activation.current.resolve() == activation.new
    assert not activation.restarts
    assert ["systemctl", "stop", *WRITERS] in activation.commands
    assert "Current release and units are retained" in capsys.readouterr().err


@pytest.mark.parametrize("rollback_compatible", [False, True])
def test_failed_drained_backup_prevents_pointer_switch_or_migration(tmp_path, monkeypatch, rollback_compatible):
    activation = Activation(tmp_path, "second_backup")
    with pytest.raises(RuntimeError, match="backup failed"):
        activation.execute(monkeypatch, rollback_compatible)
    assert activation.backup_checks == 2
    assert activation.current.resolve() == activation.old
    assert activation.restarts == []
    assert activation.commands.count(["systemctl", "stop", *WRITERS]) == 2
    assert not any("schulpilot.migrate" in cmd for cmd in activation.commands)
    assert all(release == activation.old for release in activation.command_releases)


def test_joined_backup_is_followed_by_fresh_backup_after_writer_drain(tmp_path, monkeypatch):
    activation = Activation(tmp_path, "stale_drained")
    activation.execute(monkeypatch)
    stop = activation.commands.index(["systemctl", "stop", *WRITERS])
    starts = [i for i, cmd in enumerate(activation.commands) if cmd == ["systemctl", "start", "schulpilot-backup.service"]]
    assert len(starts) == 3 and starts[0] < stop < starts[1] < starts[2]
    assert all(activation.command_releases[i] == activation.old for i in starts)
    assert activation.current.resolve() == activation.new


@pytest.mark.parametrize("failure", ["stale_drained_exhausted", "active_drained", "job_drained", "future_drained", "malformed_drained", "backwards_drained", "missing_drained", "journal_missing_drained", "invocation_changed_drained", "invalid_invocation_drained"])
def test_uncertain_or_repeated_stale_drained_backup_never_switches(tmp_path, monkeypatch, failure):
    activation = Activation(tmp_path, failure)
    with pytest.raises(RuntimeError, match="backup"):
        activation.execute(monkeypatch)
    starts = [cmd for cmd in activation.commands if cmd == ["systemctl", "start", "schulpilot-backup.service"]]
    assert len(starts) == (3 if failure == "stale_drained_exhausted" else 2)
    assert activation.current.resolve() == activation.old
    assert activation.restarts == []
    assert activation.commands.count(["systemctl", "stop", *WRITERS]) == 2
    assert not any("schulpilot.migrate" in command for command in activation.commands)


def test_unavailable_invocation_journal_stops_before_migration(tmp_path, monkeypatch):
    activation = Activation(tmp_path, "journal_unavailable_drained")
    with pytest.raises(subprocess.CalledProcessError):
        activation.execute(monkeypatch)
    assert activation.current.resolve() == activation.old
    assert activation.restarts == []
    assert activation.commands.count(["systemctl", "stop", *WRITERS]) == 2
    assert not any("schulpilot.migrate" in command for command in activation.commands)


def test_failed_drained_start_is_not_retried(tmp_path, monkeypatch):
    activation = Activation(tmp_path, "unknown_start_drained")
    with pytest.raises(subprocess.CalledProcessError):
        activation.execute(monkeypatch)
    assert activation.backup_starts == 2 and activation.backup_checks == 1
    assert activation.current.resolve() == activation.old
    assert not any("schulpilot.migrate" in command for command in activation.commands)
