# Changelog

All notable changes to this project are documented here. Format loosely follows [Keep a Changelog](https://keepachangelog.com/), versioning follows [Semantic Versioning](https://semver.org/).

## [1.2.0] - 2026-06-23

### Added
- `akad diff` CLI command — compares two contract versions (two local files, or two versions already published to the registry) and classifies every change as breaking or non-breaking for a consumer relying on the old contract
- `akad.differ` module exposing `diff_contracts()` for programmatic use
- `RegistryClient.get_contract_version(name, version)` — fetch a specific historical contract version, not just the current one

### Fixed
- CLI commands using the ✓/✗ status icons (`validate`, `check`, `history`, `diff`) could crash with `UnicodeEncodeError` on a non-UTF-8 console (e.g. the `cp1252` default on many Windows setups); output is now forced to UTF-8

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
