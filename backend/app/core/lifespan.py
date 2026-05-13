from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.infra.vault import VaultSecrets, load_secrets


@dataclass(slots=True)
class AppContext:
    settings: Settings
    secrets: VaultSecrets


@asynccontextmanager
async def lifespan(service_name: str) -> AsyncIterator[AppContext]:
    settings = get_settings()
    configure_logging(settings, service=service_name)
    secrets = load_secrets(settings)
    yield AppContext(settings=settings, secrets=secrets)


def build_fastapi_lifespan(service_name: str):
    @asynccontextmanager
    async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
        async with lifespan(service_name):
            yield

    return _lifespan
