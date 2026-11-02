"""Mutual exclusion and coordination for release deployment, activation, rollback, and pruning.

Coordinating operations:
- Deployment (prepare staging, upload, publish, activate)
- Manual rollback (activate previous release)
- Release pruning (prune_releases.py)
- Operational watchdog and timers (monitor, backup, restore-check)

The persistent lease coordinates participating code paths. Lease metadata
mutations are serialized by a separate file lock. End-to-end coordination
across SSH disconnects, old installed versions and all deployment steps still
requires integration testing; see ROADMAP.md before production use.
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
