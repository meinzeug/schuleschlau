"""Maintenance of a later admin must not rewrite first-setup history."""

import io
import sys

import pytest
from schulpilot import cli
from schulpilot.db import DB, Installation, User
from schulpilot.security import password_hash
from sqlalchemy import select


@pytest.mark.parametrize("command", ["create-admin", "reset-admin"])
def test_admin_cli_preserves_completed_installation_timestamp(monkeypatch, command):
    with DB.begin() as db:
        installation = db.get(Installation, 1)
        installation.completed = True
        installation.completed_at = 1700000000
        if command == "reset-admin":
            db.add(
                User(
                    username="synthetic-admin",
                    display_name="Admin",
                    role="admin",
                    verified=True,
                    password_hash=password_hash("old-artificial-password-123"),
                )
            )
    monkeypatch.setattr(sys, "argv", ["schulpilot.cli", command, "--username", "synthetic-admin", "--password-stdin"])
    monkeypatch.setattr(sys, "stdin", io.StringIO("new-artificial-password-123\n"))
    cli.main()
    with DB() as db:
        assert db.get(Installation, 1).completed_at == 1700000000
        assert db.scalar(select(User).where(User.username == "synthetic-admin")).role == "admin"


def test_first_admin_still_completes_installation(monkeypatch):
    with DB.begin() as db:
        item = db.get(Installation, 1)
        item.completed = False
        item.completed_at = None
    monkeypatch.setattr(
        sys, "argv", ["schulpilot.cli", "create-admin", "--username", "first-synthetic-admin", "--password-stdin"]
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO("new-artificial-password-123\n"))
    cli.main()
    with DB() as db:
        installation = db.get(Installation, 1)
        assert installation.completed is True and installation.completed_at is not None
        assert installation.bootstrap_digest is None and installation.bootstrap_expires is None
