"""A release accepts only the archive of its own successful backup invocation."""
import json
import os

import pytest

from deploy.backup_release_check import verify_invocation_log

NAME = '20261106T010203Z.tar.enc'
LOG = f'SCHULPILOT backup created: {NAME}; deletion journal: present\n'


def evidence(root):
    archive = root / NAME
    sidecar = root / (NAME + '.journal.json')
    archive.write_bytes(b'SPB1' + b'x' * 28)
    sidecar.write_text(json.dumps({'backup': NAME, 'journal': 'present'}))
    archive.chmod(0o600)
    sidecar.chmod(0o600)


def test_exact_invocation_record_and_matching_archive_are_accepted(tmp_path):
    evidence(tmp_path)
    assert verify_invocation_log('neutral service line\n' + LOG, tmp_path) == NAME


@pytest.mark.parametrize('record', [
    '', LOG.replace('present', 'missing'), LOG.replace('present', 'unavailable'),
    LOG + LOG, LOG.replace(NAME, '../../other.tar.enc'),
    LOG.replace('deletion journal: present', 'deletion journal: present -- extra'),
    'x' * 65537,
])
def test_uncertain_or_incomplete_invocation_is_rejected(tmp_path, record):
    evidence(tmp_path)
    with pytest.raises(RuntimeError):
        verify_invocation_log(record, tmp_path)


@pytest.mark.parametrize('problem', ['missing_archive', 'missing_sidecar', 'bad_magic', 'short_archive',
                                     'bad_json', 'wrong_backup', 'missing_journal', 'oversized',
                                     'archive_symlink', 'sidecar_symlink', 'hardlink'])
def test_untrusted_or_inconsistent_archive_evidence_is_rejected(tmp_path, problem):
    evidence(tmp_path)
    archive = tmp_path / NAME
    sidecar = tmp_path / (NAME + '.journal.json')
    if problem == 'missing_archive':
        archive.unlink()
    elif problem == 'missing_sidecar':
        sidecar.unlink()
    elif problem == 'bad_magic':
        archive.write_bytes(b'BAD!' + b'x' * 28)
    elif problem == 'short_archive':
        archive.write_bytes(b'SPB1')
    elif problem == 'bad_json':
        sidecar.write_text('{')
    elif problem == 'wrong_backup':
        sidecar.write_text(json.dumps({'backup': 'other', 'journal': 'present'}))
    elif problem == 'missing_journal':
        sidecar.write_text(json.dumps({'backup': NAME, 'journal': 'missing'}))
    elif problem == 'oversized':
        sidecar.write_bytes(b' ' * 8193)
    elif problem.endswith('_symlink'):
        path = archive if problem == 'archive_symlink' else sidecar
        target = tmp_path / 'other'
        path.rename(target)
        path.symlink_to(target)
    elif problem == 'hardlink':
        os.link(archive, tmp_path / 'second-link')
    with pytest.raises(RuntimeError):
        verify_invocation_log(LOG, tmp_path)
