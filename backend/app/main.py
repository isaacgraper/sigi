"""Application factory and the ASGI entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, health, oidc
from app.api.errors import register_handlers
from app.core.authorization import verify_coverage
from app.core.config import get_settings
from app.core.correlation import CorrelacaoMiddleware


def create_app() -> FastAPI:
    """Assemble the application.

    A factory rather than a module-level app so that tests can build an
    instance per configuration instead of mutating a shared one.
    """
    settings = get_settings()
    app = FastAPI(title="SIGI", version="0.1.0")

    # Outermost, so every response carries it — including the ones produced by
    # error handlers, which are exactly the responses somebody will be trying to
    # trace back to an audit row.
    app.add_middleware(CorrelacaoMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_handlers(app)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(oidc.router)

    # AC-0001-23, at assembly: a write route with no access decision breaks
    # here, in the build and in the tests, rather than serving the request.
    # Every router is included above first, or this would inspect a partial
    # route table and pass over what it never saw.
    verify_coverage(app)
    return app


app = create_app()
