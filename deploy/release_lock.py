"""Mutual exclusion and coordination for release deployment, activation, rollback, and pruning.

Coordinating operations:
- Deployment (prepare staging, upload, publish, activate)
- Manual rollback (activate previous release)
- Release pruning (prune_releases.py)
- Operational watchdog and timers (monitor, backup, restore-check)

Guarantees:
- Only one mutating release operation can proceed at a time.
- Lock is held across multi-step SSH commands via persistent lock file + server PID/path tracking.
- If SSH drops, lock remains held as long as server-side child processes (e.g. rsync) are running or accessing staging.
- In-flight releases (staged, published, or newer than current) are protected from pruning.
"""

from __future__ import annotations

try:
    from stage_release import (
        ReleaseLockError,
        acquire_lock,
        check_lock,
        is_lock_active,
        is_pid_alive,
        is_process_accessing_path,
        release_lock,
        release_operation,
        update_lock,
    )
except ImportError:
    from deploy.stage_release import (
        ReleaseLockError,
        acquire_lock,
        check_lock,
        is_lock_active,
        is_pid_alive,
        is_process_accessing_path,
        release_lock,
        release_operation,
        update_lock,
    )

__all__ = [
    "ReleaseLockError",
    "acquire_lock",
    "check_lock",
    "is_lock_active",
    "is_pid_alive",
    "is_process_accessing_path",
    "release_lock",
    "release_operation",
    "update_lock",
]
