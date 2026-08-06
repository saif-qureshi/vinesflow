from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: str | None = None
    avatar_key: str | None = Field(default=None, max_length=512)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    is_active: bool | None = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    avatar_key: str | None = None
    avatar_url: str | None = None
    is_active: bool
    is_superuser: bool
    created_at: datetime
