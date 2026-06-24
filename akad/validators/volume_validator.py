from __future__ import annotations

import pandas as pd

from akad.models.contract import DataContract
from akad.models.result import ClauseResult
from akad.validators.base import Validator


class VolumeValidator(Validator):
    def validate(
        self,
        df: pd.DataFrame,
        contract: DataContract,
        _reader_last_modified: float | None,
    ) -> list[ClauseResult]:
        if not contract.volume:
            return []

        results: list[ClauseResult] = []
        row_count = len(df)

        if contract.volume.min_rows is not None:
            results.append(ClauseResult.check(
                "volume.min_rows", None, row_count >= contract.volume.min_rows,
                expected=f">= {contract.volume.min_rows} rows", observed=f"{row_count} rows",
                fail_message=f"Row count {row_count} is below minimum {contract.volume.min_rows}",
            ))

        if contract.volume.max_rows is not None:
            results.append(ClauseResult.check(
                "volume.max_rows", None, row_count <= contract.volume.max_rows,
                expected=f"<= {contract.volume.max_rows} rows", observed=f"{row_count} rows",
                fail_message=f"Row count {row_count} exceeds maximum {contract.volume.max_rows}",
            ))

        return results
