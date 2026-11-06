"""Artificial OFD handoff tests; no network and no production files."""

import fcntl
import importlib.util
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "offsite_backup.py"
spec = importlib.util.spec_from_file_location("offsite_backup_handoff_test", SOURCE)
offsite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(offsite)

WORKER = r"""
import importlib.util,os,subprocess,sys,time
from pathlib import Path
spec=importlib.util.spec_from_file_location('offsite_supervised',sys.argv[1]);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
root=Path(sys.argv[2]); lock,pidfd,channel=map(int,sys.argv[3:6]); runid=sys.argv[6]
def pace(d):
    assert not os.get_inheritable(lock) and not os.get_inheritable(pidfd) and not os.get_inheritable(channel)
    code='import os,sys; fds=map(int,sys.argv[1:]);\nfor fd in fds:\n try: os.fstat(fd)\n except OSError: continue\n sys.exit(7)'
    assert subprocess.run([sys.executable,'-c',code,str(lock),str(pidfd),str(channel)],close_fds=False).returncode==0
    (root/'paced').touch()
def pull(d, *, _supervised=False, _check=None):
    assert _supervised
    (root/'pull-started').touch()
    deadline=time.monotonic()+5
    while not (root/'release').exists() and time.monotonic()<deadline:time.sleep(.05)
    if not (root/'release').exists():raise RuntimeError('synthetic timeout')
mod.pace_recent_success=pace;mod.pull=pull
sys.argv=['offsite_backup.py','--destination',str(root),'--supervised-lock-fd',str(lock),
          '--supervised-pid-fd',str(pidfd),'--supervised-channel-fd',str(channel),'--supervised-run-id',runid]
try:mod.main()
except Exception:
    (root/'worker-failed').touch()
    raise SystemExit(5)
"""


def launch(root):
    lock = os.open(root / ".pull.lock", os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    pidfd = os.pidfd_open(os.getpid())
    runid = "1" * 32
    p = subprocess.Popen(
        [sys.executable, "-c", WORKER, str(SOURCE), str(root), str(lock), str(pidfd), str(child.fileno()), runid],
        pass_fds=(lock, pidfd, child.fileno()),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    child.close()
    parent.settimeout(5)
    return p, lock, pidfd, parent, runid


def wait_for(path):
    until = time.monotonic() + 5
    while not path.exists() and time.monotonic() < until:
        time.sleep(0.03)
    assert path.exists()


def test_success_uses_same_ofd_runs_pace_and_leaves_recovery_marker(tmp_path, monkeypatch):
    tmp_path.chmod(0o700)
    p, lock, pidfd, control, runid = launch(tmp_path)
    try:
        assert control.recv(128) == ("READY " + runid).encode()
        wait_for(tmp_path / "pull-started")
        assert (tmp_path / "paced").exists()
        other = os.open(tmp_path / ".pull.lock", os.O_RDWR)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(other)
        (tmp_path / "release").touch()
        assert control.recv(128) == ("DONE " + runid).encode()
        assert p.wait(timeout=5) == 0
        assert (tmp_path / offsite.HANDOFF_MARKER).exists()
        monkeypatch.setattr(offsite, "run", lambda *a, **k: pytest.fail("no remote work on unresolved marker"))
        with pytest.raises(offsite.InterruptedTransfer):
            offsite.pull(tmp_path)
    finally:
        if p.poll() is None:
            p.kill()
            p.wait()
        control.close()
        os.close(lock)
        os.close(pidfd)


def test_replaced_inode_during_work_fails_closed_and_keeps_marker(tmp_path):
    tmp_path.chmod(0o700)
    p, lock, pidfd, control, runid = launch(tmp_path)
    try:
        assert control.recv(128) == ("READY " + runid).encode()
        wait_for(tmp_path / "pull-started")
        os.unlink(tmp_path / ".pull.lock")
        (tmp_path / ".pull.lock").touch(mode=0o600)
        (tmp_path / "release").touch()
        assert control.recv(128) == b""
        assert p.wait(timeout=5) != 0
        assert (tmp_path / offsite.HANDOFF_MARKER).exists()
    finally:
        if p.poll() is None:
            p.kill()
            p.wait()
        control.close()
        os.close(lock)
        os.close(pidfd)


def test_normal_pull_stops_on_unresolved_handoff_before_remote(tmp_path, monkeypatch):
    (tmp_path / offsite.HANDOFF_MARKER).write_text("{}")
    monkeypatch.setattr(offsite, "run", lambda *a, **k: pytest.fail("remote work must not start"))
    with pytest.raises(offsite.InterruptedTransfer):
        offsite.pull(tmp_path)


def test_supervisor_death_during_pull_keeps_recovery_marker(tmp_path):
    tmp_path.chmod(0o700)
    supervisor = r"""
import importlib.util,sys,time
from pathlib import Path
spec=importlib.util.spec_from_file_location('handoff_tests',sys.argv[1]);test=importlib.util.module_from_spec(spec);spec.loader.exec_module(test)
root=Path(sys.argv[2]);p,lock,pidfd,control,runid=test.launch(root)
if control.recv(128)!=('READY '+runid).encode():sys.exit(2)
test.wait_for(root/'pull-started');(root/'supervisor-ready').touch()
time.sleep(20)
"""
    sup = subprocess.Popen(
        [sys.executable, "-c", supervisor, str(Path(__file__).resolve()), str(tmp_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        wait_for(tmp_path / "supervisor-ready")
        sup.kill()
        sup.wait(timeout=5)
        (tmp_path / "release").touch()
        wait_for(tmp_path / "worker-failed")
        assert (tmp_path / offsite.HANDOFF_MARKER).exists()
        with pytest.raises(offsite.InterruptedTransfer):
            offsite.pull(tmp_path)
    finally:
        if sup.poll() is None:
            sup.kill()
            sup.wait()


@pytest.mark.parametrize("loss_at", ["inventory", "ledger", "ack"])
def test_supervisor_loss_stops_further_remote_calls_and_never_prunes(tmp_path, monkeypatch, loss_at):
    import hashlib
    import json
    from datetime import datetime, timezone
    from types import SimpleNamespace

    archive = b"artificial-ciphertext"
    name = "20261101T120000Z.tar.enc"
    expired = tmp_path / "20261001T120000Z.tar.enc"
    expired.write_bytes(archive)
    (tmp_path / "erasure-ledger.enc").write_bytes(b"old-journal")
    dead = False
    calls = []

    def check():
        if dead:
            raise RuntimeError("supervisor disappeared")

    def run(args, **kwargs):
        nonlocal dead
        command = args[-1]
        if command.endswith(" inventory"):
            kind = "inventory"
            result = SimpleNamespace(
                stdout=json.dumps(
                    {
                        "server_now": int(datetime(2026, 11, 1, 12, tzinfo=timezone.utc).timestamp()),
                        "backups": [
                            {"name": name, "size": len(archive), "sha256": hashlib.sha256(archive).hexdigest()}
                        ],
                    }
                )
            )
        elif " read " in command:
            kind = "read"
            kwargs["stdout"].write(archive)
            result = SimpleNamespace()
        elif command.endswith("export_ledger.py"):
            kind = "ledger"
            kwargs["stdout"].write(b"SPB1" + b"x" * 28)
            result = SimpleNamespace()
        elif " --ack " in command:
            kind = "ack"
            result = SimpleNamespace()
        else:
            raise AssertionError("unexpected synthetic call")
        calls.append(kind)
        if kind == loss_at:
            dead = True
        return result

    monkeypatch.setattr(offsite, "run", run)
    with pytest.raises(RuntimeError, match="supervisor disappeared"):
        offsite.pull(tmp_path, _supervised=True, _check=check)
    assert calls[-1] == loss_at
    assert expired.exists()
    if loss_at == "ack":
        assert (tmp_path / ".erasure-ledger.pending").exists()
        assert (tmp_path / ".erasure-ledger.previous").read_bytes() == b"old-journal"
        assert (tmp_path / "erasure-ledger.enc").read_bytes() == b"SPB1" + b"x" * 28
    else:
        assert (tmp_path / "erasure-ledger.enc").read_bytes() == b"old-journal"


def test_unlocked_supervised_fd_refused_without_marker(tmp_path):
    tmp_path.chmod(0o700)
    lock = os.open(tmp_path / ".pull.lock", os.O_RDWR | os.O_CREAT, 0o600)
    parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    pidfd = os.pidfd_open(os.getpid())
    p = subprocess.Popen(
        [
            sys.executable,
            "-c",
            WORKER,
            str(SOURCE),
            str(tmp_path),
            str(lock),
            str(pidfd),
            str(child.fileno()),
            "1" * 32,
        ],
        pass_fds=(lock, pidfd, child.fileno()),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    child.close()
    parent.settimeout(5)
    try:
        assert parent.recv(128) == b""
        assert p.wait(timeout=5) != 0
        assert not (tmp_path / offsite.HANDOFF_MARKER).exists()
        assert not (tmp_path / "pull-started").exists()
    finally:
        if p.poll() is None:
            p.kill()
            p.wait()
        parent.close()
        os.close(lock)
        os.close(pidfd)


def test_incomplete_internal_handoff_rejected_before_creating_destination(tmp_path, monkeypatch):
    import sys

    missing = tmp_path / "not-created"
    monkeypatch.setattr(sys, "argv", ["offsite_backup.py", "--destination", str(missing), "--supervised-lock-fd", "3"])
    with pytest.raises(RuntimeError, match="Incomplete supervised handoff"):
        offsite.main()
    assert not missing.exists()


def test_normal_main_does_not_pace_or_pull_with_recovery_marker(tmp_path, monkeypatch):
    (tmp_path / offsite.HANDOFF_MARKER).touch()
    monkeypatch.setattr(sys, "argv", ["offsite_backup.py", "--destination", str(tmp_path)])
    monkeypatch.setattr(offsite, "pace_recent_success", lambda *_: pytest.fail("must not pace"))
    monkeypatch.setattr(offsite, "pull", lambda *_: pytest.fail("must not pull"))
    with pytest.raises(offsite.InterruptedTransfer):
        offsite.main()


def test_internal_entry_runs_actual_pull_on_synthetic_transport(tmp_path):
    """Exercise actual pull/ledger/ACK paths, replacing only the SSH transport."""
    tmp_path.chmod(0o700)
    lock = os.open(tmp_path / ".pull.lock", os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    pidfd = os.pidfd_open(os.getpid())
    runid = "2" * 32
    worker = r"""
import hashlib,importlib.util,json,sys
from datetime import datetime,timezone
from types import SimpleNamespace
spec=importlib.util.spec_from_file_location('synthetic_offsite',sys.argv[1]);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
root,lock,pidfd,channel,runid=sys.argv[2:]
archive=b'synthetic-ciphertext'; name='20261101T120000Z.tar.enc'
def fake_run(args, **kwargs):
    cmd=args[-1]
    if cmd.endswith(' inventory'):
        now=int(datetime(2026,11,1,12,tzinfo=timezone.utc).timestamp())
        return SimpleNamespace(stdout=json.dumps({'server_now':now,'backups':[{'name':name,'size':len(archive),'sha256':hashlib.sha256(archive).hexdigest()}]}))
    if ' read ' in cmd: kwargs['stdout'].write(archive)
    elif cmd.endswith('export_ledger.py'): kwargs['stdout'].write(b'SPB1'+b'x'*28)
    elif ' --ack ' in cmd: pass
    else: raise RuntimeError('unexpected synthetic transport')
    return SimpleNamespace()
mod.run=fake_run;mod.pace_recent_success=lambda _:None
sys.argv=['offsite_backup.py','--destination',root,'--supervised-lock-fd',lock,'--supervised-pid-fd',pidfd,'--supervised-channel-fd',channel,'--supervised-run-id',runid]
mod.main()
"""
    process = subprocess.Popen(
        [sys.executable, "-c", worker, str(SOURCE), str(tmp_path), str(lock), str(pidfd), str(child.fileno()), runid],
        pass_fds=(lock, pidfd, child.fileno()),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    child.close()
    parent.settimeout(5)
    try:
        assert parent.recv(128) == ("READY " + runid).encode()
        assert parent.recv(128) == ("DONE " + runid).encode()
        assert process.wait(timeout=5) == 0
        assert (tmp_path / "20261101T120000Z.tar.enc").read_bytes() == b"synthetic-ciphertext"
        assert (tmp_path / "erasure-ledger.enc").read_bytes() == b"SPB1" + b"x" * 28
        assert (tmp_path / "last-success.json").exists()
        assert (tmp_path / offsite.HANDOFF_MARKER).exists()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        parent.close()
        os.close(lock)
        os.close(pidfd)
