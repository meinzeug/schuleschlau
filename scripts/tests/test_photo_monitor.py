from types import SimpleNamespace

from deploy import monitor


def test_photo_monitor_checks_only_required_release_and_detects_missing_unit(tmp_path):
    unit, required = tmp_path / 'service', tmp_path / 'decoder'
    assert monitor.photo_service_failure(unit, required) is None
    required.write_text('synthetic')
    assert monitor.photo_service_failure(unit, required) == 'photo_service_missing'


def test_photo_monitor_distinguishes_inactive_unavailable_and_healthy(tmp_path, monkeypatch):
    unit, required = tmp_path / 'service', tmp_path / 'decoder'
    unit.touch()
    required.touch()
    result = {'active': 1, 'health': 1}
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=result['active'] if command[0] == 'systemctl' else result['health'])
    monkeypatch.setattr(monitor.subprocess, 'run', run)
    assert monitor.photo_service_failure(unit, required) == 'photo_service_inactive'
    result['active'] = 0
    assert monitor.photo_service_failure(unit, required) == 'photo_service_unavailable'
    result['health'] = 0
    assert monitor.photo_service_failure(unit, required) is None
    assert calls[-1][0][:6] == ['runuser', '-u', 'schulpilot', '-g', 'schulpilot-photo', '--']
    assert calls[-1][0][-1] == '--monitor'
    assert calls[-1][1]['timeout'] > 75
