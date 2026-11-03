"""Verify the three actual backend CI partitions belong to one collection.

This checks coverage of the collected pytest nodes, including explicit skips;
it does not claim those skips passed or replace dedicated PostgreSQL checks.
"""

import json
import os
import re
import sys
from pathlib import Path


class ContractError(ValueError):
    pass


def verify(rows, revision, job_result):
    if job_result != "success":
        raise ContractError("backend matrix did not succeed")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ContractError("invalid expected revision")
    if len(rows) != 3 or any(not isinstance(row, dict) for row in rows):
        raise ContractError("exactly three shard summaries required")
    indices = [row.get("shard_index") for row in rows]
    if any(type(index) is not int for index in indices) or sorted(indices) != [0, 1, 2]:
        raise ContractError("missing or duplicate shard")
    common = None
    for row in rows:
        index = row["shard_index"]
        if (row.get("kind") != "backend_pytest_shard" or type(row.get("version")) is not int
                or row["version"] != 1 or type(row.get("shard_count")) is not int
                or row["shard_count"] != 3 or row.get("source_revision") != revision
                or type(row.get("pytest_exit_code")) is not int or row["pytest_exit_code"] != 0):
            raise ContractError("invalid shard metadata")
        counts = row.get("expected_counts")
        hashes = row.get("expected_sha256")
        if (not isinstance(counts, list) or len(counts) != 3
                or any(type(count) is not int or count <= 0 for count in counts)
                or not isinstance(hashes, list) or len(hashes) != 3
                or any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value) for value in hashes)
                or len(set(hashes)) != 3
                or not isinstance(row.get("collection_sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", row["collection_sha256"])):
            raise ContractError("invalid collection facts")
        collection_count = row.get("collection_count")
        if type(collection_count) is not int or collection_count != sum(counts):
            raise ContractError("collection count mismatch")
        facts = (collection_count, row["collection_sha256"], tuple(counts), tuple(hashes))
        if common is not None and facts != common:
            raise ContractError("backend shard collections differ")
        common = facts
        executed = row.get("executed_count")
        passed = row.get("passed_count")
        skipped = row.get("skipped_count")
        xfailed = row.get("xfailed_count")
        xpassed = row.get("xpassed_count")
        if (any(type(value) is not int or value < 0 for value in (executed, passed, skipped, xfailed, xpassed))
                or row.get("selected_count") != counts[index]
                or type(row.get("selected_count")) is not int
                or row.get("selected_sha256") != hashes[index]
                or executed != counts[index] or passed + skipped + xfailed + xpassed != executed):
            raise ContractError("selected backend tests were not completely executed")
    return {"collection_count": common[0], "passed_count": sum(r["passed_count"] for r in rows),
            "skipped_count": sum(r["skipped_count"] for r in rows),
            "xfailed_count": sum(r["xfailed_count"] for r in rows),
            "xpassed_count": sum(r["xpassed_count"] for r in rows), "source_revision": revision}


def load_artifacts(directory):
    """Require the exact output layout of three non-merged workflow artifacts."""
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ContractError("backend artifact directory missing or invalid")
    expected_dirs = {f"backend-shard-{index}" for index in range(3)}
    if {path.name for path in directory.iterdir()} != expected_dirs:
        raise ContractError("missing or unexpected backend artifacts")
    rows = []
    for index in range(3):
        shard = directory / f"backend-shard-{index}"
        expected_file = f"backend-summary-{index}.json"
        if shard.is_symlink() or not shard.is_dir() or {path.name for path in shard.iterdir()} != {expected_file}:
            raise ContractError("invalid backend artifact layout")
        receipt = shard / expected_file
        if receipt.is_symlink() or not receipt.is_file() or receipt.stat().st_size > 16384:
            raise ContractError("invalid backend artifact receipt")
        row = json.loads(receipt.read_text(encoding="utf-8"))
        if not isinstance(row, dict) or type(row.get("shard_index")) is not int or row["shard_index"] != index:
            raise ContractError("backend artifact is labelled with the wrong shard")
        rows.append(row)
    return rows


def main():
    try:
        if len(sys.argv) != 2:
            raise ContractError("expected artifact directory argument")
        rows = load_artifacts(sys.argv[1])
        result = verify(rows, os.environ.get("GITHUB_SHA", ""), os.environ.get("BACKEND_JOB_RESULT", ""))
    except (OSError, UnicodeError, json.JSONDecodeError, ContractError) as exc:
        raise SystemExit(f"Backend shard verification failed: {exc}") from exc
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
