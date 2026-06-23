from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional


class ClauseStatus(str, Enum):
    PASS    = "PASS"
    FAIL    = "FAIL"
    SKIPPED = "SKIPPED"
    ERROR   = "ERROR"


class OverallStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    BREACH    = "BREACH"
    ERROR     = "ERROR"


@dataclass
class ClauseResult:
    clause_type:   str
    clause_target: Optional[str]
    status:        ClauseStatus
    expected:      Any
    observed:      Any
    message:       str

    def to_dict(self) -> dict:
        """JSON-safe dict matching the registry's ClauseResultSchema."""
        return {
            "clause_type":   self.clause_type,
            "clause_target": self.clause_target,
            "status":        self.status.value,
            "expected":      str(self.expected),
            "observed":      str(self.observed),
            "message":       self.message,
        }


@dataclass
class ValidationResult:
    contract_name:    str
    contract_version: str
    dataset_location: str
    validated_at:     datetime
    overall_status:   OverallStatus
    clause_results:   List[ClauseResult] = field(default_factory=list)
    row_count:        Optional[int] = None
    error_message:    Optional[str] = None

    @property
    def is_breach(self) -> bool:
        return self.overall_status == OverallStatus.BREACH

    @property
    def failed_clauses(self) -> List[ClauseResult]:
        return [c for c in self.clause_results if c.status == ClauseStatus.FAIL]

    def to_dict(self) -> dict:
        """JSON-safe dict matching the registry's ValidationResultRequest payload."""
        return {
            "contract_name":    self.contract_name,
            "contract_version": self.contract_version,
            "dataset_location": self.dataset_location,
            "validated_at":     self.validated_at.isoformat(),
            "overall_status":   self.overall_status.value,
            "row_count":        self.row_count,
            "clause_results":   [c.to_dict() for c in self.clause_results],
            "error_message":    self.error_message,
        }
