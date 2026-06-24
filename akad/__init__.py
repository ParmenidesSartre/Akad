"""Akad — Data Contract Framework.

Public API::

    from akad import DataContractValidator, DataContractBreachError
"""
from akad.sdk import DataContractBreachError, DataContractValidator

__all__ = ["DataContractValidator", "DataContractBreachError"]
__version__ = "1.2.0"
