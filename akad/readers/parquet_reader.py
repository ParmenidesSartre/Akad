from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq
import pandas as pd

from akad.readers.base import DataReader, DataReadError
from akad.models.contract import DatasetSpec


class ParquetReader(DataReader):
    def read(self, spec: DatasetSpec) -> pd.DataFrame:
        try:
            table = pq.read_table(spec.location)
            return table.to_pandas()
        except Exception as exc:
            raise DataReadError(f"Cannot read Parquet at '{spec.location}': {exc}") from exc

    def get_last_modified(self, spec: DatasetSpec) -> float:
        path = Path(spec.location)
        if path.exists():
            return path.stat().st_mtime
        raise NotImplementedError("S3/remote last-modified requires s3fs configuration")
