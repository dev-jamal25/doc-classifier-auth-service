from __future__ import annotations

from typing import Protocol
from uuid import UUID


class ServiceCacheInvalidator(Protocol):
    async def invalidate_user_profile(self, user_id: UUID) -> None: ...

    async def invalidate_batches_list(self) -> None: ...

    async def invalidate_batch_detail(self, batch_id: UUID) -> None: ...

    async def invalidate_predictions_recent(self) -> None: ...


class NoOpServiceCacheInvalidator:
    async def invalidate_user_profile(self, user_id: UUID) -> None:
        return None

    async def invalidate_batches_list(self) -> None:
        return None

    async def invalidate_batch_detail(self, batch_id: UUID) -> None:
        return None

    async def invalidate_predictions_recent(self) -> None:
        return None
