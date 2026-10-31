"""Root-only encrypted deletion journal for the independent backup host.

stdout is binary ciphertext. No credentials or unencrypted IDs leave the host.
"""

import hashlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

from backup_storage import guarded_operation
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from ledger_snapshot import backup_lock, locked_journal, status_path


def require_backup_journal(directory, expected_name, expected_hash):
    """Bind acknowledgement to the newest archive verified by the receiver."""
    if (not re.fullmatch(r"\d{8}T\d{6}Z\.tar\.enc", expected_name)
            or not re.fullmatch(r"[a-f0-9]{64}", expected_hash)):
        raise RuntimeError("Invalid offsite backup identity")
    backups = sorted(directory.glob("*.tar.enc"))
    if not backups:
        raise RuntimeError("No backup available")
    latest = backups[-1]
    if latest.name != expected_name:
        raise RuntimeError("Backup changed during offsite transfer")
    try:
        value = json.loads(status_path(latest).read_text())
    except (OSError, UnicodeError, ValueError):
        raise RuntimeError("Latest backup journal status is unavailable") from None
    if not isinstance(value, dict) or value.get("backup") != latest.name or value.get("journal") != "present":
        raise RuntimeError("Latest backup does not contain a confirmed journal snapshot")
    with latest.open("rb") as source:
        if hashlib.file_digest(source, "sha256").hexdigest() != expected_hash:
            raise RuntimeError("Backup changed during offsite transfer")


def export(ledger, key_path, output):
    # Open both the stable lock and journal before writing even the header.
    # A missing source must never become a valid encrypted empty snapshot.
    with locked_journal(ledger) as source:
        key = hashlib.sha256(key_path.read_bytes()).digest()
        nonce = os.urandom(12)
        encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
        encryptor.authenticate_additional_data(b"SPB1")
        output.write(b"SPB1" + nonce)
        while chunk := source.read(1024 * 1024):
            output.write(encryptor.update(chunk))
        output.write(encryptor.finalize())
        output.write(encryptor.tag)


def acknowledge(expected_name, expected_hash):
    backup_directory = Path("/var/backups/schulpilot")
    # Recheck that an extant current journal can be read under the same lock;
    # a prior export is not evidence that it still exists at acknowledgement.
    with backup_lock(backup_directory, exclusive=False), locked_journal(Path("/var/lib/schulpilot/erasure-ledger.jsonl")):
        require_backup_journal(backup_directory, expected_name, expected_hash)
        directory = Path("/var/backups/schulpilot-monitor")
        directory.mkdir(exist_ok=True, mode=0o700)
        with tempfile.NamedTemporaryFile(mode="w", dir=directory, delete=False) as output:
            output.write(json.dumps({"checked_at": int(time.time())}) + "\n")
            temporary = Path(output.name)
        temporary.replace(directory / "offsite-last-success.json")
        enabled = Path("/etc/schulpilot/offsite-enabled")
        enabled.touch(mode=0o600, exist_ok=True)
    print("Offsite transfer acknowledged after local checksum verification.")


def main():
    if os.geteuid() != 0:
        raise SystemExit("Operator access required")
    with guarded_operation():
        if len(sys.argv[1:]) == 3 and sys.argv[1] == "--ack":
            acknowledge(sys.argv[2], sys.argv[3])
        elif not sys.argv[1:]:
            export(Path("/var/lib/schulpilot/erasure-ledger.jsonl"), Path("/etc/schulpilot/backup.key"), sys.stdout.buffer)
        else:
            raise SystemExit("Unsupported export action")


if __name__ == "__main__":
    main()
