from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

from app.infra.cache import CACHE_PREFIX, api_cache_key_builder


def init_test_cache() -> None:
    FastAPICache.reset()
    InMemoryBackend._store.clear()
    FastAPICache.init(
        InMemoryBackend(),
        prefix=CACHE_PREFIX,
        key_builder=api_cache_key_builder,
    )
