from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserReadModel(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str = "user"
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=200)
    password: str = Field(..., min_length=6, max_length=200)
    role: str = Field(default="user", max_length=50)
    is_active: bool = True


class UserUpdateRequest(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    password: str | None = Field(default=None, min_length=6, max_length=200)
    role: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None
