"""Isolated lock evidence, not a deploy guard and not a host-operation test."""

import fcntl
import os
import subprocess
import sys


def contenders(path, operation):
    script = '''
import fcntl, sys
with open(sys.argv[1], 'r+') as lock:
    try:
        fcntl.flock(lock, int(sys.argv[2]) | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(73)
'''
    return subprocess.run([sys.executable, '-c', script, str(path), str(operation)], check=False).returncode


def test_check_then_release_cannot_exclude_a_later_pull(tmp_path):
    lock = tmp_path / '.pull.lock'
    lock.touch(mode=0o600)
    with lock.open('r+') as guard:
        fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
    # A timer may start after a successful preflight has released its lock.
    assert contenders(lock, fcntl.LOCK_EX) == 0


def test_lock_held_through_deploy_excludes_same_inode_pull(tmp_path):
    lock = tmp_path / '.pull.lock'
    lock.touch(mode=0o600)
    with lock.open('r+') as guard:
        fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert contenders(lock, fcntl.LOCK_EX) == 73
    assert contenders(lock, fcntl.LOCK_EX) == 0


def test_replaced_lock_path_defeats_an_open_inode_lock(tmp_path):
    lock = tmp_path / '.pull.lock'
    lock.touch(mode=0o600)
    with lock.open('r+') as guard:
        fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        old = os.fstat(guard.fileno())
        replacement = tmp_path / 'replacement'
        replacement.touch(mode=0o600)
        os.replace(replacement, lock)
        assert os.stat(lock).st_ino != old.st_ino
        # A path-based pull now obtains a different lock concurrently.
        assert contenders(lock, fcntl.LOCK_EX) == 0


def test_exclusive_backup_operation_lock_blocks_required_shared_backup(tmp_path):
    lock = tmp_path / 'backup-operation.lock'
    lock.touch(mode=0o600)
    with lock.open('r+') as deploy:
        fcntl.flock(deploy, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # The production backup's guarded_operation obtains a shared lock.
        assert contenders(lock, fcntl.LOCK_SH) == 73
