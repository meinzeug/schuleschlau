"""Fail-closed guard for isolated capacity profiles and their helpers.

This is test infrastructure, never an application authorization decision.
"""
import os
import pwd
import stat
import subprocess
import tempfile
from pathlib import Path

from sqlalchemy.engine import make_url


def require_private_profile_database(*, helper=False):
    url_text = os.environ.get('TEST_DATABASE_URL', '')
    if not url_text:
        raise RuntimeError('Run this profile only through scripts/test_postgres.py')
    if helper and (os.environ.get('DATABASE_URL') != url_text or os.environ.get('ENVIRONMENT') != 'test'):
        raise RuntimeError('Missing explicit synthetic database and test environment')
    url = make_url(url_text)
    sock = Path(url.query.get('host', ''))
    root = sock.parent
    temp = Path(tempfile.gettempdir())
    user = pwd.getpwuid(os.getuid()).pw_name
    if (url.drivername != 'postgresql+psycopg' or url.database != 'schulpilot_isolated_test'
            or url.host is not None or url.port is not None or url.username != user or url.password is not None
            or set(url.query) != {'host', 'port'} or str(url.query.get('port')) != '55440'
            or sock.name != 'socket' or (root != temp and root.parent != temp)
            or not root.name.startswith('schulpilot-isolated-pg-')
            or not root.is_absolute() or root.resolve() != root or sock.is_symlink()):
        raise RuntimeError('Capacity profile requires the private local PostgreSQL runner')
    data = root / 'database'
    try:
        for path in (root, sock, data):
            meta = path.lstat()
            if not stat.S_ISDIR(meta.st_mode) or meta.st_uid != os.getuid() or stat.S_IMODE(meta.st_mode) != 0o700:
                raise RuntimeError('Insecure synthetic database directory')
        if not stat.S_ISSOCK((sock / '.s.PGSQL.55440').lstat().st_mode):
            raise RuntimeError('Synthetic database socket missing')
    except FileNotFoundError as exc:
        raise RuntimeError('Capacity profile requires a running isolated PostgreSQL runner') from exc
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(root), 'LANG': 'C.UTF-8',
           'PGPASSFILE': str(root / 'no-password-file'), 'PGCONNECT_TIMEOUT': '3'}
    try:
        result = subprocess.run(
            ['/usr/lib/postgresql/16/bin/psql', '-X', '-w', '-A', '-t', '-F', '|',
             '-h', str(sock), '-p', '55440', '-U', user, '-d', 'schulpilot_isolated_test', '-c',
             "SELECT current_database(), COALESCE(inet_server_addr()::text, 'unix'), current_setting('data_directory')"],
            check=True, capture_output=True, text=True, timeout=5, env=env,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError('Cannot verify synthetic database identity') from exc
    if result.stdout.strip() != f'schulpilot_isolated_test|unix|{data}':
        raise RuntimeError('Synthetic database identity does not match its isolated directory')
