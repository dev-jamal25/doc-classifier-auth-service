import importlib
from typing import Any

import sqlalchemy as sa


def _migration_module() -> Any:
    return importlib.import_module("app.db.migrations.versions.20260514_0002_add_users_table")


class _FakeOp:
    def __init__(self) -> None:
        self.tables: list[tuple[str, tuple[sa.Column, ...]]] = []
        self.indexes: list[dict[str, Any]] = []

    def create_table(self, name: str, *columns: sa.Column) -> None:
        self.tables.append((name, columns))

    def create_index(
        self,
        name: str,
        table_name: str,
        columns: list[str],
        *,
        unique: bool,
    ) -> None:
        self.indexes.append(
            {
                "name": name,
                "table_name": table_name,
                "columns": columns,
                "unique": unique,
            }
        )


def test_users_migration_revision_chain() -> None:
    module = _migration_module()

    assert module.revision == "20260514_0002"
    assert module.down_revision == "20260513_0001"


def test_users_migration_upgrade_creates_users_table(monkeypatch) -> None:
    module = _migration_module()
    fake_op = _FakeOp()
    monkeypatch.setattr(module, "op", fake_op)

    module.upgrade()

    assert len(fake_op.tables) == 1
    table_name, columns = fake_op.tables[0]
    assert table_name == "users"
    assert [column.name for column in columns] == [
        "id",
        "email",
        "hashed_password",
        "is_active",
        "is_superuser",
        "is_verified",
    ]
    assert fake_op.indexes == [
        {
            "name": "ix_users_email",
            "table_name": "users",
            "columns": ["email"],
            "unique": True,
        }
    ]
