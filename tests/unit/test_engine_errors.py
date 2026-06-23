"""Tests for engine error paths: unreadable data, broken validators, edge cases."""
from __future__ import annotations

import pandas as pd

from akad import engine as eng
from akad.models.result import ClauseStatus, OverallStatus
from akad.readers.parquet_reader import ParquetReader
from tests.conftest import make_contract, make_transactions_df


class ExplodingValidator:
    """Validator that always raises — simulates a buggy custom plugin."""

    def validate(self, df, contract, reader_last_modified):
        raise RuntimeError("validator bug")


class TestEngineReadErrors:
    def test_unsupported_format_returns_error_result(self):
        contract = make_contract()
        # bypass the Literal["parquet", "sql"] check to simulate a future format
        contract.dataset.format = "csv"

        result = eng.validate(contract)

        assert result.overall_status == OverallStatus.ERROR
        assert "Unsupported dataset format" in result.error_message
        assert result.clause_results == []

    def test_unreadable_dataset_returns_error_result(self, tmp_path):
        contract = make_contract(location=str(tmp_path / "missing.parquet"))

        result = eng.validate(contract)

        assert result.overall_status == OverallStatus.ERROR
        assert "Failed to read dataset" in result.error_message

    def test_last_modified_failure_is_tolerated(self, tmp_parquet, monkeypatch):
        """A get_last_modified error must not fail the run — freshness just skips."""
        def boom(self, spec):
            raise OSError("stat failed")

        monkeypatch.setattr(ParquetReader, "get_last_modified", boom)
        contract = make_contract(location=str(tmp_parquet), volume={"min_rows": 1})

        result = eng.validate(contract)

        assert result.overall_status == OverallStatus.COMPLIANT


class TestValidatorExceptionHandling:
    def test_validator_exception_becomes_error_clause(self):
        df = make_transactions_df(5)
        contract = make_contract()

        result = eng.validate_dataframe(df, contract,
                                        extra_validators=[ExplodingValidator()])

        assert result.overall_status == OverallStatus.ERROR
        errors = [c for c in result.clause_results if c.status == ClauseStatus.ERROR]
        assert len(errors) == 1
        assert errors[0].clause_type == "ExplodingValidator"
        assert "validator bug" in errors[0].message

    def test_breach_takes_precedence_over_error(self):
        df = make_transactions_df(2)
        contract = make_contract(volume={"min_rows": 10})  # guaranteed FAIL

        result = eng.validate_dataframe(df, contract,
                                        extra_validators=[ExplodingValidator()])

        assert result.overall_status == OverallStatus.BREACH


class TestEmptyDataset:
    def test_empty_dataframe_skips_quality_rules(self):
        df = pd.DataFrame({"transaction_id": pd.Series([], dtype="object"),
                           "amount":         pd.Series([], dtype="float64")})
        contract = make_contract(
            quality=[{"column": "transaction_id", "max_null_percentage": 0.0}],
        )

        result = eng.validate_dataframe(df, contract)

        quality = [c for c in result.clause_results
                   if c.clause_type.startswith("quality")]
        assert quality == []
        assert result.row_count == 0

    def test_empty_dataframe_still_fails_volume(self):
        df = pd.DataFrame({"transaction_id": pd.Series([], dtype="object")})
        contract = make_contract(volume={"min_rows": 1})

        result = eng.validate_dataframe(df, contract)

        assert result.overall_status == OverallStatus.BREACH
