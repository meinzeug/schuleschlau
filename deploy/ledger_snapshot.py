"""Read erasure journal snapshots under the writer's stable rotation lock."""

import fcntl
from contextlib import contextmanager


@contextmanager
def locked_journal(path):
    # The lock file, unlike the journal, is never atomically replaced by
    # pruning. Open it read-only: backup services have a read-only data mount.
    # Do not create it on an existing installation or imply missing means empty.
    with path.with_name(".erasure-ledger.lock").open("rb") as lock:
        fcntl.flock(lock, fcntl.LOCK_SH)
        with path.open("rb") as journal:
            yield journal


def status_path(backup):
    return backup.with_name(backup.name + ".journal.json")


@contextmanager
def backup_lock(directory, *, exclusive):
    """Serialize archive publication/retention and offsite acknowledgement."""
    # Readers must not create the lock: restore runs with a read-only backup
    # directory, and a missing lock must not silently split synchronization.
    with (directory / ".backup.lock").open("a+b" if exclusive else "rb") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        yield
