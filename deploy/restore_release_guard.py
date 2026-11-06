"""Fail closed on an incompatible systemd restore override before migration.

This is an additional configuration check, not a two-host coordinator or a
claim that an archive, deletion journal, runtime environment or restore works.
"""

import hashlib
import re
import subprocess
from pathlib import Path


class RestoreConfigurationError(RuntimeError):
    pass


def _source_files(root):
    paths = {}
    for directory, pattern in (("backend/schulpilot", "*.py"), ("backend/migrations", "*"), ("deploy", "*.py")):
        base = root / directory
        if not base.is_dir():
            raise RestoreConfigurationError("Restore runtime source tree is incomplete")
        for item in base.rglob(pattern):
            if item.is_symlink():
                raise RestoreConfigurationError("Symlink in restore runtime source")
            if item.is_file() and "__pycache__" not in item.parts and not item.name.endswith(".pyc"):
                paths[item.relative_to(root).as_posix()] = item
    for name in ("backend/alembic.ini", "backend/requirements.lock"):
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise RestoreConfigurationError("Restore runtime dependency metadata is unavailable")
        paths[name] = path
    if not any(p.startswith("backend/migrations/versions/") for p in paths):
        raise RestoreConfigurationError("Restore runtime migrations are unavailable")
    return paths


def _digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.digest()


def inspect(show, target, *, current=Path("/opt/schulpilot/current"),
            runtime_base=Path("/opt/schulpilot/restore-runtimes")):
    fields = {}
    for line in show.splitlines():
        key, sep, value = line.partition("=")
        if not sep or key in fields:
            raise RestoreConfigurationError("Invalid restore service metadata")
        fields[key] = value
    if set(fields) != {"LoadState", "NeedDaemonReload", "User", "ExecStart"}:
        raise RestoreConfigurationError("Incomplete restore service metadata")
    if fields["LoadState"] != "loaded" or fields["NeedDaemonReload"] != "no" or fields["User"] != "root":
        raise RestoreConfigurationError("Restore service is not safely configured")
    match = re.fullmatch(r"\{ path=(/[^ ;{}]+) ; argv\[\]=([^;{}]+) ; ignore_errors=no ; [^{}]* \}", fields["ExecStart"])
    if not match:
        raise RestoreConfigurationError("Unsupported restore service command")
    interpreter, argv = match.groups()
    if not interpreter.endswith("/venv/bin/python"):
        raise RestoreConfigurationError("Restore interpreter is not bound to a runtime")
    runtime = Path(interpreter.removesuffix("/venv/bin/python"))
    if argv != f"{interpreter} {runtime}/deploy/restore_check.py":
        raise RestoreConfigurationError("Restore interpreter and program differ")
    if runtime == current:
        # The release's unit must continue to use the same runtime-relative
        # entry point when the current symlink is atomically replaced.
        unit = (target / "deploy/schulpilot-restore-check.service").read_text()
        expected = f"ExecStart={current}/venv/bin/python {current}/deploy/restore_check.py"
        if sum(line == expected for line in unit.splitlines()) != 1:
            raise RestoreConfigurationError("Target restore unit is incompatible")
        return
    if runtime.parent != runtime_base or not re.fullmatch(r"[0-9a-f]{40}", runtime.name) or runtime.is_symlink():
        raise RestoreConfigurationError("Unrecognized restore runtime override")
    if not (runtime / "venv/bin/python").is_file():
        raise RestoreConfigurationError("Restore runtime interpreter is unavailable")
    target_files, runtime_files = _source_files(target), _source_files(runtime)
    if target_files.keys() != runtime_files.keys():
        raise RestoreConfigurationError("Restore override does not match target source")
    if any(_digest(source) != _digest(runtime_files[name]) for name, source in target_files.items()):
        raise RestoreConfigurationError("Restore override does not match target source")


def verify(target):
    args = ["systemctl", "show", "schulpilot-restore-check.service", "--no-pager"]
    for field in ("LoadState", "NeedDaemonReload", "User", "ExecStart"):
        args.extend(("-p", field))
    result = subprocess.run(args, check=True, capture_output=True, text=True, timeout=10)
    inspect(result.stdout, target)
