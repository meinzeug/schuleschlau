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


def run(args, **kwargs):
    return subprocess.run(args, check=True, timeout=120, **kwargs)


def commit_ledger(destination, partial, acknowledge, success):
    """Keep the previous snapshot when an ordinary acknowledgement fails.

    An interrupted cross-host transaction requires operator reconciliation;
    `.pending` and `.previous` deliberately survive a process crash.
    """
    ledger = destination / "erasure-ledger.enc"
    previous = destination / ".erasure-ledger.previous"
    pending = destination / ".erasure-ledger.pending"
    if pending.exists() or previous.exists():
        raise InterruptedTransfer("An interrupted journal transfer requires reconciliation")
    had_previous = ledger.exists()
    with pending.open("x") as output:
        output.write(json.dumps({"had_previous": had_previous}) + "\n")
        output.flush()
        os.fsync(output.fileno())
    installed = False
    ack_started = False
    try:
        if had_previous:
            os.link(ledger, previous)
        partial.replace(ledger)
        installed = True
        ack_started = True
        acknowledge()
        with tempfile.NamedTemporaryFile(mode="w", dir=destination, prefix=".offsite-status-", delete=False) as output:
            status = Path(output.name)
            try:
                output.write(json.dumps(success) + "\n")
                output.flush()
                os.fsync(output.fileno())
            except Exception:
                status.unlink(missing_ok=True)
                raise
        try:
            status.replace(destination / "last-success.json")
        except Exception:
            status.unlink(missing_ok=True)
            raise
    except Exception:
        # Preserve the old success marker and restore exactly the prior bytes.
        # If rollback fails, leave the transaction files for operator recovery.
        if installed:
            if had_previous:
                previous.replace(ledger)
            else:
                ledger.unlink(missing_ok=True)
        else:
            previous.unlink(missing_ok=True)
        # A remote failure or timeout may follow a successful server ACK; the
        # prior snapshot is restored but its relationship to the remote marker
        # is unknown. Retain the marker and require human reconciliation.
        if not ack_started:
            pending.unlink(missing_ok=True)
        raise
    previous.unlink(missing_ok=True)
    pending.unlink()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, default=Path.home() / ".local/share/schulpilot-offsite")
    args = parser.parse_args()
    os.umask(0o077)
    args.destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.destination.chmod(0o700)
    with (args.destination / ".pull.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        pace_recent_success(args.destination)
        pull(args.destination)


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


def pull(destination):
    if (destination / ".erasure-ledger.pending").exists() or (destination / ".erasure-ledger.previous").exists():
        raise InterruptedTransfer("An interrupted journal transfer requires reconciliation")
    ssh = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "dorfspy"]
    access = "/opt/schulpilot/current/venv/bin/python /opt/schulpilot/current/deploy/backup_access.py"
    inventory = json.loads(run([*ssh, access + " inventory"], capture_output=True, text=True).stdout)
    retained = retained_inventory(inventory)
    copied = 0
    for item in retained:
        name = item["name"]
        target = destination / name
        if not target.exists():
            partial = target.with_suffix(".partial")
            try:
                with partial.open("wb") as output:
                    run([*ssh, access + " read " + name], stdout=output, stderr=subprocess.PIPE)
                with partial.open("rb") as source:
                    digest = hashlib.file_digest(source, "sha256").hexdigest()
                if partial.stat().st_size != item["size"] or digest != item["sha256"]:
                    raise RuntimeError("Offsite ciphertext checksum mismatch")
                partial.replace(target)
                copied += 1
            finally:
                partial.unlink(missing_ok=True)
        else:
            with target.open("rb") as source:
                if hashlib.file_digest(source, "sha256").hexdigest() != item["sha256"]:
                    raise RuntimeError("Existing offsite ciphertext checksum mismatch")
    partial = destination / "erasure-ledger.partial"
    try:
        with partial.open("wb") as output:
            run(
                [*ssh, "/opt/schulpilot/current/venv/bin/python /opt/schulpilot/current/deploy/export_ledger.py"],
                stdout=output,
                stderr=subprocess.PIPE,
            )
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
            run(
                [*ssh, "/opt/schulpilot/current/venv/bin/python /opt/schulpilot/current/deploy/export_ledger.py --ack "
                 + latest_item["name"] + " " + latest_item["sha256"]],
                capture_output=True,
            )

        commit_ledger(destination, partial, acknowledge, {
                "checked_at": int(time.time()),
                "copied": copied,
                "backups": len(available),
                "ledger_source_time": inventory["server_now"],
                "encrypted_ledger": True,
        })
        # Match the 14-day retention only after a successful transfer.
        for path in set(backups) - set(available):
            path.unlink()
    finally:
        partial.unlink(missing_ok=True)
    print("Offsite backup checksums verified; encrypted journal copied without content verification; copied=" + str(copied))


if __name__ == "__main__":
    try:
        main()
    except InterruptedTransfer:
        raise SystemExit("Offsite backup failed: an interrupted journal transfer needs operator reconciliation") from None
    except Exception as error:
        # Avoid subprocess messages containing private SSH configuration.
        raise SystemExit("Offsite backup failed: " + type(error).__name__) from None
