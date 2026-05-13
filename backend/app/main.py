from fastapi import FastAPI

from app.api.routers.health import router as health_router
from app.core.lifespan import build_fastapi_lifespan


def create_app() -> FastAPI:
    app = FastAPI(
        title="doc-classifier-auth-service",
        lifespan=build_fastapi_lifespan("api"),
    )
    app.include_router(health_router)
    return app


app = create_app()
