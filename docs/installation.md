# Installation

```bash
pip install akad-framework                   # core — Airflow workers, pipelines
pip install "akad-framework[registry]"       # + registry server
pip install "akad-framework[all]"            # everything
```

The core install (`pip install akad-framework`) pulls in only what a pipeline worker needs to *run validation*: `httpx`, `pandas`, `pyarrow`, `pydantic`, `pyyaml`, `sqlalchemy`, `typer`. The `[registry]` and `[dashboard]` extras add FastAPI, Uvicorn, and the database driver needed to *host* those services — you generally only install those on the machine actually running the registry/dashboard, not on every Airflow worker.

| Extra | Adds | Use case |
|---|---|---|
| *(none)* | Core validation engine + CLI | Airflow workers, any pipeline that calls `DataContractValidator` |
| `[registry]` | FastAPI, Uvicorn, Alembic, psycopg2 | Hosting the contract registry service |
| `[dashboard]` | FastAPI, Jinja2, Uvicorn | Hosting the observability dashboard |
| `[all]` | Both of the above | Local development, the Docker lab |
