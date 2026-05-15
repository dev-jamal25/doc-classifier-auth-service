import importlib
from typing import Any

import sqlalchemy as sa


def _migration_module() -> Any:
    return importlib.import_module("app.db.migrations.versions.20260515_0003_add_casbin_rule_table")


class _FakeOp:
    def __init__(self) -> None:
        self.tables: list[tuple[str, tuple[sa.Column, ...]]] = []
        self.indexes: list[dict[str, Any]] = []
        self.bulk_inserts: list[tuple[Any, list[dict[str, str]]]] = []

    def create_table(self, name: str, *columns: sa.Column) -> None:
        self.tables.append((name, columns))

    def create_index(
        self,
        name: str,
        table_name: str,
        columns: list[Any],
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

    def bulk_insert(self, table: Any, rows: list[dict[str, str]]) -> None:
        self.bulk_inserts.append((table, rows))


def test_casbin_migration_revision_chain() -> None:
    module = _migration_module()

    assert module.revision == "20260515_0003"
    assert module.down_revision == "20260514_0002"


def test_casbin_migration_creates_adapter_table_and_baseline_policies(monkeypatch) -> None:
    module = _migration_module()
    fake_op = _FakeOp()
    monkeypatch.setattr(module, "op", fake_op)

    module.upgrade()

    table_name, columns = fake_op.tables[0]
    assert table_name == "casbin_rule"
    assert [column.name for column in columns] == [
        "id",
        "ptype",
        "v0",
        "v1",
        "v2",
        "v3",
        "v4",
        "v5",
    ]
    assert fake_op.indexes[0]["name"] == "uq_casbin_rule_policy"
    assert fake_op.indexes[0]["unique"] is True
    inserted_rows = fake_op.bulk_inserts[0][1]
    assert len(inserted_rows) == 10
    assert {"ptype": "p", "v0": "admin", "v1": "users", "v2": "manage_roles"} in inserted_rows
    assert all(row["ptype"] == "p" for row in inserted_rows)
