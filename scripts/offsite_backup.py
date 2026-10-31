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
from pathlib import Path


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
        pull(args.destination)


def pull(destination):
    if (destination / ".erasure-ledger.pending").exists() or (destination / ".erasure-ledger.previous").exists():
        raise InterruptedTransfer("An interrupted journal transfer requires reconciliation")
    ssh = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "dorfspy"]
    inventory_code = """import hashlib,json,time
from pathlib import Path
items=[]
for p in Path('/var/backups/schulpilot').glob('*.tar.enc'):
 if p.is_file() and not p.is_symlink():
  h=hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
  items.append({'name':p.name,'size':p.stat().st_size,'sha256':h})
print(json.dumps({'backups':items,'server_now':int(time.time())}))
"""
    inventory = json.loads(run([*ssh, "python3 -"], input=inventory_code, capture_output=True, text=True).stdout)
    copied = 0
    for item in inventory["backups"]:
        name = item["name"]
        if not re.fullmatch(r"\d{8}T\d{6}Z\.tar\.enc", name):
            raise RuntimeError("Unexpected backup filename")
        if not re.fullmatch(r"[a-f0-9]{64}", item["sha256"]):
            raise RuntimeError("Unexpected backup digest")
        target = destination / name
        if not target.exists():
            partial = target.with_suffix(".partial")
            try:
                with partial.open("wb") as output:
                    run([*ssh, "cat /var/backups/schulpilot/" + name], stdout=output, stderr=subprocess.PIPE)
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
    if not inventory["backups"]:
        raise RuntimeError("No server backup available")
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
        from datetime import datetime, timezone

        backups = list(destination.glob("*.tar.enc"))

        def backup_time(path):
            return datetime.strptime(path.name[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).timestamp()

        available = [p for p in backups if backup_time(p) >= inventory["server_now"] - 14 * 86400]
        if not available:
            raise RuntimeError("No retained offsite backup available")
        if inventory["server_now"] - max(map(backup_time, available)) > 30 * 3600:
            raise RuntimeError("Server backup is stale")
        # Both identity values are restricted to shell-safe syntax above.
        latest_item = max(inventory["backups"], key=lambda item: item["name"])

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
