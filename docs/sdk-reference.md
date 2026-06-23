# Python SDK Reference

## `DataContractValidator`

```python
from akad import DataContractValidator, DataContractBreachError

# Option A — from local file
validator = DataContractValidator(
    contract_path="contracts/sales.yaml",
    registry_url="http://localhost:8000",   # optional — enables breach history
    extra_validators=[MyValidator()],       # optional plugins
    notifiers=[],                           # [] disables notifications
)

# Option B — from registry by name (Airflow / remote workers)
validator = DataContractValidator(
    contract_name="daily_sales",
    registry_url="http://localhost:8000",
)

result = validator.validate()
```

## `ValidationResult`

```python
result.overall_status      # OverallStatus.COMPLIANT | BREACH | ERROR
result.is_breach           # bool
result.row_count           # int
result.failed_clauses      # List[ClauseResult]

for c in result.failed_clauses:
    print(c.clause_type)   # e.g. "schema.allowed_values"
    print(c.clause_target) # column name
    print(c.message)       # human-readable explanation
```

## `validate_dataframe()` — for unit testing

```python
from akad.engine import validate_dataframe
import pandas as pd

df = pd.DataFrame({"sale_id": ["A", "B"], "amount": [10.0, 20.0]})
result = validate_dataframe(df, contract)
```

## Custom validator plugin

```python
from akad.validators.base import Validator
from akad.models.result import ClauseResult, ClauseStatus

class MyValidator(Validator):
    def validate(self, df, contract, reader_last_modified):
        ok = df["amount"].sum() > 0
        return [ClauseResult(
            clause_type="custom.positive_total",
            clause_target="amount",
            status=ClauseStatus.PASS if ok else ClauseStatus.FAIL,
            expected="> 0",
            observed=str(df["amount"].sum()),
            message="" if ok else "Total amount must be positive",
        )]

DataContractValidator(
    contract_path="contracts/sales.yaml",
    extra_validators=[MyValidator()],
).validate()
```

## `akad.profiler` — programmatic contract inference

The same logic behind [`akad infer`](cli-reference.md#akad-infer-scaffold-a-starter-contract) is available as a library, if you'd rather generate a starter contract from code than the CLI:

```python
import pyarrow.parquet as pq
from akad.profiler import generate_contract, contract_to_yaml_dict

df = pq.read_table("data/daily_sales.parquet").to_pandas()

contract = generate_contract(
    df,
    name="daily_sales",
    dataset_format="parquet",
    owner_team="Data Engineering",
    owner_email="data@example.com",
    location="data/daily_sales.parquet",
)

print(contract_to_yaml_dict(contract))   # dict, ready for yaml.dump()
```

`generate_contract()` returns a fully-validated `DataContract` — same model the rest of the SDK uses — so it can be passed directly to `validate_dataframe()` without a round-trip through YAML. As with the CLI command, treat the result as a starting point: review `allowed_values` and volume bounds before relying on it.

For auto-generated signatures and docstrings, see the [API Reference](api-reference.md).
