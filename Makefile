UV := C:\Users\faiza\AppData\Roaming\Python\Python312\Scripts\uv.exe

.PHONY: install test test-unit test-integration test-cov lint run-registry run-dashboard docker-up docker-down clean

install:
	$(UV) sync

# ── Testing ───────────────────────────────────────────────────────────────────

test:
	$(UV) run pytest

test-unit:
	$(UV) run pytest tests/unit/ -v

test-integration:
	$(UV) run pytest tests/integration/ -v

test-cov:
	$(UV) run pytest --cov=akad --cov-report=html:htmlcov --cov-report=term-missing

test-fast:
	$(UV) run pytest -x -q

# ── Local dev servers ─────────────────────────────────────────────────────────

run-registry:
	$(UV) run uvicorn registry.main:app --reload --port 8000

run-dashboard:
	$(UV) run uvicorn dashboard.main:app --reload --port 8501

# ── Docker ────────────────────────────────────────────────────────────────────

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down -v

# ── Utilities ─────────────────────────────────────────────────────────────────

check-contract:
	$(UV) run akad check --contract $(CONTRACT)

clean:
	Remove-Item -Recurse -Force -ErrorAction SilentlyContinue htmlcov, .coverage, akad_registry.db
