"""Synthetic OSV responses cannot silently truncate a dependency audit."""

import importlib.util
import sys
from pathlib import Path

import pytest

scripts = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(scripts))
spec = importlib.util.spec_from_file_location("audit_maven_osv", scripts / "audit_maven_osv.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sys.path.remove(str(scripts))


def test_pagination_keeps_results_bound_to_their_original_package():
    calls = []

    def send(body):
        calls.append(body)
        if len(calls) == 1:
            return {"results": [{"vulns": [{"id": "A"}], "next_page_token": "next"}, {}]}
        assert body["queries"][0]["package"]["name"] == "org:first"
        assert body["queries"][0]["page_token"] == "next"
        return {"results": [{"vulns": [{"id": "B"}]}]}

    result = module.collect([("org:first", "1"), ("org:second", "2")], send)
    assert result == {("org:first", "1"): {"A", "B"}, ("org:second", "2"): set()}


@pytest.mark.parametrize("reply", [{}, {"results": []}, {"results": [None]},
    {"results": [{"vulns": [None]}]}, {"results": [{"next_page_token": True}]}])
def test_incomplete_or_invalid_response_cannot_be_passed_as_zero_hits(reply):
    with pytest.raises(ValueError):
        module.collect([("org:sample", "1")], lambda _: reply)


def test_repeated_pagination_token_is_rejected():
    with pytest.raises(ValueError, match="page token"):
        module.collect([("org:sample", "1")], lambda _: {"results": [{"next_page_token": "loop"}]})
