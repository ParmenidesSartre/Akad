from __future__ import annotations

import time

import pandas as pd

from akad.models.result import ClauseStatus
from akad.validators.freshness_validator import FreshnessValidator
from tests.conftest import make_contract


class TestFreshnessViaFileModifiedTime:
    def test_pass_when_file_is_fresh(self):
        df = pd.DataFrame({"x": [1]})
        contract = make_contract(freshness={"max_age_hours": 24})
        recent_ts = time.time() - 3600  # 1 hour ago
        results = FreshnessValidator().validate(df, contract, recent_ts)
        assert results[0].status == ClauseStatus.PASS

    def test_fail_when_file_is_stale(self):
        df = pd.DataFrame({"x": [1]})
        contract = make_contract(freshness={"max_age_hours": 1})
        stale_ts = time.time() - 7200  # 2 hours ago
        results = FreshnessValidator().validate(df, contract, stale_ts)
        assert results[0].status == ClauseStatus.FAIL
        assert "2.0h" in results[0].observed


class TestFreshnessViaCheckColumn:
    def test_pass_when_column_is_recent(self):
        recent = pd.Timestamp.now() - pd.Timedelta(hours=1)
        df = pd.DataFrame({"ts": [recent]})
        contract = make_contract(freshness={"max_age_hours": 24, "check_column": "ts"})
        results = FreshnessValidator().validate(df, contract, None)
        assert results[0].status == ClauseStatus.PASS

    def test_fail_when_column_is_stale(self):
        stale = pd.Timestamp.now() - pd.Timedelta(hours=48)
        df = pd.DataFrame({"ts": [stale]})
        contract = make_contract(freshness={"max_age_hours": 24, "check_column": "ts"})
        results = FreshnessValidator().validate(df, contract, None)
        assert results[0].status == ClauseStatus.FAIL

    def test_skipped_when_no_column_and_no_last_modified(self):
        df = pd.DataFrame({"x": [1]})
        contract = make_contract(freshness={"max_age_hours": 24})
        results = FreshnessValidator().validate(df, contract, None)
        assert results[0].status == ClauseStatus.SKIPPED

    def test_skipped_when_check_column_unparseable_instead_of_raising(self):
        df = pd.DataFrame({"ts": ["not-a-date", "also-not-a-date"]})
        contract = make_contract(freshness={"max_age_hours": 24, "check_column": "ts"})
        results = FreshnessValidator().validate(df, contract, None)
        assert results[0].status == ClauseStatus.SKIPPED

    def test_mixed_parseable_and_unparseable_values_uses_latest_valid(self):
        recent = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=1)
        df = pd.DataFrame({"ts": ["garbage", recent.isoformat()]})
        contract = make_contract(freshness={"max_age_hours": 24, "check_column": "ts"})
        results = FreshnessValidator().validate(df, contract, None)
        assert results[0].status == ClauseStatus.PASS

    def test_naive_and_tz_aware_values_do_not_raise(self):
        naive = pd.Timestamp.now() - pd.Timedelta(hours=1)
        aware = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=2)
        df = pd.DataFrame({"ts": [naive, aware]})
        contract = make_contract(freshness={"max_age_hours": 24, "check_column": "ts"})
        results = FreshnessValidator().validate(df, contract, None)
        assert results[0].status == ClauseStatus.PASS


class TestFreshnessNoSpec:
    def test_returns_empty_when_no_freshness_spec(self):
        df = pd.DataFrame({"x": [1]})
        contract = make_contract()
        results = FreshnessValidator().validate(df, contract, None)
        assert results == []
