from __future__ import annotations

import pandas as pd

from akad.models.contract import DataContract
from akad.models.result import ClauseResult, ClauseStatus
from akad.validators.base import Validator


class VolumeValidator(Validator):
    def validate(
        self,
        df: pd.DataFrame,
        contract: DataContract,
        reader_last_modified: float | None,
    ) -> list[ClauseResult]:
        if not contract.volume:
            return []

        results: list[ClauseResult] = []
        row_count = len(df)

        if contract.volume.min_rows is not None:
            ok = row_count >= contract.volume.min_rows
            results.append(ClauseResult(
                clause_type="volume.min_rows",
                clause_target=None,
                status=ClauseStatus.PASS if ok else ClauseStatus.FAIL,
                expected=f">= {contract.volume.min_rows} rows",
                observed=f"{row_count} rows",
                message="" if ok else
                        f"Row count {row_count} is below minimum {contract.volume.min_rows}",
            ))

        if contract.volume.max_rows is not None:
            ok = row_count <= contract.volume.max_rows
            results.append(ClauseResult(
                clause_type="volume.max_rows",
                clause_target=None,
                status=ClauseStatus.PASS if ok else ClauseStatus.FAIL,
                expected=f"<= {contract.volume.max_rows} rows",
                observed=f"{row_count} rows",
                message="" if ok else
                        f"Row count {row_count} exceeds maximum {contract.volume.max_rows}",
            ))

        return results
