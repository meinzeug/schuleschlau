from types import SimpleNamespace

import pytest

from deploy import photo_release as photo


def fake_show(load='loaded', active='inactive', enabled='disabled'):
    return SimpleNamespace(stdout=f'LoadState={load}\nActiveState={active}\nUnitFileState={enabled}\n')


def test_photo_inspection_accepts_only_stable_states():
    assert photo.inspect_photo(lambda *a, **k: fake_show('not-found', 'inactive', '')) == photo.PreviousPhoto(False, False, False)
    assert photo.inspect_photo(lambda *a, **k: fake_show('loaded', 'active', 'enabled')) == photo.PreviousPhoto(True, True, True)
    for state in (fake_show('loaded', 'activating', 'enabled'), fake_show('loaded', 'failed', 'disabled'),
                  fake_show('error', 'inactive', ''), SimpleNamespace(stdout='LoadState=loaded\n')):
        with pytest.raises(RuntimeError):
            photo.inspect_photo(lambda *a, **k: state)


def test_photo_definition_refuses_unknown_unit_and_dropins(tmp_path):
    unit = tmp_path / 'schulpilot-photo.service'
    release = tmp_path / 'release'
    source = release / 'deploy/schulpilot-photo.service'
    source.parent.mkdir(parents=True)
    source.write_text('synthetic safe unit')
    previous = photo.PreviousPhoto(False, False, False)
    def show(fragment='', dropins='', reload='no'):
        return lambda *a, **k: SimpleNamespace(stdout=f'FragmentPath={fragment}\nDropInPaths={dropins}\nNeedDaemonReload={reload}\n')
    photo.verify_photo_definition(previous, None, unit=unit, run=show())
    unit.write_text('foreign')
    with pytest.raises(RuntimeError):
        photo.verify_photo_definition(previous, None, unit=unit, run=show())
    previous = photo.PreviousPhoto(True, True, True)
    with pytest.raises(RuntimeError):
        photo.verify_photo_definition(previous, release, unit=unit, run=show(str(unit)))
    unit.write_bytes(source.read_bytes())
    photo.verify_photo_definition(previous, release, unit=unit, run=show(str(unit)))
    with pytest.raises(RuntimeError):
        photo.verify_photo_definition(previous, release, unit=unit, run=show(str(unit), '/etc/systemd/system/override.conf'))
    with pytest.raises(RuntimeError):
        photo.verify_photo_definition(previous, release, unit=unit, run=show('/foreign/unit'))
    with pytest.raises(RuntimeError):
        photo.verify_photo_definition(previous, release, unit=unit, run=show(str(unit), reload='yes'))


def test_photo_identity_rejects_uid_gid_alias_and_foreign_groups(tmp_path, monkeypatch):
    (tmp_path / 'deploy').mkdir()
    (tmp_path / 'deploy/schulpilot-photo.sysusers').write_text('synthetic')
    api = SimpleNamespace(pw_name='schulpilot', pw_uid=100, pw_gid=100)
    isolated = SimpleNamespace(pw_name='schulpilot-photo', pw_uid=101, pw_gid=101,
                               pw_shell='/usr/sbin/nologin', pw_dir='/nonexistent')
    group = SimpleNamespace(gr_name='schulpilot-photo', gr_gid=101, gr_mem=[])
    monkeypatch.setattr(photo.pwd, 'getpwnam', lambda name: api if name == 'schulpilot' else isolated)
    monkeypatch.setattr(photo.grp, 'getgrnam', lambda name: group)
    monkeypatch.setattr(photo.pwd, 'getpwall', lambda: [api, isolated])
    monkeypatch.setattr(photo.grp, 'getgrall', lambda: [group])
    monkeypatch.setattr(photo.os, 'getgrouplist', lambda user, gid: [gid])
    calls = []
    def run(cmd, **kwargs):
        calls.append(cmd)
    photo.ensure_isolated_identity(tmp_path, run=run)
    assert calls[0][0] == 'systemd-sysusers'
    group.gr_gid = isolated.pw_gid = 0
    with pytest.raises(RuntimeError):
        photo.ensure_isolated_identity(tmp_path, run=run)
    group.gr_gid = isolated.pw_gid = 101
    monkeypatch.setattr(photo.grp, 'getgrall', lambda: [group, SimpleNamespace(gr_name='foreign', gr_gid=101)])
    with pytest.raises(RuntimeError):
        photo.ensure_isolated_identity(tmp_path, run=run)
    monkeypatch.setattr(photo.grp, 'getgrall', lambda: [group])
    group.gr_mem = ['unrelated-user']
    with pytest.raises(RuntimeError):
        photo.ensure_isolated_identity(tmp_path, run=run)


def test_photo_start_requires_revision_health_as_api_uid_and_group(tmp_path):
    probe = tmp_path / 'backend/schulpilot/photo_health.py'
    probe.parent.mkdir(parents=True)
    probe.write_text('synthetic')
    calls = []
    def run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0 if len(calls) > 2 else 1)
    waits = []
    photo.start_candidate(tmp_path, run=run, sleep=waits.append)
    assert calls[0] == ['systemctl', 'restart', 'schulpilot-photo.service']
    assert calls[1][:6] == ['runuser', '-u', 'schulpilot', '-g', 'schulpilot-photo', '--']
    assert len(waits) == 1 and len(calls) == 3
    with pytest.raises(RuntimeError):
        photo.start_candidate(tmp_path, run=lambda *a, **k: SimpleNamespace(returncode=1), sleep=lambda n: None)


def test_photo_rollback_restores_active_and_enabled_prior_state():
    calls = []
    def run(cmd, **kwargs):
        calls.append(cmd)
    previous = photo.PreviousPhoto(True, True, True)
    photo.stop_old_photo(previous, run=run)
    photo.undo_candidate_enable(previous, run=run)
    photo.restore_previous_photo(previous, run=run)
    assert calls == [
        ['systemctl', 'stop', 'schulpilot-photo.service'],
        ['systemctl', 'stop', 'schulpilot-photo.service'],
        ['systemctl', 'enable', 'schulpilot-photo.service'],
        ['systemctl', 'start', 'schulpilot-photo.service'],
    ]
    calls.clear()
    photo.undo_candidate_enable(photo.PreviousPhoto(False, False, False), run=run)
    assert calls == [['systemctl', 'stop', 'schulpilot-photo.service'],
                     ['systemctl', 'disable', 'schulpilot-photo.service']]
