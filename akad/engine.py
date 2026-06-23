from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from akad.models.contract import DataContract
from akad.models.result import ClauseResult, ClauseStatus, OverallStatus, ValidationResult
from akad.readers.parquet_reader import ParquetReader
from akad.readers.sql_reader import SQLReader
from akad.validators.freshness_validator import FreshnessValidator
from akad.validators.quality_validator import QualityValidator
from akad.validators.schema_validator import SchemaValidator
from akad.validators.volume_validator import VolumeValidator

_READERS = {
    "parquet": ParquetReader,
    "sql":     SQLReader,
}

_DEFAULT_VALIDATORS = [
    SchemaValidator(),
    FreshnessValidator(),
    VolumeValidator(),
    QualityValidator(),
]


def validate(
    contract: DataContract,
    extra_validators: list | None = None,
) -> ValidationResult:
    """Run all validators against the dataset described in *contract*.

    Reads data from storage. Use validate_dataframe() for unit-test-friendly validation
    that skips the read step.
    """
    now = datetime.now(UTC)
    location = str(contract.dataset.location or contract.dataset.table_name or "")

    reader_cls = _READERS.get(contract.dataset.format)
    if not reader_cls:
        return ValidationResult(
            contract_name=contract.metadata.name,
            contract_version=contract.metadata.version,
            dataset_location=location,
            validated_at=now,
            overall_status=OverallStatus.ERROR,
            error_message=f"Unsupported dataset format: {contract.dataset.format}",
        )

    reader = reader_cls()

    try:
        df = reader.read(contract.dataset)
    except Exception as exc:
        return ValidationResult(
            contract_name=contract.metadata.name,
            contract_version=contract.metadata.version,
            dataset_location=location,
            validated_at=now,
            overall_status=OverallStatus.ERROR,
            error_message=f"Failed to read dataset: {exc}",
        )

    try:
        last_modified: float | None = reader.get_last_modified(contract.dataset)
    except Exception:
        last_modified = None

    return validate_dataframe(df, contract, extra_validators, last_modified, _now=now)


def validate_dataframe(
    df: pd.DataFrame,
    contract: DataContract,
    extra_validators: list | None = None,
    reader_last_modified: float | None = None,
    _now: datetime | None = None,
) -> ValidationResult:
    """Run all validators against a pre-loaded DataFrame.

    Designed for unit and integration tests — callers supply the DataFrame directly,
    no storage access needed.
    """
    now = _now or datetime.now(UTC)
    location = str(contract.dataset.location or contract.dataset.table_name or "")

    all_validators = _DEFAULT_VALIDATORS + (extra_validators or [])
    all_clause_results: list[ClauseResult] = []

    for v in all_validators:
        try:
            results = v.validate(df, contract, reader_last_modified)
            all_clause_results.extend(results)
        except Exception as exc:
            all_clause_results.append(ClauseResult(
                clause_type=type(v).__name__,
                clause_target=None,
                status=ClauseStatus.ERROR,
                expected="validator to complete",
                observed="validator raised exception",
                message=str(exc),
            ))

    has_fail  = any(r.status == ClauseStatus.FAIL  for r in all_clause_results)
    has_error = any(r.status == ClauseStatus.ERROR for r in all_clause_results)

    if has_fail:
        overall = OverallStatus.BREACH
    elif has_error:
        overall = OverallStatus.ERROR
    else:
        overall = OverallStatus.COMPLIANT

    return ValidationResult(
        contract_name=contract.metadata.name,
        contract_version=contract.metadata.version,
        dataset_location=location,
        validated_at=now,
        overall_status=overall,
        clause_results=all_clause_results,
        row_count=len(df),
    )
