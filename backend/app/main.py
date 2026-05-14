from fastapi import FastAPI

from app.api.routers.admin import router as admin_router
from app.api.routers.auth import router as auth_router
from app.api.routers.batches import router as batches_router
from app.api.routers.health import router as health_router
from app.api.routers.predictions import router as predictions_router
from app.core.lifespan import build_fastapi_lifespan


def create_app() -> FastAPI:
    app = FastAPI(
        title="doc-classifier-auth-service",
        lifespan=build_fastapi_lifespan("api"),
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(batches_router)
    app.include_router(predictions_router)
    app.include_router(admin_router)
    return app


app = create_app()
