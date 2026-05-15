from uuid import uuid4

import casbin
from casbin import persist

from app.db.models import CasbinRule
from app.domain.rbac import BASELINE_POLICY_RULES, Permission, Role
from app.infra.rbac import RBAC_MODEL_PATH


def _enforcer_with_baseline_policy() -> casbin.Enforcer:
    enforcer = casbin.Enforcer(str(RBAC_MODEL_PATH))
    for role, obj, act in BASELINE_POLICY_RULES:
        enforcer.add_policy(role, obj, act)
    return enforcer


def test_admin_policy_allows_admin_permissions() -> None:
    user_id = str(uuid4())
    enforcer = _enforcer_with_baseline_policy()
    enforcer.add_role_for_user(user_id, Role.ADMIN.value)

    assert enforcer.enforce(user_id, Permission.BATCHES_READ.obj, Permission.BATCHES_READ.act)
    assert enforcer.enforce(
        user_id,
        Permission.PREDICTIONS_READ.obj,
        Permission.PREDICTIONS_READ.act,
    )
    assert enforcer.enforce(user_id, Permission.AUDIT_READ.obj, Permission.AUDIT_READ.act)
    assert enforcer.enforce(
        user_id,
        Permission.USERS_MANAGE_ROLES.obj,
        Permission.USERS_MANAGE_ROLES.act,
    )


def test_reviewer_policy_allows_reads_and_relabel_but_not_audit() -> None:
    user_id = str(uuid4())
    enforcer = _enforcer_with_baseline_policy()
    enforcer.add_role_for_user(user_id, Role.REVIEWER.value)

    assert enforcer.enforce(user_id, Permission.BATCHES_READ.obj, Permission.BATCHES_READ.act)
    assert enforcer.enforce(
        user_id,
        Permission.PREDICTIONS_READ.obj,
        Permission.PREDICTIONS_READ.act,
    )
    assert enforcer.enforce(
        user_id,
        Permission.PREDICTIONS_RELABEL.obj,
        Permission.PREDICTIONS_RELABEL.act,
    )
    assert not enforcer.enforce(user_id, Permission.AUDIT_READ.obj, Permission.AUDIT_READ.act)


def test_auditor_policy_allows_read_only_audit_access() -> None:
    user_id = str(uuid4())
    enforcer = _enforcer_with_baseline_policy()
    enforcer.add_role_for_user(user_id, Role.AUDITOR.value)

    assert enforcer.enforce(user_id, Permission.BATCHES_READ.obj, Permission.BATCHES_READ.act)
    assert enforcer.enforce(
        user_id,
        Permission.PREDICTIONS_READ.obj,
        Permission.PREDICTIONS_READ.act,
    )
    assert enforcer.enforce(user_id, Permission.AUDIT_READ.obj, Permission.AUDIT_READ.act)
    assert not enforcer.enforce(
        user_id,
        Permission.USERS_MANAGE_ROLES.obj,
        Permission.USERS_MANAGE_ROLES.act,
    )


def test_user_without_grouping_policy_is_denied() -> None:
    user_id = str(uuid4())
    enforcer = _enforcer_with_baseline_policy()

    assert not enforcer.enforce(user_id, Permission.BATCHES_READ.obj, Permission.BATCHES_READ.act)


def test_serialized_casbin_rule_rows_load_p_and_g_policies() -> None:
    user_id = str(uuid4())
    enforcer = casbin.Enforcer(str(RBAC_MODEL_PATH))
    policy_row = CasbinRule(ptype="p", v0="admin", v1="batches", v2="read")
    grouping_row = CasbinRule(ptype="g", v0=user_id, v1="admin")

    persist.load_policy_line(str(policy_row), enforcer.model)
    persist.load_policy_line(str(grouping_row), enforcer.model)
    enforcer.build_role_links()

    assert enforcer.enforce(user_id, "batches", "read")
