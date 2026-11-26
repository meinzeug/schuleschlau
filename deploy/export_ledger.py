"""Root-only encrypted deletion journal for the independent backup host.

stdout is binary ciphertext. No credentials or unencrypted IDs leave the host.
"""

import hashlib
import hmac
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


class NewerBackupAvailable(RuntimeError):
    """The proposed backup became stale before any acknowledgement was written."""


class JournalChanged(RuntimeError):
    """The journal no longer matches the exported ciphertext receipt."""


def ledger_receipt(key, source_digest, ciphertext_digest):
    """Bind both snapshots without sending the journal digest or key offsite."""
    receipt_key = hmac.digest(key, b"schulpilot-offsite-ledger-receipt-key-v1", "sha256")
    return hmac.digest(receipt_key, b"v1\0" + source_digest + ciphertext_digest, "sha256").hex()


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
        raise NewerBackupAvailable("Backup changed during offsite transfer")
    try:
        value = json.loads(status_path(latest).read_text())
    except (OSError, UnicodeError, ValueError):
        raise RuntimeError("Latest backup journal status is unavailable") from None
    if not isinstance(value, dict) or value.get("backup") != latest.name or value.get("journal") != "present":
        raise RuntimeError("Latest backup does not contain a confirmed journal snapshot")
    with latest.open("rb") as source:
        if hashlib.file_digest(source, "sha256").hexdigest() != expected_hash:
            raise RuntimeError("Backup changed during offsite transfer")


def outbox_pending():
    # Independent read of the application outbox while the journal lock is
    # held by the caller. Never print database errors or record contents.
    from monitor import environment
    from restore_check import live_outbox_pending

    try:
        return live_outbox_pending(environment("/etc/schulpilot/environment"), timeout=10)
    except Exception:
        raise RuntimeError("Unable to check the deletion outbox") from None


def require_published_outbox(check):
    state = check()
    if state is not False:
        # Unknown/non-boolean results are not evidence of an empty outbox.
        raise RuntimeError("Deletion outbox is not verified as published")


def export(ledger, key_path, output, *, check_pending=None):
    # Open both the stable lock and journal before writing even the header.
    # A missing source must never become a valid encrypted empty snapshot.
    with locked_journal(ledger) as source:
        require_published_outbox(outbox_pending if check_pending is None else check_pending)
        key = hashlib.sha256(key_path.read_bytes()).digest()
        nonce = os.urandom(12)
        encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
        encryptor.authenticate_additional_data(b"SPB1")
        plaintext_hash = hashlib.sha256()
        encrypted_hash = hashlib.sha256()

        def write(data):
            if output.write(data) != len(data):
                raise RuntimeError("Incomplete encrypted journal write")
            encrypted_hash.update(data)

        write(b"SPB1" + nonce)
        while chunk := source.read(1024 * 1024):
            plaintext_hash.update(chunk)
            write(encryptor.update(chunk))
        write(encryptor.finalize())
        write(encryptor.tag)
        output.flush()
        return ledger_receipt(key, plaintext_hash.digest(), encrypted_hash.digest())


def acknowledge(expected_name, expected_hash, ciphertext_hash, receipt, *, check_pending=None):
    if not re.fullmatch(r"[a-f0-9]{64}", ciphertext_hash) or not re.fullmatch(r"[a-f0-9]{64}", receipt):
        raise RuntimeError("Invalid offsite journal receipt")
    backup_directory = Path("/var/backups/schulpilot")
    # Recheck that an extant current journal can be read under the same lock;
    # a prior export is not evidence that it still exists at acknowledgement.
    with backup_lock(backup_directory, exclusive=False), locked_journal(Path("/var/lib/schulpilot/erasure-ledger.jsonl")) as source:
        require_backup_journal(backup_directory, expected_name, expected_hash)
        require_published_outbox(outbox_pending if check_pending is None else check_pending)
        key = hashlib.sha256(Path("/etc/schulpilot/backup.key").read_bytes()).digest()
        source_hash = hashlib.file_digest(source, "sha256").digest()
        expected_receipt = ledger_receipt(key, source_hash, bytes.fromhex(ciphertext_hash))
        if not hmac.compare_digest(receipt, expected_receipt):
            raise JournalChanged("The exported journal no longer matches")
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
        if len(sys.argv[1:]) == 5 and sys.argv[1] == "--ack":
            try:
                acknowledge(*sys.argv[2:])
            except NewerBackupAvailable:
                # This exception can only arise during the locked identity check,
                # before acknowledgement or offsite-enabled is written. Keep a
                # protocol distinct from generic failures and SSH disconnects.
                print("offsite_ack_rejected_backup_changed_v1", file=sys.stderr)
                raise SystemExit(75) from None
            except JournalChanged:
                print("offsite_ack_rejected_ledger_changed_v1", file=sys.stderr)
                raise SystemExit(76) from None
        elif not sys.argv[1:]:
            receipt = export(Path("/var/lib/schulpilot/erasure-ledger.jsonl"), Path("/etc/schulpilot/backup.key"), sys.stdout.buffer)
            print("offsite_ledger_receipt_v1:" + receipt, file=sys.stderr)
        else:
            raise SystemExit("Unsupported export action")


if __name__ == "__main__":
    main()
