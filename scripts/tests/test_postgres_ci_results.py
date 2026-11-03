"""The concurrency gate cannot pass on skipped or incomplete reports."""

import importlib.util
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "check_postgres_ci_results.py"
spec = importlib.util.spec_from_file_location("postgres_ci_results", path)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class PostgresCiResultsTest(unittest.TestCase):
    def test_valid_report_and_rejected_incomplete_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "results.xml"
            cases = [f'<testcase classname="suite" name="case{i}" />' for i in range(13)]
            cases += [f'<testcase classname="suite" name="{name}" />' for name in sorted(check.REQUIRED_NOTICE_TESTS)]
            classname, name = check.REQUIRED_EXAM_ROLE_TEST
            cases += [f'<testcase classname="{classname}" name="{name}" />']

            def write(rows):
                report.write_text("<testsuites><testsuite>" + "".join(rows) + "</testsuite></testsuites>")

            write(cases)
            self.assertEqual(check.verify(report), 20)
            for invalid in (
                cases[:-1],
                cases[:-1] + [cases[0]],
                cases[:-1] + ['<testcase classname="suite" name="skipped"><skipped /></testcase>'],
                cases[:-1] + ['<testcase classname="suite" name="failed"><failure /></testcase>'],
                cases[:-1] + ['<testcase classname="suite" name="errored"><error /></testcase>'],
                cases[:-1] + ['<testcase classname="suite" />'],
                cases[:-1] + ['<testcase classname="suite" name="replacement" />'],
                cases[:-1] + [f'<testcase classname="other.suite" name="{name}" />'],
            ):
                with self.subTest(invalid=invalid[-1]), self.assertRaises(ValueError):
                    write(invalid)
                    check.verify(report)
            report.write_text("<unrelated />")
            with self.assertRaises(ValueError):
                check.verify(report)
            report.write_text("<testsuite>")
            with self.assertRaises(ET.ParseError):
                check.verify(report)
            with self.assertRaises(FileNotFoundError):
                check.verify(Path(directory) / "missing.xml")


if __name__ == "__main__":
    unittest.main()
