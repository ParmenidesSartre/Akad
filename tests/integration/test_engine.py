"""Integration tests for the validation engine.

These tests use validate_dataframe() which skips real storage reads,
and test_engine_with_parquet uses tmp_parquet fixture for the full read path.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from akad.engine import validate, validate_dataframe
from akad.models.result import OverallStatus, ClauseStatus
from tests.conftest import make_contract, make_transactions_df


class TestValidateDataframe:
    def test_compliant_result_on_clean_data(self):
        df = make_transactions_df(10)
        contract = make_contract(
            schema_columns=[
                {"name": "transaction_id", "type": "string", "nullable": False},
                {"name": "amount",         "type": "float",  "nullable": False},
                {"name": "currency_code",  "type": "string", "nullable": False,
                 "allowed_values": ["MYR", "USD", "SGD"]},
            ],
            volume={"min_rows": 1, "max_rows": 100},
            quality=[
                {"column": "transaction_id", "max_null_percentage": 0.0},
                {"column": "amount",         "min_value": 0.01},
            ],
        )
        result = validate_dataframe(df, contract)
        assert result.overall_status == OverallStatus.COMPLIANT
        assert result.row_count == 10
        assert not result.failed_clauses

    def test_breach_on_missing_column(self):
        df = pd.DataFrame({"amount": [10.0, 20.0]})
        contract = make_contract(schema_columns=[
            {"name": "amount",         "type": "float"},
            {"name": "transaction_id", "type": "string"},
        ])
        result = validate_dataframe(df, contract)
        assert result.overall_status == OverallStatus.BREACH
        assert result.is_breach
        missing = [c for c in result.failed_clauses if c.clause_type == "schema.column_exists"]
        assert len(missing) == 1

    def test_breach_on_volume_too_low(self):
        df = make_transactions_df(3)
        contract = make_contract(volume={"min_rows": 100})
        result = validate_dataframe(df, contract)
        assert result.overall_status == OverallStatus.BREACH
        vol_fail = [c for c in result.failed_clauses if c.clause_type == "volume.min_rows"]
        assert len(vol_fail) == 1

    def test_breach_on_bad_allowed_values(self):
        df = make_transactions_df(5, bad_currency=True)
        contract = make_contract(schema_columns=[
            {"name": "currency_code", "type": "string", "allowed_values": ["MYR", "USD", "SGD"]},
        ])
        result = validate_dataframe(df, contract)
        assert result.overall_status == OverallStatus.BREACH

    def test_compliant_on_fail_mode_does_not_raise(self):
        df = make_transactions_df(5)
        contract = make_contract(on_breach="fail")
        result = validate_dataframe(df, contract)
        assert result.overall_status == OverallStatus.COMPLIANT

    def test_multiple_breaches_all_reported(self):
        df = pd.DataFrame({"amount": [-999.0]})
        contract = make_contract(
            schema_columns=[
                {"name": "amount",   "type": "float",  "nullable": False},
                {"name": "missing1", "type": "string"},
                {"name": "missing2", "type": "integer"},
            ],
            quality=[{"column": "amount", "min_value": 0.01}],
        )
        result = validate_dataframe(df, contract)
        assert len(result.failed_clauses) >= 3


class TestValidateWithParquetFile:
    def test_validate_reads_parquet_file(self, tmp_parquet: Path):
        contract = make_contract(
            location=str(tmp_parquet),
            schema_columns=[
                {"name": "transaction_id", "type": "string"},
                {"name": "amount",         "type": "float"},
            ],
            volume={"min_rows": 1},
        )
        result = validate(contract)
        assert result.overall_status == OverallStatus.COMPLIANT
        assert result.row_count == 10

    def test_validate_returns_error_on_bad_path(self):
        contract = make_contract(location="/nonexistent/path/data.parquet")
        result = validate(contract)
        assert result.overall_status == OverallStatus.ERROR
        assert result.error_message is not None
