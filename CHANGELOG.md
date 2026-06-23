# Changelog

All notable changes to this project are documented here. Format loosely follows [Keep a Changelog](https://keepachangelog.com/), versioning follows [Semantic Versioning](https://semver.org/).

## [1.1.0] - 2026-06-23

### Added
- `akad infer` CLI command — profiles an existing dataset (Parquet or SQL) and scaffolds a starter contract YAML, with inferred schema, volume, and quality rules
- `akad.profiler` module exposing `profile_dataframe()` and `generate_contract()` for programmatic use

## [1.0.0] - 2026-06-23

Initial release as `akad-framework`, renamed from the earlier `datacontract-framework` prototype.

### Added
- Core validation engine: schema, freshness, volume, and quality checks against Parquet and SQL datasets
- `DataContractValidator` SDK with file-based and registry-based contract loading
- FastAPI contract registry with PostgreSQL/SQLite backend
- FastAPI + Jinja2 + Tailwind observability dashboard
- Webhook and email breach notifiers
- `akad` CLI: `check`, `publish`, `validate`, `list`, `history`
- CI/CD pipeline: tests + lint (ruff) + type checks (mypy) on every push, tag-triggered PyPI publish via Trusted Publishing
- MkDocs Material documentation site
