"""The monthly gate must not turn omitted tests or missing costs into success."""

import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from xml.etree import ElementTree

import pytest
from run_month_regression import ROOT, TESTS, validate_junit, validate_report


def write_junit(path, *, omit=False, skip=False, duplicate=False, missing_parameter=False):
    root = ElementTree.Element("testsuite")
    for index, item in enumerate(TESTS):
        if omit and index == 0:
            continue
        name = item.split("::")[1]
        names = [name]
        if name == "test_explicit_package_crosses_midnight_without_discarding_its_units":
            names = [name + "[before]"] if missing_parameter else [name + "[before]", name + "[during]"]
        for case_name in names:
            case = ElementTree.SubElement(root, "testcase", classname=item.split("::")[0], name=case_name)
            if skip and index == 0:
                ElementTree.SubElement(case, "skipped")
            if duplicate and index == 0:
                ElementTree.SubElement(root, "testcase", classname=item.split("::")[0], name=case_name)
    ElementTree.ElementTree(root).write(path)


@pytest.mark.parametrize("fault", ["omit", "skip", "duplicate", "missing_parameter"])
def test_gate_refuses_missing_skipped_or_duplicate_scenarios(tmp_path, fault):
    path = tmp_path / "results.xml"
    write_junit(path, **{fault: True})
    with pytest.raises(ValueError):
        validate_junit(path)
    write_junit(path)
    validate_junit(path)


def make_report():
    days = []
    for i in range(30):
        day = date(2026, 9, 1) + timedelta(days=i)
        jobs = [{"id": f"{i}-{kind}-{index}", "kind": kind, "status": "completed", "error": None,
                 "created": datetime.combine(day, time(hour=12), timezone.utc).timestamp(),
                 "cost_micros": None if i == 6 and kind == "coach" else 0,
                 "cost_source": "unknown" if i == 6 and kind == "coach" else "reported"}
                for index, kind in enumerate(("extract", "extract", "package", "coach"))]
        days.append({"date": day.isoformat(),
                     "subject": "Geographie" if i % 2 == 0 else "Geschichte", "page": f"page-{i}",
                     "unit": f"unit-{i}", "planned_parts": 1, "jobs": jobs,
                     "attempts": [{"outcome": "correct"}, {"outcome": "uncertain"}]})
    source = ROOT / "backend/tests/test_thirty_school_days.py"
    return {"database": "postgresql", "test_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "days": days}


@pytest.mark.parametrize("fault", ["missing_day", "duplicate_job", "unknown_as_zero", "changed_test", "wrong_time"])
def test_gate_refuses_incomplete_or_unverifiable_report(tmp_path, fault):
    report = make_report()
    if fault == "missing_day":
        report["days"].pop()
    elif fault == "duplicate_job":
        report["days"][1]["jobs"][0]["id"] = report["days"][0]["jobs"][0]["id"]
    elif fault == "unknown_as_zero":
        report["days"][6]["jobs"][3]["cost_micros"] = 0
    elif fault == "wrong_time":
        report["days"][0]["jobs"][0]["created"] += 86400
    else:
        report["test_sha256"] = "0" * 64
    path = tmp_path / "month.json"
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError):
        validate_report(path, "postgresql")
    path.write_text(json.dumps(make_report()))
    validate_report(path, "postgresql")
