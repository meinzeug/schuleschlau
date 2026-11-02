"""Opt-in loopback SSH interruption test; all releases and keys are synthetic."""
import json
import os
import pwd
import shlex
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RELEASE = "20261102T010000Z-1111111"
OTHER = "20261102T020000Z-2222222"


def wait_for(path, timeout=10):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if path.exists():
            return
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for {path.name}")


@pytest.mark.skipif(os.getenv("SCHULPILOT_TEST_REAL_SSH") != "1", reason="explicit loopback SSH test")
def test_disconnected_ssh_preserves_lease_for_delayed_child(tmp_path, monkeypatch):
    sshd, ssh, keygen = (shutil.which(name) for name in ("sshd", "ssh", "ssh-keygen"))
    assert sshd and ssh and keygen
    tmp_path.chmod(0o700)
    host, client = tmp_path / "host", tmp_path / "client"
    for key in (host, client):
        subprocess.run([keygen, "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
    authorized = tmp_path / "authorized_keys"
    authorized.write_bytes(client.with_suffix(".pub").read_bytes())
    authorized.chmod(0o600)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    config = tmp_path / "sshd_config"
    config.write_text(f"HostKey {host}\nPidFile {tmp_path}/sshd.pid\nListenAddress 127.0.0.1\n"
        f"Port {port}\nAuthorizedKeysFile {authorized}\nStrictModes no\nUsePAM no\n"
        "PasswordAuthentication no\nKbdInteractiveAuthentication no\n")
    base = tmp_path / "app"
    base.mkdir(mode=0o700)
    releases = base / "releases"
    releases.mkdir()
    current = releases / "20261030T200000Z-abcdef1"
    current.mkdir()
    (base / "current").symlink_to(current)
    stage_path = ROOT / "deploy" / "stage_release.py"
    child_script = tmp_path / "child.py"
    child_script.write_text("""import pathlib, sys, time
base = pathlib.Path(sys.argv[1])
(base / 'child-ready').touch()
while not (base / 'continue').exists():
    time.sleep(.05)
(base / 'staging' / sys.argv[2] / 'later.txt').write_text('completed')
""")
    remote_script = tmp_path / "remote.py"
    remote_script.write_text("""import importlib.util, os, pathlib, subprocess, sys, time
spec=importlib.util.spec_from_file_location('stage',sys.argv[1]); stage=importlib.util.module_from_spec(spec); spec.loader.exec_module(stage)
base=pathlib.Path(sys.argv[2]); release=sys.argv[3]; stage.prepare(base,release)
subprocess.Popen([sys.executable,sys.argv[4],str(base),release],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
while not (base/'child-ready').exists(): time.sleep(.05)
(base/'parent-pid').write_text(str(os.getpid()))
(base/'ssh-ready').touch()
time.sleep(30)
""")
    server = subprocess.Popen([sshd, "-D", "-e", "-f", str(config)], stdout=subprocess.DEVNULL,
                              stderr=subprocess.PIPE, text=True)
    connection = None
    try:
        wait_for(tmp_path / "sshd.pid")
        remote = " ".join(map(shlex.quote, [sys.executable, str(remote_script), str(stage_path), str(base), RELEASE, str(child_script)]))
        connection = subprocess.Popen([ssh, "-F", "/dev/null", "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
            "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-i", str(client),
            "-p", str(port), f"{pwd.getpwuid(os.getuid()).pw_name}@127.0.0.1", remote],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            wait_for(base / "ssh-ready")
        except AssertionError:
            if connection.poll() is not None:
                _, diagnostic = connection.communicate(timeout=5)
                raise AssertionError(f"Synthetic SSH command failed: {diagnostic.strip()}") from None
            raise
        connection.terminate()
        connection.communicate(timeout=5)
        sys.path.insert(0, str(ROOT))
        try:
            from deploy import prune_releases as prune
            from deploy import stage_release as stage
            assert stage.check_lock(base) is not None
            lock_path = base / ".deploy.lock"
            lease = json.loads(lock_path.read_text())
            lease.update(holder_pid=99999999, tracked_pids=[], updated_at=time.time() - 3600)
            lock_path.write_text(json.dumps(lease))
            with pytest.raises(stage.ReleaseLockError):
                stage.prepare(base, OTHER)
            monkeypatch.setattr(prune, "BASE", base)
            monkeypatch.setattr(prune, "RELEASES", releases)
            monkeypatch.setattr(prune.sys, "argv", ["prune", "--apply"])
            assert prune.main() == 2
            (base / "continue").touch()
            wait_for(base / "staging" / RELEASE / "later.txt")
            assert (base / "staging" / RELEASE / "later.txt").read_text() == "completed"
            with pytest.raises(stage.ReleaseLockError):
                stage.prepare(base, OTHER)
        finally:
            sys.path.pop(0)
    finally:
        if connection and connection.poll() is None:
            connection.kill()
            connection.communicate(timeout=5)
        (base / "continue").touch()
        if (base / "parent-pid").exists():
            pid = int((base / "parent-pid").read_text())
            try:
                if str(remote_script).encode() in Path(f"/proc/{pid}/cmdline").read_bytes():
                    os.kill(pid, 15)
            except (FileNotFoundError, ProcessLookupError):
                pass
        server.terminate()
        server.communicate(timeout=5)
