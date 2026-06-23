from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from akad.contract_loader import load_contract
from akad.models.result import OverallStatus, ValidationResult
from akad import engine as eng
from akad.notifier import dispatch_notifications
from akad.registry_client import RegistryClient


class DataContractValidator:
    """Main entry point for pipeline integration.

    Two ways to load the contract:

    1. From a local file (dev / CI)::

        DataContractValidator(contract_path="contracts/daily_sales.yaml").validate()

    2. From the registry by name — no local file needed (Airflow workers)::

        DataContractValidator(
            contract_name="daily_sales",
            registry_url="http://akad-registry:8000",
        ).validate()
    """

    def __init__(
        self,
        contract_path: Optional[str | Path] = None,
        contract_name: Optional[str] = None,
        registry_url: Optional[str] = None,
        extra_validators: Optional[List] = None,
        notifiers: Optional[List] = None,
        _registry_client=None,  # injectable RegistryClient — used in tests
    ):
        if contract_path is not None and contract_name is not None:
            raise ValueError("Provide either contract_path or contract_name, not both.")
        if contract_path is None and contract_name is None:
            raise ValueError("One of contract_path or contract_name is required.")

        # Resolve which registry client to use
        if _registry_client is not None:
            self.registry = _registry_client
        elif registry_url:
            self.registry = RegistryClient(registry_url)
        else:
            self.registry = None

        if contract_name is not None:
            if not self.registry:
                raise ValueError("registry_url is required when using contract_name.")
            self.contract = self.registry.get_contract(contract_name)
        else:
            self.contract = load_contract(contract_path)

        self.extra_validators = extra_validators or []
        self._notifiers       = notifiers  # None → use defaults; [] → disable

    def validate(self) -> ValidationResult:
        """Run validation.

        - ``on_breach='warn'``: logs, notifies, returns result.
        - ``on_breach='fail'``: logs, notifies, raises :exc:`DataContractBreachError`.
        """
        result = eng.validate(self.contract, self.extra_validators)

        if result.is_breach or result.overall_status == OverallStatus.ERROR:
            dispatch_notifications(self.contract, result, self._notifiers)

        if self.registry:
            self.registry.post_validation_result(result)

        if result.is_breach and self.contract.on_breach == "fail":
            raise DataContractBreachError(
                f'Contract "{self.contract.metadata.name}" breached. '
                f"{len(result.failed_clauses)} clause(s) failed.",
                result=result,
            )

        return result


class DataContractBreachError(Exception):
    def __init__(self, message: str, result: ValidationResult):
        super().__init__(message)
        self.result = result
