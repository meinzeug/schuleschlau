"""One owned production beta signup and real email verification, without AI.

Only a freshly generated plus-address of the configured test mailbox is used.
A mode-0600 recovery journal is written *before* registration and is removed
only after the test family has been deleted through its authenticated API.
This does not approve beta applications or claim a complete learning journey.
"""

import argparse
import email
import imaplib
import json
import os
import re
import secrets
import ssl
import sys
import tempfile
import time
from email import policy
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "deploy"))
from monitor import environment  # noqa: E402

BASE = "https://schuleschlau.dorfspy.de/api"
JOURNAL = Path.home() / ".local/share/schulpilot-operations/beta-live-signup.json"
HEADERS = {"X-Schulpilot-Request": "1", "X-Client-Platform": "native"}
ALIAS = re.compile(r"^[^+@]+\+schuleschlau-beta-qa-[a-f0-9]{20}@(gmail|googlemail)\.com$", re.I)
CHILD = re.compile(r"^beta-qa-[a-f0-9]{20}$")


def save(value):
    JOURNAL.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".beta-live-", dir=JOURNAL.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as target:
            json.dump(value, target)
            target.flush()
            os.fsync(target.fileno())
        os.replace(name, JOURNAL)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def owned(value, config):
    email_address = value.get("email", "")
    child_name = value.get("child", "")
    smtp_address = config.get("SMTP_USER", "")
    local, sep, domain = smtp_address.partition("@")
    base = local.split("+", 1)[0]
    return bool(
        sep
        and ALIAS.fullmatch(email_address)
        and CHILD.fullmatch(child_name)
        and email_address.lower().startswith(base.lower() + "+schuleschlau-beta-qa-")
        and email_address.lower().endswith("@" + domain.lower())
        and isinstance(value.get("password"), str)
        and len(value["password"]) >= 24
    )


def connect_mail(config):
    mailbox = imaplib.IMAP4_SSL("imap.gmail.com", 993, ssl_context=ssl.create_default_context(), timeout=15)
    mailbox.login(config["SMTP_USER"], config["SMTP_PASSWORD"])
    return mailbox


def confirmation(config, alias):
    deadline = time.monotonic() + 75
    while time.monotonic() < deadline:
        with connect_mail(config) as mailbox:
            mailbox.select("INBOX", readonly=True)
            status, values = mailbox.uid("search", None, "HEADER", "To", '"' + alias + '"')
            if status == "OK":
                for identifier in values[0].split()[-5:]:
                    _, chunks = mailbox.uid("fetch", identifier, "(BODY.PEEK[])")
                    raw = next((part[1] for part in chunks if isinstance(part, tuple)), b"")
                    message = email.message_from_bytes(raw, policy=policy.default)
                    if alias.lower() not in str(message.get("To", "")).lower():
                        continue
                    plain = "\n".join(
                        part.get_content() for part in message.walk() if part.get_content_type() == "text/plain"
                    )
                    found = re.search(
                        r"https://(?:schuleschlau|schulpilot)\.dorfspy\.de/verify#token=([A-Za-z0-9_-]{32,128})", plain
                    )
                    if found:
                        return found.group(1)
        time.sleep(2)
    raise RuntimeError("Verification message was not observed; recovery journal retained")


def expect(response, status):
    if response.status_code != status:
        raise RuntimeError(f"{response.request.url.path}: HTTP {response.status_code}, expected {status}")
    return response.json()


def login(api, data):
    body = expect(api.post("/auth/login", json={"username": data["email"], "password": data["password"]}), 200)
    user = body["user"]
    families = user.get("families", [])
    if user.get("role") != "parent" or len(families) != 1 or families[0].get("synthetic") is not False:
        raise RuntimeError("Refusing cleanup: unexpected account scope")
    if data.get("user_id") and data["user_id"] != user.get("id"):
        raise RuntimeError("Refusing cleanup: account identity changed")
    data["user_id"], data["family_id"] = user["id"], families[0]["id"]
    save(data)
    api.headers["Authorization"] = "Bearer " + body["token"]
    return user


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cleanup", action="store_true", help="Recover only this script’s journalled account")
    args = parser.parse_args()
    config = environment(Path.home() / ".local/share/schulpilot-operations/monitor.env")
    if config.get("SMTP_HOST") != "smtp.gmail.com" or not config.get("SMTP_USER") or not config.get("SMTP_PASSWORD"):
        raise RuntimeError("The configured owned Gmail test mailbox is required")
    if args.cleanup:
        if not JOURNAL.is_file() or JOURNAL.is_symlink() or JOURNAL.stat().st_mode & 0o077:
            raise RuntimeError("Private recovery journal unavailable")
        data = json.loads(JOURNAL.read_text())
    else:
        if JOURNAL.exists():
            raise RuntimeError("Resolve the existing test journal first")
        local, domain = config["SMTP_USER"].split("@", 1)
        nonce = secrets.token_hex(10)
        data = {
            "email": local.split("+", 1)[0] + "+schuleschlau-beta-qa-" + nonce + "@" + domain,
            "password": secrets.token_urlsafe(30),
            "child": "beta-qa-" + nonce,
            "child_password": secrets.token_urlsafe(30),
            "verified": False,
            "created": False,
        }
    if not owned(data, config):
        raise RuntimeError("Refusing non-owned or non-generated account")
    # A verified account can always be cleaned up even if the mailbox is
    # temporarily unavailable. Fresh or unverified accounts still need mail.
    if not args.cleanup or not data.get("verified"):
        with connect_mail(config) as mailbox:
            status, _ = mailbox.select("INBOX", readonly=True)
            if status != "OK":
                raise RuntimeError("Owned test mailbox is not readable")
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=35, follow_redirects=False) as api:
        if not args.cleanup:
            catalog = expect(api.get("/store/catalog"), 200)
            if catalog.get("beta", {}).get("enabled") is not True:
                raise RuntimeError("Beta is not currently enabled")
            save(data)
            expect(
                api.post(
                    "/auth/register",
                    json={
                        "email": data["email"],
                        "password": data["password"],
                        "display_name": "Künstlicher Beta-Test",
                        "family_name": "Künstliche Beta-Testfamilie",
                        "adult_consent": True,
                        "beta_requested": True,
                    },
                ),
                201,
            )
            data["created"] = True
            save(data)
        if not data.get("verified"):
            code = confirmation(config, data["email"])
            data["mail_observed"] = True
            expect(api.post("/auth/verify", json={"token": code}), 200)
            data["verified"] = True
            save(data)
        login(api, data)
        if not args.cleanup:
            status = expect(api.get(f"/families/{data['family_id']}/beta-application"), 200)
            if status.get("status") != "pending":
                raise RuntimeError("Unexpected beta application state")
            child = expect(
                api.post(
                    f"/families/{data['family_id']}/children",
                    json={
                        "display_name": "Künstliches Testkind",
                        "username": data["child"],
                        "password": data["child_password"],
                        "grade": 6,
                        "subjects": ["Mathematik"],
                    },
                ),
                201,
            )
            with httpx.Client(base_url=BASE, headers=HEADERS, timeout=35, follow_redirects=False) as device:
                result = expect(
                    device.post("/auth/login", json={"username": data["child"], "password": data["child_password"]}),
                    200,
                )
                if result["user"].get("role") != "child" or result["user"].get("child_id") != child["id"]:
                    raise RuntimeError("Unexpected child identity")
        expect(api.request("DELETE", "/account", json={"password": data["password"]}), 200)
        JOURNAL.unlink()
    print(
        json.dumps(
            {
                "owned_beta_account_verified_and_deleted": True,
                "production_mail_observed": data.get("mail_observed") is True,
                "child_login_checked": not args.cleanup,
                "admin_approval_tested": False,
                "ai_calls": 0,
                "cleanup_only": args.cleanup,
            }
        )
    )


if __name__ == "__main__":
    main()
