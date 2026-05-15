from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.infra.vault import VaultSecrets, load_secrets


@dataclass(slots=True)
class AppContext:
    settings: Settings
    secrets: VaultSecrets


async def validate_api_startup() -> None:
    from app.db.session import async_session_factory
    from app.infra.rbac import validate_baseline_policies

    async with async_session_factory() as session:
        await validate_baseline_policies(session)


@asynccontextmanager
async def lifespan(service_name: str) -> AsyncIterator[AppContext]:
    settings = get_settings()
    configure_logging(settings, service=service_name)
    secrets = load_secrets(settings)
    if service_name == "api":
        await validate_api_startup()
    yield AppContext(settings=settings, secrets=secrets)


def build_fastapi_lifespan(service_name: str):
    from fastapi import FastAPI

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with lifespan(service_name) as context:
            app.state.context = context
            yield

    return _lifespan
