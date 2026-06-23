"""Integration tests for the Akad Registry REST API.

Uses an in-memory SQLite database (no PostgreSQL required).
The registry_client fixture from conftest.py wires everything up.
"""
from __future__ import annotations

from datetime import UTC, datetime


class TestHealthEndpoint:
    def test_health_returns_ok(self, registry_client):
        resp = registry_client.get("/health/")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestContractPublish:
    def _payload(self, name="test_contract", version="1.0.0"):
        return {
            "name":    name,
            "version": version,
            "content": {
                "apiVersion": "datacontract/v1",
                "kind":       "DataContract",
                "metadata":   {
                    "name": name, "version": version,
                    "owner": {"team": "T", "email": "t@t.com"},
                },
                "dataset":   {"format": "parquet", "location": "/tmp/x.parquet"},
                "on_breach": "warn",
            },
        }

    def test_publish_returns_201(self, registry_client):
        resp = registry_client.post("/contracts/", json=self._payload())
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "test_contract"
        assert data["version"] == "1.0.0"
        assert data["is_current"] is True

    def test_publish_new_version_marks_old_as_not_current(self, registry_client):
        registry_client.post("/contracts/", json=self._payload("my_contract", "1.0.0"))
        registry_client.post("/contracts/", json=self._payload("my_contract", "2.0.0"))

        resp = registry_client.get("/contracts/my_contract")
        assert resp.status_code == 200
        assert resp.json()["version"] == "2.0.0"

    def test_publish_duplicate_version_overwrites(self, registry_client):
        registry_client.post("/contracts/", json=self._payload("dupe", "1.0.0"))
        resp = registry_client.post("/contracts/", json=self._payload("dupe", "1.0.0"))
        assert resp.status_code == 201


class TestContractRetrieval:
    def _publish(self, client, name="api_contract", version="1.0.0"):
        client.post("/contracts/", json={
            "name": name, "version": version,
            "content": {"apiVersion": "datacontract/v1", "kind": "DataContract",
                        "metadata": {"name": name, "version": version,
                                     "owner": {"team": "T", "email": "t@t.com"}},
                        "dataset": {"format": "parquet", "location": "/tmp/x.parquet"},
                        "on_breach": "warn"},
        })

    def test_list_returns_current_contracts(self, registry_client):
        self._publish(registry_client, "c1")
        self._publish(registry_client, "c2")
        resp = registry_client.get("/contracts/")
        assert resp.status_code == 200
        names = [c["name"] for c in resp.json()]
        assert "c1" in names and "c2" in names

    def test_get_by_name(self, registry_client):
        self._publish(registry_client, "named_contract")
        resp = registry_client.get("/contracts/named_contract")
        assert resp.status_code == 200
        assert resp.json()["name"] == "named_contract"

    def test_get_nonexistent_returns_404(self, registry_client):
        resp = registry_client.get("/contracts/does_not_exist")
        assert resp.status_code == 404

    def test_list_versions(self, registry_client):
        self._publish(registry_client, "versioned", "1.0.0")
        self._publish(registry_client, "versioned", "2.0.0")
        resp = registry_client.get("/contracts/versioned/versions")
        assert resp.status_code == 200
        versions = [c["version"] for c in resp.json()]
        assert "1.0.0" in versions and "2.0.0" in versions


class TestValidationResults:
    def _result_payload(self, contract_name="test", status="COMPLIANT"):
        return {
            "contract_name":    contract_name,
            "contract_version": "1.0.0",
            "dataset_location": "/tmp/x.parquet",
            "validated_at":     datetime.now(UTC).isoformat(),
            "overall_status":   status,
            "row_count":        100,
            "clause_results":   [],
            "error_message":    None,
        }

    def test_store_result_returns_201(self, registry_client):
        resp = registry_client.post("/validation-results/", json=self._result_payload())
        assert resp.status_code == 201
        data = resp.json()
        assert data["overall_status"] == "COMPLIANT"

    def test_list_results(self, registry_client):
        registry_client.post("/validation-results/", json=self._result_payload("c1", "COMPLIANT"))
        registry_client.post("/validation-results/", json=self._result_payload("c1", "BREACH"))
        resp = registry_client.get("/validation-results/?contract_name=c1")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_result_by_id(self, registry_client):
        post_resp = registry_client.post("/validation-results/", json=self._result_payload())
        rid = post_resp.json()["id"]
        resp = registry_client.get(f"/validation-results/{rid}")
        assert resp.status_code == 200

    def test_get_nonexistent_result_returns_404(self, registry_client):
        resp = registry_client.get("/validation-results/99999")
        assert resp.status_code == 404

    def test_list_with_limit(self, registry_client):
        for i in range(5):
            registry_client.post("/validation-results/", json=self._result_payload(f"c{i}"))
        resp = registry_client.get("/validation-results/?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) == 2
