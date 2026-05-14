from __future__ import annotations

from uuid import UUID

from fastapi_users import schemas
from pydantic import ConfigDict


class UserRead(schemas.BaseUser[UUID]):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(schemas.BaseUserCreate):
    pass
