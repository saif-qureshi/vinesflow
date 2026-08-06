from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MediaCreate(BaseModel):
    storage_key: str = Field(min_length=1, max_length=512)
    filename: str | None = Field(default=None, max_length=255)
    content_type: str | None = Field(default=None, max_length=100)
    size: int | None = None
    sort_order: int = 0


class MediaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    storage_key: str
    url: str
    filename: str | None = None
    content_type: str | None = None
    size: int | None = None
    sort_order: int


class MediaUploadResult(BaseModel):
    url: str
    storage_key: str
    filename: str | None = None
    content_type: str | None = None
    size: int
