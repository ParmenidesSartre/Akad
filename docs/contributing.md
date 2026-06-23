# Contributing

Issues and pull requests are welcome.

## Development setup

```bash
git clone https://github.com/ParmenidesSartre/Akad.git
cd Akad

pip install uv
uv sync --all-extras

uv run pytest
```

## Before submitting a change

```bash
uv run pytest                # full suite must pass
uv sync --group lint
uv run ruff check .          # lint
uv run mypy                  # type-check
```

All three run automatically on every push/PR via CI — a PR won't merge cleanly if any of them fail. Please keep new functionality covered by tests — the project maintains ~99% coverage. Unit tests live in `tests/unit/` and should not touch real storage or the network (use `validate_dataframe()` and the injectable `_http_client`/`_registry_client` parameters). Integration tests in `tests/integration/` may use a real SQLite database and a FastAPI `TestClient`.

## Project structure

```
akad/
├── akad/                   # Core package — install this on Airflow workers
│   ├── models/             # Contract and result Pydantic models
│   ├── readers/            # ParquetReader, SQLReader
│   ├── validators/         # Schema, Freshness, Volume, Quality validators
│   ├── notifiers/          # Webhook, Email notifiers
│   ├── engine.py           # Orchestrates readers + validators
│   ├── sdk.py               # DataContractValidator — main public API
│   ├── profiler.py          # akad infer — dataset profiling, starter contract generation
│   ├── cli.py                # akad CLI
│   └── registry_client.py  # HTTP client for the registry
├── registry/               # FastAPI registry service
├── dashboard/              # FastAPI + Jinja2 + Tailwind observability dashboard
├── lab/                    # End-to-end Docker test lab
├── tests/
│   ├── unit/               # Validator unit tests
│   ├── integration/        # Engine + registry API tests
│   └── fixtures/           # Sample contract YAML files
├── contracts/              # Example contracts
├── .github/workflows/      # CI (test + lint), docs deploy, PyPI publish
├── docker-compose.yml
└── pyproject.toml
```

See the [Changelog](https://github.com/ParmenidesSartre/Akad/blob/main/CHANGELOG.md) for release history.

## License

[MIT](https://github.com/ParmenidesSartre/Akad/blob/main/LICENSE) © Faizal Azman
