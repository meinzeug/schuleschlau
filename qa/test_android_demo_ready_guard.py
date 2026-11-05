"""Local checks for the one-shot demo-ready emulator runner; no network."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import android_demo_ready_e2e as runner
from android_push import PushQaError


def test_round_request_can_only_be_reserved_once(tmp_path):
    with patch.object(runner, 'ROOT', tmp_path):
        runner.reserve_one(244)
        claims = list((tmp_path / 'artifacts').glob('.android-demo-ready-*-reserved.json'))
        assert len(claims) == 1
        assert claims[0].stat().st_mode & 0o777 == 0o600
        with pytest.raises(PushQaError, match='already_reserved'):
            runner.reserve_one(244)


def test_observer_is_valid_python():
    compile(runner.REMOTE, '<bounded-remote-observer>', 'exec')
