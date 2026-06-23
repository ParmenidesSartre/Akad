"""Tests for ParquetReader and SQLReader — storage access and error wrapping."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine

from akad.models.contract import DatasetSpec
from akad.readers.base import DataReadError
from akad.readers.parquet_reader import ParquetReader
from akad.readers.sql_reader import SQLReader
from tests.conftest import make_transactions_df


class TestParquetReader:
    def test_reads_dataframe(self, tmp_parquet):
        spec = DatasetSpec(format="parquet", location=str(tmp_parquet))
        df = ParquetReader().read(spec)
        assert len(df) == 10
        assert "transaction_id" in df.columns

    def test_missing_file_raises_data_read_error(self, tmp_path):
        spec = DatasetSpec(format="parquet", location=str(tmp_path / "missing.parquet"))
        with pytest.raises(DataReadError, match="Cannot read Parquet"):
            ParquetReader().read(spec)

    def test_corrupt_file_raises_data_read_error(self, tmp_path):
        bad = tmp_path / "corrupt.parquet"
        bad.write_text("this is not parquet")
        spec = DatasetSpec(format="parquet", location=str(bad))
        with pytest.raises(DataReadError):
            ParquetReader().read(spec)

    def test_last_modified_uses_file_mtime(self, tmp_parquet):
        spec = DatasetSpec(format="parquet", location=str(tmp_parquet))
        mtime = ParquetReader().get_last_modified(spec)
        assert mtime == pytest.approx(Path(tmp_parquet).stat().st_mtime)

    def test_last_modified_missing_file_raises(self, tmp_path):
        spec = DatasetSpec(format="parquet", location=str(tmp_path / "missing.parquet"))
        with pytest.raises(NotImplementedError):
            ParquetReader().get_last_modified(spec)

    def test_last_modified_missing_location_raises_data_read_error(self):
        spec = DatasetSpec(format="parquet")
        with pytest.raises(DataReadError, match="missing 'location'"):
            ParquetReader().get_last_modified(spec)


class TestSQLReader:
    @pytest.fixture()
    def sqlite_spec(self, tmp_path) -> DatasetSpec:
        """SQLite database file with a populated transactions table."""
        conn_str = f"sqlite:///{tmp_path / 'test.db'}"
        make_transactions_df(8).to_sql(
            "transactions", create_engine(conn_str), index=False
        )
        return DatasetSpec(
            format="sql", connection_string=conn_str, table_name="transactions"
        )

    def test_reads_table(self, sqlite_spec):
        df = SQLReader().read(sqlite_spec)
        assert len(df) == 8
        assert list(df.columns) == ["transaction_id", "amount", "currency_code", "status"]

    def test_missing_table_raises_data_read_error(self, sqlite_spec):
        spec = sqlite_spec.model_copy(update={"table_name": "no_such_table"})
        with pytest.raises(DataReadError, match="no_such_table"):
            SQLReader().read(spec)

    def test_bad_connection_string_raises_data_read_error(self):
        spec = DatasetSpec(format="sql", connection_string="not-a-url", table_name="t")
        with pytest.raises(DataReadError):
            SQLReader().read(spec)

    def test_missing_connection_string_raises_data_read_error(self):
        spec = DatasetSpec(format="sql", table_name="t")
        with pytest.raises(DataReadError, match="missing 'connection_string'"):
            SQLReader().read(spec)

    def test_last_modified_requires_partition_column(self, sqlite_spec):
        with pytest.raises(NotImplementedError, match="partition_column"):
            SQLReader().get_last_modified(sqlite_spec)

    def test_last_modified_missing_connection_string_raises_data_read_error(self):
        spec = DatasetSpec(format="sql", table_name="t", partition_column="updated_at")
        with pytest.raises(DataReadError, match="missing 'connection_string'"):
            SQLReader().get_last_modified(spec)

    def test_last_modified_returns_max_partition_timestamp(self, tmp_path):
        conn_str = f"sqlite:///{tmp_path / 'fresh.db'}"
        df = pd.DataFrame({"updated_at": pd.to_datetime(["2024-01-01", "2024-06-15"])})
        df.to_sql("fresh_table", create_engine(conn_str), index=False)
        spec = DatasetSpec(
            format="sql",
            connection_string=conn_str,
            table_name="fresh_table",
            partition_column="updated_at",
        )
        last_modified = SQLReader().get_last_modified(spec)
        assert last_modified == pytest.approx(pd.Timestamp("2024-06-15").timestamp())

    def test_last_modified_null_partition_raises(self, tmp_path):
        conn_str = f"sqlite:///{tmp_path / 'empty.db'}"
        pd.DataFrame({"updated_at": pd.Series([], dtype="datetime64[ns]")}).to_sql(
            "empty_table", create_engine(conn_str), index=False
        )
        spec = DatasetSpec(
            format="sql",
            connection_string=conn_str,
            table_name="empty_table",
            partition_column="updated_at",
        )
        with pytest.raises(NotImplementedError, match="NULL"):
            SQLReader().get_last_modified(spec)
