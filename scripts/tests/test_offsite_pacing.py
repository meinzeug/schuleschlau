"""Offsite pacing uses only synthetic local markers and never contacts a host."""

import fcntl
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "offsite_backup", Path(__file__).resolve().parents[1] / "offsite_backup.py"
)
offsite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(offsite)


@pytest.mark.parametrize(
    "checked,expected", [(1060, 60), (1040, 40), (1001, 1), (1000, None), (1200, None), (999, None)]
)
def test_delay_is_bounded_and_only_follows_a_recent_success(tmp_path, monkeypatch, checked, expected):
    (tmp_path / "last-success.json").write_text(json.dumps({"checked_at": checked}))
    waits = []
    monkeypatch.setattr(offsite.time, "time", lambda: 1060)
    monkeypatch.setattr(offsite.time, "sleep", waits.append)
    offsite.pace_recent_success(tmp_path)
    assert waits == ([] if expected is None else [expected])


@pytest.mark.parametrize("content", ["{", "[]", "null", '{"checked_at": true}', '{"checked_at": "1060"}',
    "x" * 4097, "[" * 1200 + "]" * 1200, '{"checked_at":' + "9" * 400 + '}'])
def test_invalid_marker_never_blocks_a_backup(tmp_path, monkeypatch, content):
    (tmp_path / "last-success.json").write_text(content)
    monkeypatch.setattr(offsite.time, "sleep", lambda _: pytest.fail("invalid marker must not delay a backup"))
    offsite.pace_recent_success(tmp_path)


def test_missing_and_symlinked_marker_never_block_a_backup(tmp_path, monkeypatch):
    monkeypatch.setattr(offsite.time, "sleep", lambda _: pytest.fail("missing marker must not delay a backup"))
    offsite.pace_recent_success(tmp_path)
    other = tmp_path / "other"
    other.write_text('{"checked_at": 1060}')
    (tmp_path / "last-success.json").symlink_to(other)
    offsite.pace_recent_success(tmp_path)


def test_pacing_and_pull_share_the_existing_exclusive_lock(tmp_path, monkeypatch):
    phases = []
    monkeypatch.setattr(sys, "argv", ["offsite_backup.py", "--destination", str(tmp_path)])

    def phase(name):
        def verify(destination):
            assert destination == tmp_path
            with (destination / ".pull.lock").open("r") as contender:
                with pytest.raises(BlockingIOError):
                    fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
            phases.append(name)
        return verify

    monkeypatch.setattr(offsite, "pace_recent_success", phase("pace"))
    monkeypatch.setattr(offsite, "pull", phase("pull"))
    old_umask = os.umask(0o077)
    try:
        offsite.main()
    finally:
        os.umask(old_umask)
    assert phases == ["pace", "pull"]


def test_default_service_keeps_ten_minutes_for_transfer_after_maximum_pacing():
    unit = Path(__file__).resolve().parents[2] / "deploy/schulpilot-offsite.service"
    settings = [line for line in unit.read_text().splitlines() if line.startswith("TimeoutStartSec=")]
    assert settings == ["TimeoutStartSec=11min"]
    assert 11 * 60 - offsite.MIN_SUCCESS_GAP_SECONDS == 10 * 60
