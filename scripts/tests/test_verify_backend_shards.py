"""Tests for the aggregation contract without importing the application."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_backend_shards import ContractError, load_artifacts, verify

REVISION = "a" * 40


def summaries():
    expected = ["1" * 64, "2" * 64, "3" * 64]
    return [{
        "version": 1, "kind": "backend_pytest_shard", "source_revision": REVISION,
        "shard_index": i, "shard_count": 3, "collection_count": 6, "collection_sha256": "4" * 64,
        "expected_counts": [1, 2, 3], "expected_sha256": expected[:],
        "selected_count": i + 1, "selected_sha256": expected[i], "executed_count": i + 1,
        "passed_count": i, "skipped_count": 1, "xfailed_count": 0, "xpassed_count": 0, "pytest_exit_code": 0,
    } for i in range(3)]


class BackendReceiptContract(unittest.TestCase):
    def test_artifacts_require_exact_distinct_layout_and_indices(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index, row in enumerate(summaries()):
                shard = root / f"backend-shard-{index}"
                shard.mkdir()
                (shard / f"backend-summary-{index}.json").write_text(json.dumps(row))
            self.assertEqual(load_artifacts(root), summaries())
            extra = root / "backend-shard-3"
            extra.mkdir()
            with self.assertRaises(ContractError):
                load_artifacts(root)
            extra.rmdir()
            receipt = root / "backend-shard-1" / "backend-summary-1.json"
            receipt.write_text(json.dumps(summaries()[0]))
            with self.assertRaises(ContractError):
                load_artifacts(root)
            receipt.unlink()
            with self.assertRaises(ContractError):
                load_artifacts(root)
            receipt.symlink_to(root / "backend-shard-0" / "backend-summary-0.json")
            with self.assertRaises(ContractError):
                load_artifacts(root)

    def test_valid_union_and_visible_skips(self):
        self.assertEqual(verify(summaries(), REVISION, "success"), {
            "collection_count": 6, "passed_count": 3, "skipped_count": 3, "xfailed_count": 0,
            "xpassed_count": 0, "source_revision": REVISION,
        })

    def test_partial_duplicate_or_failed_matrix_is_rejected(self):
        rows = summaries()
        for broken in (rows[:2], rows + rows[:1], [rows[0], rows[0], rows[2]]):
            with self.subTest(broken=broken), self.assertRaises(ContractError):
                verify(broken, REVISION, "success")
        with self.assertRaises(ContractError):
            verify(rows, REVISION, "cancelled")

    def test_coverage_execution_revision_and_collection_must_match(self):
        changes = (
            ("source_revision", "b" * 40), ("collection_sha256", "0" * 64),
            ("collection_count", 5), ("expected_counts", [1, 1, 4]),
            ("expected_sha256", ["5" * 64, "2" * 64, "3" * 64]),
            ("expected_sha256", ["1" * 64, "1" * 64, "3" * 64]),
            ("selected_count", 1), ("selected_sha256", "0" * 64),
            ("executed_count", 1), ("passed_count", 0), ("pytest_exit_code", 1),
            ("version", True), ("shard_index", True),
        )
        for field, value in changes:
            rows = copy.deepcopy(summaries())
            rows[1][field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                verify(rows, REVISION, "success")

    def test_missing_required_values_fail_closed(self):
        for field in summaries()[0]:
            rows = summaries()
            del rows[1][field]
            with self.subTest(field=field), self.assertRaises(ContractError):
                verify(rows, REVISION, "success")
        for bad_revision in ("", "g" * 40, "a" * 39, None):
            with self.subTest(revision=bad_revision), self.assertRaises(ContractError):
                verify(summaries(), bad_revision, "success")


if __name__ == "__main__":
    unittest.main()
