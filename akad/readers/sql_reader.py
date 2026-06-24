from __future__ import annotations

import pandas as pd
from sqlalchemy import create_engine, text

from akad.models.contract import DatasetSpec
from akad.readers.base import DataReader, DataReadError


class SQLReader(DataReader):
    def read(self, spec: DatasetSpec) -> pd.DataFrame:
        if spec.connection_string is None:
            raise DataReadError("SQL dataset spec is missing 'connection_string'")
        try:
            engine = create_engine(spec.connection_string)
            with engine.connect() as conn:
                return pd.read_sql_table(spec.table_name, conn)
        except Exception as exc:
            raise DataReadError(f"Cannot read SQL table '{spec.table_name}': {exc}") from exc

    def get_last_modified(self, spec: DatasetSpec) -> float:
        if not spec.partition_column:
            raise NotImplementedError("SQL freshness requires partition_column in dataset spec")
        if spec.connection_string is None:
            raise DataReadError("SQL dataset spec is missing 'connection_string'")
        if spec.table_name is None:
            raise DataReadError("SQL dataset spec is missing 'table_name'")
        partition_column, table_name = spec.partition_column, spec.table_name

        engine = create_engine(spec.connection_string)
        with engine.connect() as conn:
            # Column/table names can't be bound parameters in standard SQL, so we
            # quote them through the dialect's own identifier preparer instead —
            # this escapes special characters and reserved words the same way
            # SQLAlchemy's query builder would, rather than interpolating raw text.
            quoted_column = conn.dialect.identifier_preparer.quote(partition_column)
            quoted_table = conn.dialect.identifier_preparer.quote(table_name)
            result = conn.execute(
                text(f"SELECT MAX({quoted_column}) FROM {quoted_table}")  # noqa: S608
            )
            val = result.scalar()
            if val is None:
                raise NotImplementedError("partition_column returned NULL — cannot determine freshness")
            # SQLite has no native datetime type — raw SQL returns a string there,
            # while Postgres/MySQL return a real datetime. pd.Timestamp handles both.
            return float(pd.Timestamp(val).timestamp())
