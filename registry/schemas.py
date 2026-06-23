from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ContractPublishRequest(BaseModel):
    name:    str
    version: str
    content: Dict[str, Any]


class ContractSummary(BaseModel):
    id:           int
    name:         str
    version:      str
    published_at: datetime
    is_current:   bool

    model_config = {"from_attributes": True}


class ContractDetail(ContractSummary):
    content: Dict[str, Any]

    model_config = {"from_attributes": True}


class ClauseResultSchema(BaseModel):
    clause_type:   str
    clause_target: Optional[str]
    status:        str
    expected:      str
    observed:      str
    message:       str


class ValidationResultRequest(BaseModel):
    contract_name:    str
    contract_version: str
    dataset_location: str
    validated_at:     datetime
    overall_status:   str
    row_count:        Optional[int]   = None
    clause_results:   List[ClauseResultSchema]
    error_message:    Optional[str]   = None


class ValidationResultSummary(BaseModel):
    id:               int
    contract_name:    str
    contract_version: str
    dataset_location: str
    validated_at:     datetime
    overall_status:   str
    row_count:        Optional[int]
    error_message:    Optional[str]

    model_config = {"from_attributes": True}


class ValidationResultDetail(ValidationResultSummary):
    clause_results: List[ClauseResultSchema]

    model_config = {"from_attributes": True}
