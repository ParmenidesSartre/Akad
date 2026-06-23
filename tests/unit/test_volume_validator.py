from __future__ import annotations

from akad.models.result import ClauseStatus
from akad.validators.volume_validator import VolumeValidator
from tests.conftest import make_contract, make_transactions_df


class TestVolumeMinRows:
    def test_pass_when_row_count_above_minimum(self):
        df = make_transactions_df(10)
        contract = make_contract(volume={"min_rows": 5})
        results = VolumeValidator().validate(df, contract, None)
        assert results[0].status == ClauseStatus.PASS

    def test_fail_when_row_count_below_minimum(self):
        df = make_transactions_df(3)
        contract = make_contract(volume={"min_rows": 10})
        results = VolumeValidator().validate(df, contract, None)
        assert results[0].status == ClauseStatus.FAIL
        assert "3 rows" in results[0].observed

    def test_pass_at_exact_minimum(self):
        df = make_transactions_df(5)
        contract = make_contract(volume={"min_rows": 5})
        results = VolumeValidator().validate(df, contract, None)
        assert results[0].status == ClauseStatus.PASS


class TestVolumeMaxRows:
    def test_pass_when_row_count_below_maximum(self):
        df = make_transactions_df(10)
        contract = make_contract(volume={"max_rows": 100})
        results = VolumeValidator().validate(df, contract, None)
        assert results[0].status == ClauseStatus.PASS

    def test_fail_when_row_count_above_maximum(self):
        df = make_transactions_df(200)
        contract = make_contract(volume={"max_rows": 100})
        results = VolumeValidator().validate(df, contract, None)
        assert results[0].status == ClauseStatus.FAIL

    def test_both_min_and_max_checked(self):
        df = make_transactions_df(50)
        contract = make_contract(volume={"min_rows": 10, "max_rows": 100})
        results = VolumeValidator().validate(df, contract, None)
        assert len(results) == 2
        assert all(r.status == ClauseStatus.PASS for r in results)


class TestVolumeNoSpec:
    def test_returns_empty_when_no_volume_spec(self):
        df = make_transactions_df(5)
        contract = make_contract()
        results = VolumeValidator().validate(df, contract, None)
        assert results == []
