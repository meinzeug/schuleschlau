"""Safely activate an uploaded immutable release; retain rollback pointer."""

import argparse
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    from release_lock import ReleaseLockError, release_operation, update_lock
except ImportError:
    from deploy.release_lock import ReleaseLockError, release_operation, update_lock
try:
    from backup_release_check import verify_invocation_log
except ImportError:
    from deploy.backup_release_check import verify_invocation_log
try:
    from restore_release_guard import verify as verify_restore_configuration
except ImportError:
    from deploy.restore_release_guard import verify as verify_restore_configuration
try:
    from photo_release import (
        ensure_isolated_identity,
        inspect_photo,
        start_candidate,
        stop_old_photo,
        undo_candidate_enable,
        verify_photo_definition,
    )
except ImportError:
    from deploy.photo_release import (
        ensure_isolated_identity,
        inspect_photo,
        start_candidate,
        stop_old_photo,
        undo_candidate_enable,
        verify_photo_definition,
    )

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("release_id")
parser.add_argument("--rollback-compatible", action="store_true")
parser.add_argument("--token", default=None)
args, _ = parser.parse_known_args()
release_id = args.release_id
rollback_compatible = args.rollback_compatible
token = args.token

if not re.fullmatch(r"[a-zA-Z0-9._-]+", release_id):
    raise SystemExit("Invalid release identifier")
base = Path("/opt/schulpilot")
release = base / "releases" / release_id
if not (release / "web/index.html").is_file() or not (release / "backend/requirements.lock").is_file():
    raise SystemExit("Release is incomplete")
current = base / "current"
caddy = Path("/etc/caddy/Caddyfile")
fragment = Path("/etc/caddy/schulpilot.caddy")
migration_started = False
new_writers_may_have_started = False
writer_stop_attempted = False
environment = None
unit_snapshots = None
photo_previous = None
photo_candidate_started = False

UNIT_NAMES = (
    "schulpilot-api.service", "schulpilot-worker.service", "schulpilot-photo.service", "schulpilot-backup.service",
    "schulpilot-backup.timer", "schulpilot-backup-retention.service", "schulpilot-backup-retention.timer",
    "schulpilot-monitor.service", "schulpilot-monitor.timer",
    "schulpilot-restore-check.service", "schulpilot-restore-check.timer",
)
TURN_NAMES = ("schulpilot-turn.service", "schulpilot-turn-cert.service", "schulpilot-turn-cert.timer")


def snapshot_files(paths):
    """Retain operator-owned service definitions before replacing any of them."""
    result = {}
    for path in paths:
        if path.is_symlink():
            raise RuntimeError("A managed service file is a symlink; reconcile it before deployment")
        if not path.exists():
            result[path] = None
            continue
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            raise RuntimeError("A managed service file is not regular; reconcile it before deployment")
        result[path] = (path.read_bytes(), info.st_mode, info.st_uid, info.st_gid, info.st_atime_ns, info.st_mtime_ns)
    return result


def restore_files(snapshots):
    """Atomically restore prior definitions before restarting the previous code."""
    for path, saved in snapshots.items():
        if saved is None:
            path.unlink(missing_ok=True)
            continue
        data, mode, uid, gid, atime, mtime = saved
        fd, name = tempfile.mkstemp(prefix=".schulpilot-restore-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fchown(stream.fileno(), uid, gid)
                os.fchmod(stream.fileno(), stat.S_IMODE(mode))
            os.utime(name, ns=(atime, mtime))
            os.replace(name, path)
        finally:
            Path(name).unlink(missing_ok=True)


def checked_backup():
    """Require a successful backup that actually started after this call.

    systemd coalesces `start` into an already running oneshot. Merely checking
    Result=success could therefore accept a backup started before writer drain.
    Record a kernel monotonic watermark after drain; systemd reports matching
    CLOCK_MONOTONIC timestamps in microseconds, independent of wall-clock/NTP.
    """
    started_after = time.monotonic_ns() // 1000 + 1
    for attempt in range(2):
        subprocess.run(["systemctl", "start", "schulpilot-backup.service"], check=True)
        output = subprocess.run(
            ["systemctl", "show", "schulpilot-backup.service", "--no-pager",
             "-p", "Result", "-p", "ActiveState", "-p", "SubState", "-p", "Job",
             "-p", "ExecMainStartTimestampMonotonic", "-p", "ExecMainExitTimestampMonotonic",
             "-p", "ExecMainCode", "-p", "ExecMainStatus", "-p", "InvocationID"],
            check=True, capture_output=True, text=True,
        ).stdout
        fields = {}
        for line in output.splitlines():
            key, separator, value = line.partition("=")
            if not separator or key in fields:
                raise RuntimeError("Pre-deployment database backup status is invalid")
            fields[key] = value
        required = {"Result", "ActiveState", "SubState", "Job", "ExecMainStartTimestampMonotonic",
                    "ExecMainExitTimestampMonotonic", "ExecMainCode", "ExecMainStatus", "InvocationID"}
        if (set(fields) != required or fields["Result"] != "success" or fields["ActiveState"] != "inactive"
                or fields["SubState"] != "dead" or fields["Job"] or fields["ExecMainCode"] != "1"
                or fields["ExecMainStatus"] != "0"):
            raise RuntimeError("Pre-deployment database backup failed or has an uncertain status")
        try:
            start_us = int(fields["ExecMainStartTimestampMonotonic"])
            exit_us = int(fields["ExecMainExitTimestampMonotonic"])
        except (ValueError, TypeError):
            raise RuntimeError("Pre-deployment database backup timestamps are invalid") from None
        now_us = time.monotonic_ns() // 1000
        if start_us <= 0 or exit_us < start_us or exit_us > now_us:
            raise RuntimeError("Pre-deployment database backup timestamps are invalid")
        if start_us >= started_after:
            invocation = fields["InvocationID"]
            if not re.fullmatch(r"[0-9a-f]{32}", invocation):
                raise RuntimeError("Pre-deployment backup invocation is unavailable")
            journal = subprocess.run(
                ["journalctl", "--no-pager", "--quiet", "--output=cat", "_SYSTEMD_INVOCATION_ID=" + invocation],
                check=True, capture_output=True, text=True, timeout=10,
            ).stdout
            verify_invocation_log(journal)
            current = subprocess.run(
                ["systemctl", "show", "schulpilot-backup.service", "--value", "-p", "InvocationID"],
                check=True, capture_output=True, text=True, timeout=10,
            ).stdout.strip()
            if current != invocation:
                raise RuntimeError("Pre-deployment backup invocation changed during verification")
            return
        # The first call joined an older successful execution. Start one new
        # backup, then require proof it crossed the original watermark.
        if attempt:
            raise RuntimeError("Pre-deployment database backup was not freshly started")
    raise RuntimeError("Pre-deployment database backup failed")



operation = "activate" if token else "rollback"
try:
    with release_operation(base, operation, release_id, token=token, stage="activating"):
        # The target could have disappeared after the initial check. In a
        # rollback the legacy-prune guard is now in place before we use it.
        if not (release / "web/index.html").is_file() or not (release / "backend/requirements.lock").is_file():
            raise RuntimeError("Release disappeared before activation")
        previous = current.resolve() if current.is_symlink() else None
        if previous:
            # A managed service file may be overridden by an operator drop-in.
            # Check the effective command before stopping any service or doing
            # a migration; repeat after daemon-reload just before migration.
            verify_restore_configuration(release, rollback=rollback_compatible, active=previous)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = Path(str(caddy) + ".before-schulpilot-" + stamp)
        shutil.copy2(caddy, backup)
        before = caddy.read_text()
        fragment_before = fragment.read_text() if fragment.exists() else None
        try:
            if not (release / "venv/bin/pip").exists():
                subprocess.run(["python3", "-m", "venv", str(release / "venv")], check=True)
                subprocess.run(
                    [
                        str(release / "venv/bin/pip"),
                        "install",
                        "--disable-pip-version-check",
                        "-r",
                        str(release / "backend/requirements.lock"),
                    ],
                    check=True,
                )
            fragment.write_text((release / "deploy/Caddyfile.schulpilot").read_text())
            if "import /etc/caddy/schulpilot.caddy" not in before:
                if "schulpilot.dorfspy.de" in before:
                    raise RuntimeError("Existing SCHULPILOT host block needs manual reconciliation")
                caddy.write_text(before.rstrip() + "\n\nimport /etc/caddy/schulpilot.caddy\n")
            subprocess.run(["caddy", "validate", "--config", str(caddy), "--adapter", "caddyfile"], check=True)
            if previous:
                checked_backup()
            turn = Path("/etc/schulpilot-turn")
            turn_installed = (turn / "turnserver.conf").is_file()
            destinations = [Path("/etc/systemd/system") / name for name in UNIT_NAMES]
            if turn_installed:
                destinations += [Path("/etc/systemd/system") / name for name in TURN_NAMES]
                destinations.append(turn / "refresh_certificate.py")
            unit_snapshots = snapshot_files(destinations)
            photo_previous = inspect_photo()
            verify_photo_definition(photo_previous, previous)
            photo_supported = (release / "deploy/schulpilot-photo.service").is_file()
            if photo_supported:
                ensure_isolated_identity(release)
            if previous:
                # Stop first: a crash/restart must not resolve the new current pointer
                # against the old database, including on an explicit code rollback.
                writer_stop_attempted = True
                subprocess.run(["systemctl", "stop", "schulpilot-api", "schulpilot-worker"], check=True)
            stop_old_photo(photo_previous)
            if previous:
                # This uses the old current release and captures work finished while
                # the worker was draining, before the pointer or schema is changed.
                checked_backup()
            if not photo_supported and photo_previous.loaded:
                subprocess.run(["systemctl", "disable", "schulpilot-photo.service"], check=True)
            temporary = base / ".current-new"
            temporary.unlink(missing_ok=True)
            temporary.symlink_to(release)
            temporary.replace(current)
            for name in UNIT_NAMES:
                source = release / "deploy" / name
                if source.is_file():
                    shutil.copy2(source, Path("/etc/systemd/system") / name)
            if not photo_supported:
                Path("/etc/systemd/system/schulpilot-photo.service").unlink(missing_ok=True)
            # An existing operator-installed relay is maintained, never auto-installed.
            if turn_installed:
                for name in TURN_NAMES:
                    source = release / "deploy" / name
                    if source.is_file():
                        shutil.copy2(source, Path("/etc/systemd/system") / name)
                source = release / "deploy/turn_certificate.py"
                if source.is_file():
                    shutil.copy2(source, turn / "refresh_certificate.py")
                    (turn / "refresh_certificate.py").chmod(0o644)
            subprocess.run(["systemctl", "daemon-reload"], check=True)
            if photo_supported:
                verify_photo_definition(inspect_photo(), release)
            timers = ["schulpilot-backup.timer"]
            if (release / "deploy/schulpilot-backup-retention.timer").is_file():
                timers.append("schulpilot-backup-retention.timer")
            if (release / "deploy/schulpilot-restore-check.timer").is_file():
                timers.append("schulpilot-restore-check.timer")
            if (release / "deploy/schulpilot-monitor.timer").is_file():
                timers.append("schulpilot-monitor.timer")
            environment = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
            import shlex

            for line in Path("/etc/schulpilot/environment").read_text().splitlines():
                if line.strip() and not line.lstrip().startswith("#"):
                    key, value = line.split("=", 1)
                    environment[key] = " ".join(shlex.split(value)) if value else ""
            if previous:
                verify_restore_configuration(release, rollback=rollback_compatible, active=previous, check_interpreter=True)
            if not rollback_compatible:
                migration_started = True
                subprocess.run(
                    ["runuser", "-u", "schulpilot", "--", str(release / "venv/bin/python"), "-m", "schulpilot.migrate"],
                    cwd=release / "backend",
                    env=environment,
                    check=True,
                )
            if photo_supported:
                # Start in its own cgroup and verify matching service + decoder +
                # locked dependencies as the API UID before any new writer starts.
                photo_candidate_started = True
                start_candidate(release)
            # A failed restart can still have started one writer. SQL schema equality
            # cannot prove compatibility with JSON formats persisted by the new code.
            new_writers_may_have_started = True
            subprocess.run(["systemctl", "restart", "schulpilot-api", "schulpilot-worker"], check=True)
            # These change enabled/active timer state. Only do so once new writers may
            # have run: earlier failures can then restore the old service definitions
            # without having to guess the operator's previous timer configuration.
            for optional in ("schulpilot-backup-retention.timer", "schulpilot-restore-check.timer", "schulpilot-monitor.timer"):
                if optional not in timers and Path("/etc/systemd/system", optional).exists():
                    subprocess.run(["systemctl", "stop", optional], check=True)
            enable_services = ["schulpilot-api", "schulpilot-worker", *timers]
            if photo_supported:
                enable_services.append("schulpilot-photo.service")
            subprocess.run(["systemctl", "enable", *enable_services], check=True)
            subprocess.run(["systemctl", "start", *timers], check=True)
            healthy = False
            for _ in range(30):
                try:
                    with urllib.request.urlopen("http://127.0.0.1:3240/api/health", timeout=2) as response:
                        healthy = response.status == 200
                    if healthy:
                        break
                except OSError:
                    pass
                time.sleep(1)
            if not healthy:
                raise RuntimeError("API healthcheck failed")
            subprocess.run(["systemctl", "reload", "caddy"], check=True)
            if previous and previous != release:
                prior = base / "previous"
                prior.unlink(missing_ok=True)
                prior.symlink_to(previous)
            if token:
                update_lock(base, token, stage="activated", release_id=release_id)
            print("SCHULPILOT activated: " + release_id)
        except Exception:
            if writer_stop_attempted or new_writers_may_have_started:
                # A failed stop may already have stopped only one unit. Never
                # automatically start either writer on this failure path.
                subprocess.run(["systemctl", "stop", "schulpilot-api", "schulpilot-worker"], check=False)
            if photo_candidate_started:
                try:
                    undo_candidate_enable(photo_previous)
                except Exception:
                    print("Could not stop candidate photo service; verify it before restarting writers.", file=sys.stderr)
                    # Do not restart previous writers while an uncertain decoder runs.
                    new_writers_may_have_started = True
                    subprocess.run(["systemctl", "stop", "schulpilot-api", "schulpilot-worker"], check=False)
            caddy.write_text(before)
            if fragment_before is not None:
                fragment.write_text(fragment_before)
            elif fragment.exists():
                fragment.unlink()
            # An attempted migration may persist changes before its schema
            # marker changes. Schema equality alone cannot authorize rollback.
            compatible = not migration_started and not new_writers_may_have_started
            if previous and compatible:
                try:
                    if unit_snapshots is not None:
                        restore_files(unit_snapshots)
                        subprocess.run(["systemctl", "daemon-reload"], check=True)
                    temporary = base / ".current-restore"
                    temporary.unlink(missing_ok=True)
                    temporary.symlink_to(previous)
                    temporary.replace(current)
                    if writer_stop_attempted:
                        print("Previous definitions restored; inspect writer, photo and timer state before explicit restart.", file=sys.stderr)
                except Exception:
                    subprocess.run(["systemctl", "stop", "schulpilot-api", "schulpilot-worker"], check=False)
                    print("Automatic rollback incomplete; inspect service state and restore definitions before any restart.", file=sys.stderr)
            else:
                if new_writers_may_have_started:
                    print(
                        "New release writers may have persisted incompatible JSON: stop requested and current release retained. "
                        "Use a compatible forward fix or explicitly verify data/code compatibility before any rollback; "
                        "unchanged SQL schema and --rollback-compatible are not sufficient.",
                        file=sys.stderr,
                    )
                elif migration_started and not compatible:
                    print(
                        "Migration was attempted; schema or data may have changed. Stop requested. Verify a recovery path before activating the previous release.",
                        file=sys.stderr,
                    )
            subprocess.run(["systemctl", "reload", "caddy"], check=False)
            raise
except ReleaseLockError as exc:
    print(f"Activation refused: {exc}", file=sys.stderr)
    raise SystemExit(1)
