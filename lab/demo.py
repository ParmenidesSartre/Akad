#!/usr/bin/env python3
"""
Akad End-to-End Test Lab
=======================
Runs a full 8-step workflow against the live Docker services:

  1.  Create clean dataset (500 rows, all valid)
  2.  akad check   — validate contract YAML syntax
  3.  akad publish — register contract in the registry
  4.  akad validate — clean dataset → COMPLIANT
  5.  akad validate — breached dataset (nulls + bad currency) → BREACH
  6.  SDK registry pattern: DataContractValidator(contract_name=...) → COMPLIANT
  7.  akad history — show all validation runs
  8.  akad list    — show registered contracts

Open http://localhost:8501 to see the dashboard after the lab completes.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import httpx
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# ── ANSI colours ──────────────────────────────────────────────────────────────
G = "\033[92m"   # green
R = "\033[91m"   # red
C = "\033[96m"   # cyan
B = "\033[1m"    # bold
D = "\033[2m"    # dim
X = "\033[0m"    # reset

REGISTRY_URL  = "http://registry:8000"
CONTRACT_PATH = Path("/lab/contracts/daily_sales.yaml")
DATA_PATH     = Path("/data/daily_sales.parquet")

DATA_PATH.parent.mkdir(parents=True, exist_ok=True)


# ── output helpers ────────────────────────────────────────────────────────────

def _ok(msg: str) -> None:
    print(f"  {G}✓{X} {msg}")

def _fail(msg: str) -> None:
    print(f"  {R}✗{X} {msg}")

def _info(msg: str) -> None:
    print(f"  {C}→{X} {msg}")

def _header(n: int, title: str) -> None:
    print(f"\n{B}{C}── Step {n}: {title} {'─' * max(0, 50 - len(title))}{X}")

def _cmd(s: str) -> None:
    print(f"  {D}$ {s}{X}")


# ── wait for registry ─────────────────────────────────────────────────────────

def wait_for_registry(max_wait: int = 120) -> None:
    print(f"\n{C}Waiting for registry at {REGISTRY_URL} ...{X}", end="", flush=True)
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            r = httpx.get(f"{REGISTRY_URL}/health/", timeout=3)
            if r.json().get("status") == "ok":
                print(f" {G}ready{X}")
                return
        except Exception:  # noqa: S110 — expected during startup (connection refused until the registry is up)
            pass
        print(".", end="", flush=True)
        time.sleep(2)
    print()
    sys.exit(f"{R}Registry did not start within {max_wait}s — is docker compose up running?{X}")


# ── CLI wrapper ───────────────────────────────────────────────────────────────

def run(args: list[str], *, allow_nonzero: bool = False) -> int:
    _cmd(" ".join(args))
    r = subprocess.run(args, capture_output=True, text=True)  # noqa: S603 — args are hardcoded in this file, never external input
    output = (r.stdout + r.stderr).strip()
    for line in output.splitlines():
        print(f"    {line}")
    if r.returncode != 0 and not allow_nonzero:
        _fail(f"Command exited {r.returncode}")
    return r.returncode


# ── dataset factories ─────────────────────────────────────────────────────────

def write_clean() -> None:
    n = 500
    df = pd.DataFrame({
        "sale_id":       [f"S{i:05d}" for i in range(n)],
        "amount":        [round(10.0 + i * 0.5, 2) for i in range(n)],
        "currency_code": ["MYR"] * 400 + ["USD"] * 60 + ["SGD"] * 40,
        "status":        ["COMPLETED"] * 450 + ["PENDING"] * 30 + ["FAILED"] * 20,
    })
    pq.write_table(pa.Table.from_pandas(df), str(DATA_PATH))
    _ok(f"Written {DATA_PATH}  ({n} rows, currencies: MYR/USD/SGD, all valid)")


def write_breached() -> None:
    n = 500
    df = pd.DataFrame({
        "sale_id":       [f"S{i:05d}" for i in range(n)],
        "amount":        [round(10.0 + i * 0.5, 2) for i in range(n)],
        # 10 rows with JPY — not in allowed_values
        "currency_code": ["MYR"] * 390 + ["USD"] * 60 + ["SGD"] * 40 + ["JPY"] * 10,
        "status":        ["COMPLETED"] * 450 + ["PENDING"] * 30 + ["FAILED"] * 20,
    })
    # 5 null sale_ids — violates max_null_percentage: 0.0
    df.loc[0:4, "sale_id"] = None
    pq.write_table(pa.Table.from_pandas(df), str(DATA_PATH))
    _ok(f"Written {DATA_PATH}  ({n} rows, injected breaches: 5× null sale_id, 10× JPY currency)")  # noqa: RUF001 — decorative output text, not an identifier


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{B}{'═' * 62}")
    print("  Akad — Data Contract Framework — End-to-End Test Lab")
    print(f"{'═' * 62}{X}")
    print(f"  Registry : {REGISTRY_URL}")
    print(f"  Contract : {CONTRACT_PATH}")
    print(f"  Dataset  : {DATA_PATH}")

    wait_for_registry()

    # ── 1. clean data ─────────────────────────────────────────────────────────
    _header(1, "Create clean dataset")
    write_clean()

    # ── 2. check contract syntax ──────────────────────────────────────────────
    _header(2, "Check contract syntax  (no data read)")
    run(["akad", "check", "--contract", str(CONTRACT_PATH)])

    # ── 3. publish to registry ────────────────────────────────────────────────
    _header(3, "Publish contract to registry")
    run(["akad", "publish",
         "--contract",    str(CONTRACT_PATH),
         "--registry-url", REGISTRY_URL])

    # ── 4. validate clean → COMPLIANT ─────────────────────────────────────────
    _header(4, "Validate CLEAN dataset  →  expect COMPLIANT")
    run(["akad", "validate",
         "--contract",    str(CONTRACT_PATH),
         "--registry-url", REGISTRY_URL])

    # ── 5. validate breached → BREACH ─────────────────────────────────────────
    _header(5, "Validate BREACHED dataset  →  expect BREACH")
    write_breached()
    run(["akad", "validate",
         "--contract",    str(CONTRACT_PATH),
         "--registry-url", REGISTRY_URL],
        allow_nonzero=True)   # CLI exits 1 on breach — that's correct

    # ── 6. SDK registry pattern (Airflow) ─────────────────────────────────────
    _header(6, "SDK registry pattern: no local YAML file  →  expect COMPLIANT")
    write_clean()   # restore clean data at the contract's dataset.location
    _info("Equivalent Python (this is what an Airflow task would run):")
    print(f"    {D}from akad import DataContractValidator")
    print("    result = DataContractValidator(")
    print("        contract_name='daily_sales',      # fetched from registry — no local file")
    print(f"        registry_url='{REGISTRY_URL}',")
    print(f"    ).validate(){X}")

    from akad import DataContractValidator
    result = DataContractValidator(
        contract_name="daily_sales",
        registry_url=REGISTRY_URL,
        notifiers=[],
    ).validate()
    colour = G if not result.is_breach else R
    print(f"  {colour}{B}→ {result.overall_status.value}{X}  "
          f"({result.row_count} rows, {len(result.clause_results)} clauses checked)")

    # ── 7. validation history ─────────────────────────────────────────────────
    _header(7, "Validation history  (expect 3 runs)")
    run(["akad", "history",
         "--name",         "daily_sales",
         "--registry-url",  REGISTRY_URL,
         "--limit",         "10"])

    # ── 8. list all contracts ─────────────────────────────────────────────────
    _header(8, "All registered contracts")
    run(["akad", "list", "--registry-url", REGISTRY_URL])

    # ── summary ───────────────────────────────────────────────────────────────
    print(f"\n{B}{G}{'═' * 62}")
    print("  End-to-End Test Lab Complete")
    print(f"{'═' * 62}{X}")
    print(f"\n  {B}Registry API docs:{X}  http://localhost:8000/docs")
    print(f"  {B}Dashboard:        {X}  http://localhost:8501")
    print(f"  {B}Health check:     {X}  http://localhost:8000/health/\n")


if __name__ == "__main__":
    main()
