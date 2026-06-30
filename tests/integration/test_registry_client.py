"""Integration tests for RegistryClient against the real FastAPI registry app,
plus failure-tolerance tests against an unreachable host.
"""
from __future__ import annotations

import logging
from unittest.mock import patch

import httpx
import pytest

from akad.models.result import ClauseResult, ClauseStatus, OverallStatus
from akad.registry_client import BreakingChangeRejectedError, RegistryClient
from tests.conftest import make_contract, make_validation_result

# Nothing listens here — connection is refused immediately
DEAD_URL = "http://127.0.0.1:9"


class TestPublishContractBreakingChangeGate:
    def test_breaking_change_raises_without_force(self, akad_registry_client):
        akad_registry_client.publish_contract(make_contract(
            name="gated", version="1.0.0",
            schema_columns=[{"name": "id", "type": "string"}, {"name": "region", "type": "string"}],
        ))
        with pytest.raises(BreakingChangeRejectedError) as exc_info:
            akad_registry_client.publish_contract(make_contract(
                name="gated", version="2.0.0",
                schema_columns=[{"name": "id", "type": "string"}],  # region removed
            ))
        assert exc_info.value.breaking_changes == [
            {"path": "schema.columns.region", "message": "column removed"},
        ]

    def test_non_409_http_error_still_swallowed(self, caplog):
        # Any other HTTP error status (e.g. a 500) is unrelated to the
        # breaking-change gate and must stay swallow-and-log, not raise —
        # only a 409 is treated as the deliberate "rejected" business outcome.
        response = httpx.Response(
            status_code=500, request=httpx.Request("POST", "http://x/contracts/"),
        )
        client = RegistryClient("http://x")
        with patch.object(client, "_post", return_value=response), \
             caplog.at_level(logging.WARNING):
            client.publish_contract(make_contract())  # must not raise
        assert "Failed to publish contract" in caplog.text

    def test_breaking_change_succeeds_with_force(self, akad_registry_client):
        akad_registry_client.publish_contract(make_contract(
            name="forced", version="1.0.0",
            schema_columns=[{"name": "id", "type": "string"}, {"name": "region", "type": "string"}],
        ))
        akad_registry_client.publish_contract(make_contract(
            name="forced", version="2.0.0",
            schema_columns=[{"name": "id", "type": "string"}],
        ), force=True)  # must not raise

        contract = akad_registry_client.get_contract("forced")
        assert contract.metadata.version == "2.0.0"


class TestPostValidationResult:
    def test_posted_result_is_queryable(self, akad_registry_client, registry_client):
        result = make_validation_result(
            contract_name="post_test",
            status=OverallStatus.BREACH,
            clauses=[ClauseResult(
                clause_type="volume.min_rows",
                clause_target=None,
                status=ClauseStatus.FAIL,
                expected=">= 100 rows",
                observed="10 rows",
                message="Row count 10 below minimum 100",
            )],
        )

        akad_registry_client.post_validation_result(result)

        data = registry_client.get(
            "/validation-results/?contract_name=post_test"
        ).json()
        assert len(data) == 1
        assert data[0]["contract_name"] == "post_test"
        assert data[0]["overall_status"] == "BREACH"
        assert data[0]["row_count"] == 10

    def test_compliant_and_breach_both_recorded(self, akad_registry_client, registry_client):
        akad_registry_client.post_validation_result(
            make_validation_result(contract_name="mixed", status=OverallStatus.COMPLIANT)
        )
        akad_registry_client.post_validation_result(
            make_validation_result(contract_name="mixed", status=OverallStatus.BREACH)
        )

        data = registry_client.get("/validation-results/?contract_name=mixed").json()
        statuses = {r["overall_status"] for r in data}
        assert statuses == {"COMPLIANT", "BREACH"}


class TestFailureTolerance:
    """Registry being down must never break a pipeline run."""

    def test_post_result_swallows_connection_error(self, caplog):
        client = RegistryClient(DEAD_URL)
        with caplog.at_level(logging.WARNING):
            client.post_validation_result(make_validation_result())  # must not raise
        assert "Failed to post result" in caplog.text

    def test_publish_contract_swallows_connection_error(self, caplog):
        client = RegistryClient(DEAD_URL)
        with caplog.at_level(logging.WARNING):
            client.publish_contract(make_contract())  # must not raise
        assert "Failed to publish contract" in caplog.text

    def test_get_contract_propagates_connection_error(self):
        # Fetching the contract is load-bearing — this one MUST raise
        with pytest.raises(httpx.HTTPError):
            RegistryClient(DEAD_URL).get_contract("daily_sales")

    def test_get_contract_version_propagates_connection_error(self):
        with pytest.raises(httpx.HTTPError):
            RegistryClient(DEAD_URL).get_contract_version("daily_sales", "1.0.0")


class TestBaseUrlNormalisation:
    def test_trailing_slash_is_stripped(self):
        client = RegistryClient("http://localhost:8000/")
        assert client.base_url == "http://localhost:8000"
