from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from akad.contract_loader import load_contract
from akad.registry_client import RegistryClient
from akad import engine as eng

app = typer.Typer(name="akad", help="Akad — Data Contract Framework CLI", no_args_is_help=True)


@app.command()
def validate(
    contract:     Path = typer.Option(..., "--contract", "-c", help="Path to contract YAML"),
    registry_url: Optional[str] = typer.Option(None, "--registry-url", "-r", help="Registry URL"),
    output:       str  = typer.Option("text", "--output", "-o", help="Output format: text|json"),
):
    """Validate a dataset against its contract."""
    from akad.sdk import DataContractValidator, DataContractBreachError

    try:
        validator = DataContractValidator(
            contract_path=contract,
            registry_url=registry_url,
            notifiers=[],  # CLI never sends notifications
        )
        result = validator.validate()
    except DataContractBreachError as exc:
        result = exc.result
        _print_result(result, output)
        raise typer.Exit(code=1)
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=2)

    _print_result(result, output)
    if result.is_breach:
        raise typer.Exit(code=1)


@app.command()
def publish(
    contract:     Path = typer.Option(..., "--contract", "-c", help="Path to contract YAML"),
    registry_url: str  = typer.Option(..., "--registry-url", "-r", help="Registry URL"),
):
    """Publish a contract to the registry."""
    c = load_contract(contract)
    client = RegistryClient(registry_url)
    client.publish_contract(c)
    typer.echo(f"Published {c.metadata.name} v{c.metadata.version}")


@app.command()
def check(
    contract: Path = typer.Option(..., "--contract", "-c", help="Path to contract YAML"),
):
    """Validate contract YAML syntax without accessing data."""
    try:
        c = load_contract(contract)
        typer.echo(f"OK  {c.metadata.name} v{c.metadata.version} — contract is valid")
    except Exception as exc:
        typer.echo(f"FAIL  {exc}", err=True)
        raise typer.Exit(code=1)


@app.command(name="list")
def list_contracts(
    registry_url: str = typer.Option(..., "--registry-url", "-r", help="Registry URL"),
):
    """List all contracts in the registry."""
    import httpx
    try:
        data = httpx.get(f"{registry_url.rstrip('/')}/contracts/", timeout=10).json()
        for c in data:
            status = c.get("is_current", True)
            typer.echo(f"  {c['name']:40s}  v{c['version']}")
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command()
def history(
    name:         str = typer.Option(..., "--name", "-n", help="Contract name"),
    registry_url: str = typer.Option(..., "--registry-url", "-r", help="Registry URL"),
    limit:        int = typer.Option(20, "--limit", "-l", help="Number of results"),
):
    """Show breach history for a contract."""
    import httpx
    try:
        url  = f"{registry_url.rstrip('/')}/validation-results/?contract_name={name}&limit={limit}"
        data = httpx.get(url, timeout=10).json()
        for r in data:
            icon = "✓" if r["overall_status"] == "COMPLIANT" else "✗"
            typer.echo(f"  {icon} {r['validated_at']}  {r['overall_status']}")
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)


def _print_result(result, output: str) -> None:
    if output == "json":
        typer.echo(json.dumps({
            "status":         result.overall_status.value,
            "row_count":      result.row_count,
            "failed_clauses": [c.to_dict() for c in result.failed_clauses],
        }, indent=2))
    else:
        icon = "✓" if result.overall_status.value == "COMPLIANT" else "✗"
        typer.echo(f"{icon} {result.contract_name} v{result.contract_version}: {result.overall_status.value}")
        if result.failed_clauses:
            typer.echo("Failed clauses:")
            for c in result.failed_clauses:
                target = f" [{c.clause_target}]" if c.clause_target else ""
                typer.echo(f"  - [{c.clause_type}]{target} {c.message}")


if __name__ == "__main__":
    app()
