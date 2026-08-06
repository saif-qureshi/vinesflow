from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ManufacturerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class ManufacturerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class ManufacturerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    is_active: bool
    created_at: datetime


class ManufacturerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
