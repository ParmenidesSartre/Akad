# Quick Start

## 1. Write a contract

```yaml
# contracts/sales.yaml
apiVersion: datacontract/v1
kind: DataContract
metadata:
  name: daily_sales
  version: "1.0.0"
  owner:
    team: Data Engineering
    email: data@example.com
dataset:
  format: parquet
  location: /data/sales/daily.parquet
on_breach: warn
schema:
  columns:
    - name: sale_id
      type: string
      nullable: false
    - name: amount
      type: float
      nullable: false
    - name: currency_code
      type: string
      allowed_values: [MYR, USD, SGD]
volume:
  min_rows: 1000
quality:
  - column: sale_id
    max_null_percentage: 0.0
    max_duplicate_percentage: 0.0
```

## 2. Validate

```bash
akad validate --contract contracts/sales.yaml
# ✓ daily_sales v1.0.0: COMPLIANT

# On breach:
# ✗ daily_sales v1.0.0: BREACH
# Failed clauses:
#   - [schema.allowed_values] [currency_code] Contains values not in allowed list: ['JPY']
```

That's the whole loop: declare what the data must look like, then check it against reality. See [Workflow](workflow.md) for wiring this into a registry and a real pipeline.
