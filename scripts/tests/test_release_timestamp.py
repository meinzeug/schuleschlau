"""The release name uses only a valid timestamp from the target, never local time."""

import importlib.util
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('release_timestamp', ROOT / 'scripts/release_timestamp.py')
clock = importlib.util.module_from_spec(spec)
spec.loader.exec_module(clock)


def test_target_clock_is_requested_over_checked_bounded_ssh(monkeypatch):
    def fake_run(args, **kwargs):
        assert args == ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', 'dorfspy', 'date -u +%Y%m%dT%H%M%SZ']
        assert kwargs == {'capture_output': True, 'text': True, 'timeout': 20, 'check': True}
        return SimpleNamespace(stdout='20261101T185406Z\n')
    monkeypatch.setattr(clock.subprocess, 'run', fake_run)
    assert clock.release_timestamp() == '20261101T185406Z'


@pytest.mark.parametrize('invalid', ['', '20261301T185406Z', '20260229T000000Z',
    '20261101T185460Z', '２０２６１１０１T１８５４０６Z', '20261101T185406Z;command', '20261101T185406Z\nextra', 'private sentinel'])
def test_invalid_or_multiple_values_never_become_release_names(monkeypatch, invalid):
    monkeypatch.setattr(clock.subprocess, 'run', lambda *args, **kwargs: SimpleNamespace(stdout=invalid))
    with pytest.raises(clock.ReleaseClockError, match='Invalid deployment server timestamp'):
        clock.release_timestamp()


@pytest.mark.parametrize('error', [OSError('private sentinel'), UnicodeDecodeError('utf-8', b'\xff', 0, 1, 'bad input'),
    subprocess.TimeoutExpired('ssh', 20),
    subprocess.CalledProcessError(1, 'ssh', stderr='private sentinel')])
def test_failed_ssh_never_falls_back_to_unsynchronized_local_time(monkeypatch, error):
    def fail(*_args, **_kwargs):
        raise error
    monkeypatch.setattr(clock.subprocess, 'run', fail)
    with pytest.raises(clock.ReleaseClockError, match='Unable to read the deployment server clock') as exc:
        clock.release_timestamp()
    assert 'private sentinel' not in str(exc.value)


def test_deploy_requests_validated_target_timestamp_before_staging():
    script = (ROOT / 'scripts/deploy.sh').read_text()
    assert script.index('python3 scripts/release_timestamp.py') < script.index('stage_release.py')
    assert '$(date -u +%Y%m%dT%H%M%SZ)' not in script
