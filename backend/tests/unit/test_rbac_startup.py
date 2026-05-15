import pytest

from app.domain.rbac import BASELINE_POLICY_RULES
from app.infra.rbac import RBACStartupError, validate_baseline_policies


class _FakeResult:
    def __init__(self, rows: list[tuple[str, str, str]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[str, str, str]]:
        return self._rows


class _FakeSession:
    def __init__(self, rows: list[tuple[str, str, str]]) -> None:
        self._rows = rows

    async def execute(self, statement) -> _FakeResult:
        return _FakeResult(self._rows)


@pytest.mark.asyncio
async def test_validate_baseline_policies_accepts_expected_policy_rows() -> None:
    await validate_baseline_policies(_FakeSession(list(BASELINE_POLICY_RULES)))


@pytest.mark.asyncio
async def test_validate_baseline_policies_rejects_empty_policy_table() -> None:
    with pytest.raises(RBACStartupError, match="Missing baseline Casbin policies"):
        await validate_baseline_policies(_FakeSession([]))


@pytest.mark.asyncio
async def test_validate_baseline_policies_rejects_missing_policy_row() -> None:
    rows = list(BASELINE_POLICY_RULES)
    rows.pop()

    with pytest.raises(RBACStartupError, match="p,"):
        await validate_baseline_policies(_FakeSession(rows))
