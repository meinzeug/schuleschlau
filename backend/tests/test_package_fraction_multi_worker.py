"""Exercise the real worker/codec with the artificial OCR layout seen live."""

from test_package_fraction_plan_groundwork import OCR_EXPAND, OCR_REDUCE
from test_package_fraction_worker import (
    test_worker_reserves_before_provider_and_checks_before_publication as exercise_worker,
)


def test_two_rule_package_reserves_binds_checks_and_publishes(api, household, monkeypatch):
    exercise_worker(api, household, monkeypatch, [OCR_REDUCE, OCR_EXPAND], 'default', None, 2)
