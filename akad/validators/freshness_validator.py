from __future__ import annotations

import time
from typing import List, Optional

import pandas as pd

from akad.models.contract import DataContract
from akad.models.result import ClauseResult, ClauseStatus
from akad.validators.base import Validator


class FreshnessValidator(Validator):
    def validate(
        self,
        df: pd.DataFrame,
        contract: DataContract,
        reader_last_modified: Optional[float],
    ) -> List[ClauseResult]:
        if not contract.freshness:
            return []

        spec = contract.freshness
        now  = time.time()

        if spec.check_column and spec.check_column in df.columns:
            # utc=True normalizes naive AND tz-aware values to a common
            # timezone, so the result doesn't depend on server-local time.
            # errors="coerce" turns unparseable values into NaT instead of
            # raising, so one bad date string can't crash the whole run.
            max_val = pd.to_datetime(df[spec.check_column], errors="coerce", utc=True).max()
            if pd.isna(max_val):
                return [ClauseResult(
                    clause_type="freshness",
                    clause_target=spec.check_column,
                    status=ClauseStatus.SKIPPED,
                    expected=f"age <= {spec.max_age_hours}h",
                    observed="no parseable date values",
                    message=f'Column "{spec.check_column}" has no parseable date values',
                )]
            last_ts = max_val.timestamp()
            method  = f"max({spec.check_column})"
        elif reader_last_modified is not None:
            last_ts = reader_last_modified
            method  = "file last-modified time"
        else:
            return [ClauseResult(
                clause_type="freshness",
                clause_target=None,
                status=ClauseStatus.SKIPPED,
                expected=f"age <= {spec.max_age_hours}h",
                observed="could not determine last update time",
                message="No check_column and no file modification time available",
            )]

        age_hours = (now - last_ts) / 3600
        fresh = age_hours <= spec.max_age_hours

        return [ClauseResult(
            clause_type="freshness",
            clause_target=None,
            status=ClauseStatus.PASS if fresh else ClauseStatus.FAIL,
            expected=f"age <= {spec.max_age_hours}h (via {method})",
            observed=f"age = {age_hours:.1f}h",
            message="" if fresh else
                    f"Dataset is {age_hours:.1f}h old, exceeds max_age_hours={spec.max_age_hours}",
        )]
