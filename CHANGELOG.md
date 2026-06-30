# Changelog

All notable changes to this project are documented here. Format loosely follows [Keep a Changelog](https://keepachangelog.com/), versioning follows [Semantic Versioning](https://semver.org/).

## [1.4.0] - 2026-06-30

### Added
- `ConsumerSpec.depends_on` — a consumer can now declare which specific contract guarantees it relies on (e.g. `schema.columns.currency_code`, `quality.amount.max_value`), using the same path vocabulary `akad diff` already produces
- `akad diff` cross-references every detected change against the old contract's consumers and annotates each `DiffEntry` with `affected_consumers` — turning "this is breaking" into "this will break Fraud Detection's currency check," before the change ships. Matching works in both directions: depending on a whole column/rule is flagged when a sub-attribute changes, and depending on one specific sub-rule is still flagged if the whole thing is removed.
- Purely additive: a consumer with no `depends_on` declared behaves exactly as before, and existing breach-notification behavior is unchanged

## [1.3.0] - 2026-06-24

### Added
- `business_rules` contract section — cross-column and conditional checks that column-level Schema/Quality rules can't express (e.g. `status != 'COMPLETED' or ship_date.notnull()`, `end_date >= start_date`). Backed by pandas' own restricted expression evaluator (`df.eval(..., engine="python")`), not Python's `eval()` — no access to builtins, imports, or arbitrary function calls. A malformed expression becomes an `ERROR` clause rather than crashing the run.
- `akad diff` now understands `business_rules`: a removed rule is breaking, an added rule is non-breaking, and a changed expression is conservatively always breaking (strictness can't be inferred statically from arbitrary code).
- `akad.profiler.contract_to_yaml_dict()` now also serializes `business_rules` when present, for round-trip completeness (note: `akad infer` itself never generates business rules — there's no reliable way to derive cross-column logic from a data sample).

## [1.2.1] - 2026-06-23

Code-quality hardening pass — no new features, no behavior changes for existing users.

### Changed
- Expanded the `ruff` lint ruleset to include security (`S`), performance (`PERF`), unused-argument (`ARG`), complexity (`C901`), naming (`N`), pathlib (`PTH`), and ruff-specific (`RUF`) checks, with a per-path exception for `tests/` where bare `assert` and placeholder `/tmp/...` paths are the established idiom, not a real risk
- `DataContract.api_version` renamed from `apiVersion` (still aliased to the `apiVersion` YAML key — the contract format on disk is unchanged) for consistency with every other snake_case field, mirroring the existing `schema_`/`schema` alias
- `SQLReader.get_last_modified()` now quotes the dynamic column/table identifiers through SQLAlchemy's own `identifier_preparer` instead of raw f-string interpolation, and gained an explicit guard for a missing `table_name`
- Reduced `akad cli.py`'s `diff` command below the complexity threshold by extracting its argument-validation/loading logic into `_load_diff_contracts()`
- Various conciseness fixes surfaced by the expanded linting: comprehensions instead of manual append loops in `akad.differ` and the email notifier, `next()` instead of a single-element list slice in tests, dead `contract` parameter removed from `_build_email_body()`

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
