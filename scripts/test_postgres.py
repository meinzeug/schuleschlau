"""Run backend checks on an isolated PostgreSQL 16 cluster, never production."""

import os
import pwd
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote


def child_environment(root: Path, socket: Path, *, database: str) -> dict[str, str]:
    """Construct a fresh environment; never inherit libpq or loader options."""
    username = pwd.getpwuid(os.geteuid()).pw_name
    result = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(root),
        "TMPDIR": str(root),
        "XDG_CONFIG_HOME": str(root / "config"),
        "USER": username,
        "LOGNAME": username,
        "LANG": "C.UTF-8",
        "PGHOST": str(socket),
        "PGPORT": "55440",
        "PGUSER": username,
        "PGDATABASE": database,
        "PGPASSFILE": str(root / "no-password-file"),
    }
    # Explicitly supported local test harness settings, never arbitrary
    # Python, libpq, dynamic-loader, service, or application credentials.
    runtime = f"/run/user/{os.geteuid()}"
    if os.environ.get("XDG_RUNTIME_DIR") == runtime:
        result["XDG_RUNTIME_DIR"] = runtime
        address = f"unix:path={runtime}/bus"
        if os.environ.get("DBUS_SESSION_BUS_ADDRESS") == address:
            result["DBUS_SESSION_BUS_ADDRESS"] = address
    for name in ("SCHULPILOT_LAB_SUDO_STDIN", "SCHULPILOT_TEST_REAL_SSH",
                 "CAPACITY_LARGE", "CAPACITY_FAMILIES", "CAPACITY_PNG"):
        if name in os.environ:
            result[name] = os.environ[name]
    return result


def main():
    bins = Path("/usr/lib/postgresql/16/bin")
    if not (bins / "initdb").is_file():
        raise SystemExit("PostgreSQL 16 binaries are required locally.")
    root = Path(tempfile.mkdtemp(prefix="schulpilot-isolated-pg-"))
    root.chmod(0o700)
    data, sock = root / "database", root / "socket"
    sock.mkdir(mode=0o700)
    control_env = child_environment(root, sock, database="postgres")
    test_env = child_environment(root, sock, database="schulpilot_isolated_test")
    username = pwd.getpwuid(os.geteuid()).pw_name
    test_env["PYTHONPATH"] = "backend"
    test_env["TEST_DATABASE_URL"] = (
        f"postgresql+psycopg://{quote(username, safe='')}@/schulpilot_isolated_test"
        f"?host={quote(str(sock), safe='')}&port=55440"
    )
    started = False
    try:
        subprocess.run(
            [
                str(bins / "initdb"),
                "-D",
                str(data),
                "--auth-local=trust",
                "--auth-host=reject",
                "--no-locale",
                "--encoding=UTF8",
            ],
            check=True,
            capture_output=True,
            env=control_env,
        )
        subprocess.run(
            [
                str(bins / "pg_ctl"),
                "-D",
                str(data),
                "-l",
                str(root / "postgres.log"),
                "-o",
                f"-F -k {shlex.quote(str(sock))} -c listen_addresses='' -c unix_socket_permissions=0700 -p 55440",
                "-w",
                "start",
            ],
            check=True,
            capture_output=True,
            env=control_env,
        )
        started = True
        subprocess.run([str(bins / "createdb"), "-h", str(sock), "-p", "55440", "schulpilot_isolated_test"],
                       check=True, env=control_env)
        identity = subprocess.run(
            [str(bins / "psql"), "-X", "-A", "-t", "-F", "|", "-c",
             "SELECT current_database(), COALESCE(inet_server_addr()::text, 'unix'), current_setting('data_directory')"],
            check=True, capture_output=True, text=True, env=test_env,
        ).stdout.strip()
        if identity != f"schulpilot_isolated_test|unix|{data}":
            raise RuntimeError("Disposable PostgreSQL identity verification failed")
        return subprocess.run(
            [sys.executable, "-m", "pytest", "-q", *(sys.argv[1:] or ["backend/tests"])], env=test_env
        ).returncode
    finally:
        if started:
            subprocess.run([str(bins / "pg_ctl"), "-D", str(data), "-m", "fast", "-w", "stop"],
                           capture_output=True, env=control_env)
        shutil.rmtree(root)


if __name__ == "__main__":
    sys.exit(main())
