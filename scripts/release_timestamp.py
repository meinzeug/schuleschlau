"""Obtain a validated UTC release timestamp from the deployment server."""

import re
import subprocess
from datetime import datetime


class ReleaseClockError(RuntimeError):
    """The target server did not supply a usable release timestamp."""


def release_timestamp():
    """Use the target's clock; the operator machine may be unsynchronized."""
    try:
        reply = subprocess.run(
            ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', 'dorfspy', 'date -u +%Y%m%dT%H%M%SZ'],
            capture_output=True, text=True, timeout=20, check=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ReleaseClockError('Unable to read the deployment server clock') from exc
    value = reply.stdout.strip()
    if not re.fullmatch(r'[0-9]{8}T[0-9]{6}Z', value):
        raise ReleaseClockError('Invalid deployment server timestamp')
    try:
        datetime.strptime(value, '%Y%m%dT%H%M%SZ')
    except ValueError as exc:
        raise ReleaseClockError('Invalid deployment server timestamp') from exc
    return value


if __name__ == '__main__':
    try:
        print(release_timestamp())
    except ReleaseClockError as error:
        raise SystemExit(str(error)) from None
