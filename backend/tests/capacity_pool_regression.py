"""Saturate the isolated PostgreSQL pool with independent reservation requests."""
from capacity_network_profile import run_loopback_profile


def test_reservation_does_not_wait_for_second_pool_connection(api, household, mailbox, monkeypatch):
    run_loopback_profile(api, household, mailbox, monkeypatch, families=15, gate_reservations=True)
