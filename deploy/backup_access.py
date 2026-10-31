"""Read-only, guarded ciphertext access for the independent offsite host."""

import hashlib
import json
import os
import re
import stat
import sys
import time
from pathlib import Path

from backup_storage import guarded_operation
from ledger_snapshot import backup_lock

DIRECTORY = Path('/var/backups/schulpilot')
NAME = re.compile(r'\d{8}T\d{6}Z\.tar\.enc\Z')


def open_backup(name):
    if not NAME.fullmatch(name):
        raise ValueError('Invalid backup name')
    fd = os.open(DIRECTORY / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    stream = os.fdopen(fd, 'rb')
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        stream.close()
        raise ValueError('Invalid backup file')
    return stream


def inventory():
    items = []
    for path in sorted(DIRECTORY.glob('*.tar.enc')):
        with open_backup(path.name) as stream:
            before = os.fstat(stream.fileno())
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            after = os.fstat(stream.fileno())
            if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                raise RuntimeError('Backup changed')
            items.append({'name': path.name, 'size': after.st_size, 'sha256': digest})
    return {'backups': items, 'server_now': int(time.time())}


def main():
    if os.geteuid() != 0:
        raise SystemExit('Operator access required')
    with guarded_operation(), backup_lock(DIRECTORY, exclusive=False):
        if sys.argv[1:] == ['inventory']:
            print(json.dumps(inventory()))
        elif len(sys.argv) == 3 and sys.argv[1] == 'read':
            with open_backup(sys.argv[2]) as source:
                while chunk := source.read(1024 * 1024):
                    sys.stdout.buffer.write(chunk)
        else:
            raise SystemExit('Unsupported backup access action')


if __name__ == '__main__':
    main()
