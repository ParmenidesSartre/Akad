from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class ColumnType(StrEnum):
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
    description:    str | None = None
    allowed_values: list[str] | None = None


class SchemaSpec(BaseModel):
    enforce_no_extra_columns: bool = False
    columns: list[ColumnSpec]


class FreshnessSpec(BaseModel):
    max_age_hours: float
    check_column:  str | None = None


class VolumeSpec(BaseModel):
    min_rows: int | None = None
    max_rows: int | None = None


class QualityRule(BaseModel):
    column:                   str
    max_null_percentage:      float | None = None
    max_duplicate_percentage: float | None = None
    min_value:                float | None = None
    max_value:                float | None = None


class ConsumerSpec(BaseModel):
    team:          str
    email:         str
    slack_webhook: str | None = None


class OwnerSpec(BaseModel):
    team:  str
    email: str


class MetadataSpec(BaseModel):
    name:        str
    version:     str
    description: str | None = None
    owner:       OwnerSpec
    tags:        list[str] = []


class DatasetSpec(BaseModel):
    format:            Literal["parquet", "sql"]
    location:          str | None = None
    catalog_uri:       str | None = None
    catalog_type:      str | None = None
    namespace:         str | None = None
    table_name:        str | None = None
    connection_string: str | None = None
    partition_column:  str | None = None


class WebhookSpec(BaseModel):
    url:     str
    headers: dict[str, str] = {}


class EmailSpec(BaseModel):
    smtp_host:         str
    smtp_port:         int = 587
    smtp_user:         str
    smtp_password_env: str
    recipients:        list[str] = []


class NotificationsSpec(BaseModel):
    webhook: WebhookSpec | None = None
    email:   EmailSpec | None   = None


class DataContract(BaseModel):
    apiVersion: Literal["datacontract/v1"]
    kind:       Literal["DataContract"]
    metadata:   MetadataSpec
    dataset:    DatasetSpec
    on_breach:  Literal["warn", "fail"] = "warn"
    consumers:  list[ConsumerSpec]           = []
    schema_:    SchemaSpec | None         = Field(None, alias="schema")
    freshness:  FreshnessSpec | None      = None
    volume:     VolumeSpec | None         = None
    quality:    list[QualityRule]            = []
    notifications: NotificationsSpec | None = None

    model_config = {"populate_by_name": True}
