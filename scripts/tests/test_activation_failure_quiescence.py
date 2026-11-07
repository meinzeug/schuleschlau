"""Execute the real exception handler against fake units and synthetic paths."""
import ast
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


def handler_code():
    source = (ROOT / 'deploy/activate.py').read_text()
    module = ast.parse(source)
    handlers = [node for node in ast.walk(module) if isinstance(node, ast.ExceptHandler)
                and len(node.body) > 4 and isinstance(node.body[0], ast.If)
                and any(isinstance(item, ast.Name) and item.id == 'writer_stop_attempted'
                        for item in ast.walk(node.body[0].test))]
    assert len(handlers) == 1
    isolated = ast.Module(body=[ast.Try(body=[ast.Raise(exc=ast.Call(func=ast.Name(id='RuntimeError', ctx=ast.Load()),
                                                                       args=[ast.Constant(value='synthetic')], keywords=[]), cause=None)],
                                     handlers=[handlers[0]], orelse=[], finalbody=[])], type_ignores=[])
    return compile(ast.fix_missing_locations(isolated), '<isolated-activation-handler>', 'exec')


@pytest.mark.parametrize(('stop_attempted', 'new_writers', 'migration', 'same_revision'), [
    (False, False, False, True),
    (True, False, False, True),
    (True, False, True, True),
    (True, False, True, False),
    (True, True, True, True),
])
def test_exception_path_never_restarts_writers(tmp_path, stop_attempted, new_writers, migration, same_revision):
    base = tmp_path / 'base'
    base.mkdir()
    old = base / 'old'
    old.mkdir()
    current = base / 'current'
    current.symlink_to(old if not stop_attempted else base / 'candidate')
    caddy = tmp_path / 'Caddyfile'
    fragment = tmp_path / 'fragment'
    calls = []
    fake_subprocess = SimpleNamespace(run=lambda args, **kwargs: calls.append((args, kwargs)))
    context = {
        'new_writers_may_have_started': new_writers, 'writer_stop_attempted': stop_attempted,
        'photo_candidate_started': False, 'photo_previous': object(),
        'caddy': caddy, 'before': 'synthetic', 'fragment_before': 'synthetic-fragment', 'fragment': fragment,
        'migration_started': migration, 'database_revision': lambda: 'old' if same_revision else 'new',
        'schema_before': 'old', 'previous': old, 'unit_snapshots': {},
        'restore_files': lambda saved: None, 'base': base, 'current': current,
        'subprocess': fake_subprocess, 'sys': sys,
    }
    with pytest.raises(RuntimeError, match='synthetic'):
        exec(handler_code(), context)
    commands = [args for args, _ in calls]
    assert not any(args[:2] == ['systemctl', 'restart'] for args in commands)
    assert not any(args[:2] == ['systemctl', 'start'] for args in commands)
    stop_calls = [args for args in commands if args[:2] == ['systemctl', 'stop']]
    assert bool(stop_calls) == (stop_attempted or new_writers)
    assert current.resolve() == ((base / 'candidate').resolve() if stop_attempted else old.resolve())


def test_failed_rollback_reload_never_starts_service(tmp_path):
    """Failure handler never rolls unit files or invokes daemon reload."""
    base = tmp_path / 'base'
    base.mkdir()
    old = base / 'old'
    old.mkdir()
    current = base / 'current'
    current.symlink_to(base / 'candidate')
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        if args[:2] == ['systemctl', 'daemon-reload']:
            raise RuntimeError('synthetic reload failure')
    context = {'new_writers_may_have_started': False, 'writer_stop_attempted': True,
               'photo_candidate_started': False, 'photo_previous': object(),
               'caddy': tmp_path / 'caddy', 'before': '', 'fragment_before': None, 'fragment': tmp_path / 'fragment',
               'migration_started': False, 'schema_before': None, 'previous': old,
               'unit_snapshots': {}, 'restore_files': lambda saved: None,
               'base': base, 'current': current, 'subprocess': SimpleNamespace(run=run), 'sys': sys}
    with pytest.raises(RuntimeError, match='synthetic'):
        exec(handler_code(), context)
    assert not any(args[:2] in (['systemctl', 'start'], ['systemctl', 'restart']) for args in calls)


@pytest.mark.parametrize(('previous_exists', 'candidate_stop_fails'), [
    (False, False), (True, False), (False, True), (True, True),
])
def test_first_install_and_photo_failure_leave_writers_stopped(tmp_path, previous_exists, candidate_stop_fails):
    """Failure of a candidate decoder never restarts writers, including setup."""
    base = tmp_path / 'base'
    base.mkdir()
    previous = base / 'old' if previous_exists else None
    if previous:
        previous.mkdir()
    current = base / 'current'
    current.symlink_to(base / 'candidate')
    calls = []
    photo_calls = []

    def stop_photo(previous_photo):
        photo_calls.append(previous_photo)
        if candidate_stop_fails:
            raise RuntimeError('synthetic decoder stop failure')

    context = {'new_writers_may_have_started': False, 'writer_stop_attempted': previous_exists,
               'photo_candidate_started': True, 'photo_previous': 'synthetic-photo',
               'undo_candidate_enable': stop_photo, 'caddy': tmp_path / 'caddy', 'before': '',
               'fragment_before': None, 'fragment': tmp_path / 'fragment', 'migration_started': True,
               'previous': previous, 'unit_snapshots': {}, 'restore_files': lambda saved: None,
               'base': base, 'current': current,
               'subprocess': SimpleNamespace(run=lambda args, **kwargs: calls.append(args)), 'sys': sys}
    with pytest.raises(RuntimeError, match='synthetic'):
        exec(handler_code(), context)
    assert photo_calls == ['synthetic-photo']
    assert not any(args[:2] in (['systemctl', 'start'], ['systemctl', 'restart']) for args in calls)
    assert current.resolve() == (base / 'candidate').resolve()
    stop_calls = [args for args in calls if args[:2] == ['systemctl', 'stop']]
    assert bool(stop_calls) == (previous_exists or candidate_stop_fails)
    assert not any(args[:2] in (['systemctl', 'start'], ['systemctl', 'stop'])
                   and any(str(name).endswith('.timer') for name in args[2:]) for args in calls)


@pytest.mark.parametrize('snapshot', [None, {}])
def test_before_writer_stop_does_not_restore_units_or_touch_current_even_if_restore_would_fail(tmp_path, snapshot):
    """Before a stop no release/unit restoration is needed or permitted."""
    base = tmp_path / 'base'
    base.mkdir()
    old = base / 'old'
    old.mkdir()
    current = base / 'current'
    current.symlink_to(old)
    original_inode = current.lstat().st_ino
    calls = []

    def restore_files(saved):
        raise AssertionError('unit restoration must not be called before writer stop')

    def systemctl(args, **kwargs):
        calls.append(args)
        if args[:2] == ['systemctl', 'daemon-reload']:
            raise AssertionError('daemon-reload must not be called before writer stop')

    context = {'new_writers_may_have_started': False, 'writer_stop_attempted': False,
               'photo_candidate_started': False, 'photo_previous': None,
               'caddy': tmp_path / 'caddy', 'before': '', 'fragment_before': None,
               'fragment': tmp_path / 'fragment', 'migration_started': False, 'previous': old,
               'unit_snapshots': snapshot, 'restore_files': restore_files,
               'base': base, 'current': current, 'subprocess': SimpleNamespace(run=systemctl), 'sys': sys}
    with pytest.raises(RuntimeError, match='synthetic'):
        exec(handler_code(), context)
    assert current.lstat().st_ino == original_inode
    assert current.resolve() == old
    assert not any(args[:2] in (['systemctl', 'stop'], ['systemctl', 'start'], ['systemctl', 'restart'],
                                ['systemctl', 'daemon-reload']) for args in calls)


@pytest.mark.parametrize(('failed_file', 'stop_raises'), [('caddy', False), ('fragment', False), ('caddy', True)])
def test_independent_recovery_failure_preserves_original_and_never_switches_release(tmp_path, failed_file, stop_raises):
    class ConfigFile:
        def __init__(self, name):
            self.name = name
            self.writes = []
        def write_text(self, value):
            self.writes.append(value)
            if self.name == failed_file:
                raise OSError('synthetic config error')
    base = tmp_path / 'base'
    base.mkdir()
    old = base / 'old'
    old.mkdir()
    current = base / 'current'
    current.symlink_to(base / 'candidate')
    inode = current.lstat().st_ino
    caddy, fragment = ConfigFile('caddy'), ConfigFile('fragment')
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        if stop_raises:
            raise OSError('synthetic stop failure')
        return SimpleNamespace(returncode=1)
    context = {'new_writers_may_have_started': False, 'writer_stop_attempted': True,
               'photo_candidate_started': False, 'photo_previous': None,
               'caddy': caddy, 'before': 'before', 'fragment_before': 'fragment-before', 'fragment': fragment,
               'migration_started': False, 'previous': old, 'unit_snapshots': {},
               'restore_files': lambda saved: pytest.fail('must not restore units'),
               'base': base, 'current': current, 'subprocess': SimpleNamespace(run=run), 'sys': sys}
    with pytest.raises(RuntimeError, match='synthetic'):
        exec(handler_code(), context)
    assert caddy.writes == ['before'] and fragment.writes == ['fragment-before']
    assert current.lstat().st_ino == inode
    assert current.resolve() == (base / 'candidate').resolve()
    assert calls == [['systemctl', 'stop', 'schulpilot-api', 'schulpilot-worker']]
