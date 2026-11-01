"""Project-only encrypted daily backup; run as root by systemd timer."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from backup_storage import guarded_operation
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from ledger_snapshot import backup_lock, locked_journal, status_path


def capture_journal(ledger, snapshot):
    """Copy under the writer lock; preserve the DB backup if it is unavailable."""
    try:
        with locked_journal(ledger) as source, snapshot.open("wb") as output:
            shutil.copyfileobj(source, output, 1024 * 1024)
        return "present"
    except OSError:
        snapshot.unlink(missing_ok=True)
        # A missing journal and a missing/unreadable lock are distinct enough
        # for operators, but neither authorises a claim of an empty journal.
        return "missing" if not ledger.exists() else "unavailable"


def write_status(backup, journal):
    path = status_path(backup)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, prefix=".backup-status-", delete=False) as output:
        temporary = Path(output.name)
        output.write(json.dumps({"backup": backup.name, "journal": journal}) + "\n")
        output.flush()
        os.fsync(output.fileno())
    temporary.chmod(0o600)
    temporary.replace(path)


def publish_backup(partial, final, journal):
    with backup_lock(final.parent, exclusive=True):
        if final.exists():
            raise FileExistsError("Backup for this timestamp already exists")
        # Publish status before the archive, so no visible new archive lacks it.
        write_status(final, journal)
        partial.replace(final)


def create_backup(destination, data_dir, key_path, *, stamp=None):
    destination.mkdir(exist_ok=True, mode=0o700)
    stamp = stamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    final = destination / (stamp + ".tar.enc")
    with tempfile.TemporaryDirectory(prefix="schulpilot-backup-") as directory:
        directory = Path(directory)
        dump = directory / "database.dump"
        with dump.open("wb") as output:
            subprocess.run(
                ["runuser", "-u", "schulpilot", "--", "pg_dump", "--format=custom", "schulpilot"], stdout=output, check=True
            )
        archive = directory / "backup.tar"
        snapshot = directory / "erasure-ledger.jsonl"
        journal = capture_journal(data_dir / "erasure-ledger.jsonl", snapshot)
        with tarfile.open(archive, "w") as bundle:
            bundle.add(dump, arcname="database.dump")
            bundle.add(data_dir / "uploads", arcname="uploads")
            if journal == "present":
                bundle.add(snapshot, arcname="erasure-ledger.jsonl")
            status = directory / "erasure-journal-status.json"
            status.write_text(json.dumps({"journal": journal}) + "\n")
            bundle.add(status, arcname=status.name)
        with tempfile.NamedTemporaryFile(dir=destination, prefix=".backup-", suffix=".partial", delete=False) as output:
            partial = Path(output.name)
        try:
            key = hashlib.sha256(key_path.read_bytes()).digest()
            nonce = os.urandom(12)
            encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
            encryptor.authenticate_additional_data(b"SPB1")
            with archive.open("rb") as source, partial.open("wb") as output:
                output.write(b"SPB1" + nonce)
                while chunk := source.read(1024 * 1024):
                    output.write(encryptor.update(chunk))
                output.write(encryptor.finalize())
                output.write(encryptor.tag)
            partial.chmod(0o600)
            publish_backup(partial, final, journal)
        finally:
            partial.unlink(missing_ok=True)
    if journal != "present":
        print("SCHULPILOT backup: deletion journal " + journal + "; restore requires investigation.", file=sys.stderr)
    print("SCHULPILOT backup created: " + final.name + "; deletion journal: " + journal)
    return final


def main():
    with guarded_operation():
        create_backup(Path("/var/backups/schulpilot"), Path("/var/lib/schulpilot"), Path("/etc/schulpilot/backup.key"))


if __name__ == "__main__":
    main()
