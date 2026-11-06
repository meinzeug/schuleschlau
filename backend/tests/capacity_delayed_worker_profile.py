"""Explicit slower-provider, two-worker synthetic capacity probe.

Run only through scripts/test_postgres.py with an isolated PostgreSQL cluster.
The provider is simulated; the test never contacts an external model.
"""

from capacity_worker_profile import run_worker_profile


def test_bounded_delayed_multi_family_worker_profile(api, household, mailbox, monkeypatch):
    run_worker_profile(api, household, mailbox, monkeypatch, provider_delay=2, worker_threads=2)
