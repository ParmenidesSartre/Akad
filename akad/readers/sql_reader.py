from __future__ import annotations

import pandas as pd
from sqlalchemy import create_engine, text

from akad.readers.base import DataReader, DataReadError
from akad.models.contract import DatasetSpec


class SQLReader(DataReader):
    def read(self, spec: DatasetSpec) -> pd.DataFrame:
        try:
            engine = create_engine(spec.connection_string)
            with engine.connect() as conn:
                return pd.read_sql_table(spec.table_name, conn)
        except Exception as exc:
            raise DataReadError(f"Cannot read SQL table '{spec.table_name}': {exc}") from exc

    def get_last_modified(self, spec: DatasetSpec) -> float:
        if not spec.partition_column:
            raise NotImplementedError("SQL freshness requires partition_column in dataset spec")
        engine = create_engine(spec.connection_string)
        with engine.connect() as conn:
            result = conn.execute(
                text(f"SELECT MAX({spec.partition_column}) FROM {spec.table_name}")
            )
            val = result.scalar()
            if val is None:
                raise NotImplementedError("partition_column returned NULL — cannot determine freshness")
            return val.timestamp()
