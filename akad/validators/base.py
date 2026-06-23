from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from akad.models.contract import DataContract
from akad.models.result import ClauseResult


class Validator(ABC):
    @abstractmethod
    def validate(
        self,
        df: pd.DataFrame,
        contract: DataContract,
        reader_last_modified: float | None,
    ) -> list[ClauseResult]:
        """Evaluate clauses. Never raise — catch internally and return ERROR ClauseResult."""
        ...
