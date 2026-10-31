"""Project-only health watchdog with optional neutral operator email.

This runs independently of the API/worker. It cannot detect loss of the whole
host; scripts/watch_public.py supplies the independent-host check.
"""

import argparse
import json
import os
import re
import shlex
import shutil
import smtplib
import ssl
import subprocess
import time
import urllib.request
from email.message import EmailMessage
from pathlib import Path

RESTORE_MAX_AGE = 14 * 86400
RESTORE_TABLES = ("families", "children", "materials", "learning_units", "attempts", "unit_coaching")


def disk_space_low(disk):
    """Compare used space to usable space, including reserved blocks correctly."""
    usable = disk.used + disk.free
    return disk.free < 1024**3 or usable <= 0 or disk.used / usable > 0.9


def restore_status(report_path, setup_path, now):
    """Return a neutral failure code and whether initial setup is still pending."""
    try:
        report = json.loads(report_path.read_text())
    except FileNotFoundError:
        try:
            started = int(setup_path.read_text().strip())
            if 0 < started <= now and now - started <= RESTORE_MAX_AGE:
                return None, True
        except (OSError, UnicodeError, ValueError):
            pass
        return "restore_rehearsal_missing", False
    except (OSError, UnicodeError, ValueError):
        return "restore_rehearsal_invalid", False

    def count(value):
        return type(value) is int and value >= 0

    if not isinstance(report, dict):
        return "restore_rehearsal_invalid", False
    checked = report.get("checked_at")
    complete = (
        type(checked) is int and 0 < checked <= now
        and isinstance(report.get("backup"), str)
        and re.fullmatch(r"\d{8}T\d{6}Z\.tar\.enc", report["backup"]) is not None
        and isinstance(report.get("schema"), str) and bool(report["schema"].strip())
        and report.get("production_overwritten") is False
        and all(report.get(key) is True for key in ("authenticated_restore", "sessions_revoked", "ai_emergency_stop"))
        and all(count(report.get(key)) for key in ("verified_erasure_records", "orphan_images_removed", "erasure_images_removed"))
        and all(
            isinstance(report.get(group), dict) and all(count(report[group].get(table)) for table in RESTORE_TABLES)
            for group in ("before", "after")
        )
    )
    if not complete:
        return "restore_rehearsal_invalid", False
    if now - checked > RESTORE_MAX_AGE:
        return "restore_rehearsal_stale", False
    return None, False


def environment(path):
    values = {}
    for line in Path(path).read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key] = " ".join(shlex.split(value)) if value else ""
    return values


def notify(config, failures, previous, path, *, dry_run=False):
    fingerprint = ",".join(sorted(failures))
    stamp = int(time.time())
    should_send = fingerprint != previous.get("fingerprint", "") or (
        failures and stamp - previous.get("sent", 0) > 21600
    )
    if not failures and not previous.get("sent"):
        should_send = False
    state = {"checked_at": stamp, "fingerprint": fingerprint, "failures": failures, "sent": previous.get("sent", 0)}
    recipient = config.get("OPERATIONS_ALERT_EMAIL", "")
    if should_send and recipient and not dry_run:
        message = EmailMessage()
        message["Subject"] = (
            "SCHULPILOT: Betriebsprüfung fehlgeschlagen" if failures else "SCHULPILOT: Betrieb wieder erreichbar"
        )
        if config.get("ALERT_TEST_TOKEN"):
            message.replace_header("Subject", "TEST SCHULPILOT Alarmtest " + config["ALERT_TEST_TOKEN"])
        message["From"] = config["SMTP_FROM"]
        message["To"] = recipient
        message.set_content(
            "Technische Prüfungen: " + (fingerprint or "wieder erfolgreich") + ". Keine Lerninhalte enthalten."
        )
        if config.get("ALERT_TEST_TOKEN"):
            message.set_content(
                "Dies ist ein ausdrücklich ausgelöster technischer Alarmtest von SCHULPILOT. Es liegt keine gemeldete Betriebsstörung vor. Testkennung: "
                + config["ALERT_TEST_TOKEN"]
            )
        try:
            mode = config.get("SMTP_MODE", "starttls")
            context = ssl.create_default_context()
            if mode not in ("tls", "starttls"):
                raise ValueError("TLS configuration required")
            server = (
                smtplib.SMTP_SSL(config["SMTP_HOST"], int(config.get("SMTP_PORT", "465")), timeout=15, context=context)
                if mode == "tls"
                else smtplib.SMTP(config["SMTP_HOST"], int(config.get("SMTP_PORT", "587")), timeout=15)
            )
            with server:
                if mode == "starttls":
                    server.starttls(context=context)
                if config.get("SMTP_USER"):
                    server.login(config["SMTP_USER"], config["SMTP_PASSWORD"])
                server.send_message(message)
            state["sent"] = stamp
        except Exception as error:
            # Keep the previous fingerprint so the next scheduled check retries
            # the alert, independently of application mail delivery.
            state["fingerprint"] = previous.get("fingerprint", "")
            state["alert_error"] = "smtp_" + type(error).__name__
            if isinstance(getattr(error, "smtp_code", None), int):
                state["smtp_code"] = error.smtp_code
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        partial = path.with_suffix(".partial")
        partial.write_text(json.dumps(state) + "\n")
        partial.chmod(0o600)
        partial.replace(path)
    return state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    config = environment("/etc/schulpilot/environment")
    failures = []
    for service in ("schulpilot-api", "schulpilot-worker", "schulpilot-backup.timer"):
        if subprocess.run(["systemctl", "is-active", "--quiet", service]).returncode:
            failures.append(service + "_inactive")
    try:
        with urllib.request.urlopen("http://127.0.0.1:3240/api/health", timeout=10) as response:
            if response.status != 200:
                failures.append("api_health")
    except Exception:
        failures.append("api_health")
    try:
        result = subprocess.run(
            [
                "runuser",
                "-u",
                "schulpilot",
                "--",
                "/opt/schulpilot/current/venv/bin/python",
                "-m",
                "schulpilot.operations",
            ],
            cwd="/opt/schulpilot/current/backend",
            env={**config, "PATH": "/usr/sbin:/usr/bin:/sbin:/bin"},
            timeout=20,
            capture_output=True,
            check=True,
            text=True,
        )
        metrics = json.loads(result.stdout)
        if metrics["worker_age_seconds"] is None or metrics["worker_age_seconds"] > 240:
            failures.append("worker_heartbeat")
        if metrics["stalled_queued"] or metrics["stalled_running"]:
            failures.append("jobs_stalled")
        if metrics["pending_erasure_journal"]:
            failures.append("erasure_journal_pending")
    except Exception:
        failures.append("database_metrics")
    backups = list(Path("/var/backups/schulpilot").glob("*.tar.enc"))
    if not backups or time.time() - max(p.stat().st_mtime for p in backups) > 30 * 3600:
        failures.append("backup_stale")
    restore = Path("/var/backups/schulpilot-monitor/restore-check.json")
    if Path("/etc/schulpilot/offsite-enabled").exists():
        marker = Path("/var/backups/schulpilot-monitor/offsite-last-success.json")
        try:
            offsite_checked = json.loads(marker.read_text())["checked_at"]
            offsite_fresh = type(offsite_checked) is int and 0 < offsite_checked <= time.time() and time.time() - offsite_checked <= 3600
        except (OSError, UnicodeError, ValueError, TypeError, KeyError):
            offsite_fresh = False
        if not offsite_fresh:
            failures.append("offsite_copy_stale")
    if subprocess.run(["systemctl", "is-failed", "--quiet", "schulpilot-restore-check.service"]).returncode == 0:
        failures.append("restore_rehearsal_failed")
    restore_failure, restore_initializing = restore_status(
        restore, restore.with_name("restore-setup-started"), time.time()
    )
    if restore_failure:
        failures.append(restore_failure)
    disk = shutil.disk_usage("/var/lib/schulpilot")
    if disk_space_low(disk):
        failures.append("disk_space")
    path = Path("/var/backups/schulpilot-monitor/state.json")
    try:
        previous = json.loads(path.read_text())
        if not isinstance(previous, dict) or not isinstance(previous.get("fingerprint", ""), str) or type(previous.get("sent", 0)) is not int:
            previous = {}
    except (OSError, UnicodeError, ValueError):
        previous = {}
    state = notify(config, failures, previous, path, dry_run=args.dry_run)
    print(
        json.dumps(
            {
                "failures": failures,
                "alert_configured": bool(config.get("OPERATIONS_ALERT_EMAIL")),
                "dry_run": args.dry_run,
                "alert_error": state.get("alert_error"),
                "restore_rehearsal_initializing": restore_initializing,
            }
        )
    )
    return bool(failures or state.get("alert_error"))


if __name__ == "__main__":
    raise SystemExit(main())
