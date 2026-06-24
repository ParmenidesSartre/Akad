from __future__ import annotations

import pandas as pd

from akad.models.contract import DataContract
from akad.models.result import ClauseResult, ClauseStatus
from akad.validators.base import Validator


class QualityValidator(Validator):
    def validate(
        self,
        df: pd.DataFrame,
        contract: DataContract,
        _reader_last_modified: float | None,
    ) -> list[ClauseResult]:
        results: list[ClauseResult] = []

        for rule in contract.quality:
            if rule.column not in df.columns:
                results.append(ClauseResult(
                    clause_type="quality",
                    clause_target=rule.column,
                    status=ClauseStatus.SKIPPED,
                    expected="column present",
                    observed="column missing",
                    message=f'Quality rule skipped: column "{rule.column}" not found',
                ))
                continue

            series = df[rule.column]
            total  = len(series)
            if total == 0:
                continue

            if rule.max_null_percentage is not None:
                null_pct = (series.isnull().sum() / total) * 100
                results.append(ClauseResult.check(
                    "quality.null_percentage", rule.column, null_pct <= rule.max_null_percentage,
                    expected=f"<= {rule.max_null_percentage}%", observed=f"{null_pct:.2f}%",
                    fail_message=f'Column "{rule.column}" null rate {null_pct:.2f}% exceeds {rule.max_null_percentage}%',
                ))

            if rule.max_duplicate_percentage is not None:
                dup_pct = (series.duplicated().sum() / total) * 100
                results.append(ClauseResult.check(
                    "quality.duplicate_percentage", rule.column, dup_pct <= rule.max_duplicate_percentage,
                    expected=f"<= {rule.max_duplicate_percentage}%", observed=f"{dup_pct:.2f}%",
                    fail_message=f'Column "{rule.column}" duplicate rate {dup_pct:.2f}% exceeds {rule.max_duplicate_percentage}%',
                ))

            if rule.min_value is not None:
                min_obs = series.min()
                results.append(ClauseResult.check(
                    "quality.min_value", rule.column, min_obs >= rule.min_value,
                    expected=f">= {rule.min_value}", observed=str(min_obs),
                    fail_message=f'Column "{rule.column}" min value {min_obs} is below {rule.min_value}',
                ))

            if rule.max_value is not None:
                max_obs = series.max()
                results.append(ClauseResult.check(
                    "quality.max_value", rule.column, max_obs <= rule.max_value,
                    expected=f"<= {rule.max_value}", observed=str(max_obs),
                    fail_message=f'Column "{rule.column}" max value {max_obs} exceeds {rule.max_value}',
                ))

        return results
