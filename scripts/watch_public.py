"""Independent-host public HTTPS and offsite watchdog; no private API calls."""

import fcntl
import json
import os
import shutil
import stat
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy"))
from monitor import disk_space_low, environment, notify  # noqa: E402


def interrupted_offsite_transaction(base):
    """Report leftovers only after the pull's exclusive lock is released.

    The marker exists briefly during a normal transfer. Never block this
    independent watchdog on a running pull, and do not treat a dangling
    symlink as an absent marker.
    """
    markers = (base / '.erasure-ledger.pending', base / '.erasure-ledger.previous',
               base / '.offsite-status.previous', base / '.offsite-handoff.pending')
    if not any(os.path.lexists(path) for path in markers):
        return False
    try:
        fd = os.open(base / '.pull.lock', os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError:
        return True
    except OSError:
        return True
    try:
        try:
            info = os.fstat(fd)
        except OSError:
            return True
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1:
            return True
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        except OSError:
            return True
        return any(os.path.lexists(path) for path in markers)
    finally:
        os.close(fd)


def main():
    os.umask(0o077)
    base = Path.home() / ".local/share/schulpilot-offsite"
    config_file = Path.home() / ".local/share/schulpilot-operations/monitor.env"
    config = environment(config_file) if config_file.exists() else {}
    failures = []
    try:
        with urllib.request.urlopen("https://schulpilot.dorfspy.de/api/health", timeout=20) as response:
            if response.status != 200 or json.load(response).get("status") != "ok":
                failures.append("public_https_health")
    except Exception:
        failures.append("public_https_health")
    success = base / "last-success.json"
    try:
        stamp = json.loads(success.read_text())["checked_at"]
        fresh = type(stamp) is int and 0 < stamp <= time.time() and time.time() - stamp <= 3600
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        fresh = False
    if not fresh:
        failures.append("offsite_copy_stale")
    if interrupted_offsite_transaction(base):
        failures.append("offsite_transaction_incomplete")
    try:
        if disk_space_low(shutil.disk_usage(base)):
            failures.append("offsite_disk_space")
    except OSError:
        failures.append("offsite_disk_space_unavailable")
    path = base / "watch-state.json"
    try:
        previous = json.loads(path.read_text())
        if not isinstance(previous, dict) or not isinstance(previous.get("fingerprint", ""), str) or type(previous.get("sent", 0)) is not int:
            previous = {}
    except (OSError, UnicodeError, ValueError):
        previous = {}
    state = notify(config, failures, previous, path, dry_run="--dry-run" in sys.argv)
    print(
        json.dumps(
            {
                "failures": failures,
                "alert_configured": bool(config.get("OPERATIONS_ALERT_EMAIL")),
                "alert_error": state.get("alert_error"),
            }
        )
    )
    return bool(failures or state.get("alert_error"))


if __name__ == "__main__":
    raise SystemExit(main())
