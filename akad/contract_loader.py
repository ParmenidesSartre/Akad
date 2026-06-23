from __future__ import annotations

from pathlib import Path

import yaml

from akad.models.contract import DataContract


def load_contract(path: str | Path) -> DataContract:
    """Load and validate a contract YAML file.

    Raises pydantic.ValidationError with clear messages if the file is invalid.
    """
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return DataContract.model_validate(raw)
