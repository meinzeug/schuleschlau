#!/usr/bin/env python3
"""Read-only, installation-specific restore-runtime cutover preflight.

This is deliberately NOT a cutover, lock manager, supervisor, or release tool.
Run on the server only.  A passing result never authorizes activation.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

TARGET = "45b66d20dc3b4c9b504eb8bb38f2b54dfc2fb86f"
OLD = "06b7301e0c6528578563a48d2019f9cd0e015cee"
BACKUP = "schulpilot-backup.service"
RESTORE = "schulpilot-restore-check.service"
FIELDS = ("LoadState", "ActiveState", "SubState", "Job", "Type", "NeedDaemonReload", "ExecStart")


def parse_show(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if any("=" not in item for item in lines):
        raise ValueError("Unvollständige Unit-Abfrage")
    pairs = [item.split("=", 1) for item in lines]
    data = dict(pairs)
    if len(data) != len(pairs) or set(data) != set(FIELDS):
        raise ValueError("Unerwartete Unit-Felder")
    return data


def validate_unit(name: str, data: dict[str, str]) -> None:
    if name not in (BACKUP, RESTORE) or set(data) != set(FIELDS):
        raise ValueError("Unbekannte Unit")
    if (
        data["LoadState"] != "loaded"
        or data["ActiveState"] != "inactive"
        or data["SubState"] != "dead"
        or data["Job"]
        or data["Type"] != "oneshot"
        or data["NeedDaemonReload"] != "no"
    ):
        raise ValueError("Unit nicht eindeutig geladen und inaktiv")
    if name == BACKUP:
        exe = "/opt/schulpilot/current/venv/bin/python"
        script = "/opt/schulpilot/current/deploy/backup.py"
    else:
        exe = f"/opt/schulpilot/restore-runtimes/{OLD}/venv/bin/python"
        script = f"/opt/schulpilot/restore-runtimes/{OLD}/deploy/restore_check.py"
    # systemd serializes this property with command metadata. Check both path
    # and full argv start, and reject multiple ExecStart entries.
    start = data["ExecStart"]
    expression = r"^\{ path=" + re.escape(exe) + r" ; argv\[\]=" + re.escape(exe + " " + script) + r" ; ignore_errors=no ; [^{}]* \}$"
    if not re.fullmatch(expression, start):
        raise ValueError("Unit-Kommando entspricht nicht dem geprüften Ausgangsstand")


def inspect(show, runtime: Path) -> dict[str, object]:
    if runtime != Path("/opt/schulpilot/restore-runtimes") / TARGET:
        raise ValueError("Nicht freigegebener Zielpfad")
    for relative in ("venv/bin/python", "deploy/restore_check.py"):
        if not (runtime / relative).is_file():
            raise ValueError("Vorbereitete Ziel-Runtime ist unvollständig")
    for unit in (BACKUP, RESTORE):
        validate_unit(unit, parse_show(show(unit)))
    return {
        "status": "read_only_preflight_ok",
        "target_revision": TARGET,
        "units": [BACKUP, RESTORE],
        "activation_authorized": False,
        "limitations": [
            "no_lock_or_timer_fencing",
            "no_cgroup_or_descendant_check",
            "no_job_or_provider_test",
            "no_target_integrity_or_restore_test",
            "no_target_symlink_or_source_identity_check",
            "no_offsite_or_recovery_test",
        ],
    }


def systemd_show(unit: str) -> str:
    if unit not in (BACKUP, RESTORE):
        raise ValueError("Unbekannte Unit")
    args = ["systemctl", "show", unit]
    for name in FIELDS:
        args += ["-p", name]
    return subprocess.run(args, capture_output=True, text=True, check=True, timeout=10).stdout


def main() -> int:
    try:
        result = inspect(systemd_show, Path("/opt/schulpilot/restore-runtimes") / TARGET)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(json.dumps({"status": "preflight_refused", "reason": str(error), "activation_authorized": False}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
