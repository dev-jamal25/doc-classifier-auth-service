"""add casbin rule table

Revision ID: 20260515_0003
Revises: 20260514_0002
Create Date: 2026-05-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260515_0003"
down_revision: str | None = "20260514_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


BASELINE_POLICY_ROWS: tuple[dict[str, str], ...] = (
    {"ptype": "p", "v0": "admin", "v1": "batches", "v2": "read"},
    {"ptype": "p", "v0": "admin", "v1": "predictions", "v2": "read"},
    {"ptype": "p", "v0": "admin", "v1": "audit", "v2": "read"},
    {"ptype": "p", "v0": "admin", "v1": "users", "v2": "manage_roles"},
    {"ptype": "p", "v0": "reviewer", "v1": "batches", "v2": "read"},
    {"ptype": "p", "v0": "reviewer", "v1": "predictions", "v2": "read"},
    {"ptype": "p", "v0": "reviewer", "v1": "predictions", "v2": "relabel"},
    {"ptype": "p", "v0": "auditor", "v1": "batches", "v2": "read"},
    {"ptype": "p", "v0": "auditor", "v1": "predictions", "v2": "read"},
    {"ptype": "p", "v0": "auditor", "v1": "audit", "v2": "read"},
)


def upgrade() -> None:
    op.create_table(
        "casbin_rule",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("ptype", sa.String(length=255), nullable=True),
        sa.Column("v0", sa.String(length=255), nullable=True),
        sa.Column("v1", sa.String(length=255), nullable=True),
        sa.Column("v2", sa.String(length=255), nullable=True),
        sa.Column("v3", sa.String(length=255), nullable=True),
        sa.Column("v4", sa.String(length=255), nullable=True),
        sa.Column("v5", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "uq_casbin_rule_policy",
        "casbin_rule",
        [
            sa.text("ptype"),
            sa.text("coalesce(v0, '')"),
            sa.text("coalesce(v1, '')"),
            sa.text("coalesce(v2, '')"),
            sa.text("coalesce(v3, '')"),
            sa.text("coalesce(v4, '')"),
            sa.text("coalesce(v5, '')"),
        ],
        unique=True,
    )

    casbin_rule = sa.table(
        "casbin_rule",
        sa.column("ptype", sa.String(length=255)),
        sa.column("v0", sa.String(length=255)),
        sa.column("v1", sa.String(length=255)),
        sa.column("v2", sa.String(length=255)),
    )
    op.bulk_insert(casbin_rule, list(BASELINE_POLICY_ROWS))


def downgrade() -> None:
    op.drop_index("uq_casbin_rule_policy", table_name="casbin_rule")
    op.drop_table("casbin_rule")
