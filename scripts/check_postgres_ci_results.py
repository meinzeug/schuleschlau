"""Fail closed when the dedicated PostgreSQL concurrency suite did not run."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def verify(path, minimum=13):
    root = ET.parse(path).getroot()
    if root.tag not in {"testsuite", "testsuites"}:
        raise ValueError("Not a JUnit test report")
    cases = root.findall(".//testcase")
    identities = [(case.get("classname"), case.get("name")) for case in cases]
    if len(cases) < minimum or len(set(identities)) != len(cases):
        raise ValueError("The expected distinct PostgreSQL tests did not all run")
    if any(not all(identity) for identity in identities):
        raise ValueError("A PostgreSQL test has no identity")
    if any(next(root.iter(tag), None) is not None for tag in ("skipped", "failure", "error")):
        raise ValueError("A PostgreSQL test was skipped or failed")
    return len(cases)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: check_postgres_ci_results.py REPORT.xml")
    try:
        count = verify(Path(sys.argv[1]))
    except (OSError, ET.ParseError, ValueError) as exc:
        raise SystemExit(f"PostgreSQL results not verified: {exc}") from exc
    print(f"Verified {count} distinct PostgreSQL test cases without skips.")
