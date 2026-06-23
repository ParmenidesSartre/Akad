from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from akad.models.contract import DatasetSpec


class DataReadError(Exception):
    """Raised when a DataReader cannot load the requested dataset."""


class DataReader(ABC):
    @abstractmethod
    def read(self, spec: DatasetSpec) -> pd.DataFrame:
        """Read the dataset and return a DataFrame. Raise DataReadError on failure."""
        ...

    @abstractmethod
    def get_last_modified(self, spec: DatasetSpec) -> float:
        """Return Unix epoch of last modification. Raise NotImplementedError if unsupported."""
        ...
