"""Tests for the contract_name flow: publish → fetch from registry → validate.

This is the Airflow pattern — no local contract file needed on the worker.
"""
from __future__ import annotations

import pytest
import httpx

from akad import DataContractValidator, DataContractBreachError
from tests.conftest import make_contract


def _publish(akad_registry_client, name="daily_sales", version="1.0.0", location="/tmp/x.parquet"):
    """Helper: publish a minimal contract to the test registry."""
    contract = make_contract(
        name=name,
        version=version,
        location=location,
        schema_columns=[
            {"name": "transaction_id", "type": "string", "nullable": False},
            {"name": "amount",         "type": "float",  "nullable": False},
        ],
        volume={"min_rows": 1, "max_rows": 1000},
    )
    akad_registry_client.publish_contract(contract)
    return contract


class TestGetContractFromRegistry:
    def test_fetches_published_contract_by_name(self, akad_registry_client):
        _publish(akad_registry_client, "sales_flow")
        contract = akad_registry_client.get_contract("sales_flow")
        assert contract.metadata.name == "sales_flow"
        assert contract.metadata.version == "1.0.0"

    def test_always_returns_current_version(self, akad_registry_client):
        _publish(akad_registry_client, "versioned", version="1.0.0")
        _publish(akad_registry_client, "versioned", version="2.0.0")
        contract = akad_registry_client.get_contract("versioned")
        assert contract.metadata.version == "2.0.0"

    def test_raises_404_for_unknown_contract(self, akad_registry_client):
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            akad_registry_client.get_contract("does_not_exist")
        assert exc_info.value.response.status_code == 404


class TestDataContractValidatorContractName:
    def test_raises_without_path_or_name(self):
        with pytest.raises(ValueError, match="contract_path or contract_name"):
            DataContractValidator()

    def test_raises_with_both_path_and_name(self):
        with pytest.raises(ValueError, match="not both"):
            DataContractValidator(contract_path="x.yaml", contract_name="x")

    def test_raises_contract_name_without_registry_url(self):
        with pytest.raises(ValueError, match="registry_url is required"):
            DataContractValidator(contract_name="daily_sales")

    def test_loads_contract_from_registry_by_name(self, akad_registry_client, tmp_parquet):
        _publish(akad_registry_client, "airflow_sales", location=str(tmp_parquet))

        # This is the Airflow pattern: no contract file on the worker
        validator = DataContractValidator(
            contract_name="airflow_sales",
            registry_url="http://testserver",
            notifiers=[],  # disable notifications in test
            _registry_client=akad_registry_client,
        )
        assert validator.contract.metadata.name == "airflow_sales"
        assert validator.contract.dataset.location == str(tmp_parquet)
