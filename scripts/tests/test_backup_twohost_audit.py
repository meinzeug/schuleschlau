"""Only artificial metadata and files; never contact a real server."""

import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location("twohost_audit", Path(__file__).resolve().parents[1] / "backup_twohost_audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
NOW = int(datetime(2026, 11, 1, 12, tzinfo=timezone.utc).timestamp())


@pytest.fixture
def sample(tmp_path):
    offsite = tmp_path / "offsite"
    offsite.mkdir(mode=0o700)
    rows = []
    for i, age in enumerate((1, 3, 50, 51, 52, 53, 169, 170, 337)):
        epoch = NOW - age * 3600
        name = datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y%m%dT%H%M%SZ.tar.enc")
        content = f"synthetic-{age}".encode()
        path = offsite / name
        path.write_bytes(content)
        path.chmod(0o600)
        # Local clock is intentionally an hour ahead, including fresh offsite
        # copies. Selection must use the server clock, not local mtime.
        os.utime(path, (NOW + 3600, NOW + 3600))
        rows.append({"name": name, "identity": [1, i + 1, len(content), epoch * 10**9,
                                               epoch * 10**9, 0, 1, stat.S_IFREG | 0o600],
                     "sha256": hashlib.sha256(content).hexdigest()})
    inventory = {"server_now": NOW, "archives": rows, "restore": rows[1]["name"],
                 "release_stamps": [rows[0]["name"][:16], rows[1]["name"][:16]]}
    return offsite, inventory, rows


def chosen(result):
    assert result["advisory_only"] and result["offsite_independence_and_concurrent_writers_unverified"]
    return {item["name"] for item in result["candidates"]}


def test_clock_offset_all_48h_restore_and_explicit_deploy_are_protected(sample):
    directory, inv, rows = sample
    result = audit.build_manifest(inv, directory, [rows[4]["name"]])
    assert chosen(result) == {rows[3]["name"], rows[5]["name"], rows[7]["name"]}
    assert rows[0]["name"] not in chosen(result) and rows[1]["name"] not in chosen(result)
    assert rows[8]["name"] not in chosen(result)


def test_offsite_mismatch_symlink_and_hardlink_are_rejected(sample):
    directory, inv, rows = sample
    (directory / rows[5]["name"]).write_bytes(b"different")
    (directory / rows[7]["name"]).unlink()
    (directory / rows[7]["name"]).symlink_to(directory / rows[6]["name"])
    os.link(directory / rows[3]["name"], directory.parent / "extra-hardlink")
    assert not chosen(audit.build_manifest(inv, directory, [rows[4]["name"]]))


def test_missing_survivor_stops_thinning_its_slot(sample):
    directory, inv, rows = sample
    (directory / rows[2]["name"]).unlink()
    result = audit.build_manifest(inv, directory, [rows[4]["name"]])
    assert rows[5]["name"] not in chosen(result)
    assert rows[7]["name"] in chosen(result)


def test_mutated_survivor_cannot_authorize_candidates(sample, monkeypatch):
    directory, inv, rows = sample
    original = audit.local_digest

    def changed(path):
        result = original(path)
        if path.name == rows[5]["name"]:
            (directory / rows[2]["name"]).write_bytes(b"changed later")
        return result

    monkeypatch.setattr(audit, "local_digest", changed)
    result = audit.build_manifest(inv, directory, [rows[4]["name"]])
    assert rows[3]["name"] not in chosen(result)
    assert rows[5]["name"] not in chosen(result)


def test_untrusted_server_metadata_or_missing_protection_fails_closed(sample):
    directory, inv, rows = sample
    with pytest.raises(ValueError):
        audit.build_manifest(inv, directory, [])
    inv["archives"][0]["identity"][6] = 2
    with pytest.raises(ValueError):
        audit.build_manifest(inv, directory, [rows[4]["name"]])


def test_manifest_is_private_and_never_overwrites_existing_file(tmp_path):
    path = tmp_path / "manifest.json"
    audit.write_new_private_manifest(path, {"advisory_only": True})
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert json.loads(path.read_text()) == {"advisory_only": True}
    with pytest.raises(FileExistsError):
        audit.write_new_private_manifest(path, {"other": True})
    assert json.loads(path.read_text()) == {"advisory_only": True}


def test_remote_command_is_fixed_and_ssh_alias_restricted(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(stdout='{"server_now":1}')

    monkeypatch.setattr(audit.subprocess, "run", fake_run)
    assert audit.remote_scan("example-host")["server_now"] == 1
    assert calls[0][0][-1] == "sudo -n python3 -"
    assert calls[0][1]["input"] == audit.REMOTE_SCAN
    with pytest.raises(ValueError):
        audit.remote_scan("-oProxyCommand=unsafe")


def test_remote_scanner_against_synthetic_directories_only(tmp_path):
    archives = tmp_path / "server-backups"
    releases = tmp_path / "releases"
    archives.mkdir()
    releases.mkdir()
    name = "20261030T100000Z.tar.enc"
    fake = archives / name
    fake.write_bytes(b"synthetic ciphertext only")
    fake.chmod(0o600)
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"backup": name, "authenticated_restore": True}))
    for label in ("current", "previous"):
        target = releases / "20261030T110000Z-abcdef"
        target.mkdir(exist_ok=True)
        (releases / label).symlink_to(target)
    script = (audit.REMOTE_SCAN
              .replace("'/var/backups/schulpilot'", repr(str(archives)))
              .replace("'/var/backups/schulpilot-monitor/restore-check.json'", repr(str(report)))
              .replace("'/opt/schulpilot'", repr(str(releases)))
              .replace("before.st_uid!=0", "before.st_uid!=os.getuid()"))
    result = subprocess.run([sys.executable, "-"], input=script, text=True, capture_output=True, check=True)
    inventory = json.loads(result.stdout)
    assert inventory["restore"] == name
    assert inventory["archives"][0]["sha256"] == hashlib.sha256(fake.read_bytes()).hexdigest()
    os.link(fake, archives / "20261030T120000Z.tar.enc")
    result = subprocess.run([sys.executable, "-"], input=script, text=True, capture_output=True)
    assert result.returncode != 0
