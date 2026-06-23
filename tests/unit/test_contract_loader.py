from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from pydantic import ValidationError

from akad.contract_loader import load_contract
from akad.models.contract import DataContract


def _write_contract(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "contract.yaml"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


class TestLoadContractValid:
    def test_loads_minimal_contract(self, tmp_path):
        p = _write_contract(tmp_path, """
            apiVersion: datacontract/v1
            kind: DataContract
            metadata:
              name: test
              version: '1.0.0'
              owner:
                team: Team A
                email: a@example.com
            dataset:
              format: parquet
              location: /tmp/test.parquet
            on_breach: warn
        """)
        contract = load_contract(p)
        assert isinstance(contract, DataContract)
        assert contract.metadata.name == "test"
        assert contract.metadata.version == "1.0.0"
        assert contract.on_breach == "warn"

    def test_loads_full_contract_fixture(self):
        fixture = Path(__file__).parent.parent / "fixtures" / "contracts" / "valid_transactions.yaml"
        contract = load_contract(fixture)
        assert contract.metadata.name == "daily_transactions"
        assert contract.schema_ is not None
        assert len(contract.schema_.columns) == 4
        assert contract.volume is not None
        assert len(contract.quality) == 2


class TestLoadContractInvalid:
    def test_raises_on_missing_owner(self, tmp_path):
        p = _write_contract(tmp_path, """
            apiVersion: datacontract/v1
            kind: DataContract
            metadata:
              name: broken
              version: '1.0.0'
            dataset:
              format: parquet
              location: /tmp/x.parquet
            on_breach: warn
        """)
        with pytest.raises(ValidationError):
            load_contract(p)

    def test_raises_on_invalid_format(self, tmp_path):
        p = _write_contract(tmp_path, """
            apiVersion: datacontract/v1
            kind: DataContract
            metadata:
              name: broken
              version: '1.0.0'
              owner:
                team: T
                email: t@t.com
            dataset:
              format: csv    # not supported
              location: /tmp/x.csv
            on_breach: warn
        """)
        with pytest.raises(ValidationError):
            load_contract(p)

    def test_raises_on_invalid_on_breach(self, tmp_path):
        p = _write_contract(tmp_path, """
            apiVersion: datacontract/v1
            kind: DataContract
            metadata:
              name: broken
              version: '1.0.0'
              owner:
                team: T
                email: t@t.com
            dataset:
              format: parquet
              location: /tmp/x.parquet
            on_breach: maybe   # invalid
        """)
        with pytest.raises(ValidationError):
            load_contract(p)

    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_contract(tmp_path / "nonexistent.yaml")
