"""Safety properties of the owned production beta signup probe; no network."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("beta_live_probe", ROOT / "scripts/beta_live_signup_smoke.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def fixture():
    return {
        "email": "owner+schuleschlau-beta-qa-" + "a" * 20 + "@gmail.com",
        "child": "beta-qa-" + "a" * 20,
        "password": "synthetic-password-with-adequate-length",
    }


def test_scope_only_allows_owned_generated_alias_and_child():
    config = {"SMTP_USER": "owner@gmail.com"}
    assert probe.owned(fixture(), config)
    for change in (
        {"email": "other+schuleschlau-beta-qa-" + "a" * 20 + "@gmail.com"},
        {"email": "owner@gmail.com"},
        {"child": "actual-child"},
        {"email": "owner+schuleschlau-beta-qa-" + "a" * 20 + "@example.org"},
        {"password": "short"},
    ):
        assert not probe.owned(fixture() | change, config)


def test_recovery_journal_is_private_and_replaceable(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, "JOURNAL", tmp_path / "journal.json")
    data = fixture()
    probe.save(data)
    assert probe.JOURNAL.stat().st_mode & 0o077 == 0
    assert json.loads(probe.JOURNAL.read_text()) == data
    probe.save(data | {"verified": True})
    assert json.loads(probe.JOURNAL.read_text())["verified"] is True
    assert sorted(p.name for p in tmp_path.iterdir()) == ["journal.json"]


def test_reject_unexpected_http_status_without_echoing_body():
    class Request:
        class url:
            path = "/auth/register"

    class Response:
        status_code = 500
        request = Request()

    with pytest.raises(RuntimeError, match="HTTP 500") as error:
        probe.expect(Response(), 201)
    assert "password" not in str(error.value)


def test_verified_cleanup_does_not_depend_on_mail_service(tmp_path, monkeypatch, capsys):
    import sys

    journal = tmp_path / "journal.json"
    data = fixture() | {"verified": True, "created": True, "child_password": "synthetic-child-password"}
    monkeypatch.setattr(probe, "JOURNAL", journal)
    probe.save(data)
    monkeypatch.setattr(
        probe,
        "environment",
        lambda _: {"SMTP_HOST": "smtp.gmail.com", "SMTP_USER": "owner@gmail.com", "SMTP_PASSWORD": "synthetic"},
    )
    monkeypatch.setattr(probe, "connect_mail", lambda _: pytest.fail("Verified cleanup must not call mail"))
    monkeypatch.setattr(sys, "argv", ["beta_live_signup_smoke.py", "--cleanup"])

    class Response:
        status_code = 200

        def __init__(self, value):
            self.value = value

        def json(self):
            return self.value

    class Client:
        def __init__(self, **kwargs):
            self.headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, path, json):
            assert path == "/auth/login" and json["username"] == data["email"]
            return Response(
                {
                    "token": "synthetic",
                    "user": {"id": "parent", "role": "parent", "families": [{"id": "family", "synthetic": False}]},
                }
            )

        def request(self, method, path, json):
            assert method == "DELETE" and path == "/account" and json["password"] == data["password"]
            return Response({"deleted": True})

    monkeypatch.setattr(probe.httpx, "Client", Client)
    probe.main()
    assert not journal.exists()
    report = json.loads(capsys.readouterr().out)
    assert report["production_mail_observed"] is False
    assert "owner@gmail.com" not in json.dumps(report)
