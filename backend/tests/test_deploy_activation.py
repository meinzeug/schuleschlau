"""Run the real activation script against temporary files and offline OS mocks."""

import builtins
import os
import runpy
import subprocess
import sys
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
        if command[0] == "runuser" and "-c" in command:
            self.schema_reads += 1
            schema = "0032" if self.changed_schema and self.schema_reads > 1 else "0031"
            return subprocess.CompletedProcess(command, 0, stdout=schema + "\n")
        if command[:3] == ["systemctl", "show", "schulpilot-backup.service"]:
            self.backup_checks += 1
            result = "failed" if self.failure == "second_backup" and self.backup_checks == 2 else "success"
            return subprocess.CompletedProcess(command, 0, stdout=result + "\n")
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

    def health(self, *_args, **_kwargs):
        self.commands.append(["health"])
        if self.failure == "health":
            raise OSError("synthetic health unavailable")
        return SimpleNamespace(__enter__=lambda self: self, __exit__=lambda *_: None, status=200)

    def execute(self, monkeypatch, rollback_compatible=False, token=None):
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
            "pathlib": SimpleNamespace(Path=self.path),
            "subprocess": SimpleNamespace(run=self.run),
            "time": SimpleNamespace(sleep=lambda _: None),
            "urllib.request": SimpleNamespace(request=SimpleNamespace(urlopen=urlopen)),
        }

        def imports(name, globals=None, locals=None, fromlist=(), level=0):
            return replacements.get(name) or real_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(sys, "argv", [str(SCRIPT), NEW, *(["--rollback-compatible"] if rollback_compatible else []),
                                         *(["--token", token] if token else [])])
        return runpy.run_path(str(SCRIPT), init_globals={"__builtins__": {**vars(builtins), "__import__": imports}})


@pytest.mark.parametrize("rollback_compatible", [False, True])
@pytest.mark.parametrize("failure", ["validate", "drain"])
def test_failure_before_new_writers_keeps_schema_safe_old_release(tmp_path, monkeypatch, capsys, rollback_compatible, failure):
    activation = Activation(tmp_path, failure)
    with pytest.raises(subprocess.CalledProcessError):
        activation.execute(monkeypatch, rollback_compatible)
    assert activation.current.resolve() == activation.old
    assert activation.restarts == [(activation.old, True)]
    assert activation.fragment.read_text() == "old fragment"
    assert (activation.root / "etc/systemd/system/schulpilot-api.service").read_text() == "operator service"
    assert "incompatible JSON" not in capsys.readouterr().err


@pytest.mark.parametrize("changed_schema", [False, True])
def test_migration_failure_before_new_writers_only_rolls_back_unchanged_schema(tmp_path, monkeypatch, capsys, changed_schema):
    activation = Activation(tmp_path, "migration", changed_schema=changed_schema)
    with pytest.raises(subprocess.CalledProcessError):
        activation.execute(monkeypatch)
    assert activation.schema_reads == 2
    if changed_schema:
        assert activation.current.resolve() == activation.new
        assert activation.restarts == []
        assert ["systemctl", "stop", *WRITERS] in activation.commands
        assert "Schema changed" in capsys.readouterr().err
    else:
        assert activation.current.resolve() == activation.old
        assert activation.restarts == [(activation.old, True)]
        assert (activation.root / "etc/systemd/system/schulpilot-api.service").read_text() == "operator service"
        assert (activation.root / "etc/systemd/system/schulpilot-monitor.timer").read_text() == "operator timer"
        assert (activation.root / "etc/schulpilot-turn/refresh_certificate.py").read_text() == "operator certificate helper"
        assert ["systemctl", "stop", "schulpilot-monitor.timer"] not in activation.commands


@pytest.mark.parametrize("rollback_compatible", [False, True])
@pytest.mark.parametrize("failure", ["restart", "enable", "timer", "health", "caddy"])
def test_possible_new_writer_always_stops_and_retains_new_reader(tmp_path, monkeypatch, capsys, rollback_compatible, failure):
    activation = Activation(tmp_path, failure)
    expected = RuntimeError if failure == "health" else subprocess.CalledProcessError
    with pytest.raises(expected):
        activation.execute(monkeypatch, rollback_compatible)
    assert activation.current.resolve() == activation.new
    assert activation.restarts == [(activation.new, True)]  # Partial restart may already have written.
    assert activation.schema_reads == (0 if rollback_compatible else 1)  # Never read revision after possible writes.
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
    assert "current release retained" in message and "compatible forward fix" in message
    assert "--rollback-compatible are not sufficient" in message


@pytest.mark.parametrize("rollback_compatible", [False, True])
def test_success_activates_new_release_and_preserves_previous_pointer(tmp_path, monkeypatch, capsys, rollback_compatible):
    activation = Activation(tmp_path)
    activation.execute(monkeypatch, rollback_compatible)
    assert activation.current.resolve() == activation.new and activation.prior.resolve() == activation.old
    assert activation.restarts == [(activation.new, True)]
    assert activation.fragment.read_text() == "new fragment"
    assert activation.schema_reads == (0 if rollback_compatible else 1)
    assert activation.commands[-1] == ["systemctl", "reload", "caddy"]
    assert f"SCHULPILOT activated: {NEW}" in capsys.readouterr().out


def test_deployment_activation_retains_lease_until_followup_finishes(tmp_path, monkeypatch):
    from deploy.stage_release import acquire_lock, check_lock, finish

    activation = Activation(tmp_path)
    token = acquire_lock(activation.base, "deploy", NEW)["token"]
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


def test_restore_failure_keeps_writers_stopped(tmp_path, monkeypatch, capsys):
    activation = Activation(tmp_path, "migration")
    original_replace = os.replace

    def replace(source, destination, *args, **kwargs):
        if Path(source).name.startswith(".schulpilot-restore-"):
            raise OSError("synthetic restore failure")
        return original_replace(source, destination, *args, **kwargs)

    monkeypatch.setattr(os, "replace", replace)
    with pytest.raises(subprocess.CalledProcessError):
        activation.execute(monkeypatch)
    assert activation.current.resolve() == activation.new
    assert not activation.restarts
    assert activation.commands[-2] == ["systemctl", "stop", *WRITERS]
    assert "Automatic rollback incomplete; services stopped" in capsys.readouterr().err


@pytest.mark.parametrize("rollback_compatible", [False, True])
def test_failed_drained_backup_prevents_pointer_switch_or_migration(tmp_path, monkeypatch, rollback_compatible):
    activation = Activation(tmp_path, "second_backup")
    with pytest.raises(RuntimeError, match="backup failed"):
        activation.execute(monkeypatch, rollback_compatible)
    assert activation.backup_checks == 2
    assert activation.current.resolve() == activation.old
    assert activation.restarts == [(activation.old, True)]
    assert not any("schulpilot.migrate" in cmd for cmd in activation.commands)
    assert all(release == activation.old for release in activation.command_releases)
