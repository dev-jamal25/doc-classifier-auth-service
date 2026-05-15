from uuid import UUID

from pydantic import BaseModel

from app.domain.rbac import Role, UserRoles


class UserRolesResponse(BaseModel):
    user_id: UUID
    roles: list[Role]
    changed: bool

    @classmethod
    def from_domain(cls, model: UserRoles) -> "UserRolesResponse":
        return cls(**model.model_dump())
