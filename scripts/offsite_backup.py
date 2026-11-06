"""Pull existing project ciphertext to an independent, authorized host.

Uses the operator's existing SSH alias; never transfers SSH or backup keys.
Only constrained backup filenames are passed to the remote shell.
"""

import argparse
import fcntl
import hashlib
import json
import os
import re
import select
import socket
import stat
import struct
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

MIN_SUCCESS_GAP_SECONDS = 60
RETENTION_SECONDS = 14 * 86400
# Allow regular timer cadence, the configured transfer timeout and a bounded
# pacing delay to complete before the maximum retention period expires.
RETENTION_BUFFER_SECONDS = 2 * 3600


class InterruptedTransfer(RuntimeError):
    """A previous transfer needs an operator to reconcile both hosts."""


HANDOFF_MARKER = ".offsite-handoff.pending"


class AcknowledgementRejected(RuntimeError):
    """The server explicitly rejected a stale backup before writing its ACK."""


def run(args, **kwargs):
    return subprocess.run(args, check=True, timeout=120, **kwargs)


def sync_directory(destination):
    """Persist directory entries before making claims about the local copy."""
    fd = os.open(destination, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def commit_ledger(destination, partial, acknowledge, success, *, check=lambda: None):
    """Keep the previous snapshot when an ordinary acknowledgement fails.

    An interrupted cross-host transaction requires operator reconciliation;
    `.pending` and `.previous` deliberately survive a process crash.
    """
    check()
    ledger = destination / "erasure-ledger.enc"
    previous = destination / ".erasure-ledger.previous"
    pending = destination / ".erasure-ledger.pending"
    marker = destination / "last-success.json"
    marker_previous = destination / ".offsite-status.previous"
    if any(os.path.lexists(path) for path in (pending, previous, marker_previous)):
        raise InterruptedTransfer("An interrupted journal transfer requires reconciliation")
    had_previous = ledger.exists()
    with pending.open("x") as output:
        output.write(json.dumps({"had_previous": had_previous}) + "\n")
        output.flush()
        os.fsync(output.fileno())
    # A crash from this point must leave a reconciliation marker before the
    # old journal is linked or replaced and especially before any remote ACK.
    sync_directory(destination)
    installed = False
    marker_installed = False
    had_marker = False
    ack_started = False
    try:
        check()
        if had_previous:
            os.link(ledger, previous)
            sync_directory(destination)
        check()
        partial.replace(ledger)
        installed = True
        sync_directory(destination)
        check()
        ack_started = True
        acknowledge()
        check()
        with tempfile.NamedTemporaryFile(mode="w", dir=destination, prefix=".offsite-status-", delete=False) as output:
            status = Path(output.name)
            try:
                output.write(json.dumps(success) + "\n")
                output.flush()
                os.fsync(output.fileno())
            except Exception:
                check()
                status.unlink(missing_ok=True)
                raise
        try:
            check()
            had_marker = marker.exists()
            if had_marker:
                if marker.is_symlink() or not marker.is_file():
                    raise RuntimeError("Untrusted success marker")
                os.link(marker, marker_previous)
                sync_directory(destination)
            check()
            status.replace(marker)
            marker_installed = True
            sync_directory(destination)
        except Exception:
            check()
            status.unlink(missing_ok=True)
            raise
    except Exception as error:
        # If supervised ownership was lost, another recovery/operator may hold
        # the path now. Leave durable transaction markers and all files alone.
        check()
        # Preserve the old success marker and restore exactly the prior bytes.
        # If rollback fails, leave the transaction files for operator recovery.
        if installed:
            if had_previous:
                previous.replace(ledger)
            else:
                ledger.unlink(missing_ok=True)
        else:
            previous.unlink(missing_ok=True)
        if marker_installed:
            if had_marker:
                marker_previous.replace(marker)
            else:
                marker.unlink(missing_ok=True)
        else:
            marker_previous.unlink(missing_ok=True)
        sync_directory(destination)
        # A remote failure or timeout may follow a successful server ACK; the
        # prior snapshot is restored but its relationship to the remote marker
        # is unknown. Retain the marker and require human reconciliation.
        if not ack_started or isinstance(error, AcknowledgementRejected):
            pending.unlink(missing_ok=True)
            sync_directory(destination)
        raise
    check()
    previous.unlink(missing_ok=True)
    check()
    marker_previous.unlink(missing_ok=True)
    sync_directory(destination)
    check()
    pending.unlink()
    sync_directory(destination)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, default=Path.home() / ".local/share/schulpilot-offsite")
    # Internal handoff for a trusted local supervisor; no descriptor is opened
    # on behalf of the caller. The ordinary timer continues to pass no flags.
    parser.add_argument("--supervised-lock-fd", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--supervised-pid-fd", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--supervised-channel-fd", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--supervised-run-id", help=argparse.SUPPRESS)
    args = parser.parse_args()
    os.umask(0o077)
    values = (args.supervised_lock_fd, args.supervised_pid_fd, args.supervised_channel_fd, args.supervised_run_id)
    if any(value is not None for value in values):
        if (any(value is None for value in values) or any(fd < 3 for fd in values[:3])
                or len(set(values[:3])) != 3):
            raise RuntimeError("Incomplete supervised handoff")
        SupervisedHandoff(args.destination, *values).run()
        return
    args.destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.destination.chmod(0o700)
    with (args.destination / ".pull.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if os.path.lexists(args.destination / HANDOFF_MARKER):
            raise InterruptedTransfer("An interrupted supervised transfer requires reconciliation")
        pace_recent_success(args.destination)
        pull(args.destination)



class SupervisedHandoff:
    """Experimental local OFD handoff; caller must be the trusted supervisor.

    Liveness is checked between long operations. A supervisor death during an
    SSH call can leave that call running; the durable marker prohibits retry
    until operator reconciliation and independent unit/cgroup verification.
    This is not an independently usable two-host guard or a release protocol.
    """

    def __init__(self, destination, lock_fd, pid_fd, channel_fd, run_id):
        if not re.fullmatch(r"[0-9a-f]{32}", run_id):
            raise RuntimeError("Invalid supervised run identity")
        self.destination = Path(destination)
        self.lock_fd, self.pid_fd, self.channel_fd = lock_fd, pid_fd, channel_fd
        self.run_id = run_id
        # pass_fds makes descriptors inheritable in this interpreter; never
        # leak the lock, pidfd or channel to SSH or any other descendant.
        for fd in (lock_fd, pid_fd, channel_fd):
            os.set_inheritable(fd, False)
        self.channel = socket.socket(fileno=channel_fd)
        self.parent_pid = os.getppid()
        peer_pid, peer_uid, _ = struct.unpack("3i", self.channel.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        if peer_pid != self.parent_pid or peer_uid != os.geteuid():
            raise RuntimeError("Untrusted supervisor channel")
        if self.channel.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE) != socket.SOCK_SEQPACKET:
            raise RuntimeError("Supervised channel must preserve message boundaries")
        if os.readlink(f"/proc/self/fd/{pid_fd}") != "anon_inode:[pidfd]":
            raise RuntimeError("Supervisor pidfd required")
        pid_info = Path(f"/proc/self/fdinfo/{pid_fd}").read_text().splitlines()
        if f"Pid:\t{self.parent_pid}" not in pid_info:
            raise RuntimeError("Supervisor pidfd does not match parent")
        self.check()

    def check(self):
        if os.getppid() != self.parent_pid or select.select([self.pid_fd], [], [], 0)[0]:
            raise RuntimeError("Supervisor no longer running")
        if select.select([self.channel], [], [], 0)[0]:
            if not self.channel.recv(1, socket.MSG_PEEK | socket.MSG_DONTWAIT):
                raise RuntimeError("Supervisor channel closed")
            raise RuntimeError("Unexpected supervisor message")
        directory = os.lstat(self.destination)
        held = os.fstat(self.lock_fd)
        actual = os.lstat(self.destination / ".pull.lock")
        if (not stat.S_ISDIR(directory.st_mode) or directory.st_uid != os.geteuid()
                or directory.st_mode & 0o077 or not stat.S_ISREG(held.st_mode)
                or held.st_uid != os.geteuid() or held.st_mode & 0o077 or held.st_nlink != 1
                or (held.st_dev, held.st_ino) != (actual.st_dev, actual.st_ino)):
            raise RuntimeError("Untrusted supervised lock or destination")
        # The trusted supervisor retains the same locked open description.
        # This catches accidental unlocks, but cannot establish provenance
        # against an adversarial equally privileged process.
        probe = os.open(self.destination / ".pull.lock", os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            probed = os.fstat(probe)
            if (probed.st_dev, probed.st_ino) != (held.st_dev, held.st_ino):
                raise RuntimeError("Supervised lock was replaced")
            try:
                fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                pass
            else:
                fcntl.flock(probe, fcntl.LOCK_UN)
                raise RuntimeError("Supervised lock is not held")
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(probe)

    def run(self):
        self.check()
        marker = self.destination / HANDOFF_MARKER
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        try:
            with os.fdopen(fd, "w") as output:
                output.write(json.dumps({"run_id": self.run_id}) + "\n")
                output.flush()
                os.fsync(output.fileno())
        finally:
            sync_directory(self.destination)
        self.check()
        self.channel.sendall(("READY " + self.run_id).encode())
        pace_recent_success(self.destination)
        self.check()
        pull(self.destination, _supervised=True, _check=self.check)
        self.check()
        self.channel.sendall(("DONE " + self.run_id).encode())
        # The supervisor/recovery procedure, after unit and remote-ACK checks,
        # removes the durable marker. This worker must never clear it.


def pace_recent_success(destination):
    """Avoid immediately repeating a successful long full-digest run.

    Only an existing local success marker can cause a bounded delay; missing,
    invalid or future timestamps never stop a backup. The normal timer and
    the complete checksum verification remain unchanged.
    """
    try:
        marker = destination / "last-success.json"
        if marker.is_symlink() or not marker.is_file() or marker.stat().st_size > 4096:
            return
        checked = json.loads(marker.read_text()).get("checked_at")
    except (OSError, UnicodeError, ValueError, AttributeError, RecursionError):
        return
    # Guard floating-point conversion and reject impossible dates. Corrupt
    # local metadata must never prevent the real backup from starting.
    if type(checked) is not int or not 0 <= checked <= 253402300799:
        return
    age = time.time() - checked
    if 0 <= age < MIN_SUCCESS_GAP_SECONDS:
        time.sleep(MIN_SUCCESS_GAP_SECONDS - age)


def backup_time(name):
    if not isinstance(name, str) or not re.fullmatch(r"\d{8}T\d{6}Z\.tar\.enc", name):
        raise RuntimeError("Unexpected backup filename")
    try:
        return datetime.strptime(name[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).timestamp()
    except (ValueError, OverflowError):
        raise RuntimeError("Invalid backup timestamp") from None


def retained_inventory(inventory):
    """Validate all identities before transferring only currently retained archives."""
    stamp, rows = inventory.get("server_now"), inventory.get("backups")
    if type(stamp) is not int or stamp <= 0 or not isinstance(rows, list):
        raise RuntimeError("Invalid server inventory")
    names, retained = set(), []
    for item in rows:
        if not isinstance(item, dict):
            raise RuntimeError("Invalid backup inventory item")
        name = item.get("name")
        created = backup_time(name)
        if (name in names or created > stamp or type(item.get("size")) is not int or item["size"] < 1
                or not isinstance(item.get("sha256"), str) or not re.fullmatch(r"[a-f0-9]{64}", item["sha256"])):
            raise RuntimeError("Invalid backup inventory identity")
        names.add(name)
        if created >= stamp - RETENTION_SECONDS + RETENTION_BUFFER_SECONDS:
            retained.append(item)
    if not retained:
        raise RuntimeError("No retained server backup available")
    if stamp - max(backup_time(item["name"]) for item in retained) > 30 * 3600:
        raise RuntimeError("Server backup is stale")
    return retained


def pull(destination, *, _supervised=False, _check=lambda: None):
    if not _supervised and os.path.lexists(destination / HANDOFF_MARKER):
        raise InterruptedTransfer("An interrupted supervised transfer requires reconciliation")
    if any(os.path.lexists(destination / name) for name in
           (".erasure-ledger.pending", ".erasure-ledger.previous", ".offsite-status.previous")):
        raise InterruptedTransfer("An interrupted journal transfer requires reconciliation")
    def guarded_run(*args, **kwargs):
        _check()
        result = run(*args, **kwargs)
        _check()
        return result

    _check()
    ssh = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "dorfspy"]
    access = "/opt/schulpilot/current/venv/bin/python /opt/schulpilot/current/deploy/backup_access.py"
    inventory = json.loads(guarded_run([*ssh, access + " inventory"], capture_output=True, text=True).stdout)
    retained = retained_inventory(inventory)
    copied = 0
    for item in retained:
        _check()
        name = item["name"]
        target = destination / name
        if not target.exists():
            partial = target.with_suffix(".partial")
            try:
                with partial.open("wb") as output:
                    guarded_run([*ssh, access + " read " + name], stdout=output, stderr=subprocess.PIPE)
                    output.flush()
                    os.fsync(output.fileno())
                with partial.open("rb") as source:
                    digest = hashlib.file_digest(source, "sha256").hexdigest()
                if partial.stat().st_size != item["size"] or digest != item["sha256"]:
                    raise RuntimeError("Offsite ciphertext checksum mismatch")
                _check()
                partial.replace(target)
                sync_directory(destination)
                copied += 1
            finally:
                _check()
                partial.unlink(missing_ok=True)
        else:
            with target.open("rb") as source:
                if hashlib.file_digest(source, "sha256").hexdigest() != item["sha256"]:
                    raise RuntimeError("Existing offsite ciphertext checksum mismatch")
                # Also make earlier copies from older clients durable before
                # confirming them with a newer journal snapshot.
                os.fsync(source.fileno())
            sync_directory(destination)
    partial = destination / "erasure-ledger.partial"
    try:
        _check()
        with partial.open("wb") as output:
            guarded_run(
                [*ssh, "/opt/schulpilot/current/venv/bin/python /opt/schulpilot/current/deploy/export_ledger.py"],
                stdout=output,
                stderr=subprocess.PIPE,
            )
            output.flush()
            os.fsync(output.fileno())
        with partial.open("rb") as source:
            if source.read(4) != b"SPB1" or partial.stat().st_size < 32:
                raise RuntimeError("Invalid encrypted ledger")
        backups = list(destination.glob("*.tar.enc"))
        if any(backup_time(p.name) > inventory["server_now"] for p in backups):
            raise RuntimeError("Offsite backup timestamp is in the future")
        available = [p for p in backups if backup_time(p.name) >= inventory["server_now"] - RETENTION_SECONDS + RETENTION_BUFFER_SECONDS]
        if not available:
            raise RuntimeError("No retained offsite backup available")
        # Both identity values are restricted to shell-safe syntax above.
        latest_item = max(retained, key=lambda item: item["name"])

        def acknowledge():
            try:
                guarded_run(
                    [*ssh, "/opt/schulpilot/current/venv/bin/python /opt/schulpilot/current/deploy/export_ledger.py --ack "
                     + latest_item["name"] + " " + latest_item["sha256"]],
                    capture_output=True,
                )
            except subprocess.CalledProcessError as error:
                # No generic SSH failure or unrecognised server response proves
                # that the remote ACK was not written; leave those pending.
                if (error.returncode == 75
                        and error.stderr == b"offsite_ack_rejected_backup_changed_v1\n"
                        and error.stdout == b""):
                    raise AcknowledgementRejected("A newer backup appeared before acknowledgement") from None
                raise

        commit_ledger(destination, partial, acknowledge, {
                "checked_at": int(time.time()),
                "copied": copied,
                "backups": len(available),
                "ledger_source_time": inventory["server_now"],
                "encrypted_ledger": True,
        }, check=_check)
        # Match the 14-day retention only after a successful transfer.
        for path in set(backups) - set(available):
            _check()
            path.unlink()
        sync_directory(destination)
    finally:
        _check()
        partial.unlink(missing_ok=True)
    print("Offsite backup checksums verified; encrypted journal copied without content verification; copied=" + str(copied))


if __name__ == "__main__":
    try:
        main()
    except InterruptedTransfer:
        raise SystemExit("Offsite backup failed: an interrupted transfer needs operator reconciliation") from None
    except Exception as error:
        # Avoid subprocess messages containing private SSH configuration.
        raise SystemExit("Offsite backup failed: " + type(error).__name__) from None
