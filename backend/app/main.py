"""Application factory and the ASGI entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.core.config import get_settings


def create_app() -> FastAPI:
    """Assemble the application.

    A factory rather than a module-level app so that tests can build an
    instance per configuration instead of mutating a shared one.
    """
    settings = get_settings()
    app = FastAPI(title="SIGI", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    return app


app = create_app()
