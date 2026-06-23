from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ColumnType(str, Enum):
    STRING    = "string"
    INTEGER   = "integer"
    FLOAT     = "float"
    BOOLEAN   = "boolean"
    DATE      = "date"
    TIMESTAMP = "timestamp"
    DECIMAL   = "decimal"


class ColumnSpec(BaseModel):
    name:           str
    type:           ColumnType
    nullable:       bool = True
    description:    Optional[str] = None
    allowed_values: Optional[List[str]] = None


class SchemaSpec(BaseModel):
    enforce_no_extra_columns: bool = False
    columns: List[ColumnSpec]


class FreshnessSpec(BaseModel):
    max_age_hours: float
    check_column:  Optional[str] = None


class VolumeSpec(BaseModel):
    min_rows: Optional[int] = None
    max_rows: Optional[int] = None


class QualityRule(BaseModel):
    column:                   str
    max_null_percentage:      Optional[float] = None
    max_duplicate_percentage: Optional[float] = None
    min_value:                Optional[float] = None
    max_value:                Optional[float] = None


class ConsumerSpec(BaseModel):
    team:          str
    email:         str
    slack_webhook: Optional[str] = None


class OwnerSpec(BaseModel):
    team:  str
    email: str


class MetadataSpec(BaseModel):
    name:        str
    version:     str
    description: Optional[str] = None
    owner:       OwnerSpec
    tags:        List[str] = []


class DatasetSpec(BaseModel):
    format:            Literal["parquet", "sql"]
    location:          Optional[str] = None
    catalog_uri:       Optional[str] = None
    catalog_type:      Optional[str] = None
    namespace:         Optional[str] = None
    table_name:        Optional[str] = None
    connection_string: Optional[str] = None
    partition_column:  Optional[str] = None


class WebhookSpec(BaseModel):
    url:     str
    headers: Dict[str, str] = {}


class EmailSpec(BaseModel):
    smtp_host:         str
    smtp_port:         int = 587
    smtp_user:         str
    smtp_password_env: str
    recipients:        List[str] = []


class NotificationsSpec(BaseModel):
    webhook: Optional[WebhookSpec] = None
    email:   Optional[EmailSpec]   = None


class DataContract(BaseModel):
    apiVersion: Literal["datacontract/v1"]
    kind:       Literal["DataContract"]
    metadata:   MetadataSpec
    dataset:    DatasetSpec
    on_breach:  Literal["warn", "fail"] = "warn"
    consumers:  List[ConsumerSpec]           = []
    schema_:    Optional[SchemaSpec]         = Field(None, alias="schema")
    freshness:  Optional[FreshnessSpec]      = None
    volume:     Optional[VolumeSpec]         = None
    quality:    List[QualityRule]            = []
    notifications: Optional[NotificationsSpec] = None

    model_config = {"populate_by_name": True}
