from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from akad.models.contract import DatasetSpec
from akad.readers.base import DataReader, DataReadError


class ParquetReader(DataReader):
    def read(self, spec: DatasetSpec) -> pd.DataFrame:
        try:
            table = pq.read_table(spec.location)
            return table.to_pandas()
        except Exception as exc:
            raise DataReadError(f"Cannot read Parquet at '{spec.location}': {exc}") from exc

    def get_last_modified(self, spec: DatasetSpec) -> float:
        if spec.location is None:
            raise DataReadError("Parquet dataset spec is missing 'location'")
        path = Path(spec.location)
        if path.exists():
            return path.stat().st_mtime
        raise NotImplementedError("S3/remote last-modified requires s3fs configuration")
