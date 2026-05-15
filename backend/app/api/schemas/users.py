from __future__ import annotations

from uuid import UUID

from fastapi_users import schemas
from pydantic import ConfigDict, Field


class UserRead(schemas.BaseUser[UUID]):
    model_config = ConfigDict(from_attributes=True)

    roles: list[str] = Field(default_factory=list)


class UserCreate(schemas.BaseUserCreate):
    pass
