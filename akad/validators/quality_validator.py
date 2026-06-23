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
        reader_last_modified: float | None,
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
                ok = null_pct <= rule.max_null_percentage
                results.append(ClauseResult(
                    clause_type="quality.null_percentage",
                    clause_target=rule.column,
                    status=ClauseStatus.PASS if ok else ClauseStatus.FAIL,
                    expected=f"<= {rule.max_null_percentage}%",
                    observed=f"{null_pct:.2f}%",
                    message="" if ok else
                            f'Column "{rule.column}" null rate {null_pct:.2f}% exceeds {rule.max_null_percentage}%',
                ))

            if rule.max_duplicate_percentage is not None:
                dup_pct = (series.duplicated().sum() / total) * 100
                ok = dup_pct <= rule.max_duplicate_percentage
                results.append(ClauseResult(
                    clause_type="quality.duplicate_percentage",
                    clause_target=rule.column,
                    status=ClauseStatus.PASS if ok else ClauseStatus.FAIL,
                    expected=f"<= {rule.max_duplicate_percentage}%",
                    observed=f"{dup_pct:.2f}%",
                    message="" if ok else
                            f'Column "{rule.column}" duplicate rate {dup_pct:.2f}% exceeds {rule.max_duplicate_percentage}%',
                ))

            if rule.min_value is not None:
                min_obs = series.min()
                ok = min_obs >= rule.min_value
                results.append(ClauseResult(
                    clause_type="quality.min_value",
                    clause_target=rule.column,
                    status=ClauseStatus.PASS if ok else ClauseStatus.FAIL,
                    expected=f">= {rule.min_value}",
                    observed=str(min_obs),
                    message="" if ok else
                            f'Column "{rule.column}" min value {min_obs} is below {rule.min_value}',
                ))

            if rule.max_value is not None:
                max_obs = series.max()
                ok = max_obs <= rule.max_value
                results.append(ClauseResult(
                    clause_type="quality.max_value",
                    clause_target=rule.column,
                    status=ClauseStatus.PASS if ok else ClauseStatus.FAIL,
                    expected=f"<= {rule.max_value}",
                    observed=str(max_obs),
                    message="" if ok else
                            f'Column "{rule.column}" max value {max_obs} exceeds {rule.max_value}',
                ))

        return results
