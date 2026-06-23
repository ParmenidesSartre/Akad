from __future__ import annotations

import pandas as pd

from akad.models.result import ClauseStatus
from akad.validators.quality_validator import QualityValidator
from tests.conftest import make_contract, make_transactions_df


class TestNullPercentage:
    def test_pass_when_null_rate_within_limit(self):
        df = pd.DataFrame({"col": ["a", "b", None, "d"]})  # 25% nulls
        contract = make_contract(quality=[{"column": "col", "max_null_percentage": 50.0}])
        results = QualityValidator().validate(df, contract, None)
        r = [x for x in results if x.clause_type == "quality.null_percentage"][0]
        assert r.status == ClauseStatus.PASS

    def test_fail_when_null_rate_exceeds_limit(self):
        df = pd.DataFrame({"col": [None, None, "c"]})  # 66% nulls
        contract = make_contract(quality=[{"column": "col", "max_null_percentage": 0.0}])
        results = QualityValidator().validate(df, contract, None)
        r = [x for x in results if x.clause_type == "quality.null_percentage"][0]
        assert r.status == ClauseStatus.FAIL

    def test_pass_when_zero_nulls_allowed_and_none_present(self):
        df = pd.DataFrame({"col": ["a", "b", "c"]})
        contract = make_contract(quality=[{"column": "col", "max_null_percentage": 0.0}])
        results = QualityValidator().validate(df, contract, None)
        r = [x for x in results if x.clause_type == "quality.null_percentage"][0]
        assert r.status == ClauseStatus.PASS


class TestDuplicatePercentage:
    def test_pass_when_all_unique(self):
        df = pd.DataFrame({"id": ["A", "B", "C"]})
        contract = make_contract(quality=[{"column": "id", "max_duplicate_percentage": 0.0}])
        results = QualityValidator().validate(df, contract, None)
        r = [x for x in results if x.clause_type == "quality.duplicate_percentage"][0]
        assert r.status == ClauseStatus.PASS

    def test_fail_when_duplicates_exceed_limit(self):
        df = pd.DataFrame({"id": ["A", "A", "C"]})  # ~33% duplicates
        contract = make_contract(quality=[{"column": "id", "max_duplicate_percentage": 0.0}])
        results = QualityValidator().validate(df, contract, None)
        r = [x for x in results if x.clause_type == "quality.duplicate_percentage"][0]
        assert r.status == ClauseStatus.FAIL


class TestValueRange:
    def test_pass_when_values_in_range(self):
        df = pd.DataFrame({"amount": [10.0, 50.0, 100.0]})
        contract = make_contract(quality=[{"column": "amount", "min_value": 1.0, "max_value": 200.0}])
        results = QualityValidator().validate(df, contract, None)
        fails = [r for r in results if r.status == ClauseStatus.FAIL]
        assert not fails

    def test_fail_when_min_value_violated(self):
        df = pd.DataFrame({"amount": [-5.0, 10.0]})
        contract = make_contract(quality=[{"column": "amount", "min_value": 0.01}])
        results = QualityValidator().validate(df, contract, None)
        r = [x for x in results if x.clause_type == "quality.min_value"][0]
        assert r.status == ClauseStatus.FAIL

    def test_fail_when_max_value_violated(self):
        df = pd.DataFrame({"amount": [100.0, 9999999.0]})
        contract = make_contract(quality=[{"column": "amount", "max_value": 10000.0}])
        results = QualityValidator().validate(df, contract, None)
        r = [x for x in results if x.clause_type == "quality.max_value"][0]
        assert r.status == ClauseStatus.FAIL


class TestMissingColumn:
    def test_skipped_when_column_not_found(self):
        df = pd.DataFrame({"other": [1, 2]})
        contract = make_contract(quality=[{"column": "missing_col", "max_null_percentage": 0.0}])
        results = QualityValidator().validate(df, contract, None)
        assert results[0].status == ClauseStatus.SKIPPED


class TestNoQualityRules:
    def test_returns_empty_when_no_rules(self):
        df = make_transactions_df(5)
        contract = make_contract()
        results = QualityValidator().validate(df, contract, None)
        assert results == []
