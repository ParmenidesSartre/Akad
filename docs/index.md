# Akad

**Akad** (Malay/Arabic: *contract, covenant* — the term for the underlying contract of any Islamic finance product) is a lightweight Python library for defining, enforcing, and monitoring data quality contracts on batch datasets. Built for data engineering pipelines — works standalone, in Airflow, or any Python environment.

```bash
pip install akad-framework
```

## What it does

When a producer pipeline changes a dataset (renames a column, drops rows, adds bad values), downstream consumers break silently. Akad gives you:

- A **contract file** (YAML) that declares what the dataset must look like
- An **enforcement engine** that validates the dataset against the contract at pipeline runtime
- A **registry** that stores contract versions and validation history
- A **CLI** for manual validation and contract management
- A **dashboard** to monitor all contracts across your data platform

## Features

### Validation Rules

| Feature | What it checks |
|---|---|
| **Schema — column existence** | Every declared column is present in the dataset |
| **Schema — column types** | Column dtype matches declared type (`string`, `integer`, `float`, `boolean`, `date`, `timestamp`) |
| **Schema — nullable** | Non-nullable columns have zero null values |
| **Schema — allowed values** | Column contains only the declared set of allowed values |
| **Schema — no extra columns** | Dataset has no undeclared columns (optional, off by default) |
| **Freshness** | Dataset was updated within `max_age_hours`; uses file mtime or `max(check_column)` |
| **Volume** | Row count is within `min_rows` / `max_rows` bounds |
| **Quality — null rate** | Column null percentage does not exceed `max_null_percentage` |
| **Quality — duplicate rate** | Column duplicate percentage does not exceed `max_duplicate_percentage` |
| **Quality — value range** | Column values are within `min_value` / `max_value` bounds |

### Dataset Formats

| Format | How |
|---|---|
| **Parquet** | Local path or S3 via `pyarrow` |
| **SQL** | Any SQLAlchemy-supported database (PostgreSQL, MySQL, SQLite) via `table_name` + `connection_string` |

### Breach Modes

| Mode | Behaviour |
|---|---|
| `on_breach: warn` | Returns result with `is_breach=True`, pipeline continues |
| `on_breach: fail` | Raises `DataContractBreachError`, pipeline halts |

### Notifications

- **Webhook** — POST JSON breach payload to any URL (Slack, Teams, PagerDuty)
- **Email** — SMTP with configurable recipients; password stored in env var, never in YAML

### Registry

- REST API (FastAPI) — publish contracts, fetch by name, list versions, store validation results
- PostgreSQL backend for production; SQLite for local dev
- Interactive API docs at `/docs`

### Observability Dashboard

FastAPI + Jinja2 + Tailwind (CDN, no build step) — overview of all contracts, compliant vs breach counts, per-contract validation history, breach history with status filters, contract discovery/search.

### CLI

- `akad infer` — profile an existing dataset and scaffold a starter contract YAML
- `akad diff` — compare two contract versions, flag breaking vs non-breaking changes (CI-friendly)
- `akad check` — parse and validate YAML syntax without touching data (CI-safe)
- `akad publish` — register a contract version
- `akad validate` — run full validation, exit 1 on breach (CI-friendly)
- `akad list` — list all current contracts in registry
- `akad history` — show recent validation runs for a contract

### Developer Experience

- `validate_dataframe(df, contract)` — skip storage reads in unit tests, pass a DataFrame directly
- Injectable `_http_client` and `_registry_client` — test the full SDK without a real server
- Custom validator plugin API — extend with your own business rules
- Split dependencies — `pip install akad-framework` (core only) keeps Airflow worker environments lean

Continue to [Installation](installation.md) or jump straight to the [Quick Start](quickstart.md).
