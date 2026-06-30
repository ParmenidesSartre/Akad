from __future__ import annotations

import logging
from typing import Any

import httpx

from akad.models.contract import DataContract
from akad.models.result import ValidationResult

log = logging.getLogger(__name__)


class BreakingChangeRejectedError(Exception):
    """Raised by publish_contract() when the registry rejects a publish
    because it would introduce a breaking change relative to the contract's
    current version. Pass force=True to publish_contract() to override.
    """

    def __init__(self, message: str, breaking_changes: list[dict[str, str]]):
        super().__init__(message)
        self.breaking_changes = breaking_changes


class RegistryClient:
    def __init__(self, base_url: str, _http_client: httpx.Client | None = None):
        self.base_url = base_url.rstrip("/")
        # Injected client is used in tests (ASGI transport); None → real httpx calls
        self._http = _http_client

    # ── internal helpers ──────────────────────────────────────────────────────

    def _get(self, path: str, **kwargs: Any) -> httpx.Response:
        url = f"{self.base_url}{path}"
        if self._http:
            return self._http.get(url, **kwargs)
        return httpx.get(url, **kwargs)

    def _post(self, path: str, **kwargs: Any) -> httpx.Response:
        url = f"{self.base_url}{path}"
        if self._http:
            return self._http.post(url, **kwargs)
        return httpx.post(url, **kwargs)

    # ── public API ────────────────────────────────────────────────────────────

    def get_contract(self, name: str) -> DataContract:
        """Fetch the current version of a contract from the registry by name.

        Raises httpx.HTTPStatusError if the contract is not found (404).
        """
        resp = self._get(f"/contracts/{name}", timeout=10)
        resp.raise_for_status()
        return DataContract.model_validate(resp.json()["content"])

    def get_contract_version(self, name: str, version: str) -> DataContract:
        """Fetch a specific historical version of a contract — used by `akad diff`.

        Raises httpx.HTTPStatusError if that version doesn't exist (404).
        """
        resp = self._get(f"/contracts/{name}/versions/{version}", timeout=10)
        resp.raise_for_status()
        return DataContract.model_validate(resp.json()["content"])

    def publish_contract(self, contract: DataContract, *, force: bool = False) -> None:
        """Publish a contract version. Connectivity failures are swallowed
        (registry being down must never crash a pipeline) but a 409 — the
        registry rejecting a breaking change — is deliberate business logic,
        not a connectivity problem, and is raised as BreakingChangeRejectedError
        rather than silently logged.
        """
        payload = {
            "name":    contract.metadata.name,
            "version": contract.metadata.version,
            "content": contract.model_dump(by_alias=True),
            "force":   force,
        }
        try:
            self._post("/contracts/", json=payload, timeout=10).raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 409:
                detail = exc.response.json().get("detail", {})
                raise BreakingChangeRejectedError(
                    detail.get("message", "Publish rejected: breaking change detected"),
                    detail.get("breaking_changes", []),
                ) from exc
            log.warning("Failed to publish contract to registry: %s", exc)
        except Exception as exc:
            log.warning("Failed to publish contract to registry: %s", exc)

    def post_validation_result(self, result: ValidationResult) -> None:
        try:
            self._post("/validation-results/", json=result.to_dict(), timeout=5).raise_for_status()
        except Exception as exc:
            log.warning("Failed to post result to registry: %s", exc)
