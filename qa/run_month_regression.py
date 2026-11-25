#!/usr/bin/env python3
"""Run a bounded synthetic month and its named failure scenarios in isolation."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
TESTS = (
    "backend/tests/test_thirty_school_days.py::test_thirty_individual_synthetic_school_days",
    "backend/tests/test_school_preparation.py::test_ocr_failures_need_explicit_retry_and_two_attempts_are_final",
    "backend/tests/test_school_preparation.py::test_new_preparation_after_saved_source_revision_reopens_review",
    "backend/tests/test_school_preparation.py::test_persisted_intent_is_picked_up_after_request_interruption",
    "backend/tests/test_school_preparation.py::test_source_revision_change_during_call_discards_result",
    "backend/tests/test_school_preparation.py::test_midnight_ocr_and_explicit_package_finish_without_a_new_day_time_gate",
    "backend/tests/test_school_preparation.py::test_explicit_package_crosses_midnight_without_discarding_its_units",
    "backend/tests/test_school_day.py::test_voluntary_package_stays_finite_on_free_day_after_time_goal",
    "backend/tests/test_school_day.py::test_confirmed_archived_day_allows_explicit_package_but_no_additional_upload",
    "backend/tests/test_learning_controller.py::test_two_devices_cannot_overwrite_another_draft",
)


def validate_junit(path):
    expected = {test.split("::", 1)[1] for test in TESTS}
    midnight = "test_explicit_package_crosses_midnight_without_discarding_its_units"
    expected.remove(midnight)
    expected.update({f"{midnight}[before]", f"{midnight}[during]"})
    found, seen = set(), set()
    for case in ElementTree.parse(path).getroot().iter("testcase"):
        name = case.get("name", "")
        identity = (case.get("classname"), case.get("name"))
        if (identity in seen or name not in expected
                or any(case.find(tag) is not None for tag in ("skipped", "failure", "error"))):
            raise ValueError("A required month scenario was skipped, failed or unexpected")
        seen.add(identity)
        found.add(name)
    if found != expected:
        raise ValueError("A required month scenario was not executed")


def validate_report(path, dialect):
    report = json.loads(path.read_text())
    days = report["days"]
    if report.get("database") != dialect or len(days) != 30:
        raise ValueError("Month report has wrong database or day count")
    source = ROOT / "backend/tests/test_thirty_school_days.py"
    if report.get("test_sha256") != hashlib.sha256(source.read_bytes()).hexdigest():
        raise ValueError("Month report does not match the test source")
    dates = [date.fromisoformat(day["date"]) for day in days]
    if dates != sorted(set(dates)) or {day["subject"] for day in days} != {"Geographie", "Geschichte"}:
        raise ValueError("Month report does not contain the expected dated synthetic subjects")
    if len({day["page"] for day in days}) != 30 or len({day["unit"] for day in days}) != 30:
        raise ValueError("Month report repeats a source or unit")
    jobs = [job for day in days for job in day["jobs"]]
    if len(jobs) != 120 or len({job["id"] for job in jobs}) != 120:
        raise ValueError("Month report has missing or duplicate jobs")
    if any(job["status"] != "completed" or job["error"] for job in jobs):
        raise ValueError("Month report contains an unsuccessful job")
    unknown = [job for job in jobs if job["cost_micros"] is None]
    if len(unknown) != 1 or unknown[0]["cost_source"] != "unknown":
        raise ValueError("Unknown cost must remain distinct from reported zero")
    if any(day["planned_parts"] != 1 or len(day["attempts"]) != 2 for day in days):
        raise ValueError("A planned unit or its recorded attempts are missing")
    if any([job["kind"] for job in day["jobs"]] != ["extract", "extract", "package", "coach"] for day in days):
        raise ValueError("A day's pipeline has missing or unexpected phases")
    if any(datetime.fromtimestamp(job["created"], timezone.utc).date() != date.fromisoformat(day["date"])
           for day in days for job in day["jobs"]):
        raise ValueError("A job timestamp does not match its simulated school day")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", choices=("sqlite", "postgresql"), default="postgresql")
    parser.add_argument("--output-dir", type=Path, default=Path(tempfile.gettempdir()))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="schuleschlau-month-", dir=args.output_dir))
    environment = {"PATH": os.defpath, "LANG": "C.UTF-8", "TMPDIR": str(scratch),
                   "PYTHONPATH": str(ROOT / "backend"), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    command = ([sys.executable, "scripts/test_postgres.py"] if args.database == "postgresql"
               else [sys.executable, "-m", "pytest", "-q"])
    command += [*TESTS, "--tb=short", "--basetemp", str(scratch / "pytest"),
                "--junitxml", str(scratch / "results.xml")]
    subprocess.run(command, cwd=ROOT, env=environment, check=True)
    validate_junit(scratch / "results.xml")
    candidates = list(scratch.rglob("thirty-school-days.json"))
    if len(candidates) != 1:
        raise ValueError("Expected exactly one synthetic month report")
    validate_report(candidates[0], args.database)
    print(json.dumps({"database": args.database, "days": 30, "report": str(candidates[0]),
                      "junit": str(scratch / "results.xml")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
