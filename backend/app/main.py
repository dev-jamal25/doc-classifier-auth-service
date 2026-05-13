from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routers.health import router as health_router
from app.core.config import get_settings
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings, service="api")
    # TODO(startup-checks): enforce Vault/Casbin/classifier readiness checks from ARCH.md.
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="doc-classifier-auth-service", lifespan=lifespan)
    app.include_router(health_router)
    return app


app = create_app()
