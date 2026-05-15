from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

logger = logging.getLogger(__name__)

CACHE_PREFIX = "doc-classifier"

CACHE_NAMESPACE_ME = "me"
CACHE_NAMESPACE_BATCHES_LIST = "batches:list"
CACHE_NAMESPACE_BATCHES_DETAIL = "batches:detail"
CACHE_NAMESPACE_PREDICTIONS_RECENT = "predictions:recent"

CACHE_TTL_ME_SECONDS = 300
CACHE_TTL_BATCHES_SECONDS = 60
CACHE_TTL_PREDICTIONS_SECONDS = 60


def user_profile_cache_key(user_id: UUID) -> str:
    return f"{CACHE_PREFIX}:{CACHE_NAMESPACE_ME}:{user_id}"


def batch_detail_cache_key(batch_id: UUID) -> str:
    return _request_cache_key(
        namespace=f"{CACHE_PREFIX}:{CACHE_NAMESPACE_BATCHES_DETAIL}",
        method="GET",
        path=f"/batches/{batch_id}",
        query_items=(),
    )


def api_cache_key_builder(
    func: Any,
    namespace: str = "",
    *,
    request: Any = None,
    response: Any = None,
    args: tuple[Any, ...] | None = None,
    kwargs: dict[str, Any] | None = None,
) -> str:
    del response
    kwargs = kwargs or {}

    if namespace.endswith(f":{CACHE_NAMESPACE_ME}"):
        user = kwargs.get("user")
        user_id = getattr(user, "id", None)
        if user_id is not None:
            return user_profile_cache_key(user_id)

        # Safety fallback: /me should always receive a resolved user dependency,
        # but never let profile cache entries collapse into one shared key.
        authorization = ""
        if request is not None:
            authorization = request.headers.get("authorization", "")
        digest = hashlib.sha256(authorization.encode("utf-8")).hexdigest()
        return f"{namespace}:auth:{digest}"

    if request is None:
        return f"{namespace}:{func.__module__}.{func.__qualname__}:{args!r}:{kwargs!r}"

    return _request_cache_key(
        namespace=namespace,
        method=request.method,
        path=request.url.path,
        query_items=sorted(request.query_params.multi_items()),
    )


async def initialize_api_cache(redis_url: str):
    from fastapi_cache import FastAPICache
    from fastapi_cache.backends.redis import RedisBackend
    from redis import asyncio as aioredis

    redis = aioredis.from_url(redis_url)
    try:
        await redis.ping()
    except Exception:
        await redis.aclose()
        raise
    FastAPICache.init(
        RedisBackend(redis),
        prefix=CACHE_PREFIX,
        key_builder=api_cache_key_builder,
    )
    return redis


class RedisServiceCacheInvalidator:
    def __init__(self, redis_url: str) -> None:
        from redis import asyncio as aioredis

        self._redis = aioredis.from_url(redis_url)

    async def close(self) -> None:
        await self._redis.aclose()

    async def invalidate_user_profile(self, user_id: UUID) -> None:
        await self._delete_key(user_profile_cache_key(user_id))

    async def invalidate_batches_list(self) -> None:
        await self._delete_namespace(CACHE_NAMESPACE_BATCHES_LIST)

    async def invalidate_batch_detail(self, batch_id: UUID) -> None:
        await self._delete_key(batch_detail_cache_key(batch_id))

    async def invalidate_predictions_recent(self) -> None:
        await self._delete_namespace(CACHE_NAMESPACE_PREDICTIONS_RECENT)

    async def _delete_namespace(self, namespace: str) -> None:
        await self._delete_pattern(f"{CACHE_PREFIX}:{namespace}:*")

    async def _delete_pattern(self, pattern: str) -> None:
        keys: list[bytes | str] = []
        try:
            async for key in self._redis.scan_iter(match=pattern, count=100):
                keys.append(key)
                if len(keys) >= 100:
                    await self._redis.delete(*keys)
                    keys.clear()
            if keys:
                await self._redis.delete(*keys)
        except Exception:
            logger.warning(
                "Cache namespace invalidation failed.",
                exc_info=True,
                extra={"event": "cache_invalidation_failed", "pattern": pattern},
            )

    async def _delete_key(self, key: str) -> None:
        try:
            await self._redis.delete(key)
        except Exception:
            logger.warning(
                "Cache key invalidation failed.",
                exc_info=True,
                extra={"event": "cache_invalidation_failed", "cache_key": key},
            )


def _request_cache_key(
    *,
    namespace: str,
    method: str,
    path: str,
    query_items: Iterable[tuple[str, str]],
) -> str:
    query = urlencode(tuple(query_items))
    return f"{namespace}:{method.lower()}:{path}:{query}"
