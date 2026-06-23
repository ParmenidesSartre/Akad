from __future__ import annotations

from abc import ABC, abstractmethod

from akad.models.contract import DataContract
from akad.models.result import ValidationResult


class Notifier(ABC):
    @abstractmethod
    def notify(self, contract: DataContract, result: ValidationResult) -> None:
        """Send a breach notification. Must never raise."""
        ...
