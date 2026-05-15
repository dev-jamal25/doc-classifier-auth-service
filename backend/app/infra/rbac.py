from __future__ import annotations

from pathlib import Path

import casbin
from casbin_async_sqlalchemy_adapter import Adapter
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CasbinRule
from app.domain.rbac import BASELINE_POLICY_RULES

RBAC_MODEL_PATH = Path(__file__).resolve().parent.parent / "core" / "rbac_model.conf"


class RBACStartupError(RuntimeError):
    """Raised when Casbin policy startup checks fail."""


async def build_enforcer(session: AsyncSession) -> casbin.AsyncEnforcer:
    bind = session.bind
    if bind is None:
        raise RuntimeError("Cannot build Casbin enforcer from an unbound AsyncSession.")

    adapter = Adapter(bind, db_class=CasbinRule, db_session=session)
    enforcer = casbin.AsyncEnforcer(str(RBAC_MODEL_PATH), adapter)
    await enforcer.load_policy()
    return enforcer


async def validate_baseline_policies(session: AsyncSession) -> None:
    try:
        result = await session.execute(
            select(CasbinRule.v0, CasbinRule.v1, CasbinRule.v2).where(CasbinRule.ptype == "p")
        )
    except SQLAlchemyError as exc:
        raise RBACStartupError("Unable to read Casbin policy table at startup.") from exc

    present = {
        (role, obj, act)
        for role, obj, act in result.all()
        if role is not None and obj is not None and act is not None
    }
    expected = set(BASELINE_POLICY_RULES)
    missing = sorted(expected - present)
    if missing:
        formatted = ", ".join(f"p, {role}, {obj}, {act}" for role, obj, act in missing)
        raise RBACStartupError(f"Missing baseline Casbin policies: {formatted}.")
