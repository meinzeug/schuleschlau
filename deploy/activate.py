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
    from release_lock import ReleaseLockError, release_lock, release_operation
except ImportError:
    from deploy.release_lock import ReleaseLockError, release_lock, release_operation

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
previous = current.resolve() if current.is_symlink() else None
caddy = Path("/etc/caddy/Caddyfile")
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
backup = Path(str(caddy) + ".before-schulpilot-" + stamp)
shutil.copy2(caddy, backup)
before = caddy.read_text()
fragment = Path("/etc/caddy/schulpilot.caddy")
fragment_before = fragment.read_text() if fragment.exists() else None
migration_started = False
new_writers_may_have_started = False
schema_before = None
environment = None
unit_snapshots = None

UNIT_NAMES = (
    "schulpilot-api.service", "schulpilot-worker.service", "schulpilot-backup.service",
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
    """Require a completed successful systemd backup before using it as recovery."""
    subprocess.run(["systemctl", "start", "schulpilot-backup.service"], check=True)
    result = subprocess.run(
        ["systemctl", "show", "schulpilot-backup.service", "-p", "Result", "--value"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if result != "success":
        raise RuntimeError("Pre-deployment database backup failed")


def database_revision():
    """Read only the schema marker, never database credentials or private data."""
    script = (
        "from sqlalchemy import create_engine, inspect, text; import os; "
        "e=create_engine(os.environ['DATABASE_URL']); "
        "c=e.connect(); "
        "print(','.join(sorted(c.execute(text('SELECT version_num FROM alembic_version')).scalars())) "
        "if inspect(e).has_table('alembic_version') else '<empty>')"
    )
    result = subprocess.run(
        ["runuser", "-u", "schulpilot", "--", str(release / "venv/bin/python"), "-c", script],
        cwd=release / "backend",
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


operation = "activate" if token else "rollback"
try:
    with release_operation(base, operation, release_id, token=token, stage="activating"):
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
            if previous:
                # Stop first: a crash/restart must not resolve the new current pointer
                # against the old database, including on an explicit code rollback.
                subprocess.run(["systemctl", "stop", "schulpilot-api", "schulpilot-worker"], check=True)
                # This uses the old current release and captures work finished while
                # the worker was draining, before the pointer or schema is changed.
                checked_backup()
            temporary = base / ".current-new"
            temporary.unlink(missing_ok=True)
            temporary.symlink_to(release)
            temporary.replace(current)
            for name in UNIT_NAMES:
                source = release / "deploy" / name
                if source.is_file():
                    shutil.copy2(source, Path("/etc/systemd/system") / name)
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
            if not rollback_compatible:
                schema_before = database_revision()
                migration_started = True
                subprocess.run(
                    ["runuser", "-u", "schulpilot", "--", str(release / "venv/bin/python"), "-m", "schulpilot.migrate"],
                    cwd=release / "backend",
                    env=environment,
                    check=True,
                )
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
            subprocess.run(["systemctl", "enable", "schulpilot-api", "schulpilot-worker", *timers], check=True)
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
                release_lock(base, token)
            print("SCHULPILOT activated: " + release_id)
        except Exception:
            if new_writers_may_have_started:
                # Stop possible writers before any recovery checks; retain this release
                # as the reader for JSON it may already have stored.
                subprocess.run(["systemctl", "stop", "schulpilot-api", "schulpilot-worker"], check=False)
            caddy.write_text(before)
            if fragment_before is not None:
                fragment.write_text(fragment_before)
            elif fragment.exists():
                fragment.unlink()
            compatible = not migration_started and not new_writers_may_have_started
            if migration_started and not new_writers_may_have_started:
                try:
                    compatible = database_revision() == schema_before
                except Exception:
                    compatible = False
            if previous and compatible:
                try:
                    if unit_snapshots is not None:
                        restore_files(unit_snapshots)
                        subprocess.run(["systemctl", "daemon-reload"], check=True)
                    temporary = base / ".current-restore"
                    temporary.unlink(missing_ok=True)
                    temporary.symlink_to(previous)
                    temporary.replace(current)
                    subprocess.run(["systemctl", "restart", "schulpilot-api", "schulpilot-worker"], check=True)
                except Exception:
                    subprocess.run(["systemctl", "stop", "schulpilot-api", "schulpilot-worker"], check=False)
                    print("Automatic rollback incomplete; services stopped. Restore service definitions and verify the active release before restart.", file=sys.stderr)
            else:
                if not new_writers_may_have_started:
                    subprocess.run(["systemctl", "stop", "schulpilot-api", "schulpilot-worker"], check=False)
                if new_writers_may_have_started:
                    print(
                        "New release writers may have persisted incompatible JSON: services stopped and current release retained. "
                        "Use a compatible forward fix or explicitly verify data/code compatibility before any rollback; "
                        "unchanged SQL schema and --rollback-compatible are not sufficient.",
                        file=sys.stderr,
                    )
                elif migration_started and not compatible:
                    print(
                        "Schema changed: services stopped. Restore the verified pre-deployment database backup before activating the previous release.",
                        file=sys.stderr,
                    )
            subprocess.run(["systemctl", "reload", "caddy"], check=False)
            raise
except ReleaseLockError as exc:
    print(f"Activation refused: {exc}", file=sys.stderr)
    raise SystemExit(1)
