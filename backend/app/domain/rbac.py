from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class Role(StrEnum):
    ADMIN = "admin"
    REVIEWER = "reviewer"
    AUDITOR = "auditor"


class Permission(StrEnum):
    BATCHES_READ = "batches:read"
    PREDICTIONS_READ = "predictions:read"
    PREDICTIONS_RELABEL = "predictions:relabel"
    AUDIT_READ = "audit:read"
    USERS_MANAGE_ROLES = "users:manage_roles"

    @property
    def obj(self) -> str:
        return self.value.split(":", maxsplit=1)[0]

    @property
    def act(self) -> str:
        return self.value.split(":", maxsplit=1)[1]


BASELINE_ROLE_PERMISSIONS: dict[Role, tuple[Permission, ...]] = {
    Role.ADMIN: (
        Permission.BATCHES_READ,
        Permission.PREDICTIONS_READ,
        Permission.AUDIT_READ,
        Permission.USERS_MANAGE_ROLES,
    ),
    Role.REVIEWER: (
        Permission.BATCHES_READ,
        Permission.PREDICTIONS_READ,
        Permission.PREDICTIONS_RELABEL,
    ),
    Role.AUDITOR: (
        Permission.BATCHES_READ,
        Permission.PREDICTIONS_READ,
        Permission.AUDIT_READ,
    ),
}


BASELINE_POLICY_RULES: tuple[tuple[str, str, str], ...] = tuple(
    (role.value, permission.obj, permission.act)
    for role, permissions in BASELINE_ROLE_PERMISSIONS.items()
    for permission in permissions
)


def role_sort_key(role: str) -> int:
    ordered_roles = [item.value for item in Role]
    try:
        return ordered_roles.index(role)
    except ValueError:
        return len(ordered_roles)


def known_roles(role_names: list[str]) -> list[Role]:
    roles: list[Role] = []
    for role_name in role_names:
        try:
            roles.append(Role(role_name))
        except ValueError:
            continue
    return sorted(roles, key=lambda role: role_sort_key(role.value))


class UserRoles(BaseModel):
    user_id: UUID
    roles: list[Role]
    changed: bool = False
