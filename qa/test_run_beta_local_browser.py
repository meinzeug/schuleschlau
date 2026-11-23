"""The beta runner may not silently pass skipped or missing browser tests."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("beta_runner", Path(__file__).with_name("run_beta_local_browser.py"))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def report(path, entries):
    path.write_text(
        "<testsuite>"
        + "".join('<testcase name="' + name + '">' + body + "</testcase>" for name, body in entries)
        + "</testsuite>"
    )


def test_runner_requires_each_successful_check(tmp_path):
    path = tmp_path / "result.xml"
    entries = [(name, "") for name in sorted(runner.REQUIRED)]
    report(path, entries)
    runner.validate_results(path)
    report(path, entries[:-1])
    with pytest.raises(RuntimeError):
        runner.validate_results(path)
    report(path, entries + [entries[0]])
    with pytest.raises(RuntimeError):
        runner.validate_results(path)
    for failure in ("<skipped/>", "<failure/>", "<error/>"):
        report(path, [entries[0], (entries[1][0], failure)])
        with pytest.raises(RuntimeError):
            runner.validate_results(path)
