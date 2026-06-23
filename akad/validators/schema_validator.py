from __future__ import annotations

import pandas as pd

from akad.models.contract import ColumnType, DataContract
from akad.models.result import ClauseResult, ClauseStatus
from akad.validators.base import Validator


def _is_integer_like(s: pd.Series) -> bool:
    """True for real integer dtypes, and for float columns where every
    non-null value is a whole number — pandas promotes an otherwise-integer
    column to float64 as soon as it contains a single null."""
    if pd.api.types.is_integer_dtype(s):
        return True
    if pd.api.types.is_float_dtype(s):
        non_null = s.dropna()
        return non_null.empty or bool((non_null % 1 == 0).all())
    return False


_TYPE_CHECKS = {
    # pandas 3.x uses StringDtype (str(dtype)=="str"); older uses object dtype
    ColumnType.STRING:    lambda s: (
        s.dtype == object
        or str(s.dtype) in ("string", "str")
        or pd.api.types.is_string_dtype(s)
    ),
    ColumnType.INTEGER:   _is_integer_like,
    ColumnType.FLOAT:     lambda s: pd.api.types.is_float_dtype(s),
    ColumnType.BOOLEAN:   lambda s: pd.api.types.is_bool_dtype(s),
    ColumnType.DATE:      lambda s: pd.api.types.is_datetime64_any_dtype(s),
    ColumnType.TIMESTAMP: lambda s: pd.api.types.is_datetime64_any_dtype(s),
    ColumnType.DECIMAL:   lambda s: pd.api.types.is_float_dtype(s),
}


class SchemaValidator(Validator):
    def validate(
        self,
        df: pd.DataFrame,
        contract: DataContract,
        reader_last_modified: float | None,
    ) -> list[ClauseResult]:
        results: list[ClauseResult] = []
        if not contract.schema_:
            return results

        actual_cols = set(df.columns)

        for col in contract.schema_.columns:
            if col.name not in actual_cols:
                results.append(ClauseResult(
                    clause_type="schema.column_exists",
                    clause_target=col.name,
                    status=ClauseStatus.FAIL,
                    expected="column present",
                    observed="column missing",
                    message=f'Column "{col.name}" not found in dataset',
                ))
                continue

            series = df[col.name]

            type_ok = _TYPE_CHECKS[col.type](series)
            results.append(ClauseResult(
                clause_type="schema.column_type",
                clause_target=col.name,
                status=ClauseStatus.PASS if type_ok else ClauseStatus.FAIL,
                expected=col.type.value,
                observed=str(series.dtype),
                message="" if type_ok else
                        f'Column "{col.name}" type mismatch: expected {col.type.value}, got {series.dtype}',
            ))

            if not col.nullable:
                null_count = int(series.isnull().sum())
                null_ok = null_count == 0
                results.append(ClauseResult(
                    clause_type="schema.column_nullable",
                    clause_target=col.name,
                    status=ClauseStatus.PASS if null_ok else ClauseStatus.FAIL,
                    expected="non-nullable (0 nulls)",
                    observed=f"{null_count} nulls found",
                    message="" if null_ok else
                            f'Column "{col.name}" has {null_count} null value(s) but is declared non-nullable',
                ))

            if col.allowed_values is not None:
                invalid = set(series.dropna().unique()) - set(col.allowed_values)
                av_ok = len(invalid) == 0
                results.append(ClauseResult(
                    clause_type="schema.allowed_values",
                    clause_target=col.name,
                    status=ClauseStatus.PASS if av_ok else ClauseStatus.FAIL,
                    expected=f"values in {col.allowed_values}",
                    observed=f"unexpected values: {sorted(invalid)[:10]}",
                    message="" if av_ok else
                            f'Column "{col.name}" contains values not in allowed list: {sorted(invalid)[:10]}',
                ))

        if contract.schema_.enforce_no_extra_columns:
            expected_cols = {c.name for c in contract.schema_.columns}
            extra = actual_cols - expected_cols
            extra_ok = len(extra) == 0
            results.append(ClauseResult(
                clause_type="schema.no_extra_columns",
                clause_target=None,
                status=ClauseStatus.PASS if extra_ok else ClauseStatus.FAIL,
                expected="no extra columns",
                observed=f"extra columns: {sorted(extra)}",
                message="" if extra_ok else f"Unexpected columns found: {sorted(extra)}",
            ))

        return results
