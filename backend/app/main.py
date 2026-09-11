from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, health
from app.api.erros import registrar_tratadores
from app.core.config import get_settings
from app.core.correlacao import CorrelacaoMiddleware


def create_app() -> FastAPI:
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

    registrar_tratadores(app)

    app.include_router(health.router)
    app.include_router(auth.router)
    return app


app = create_app()
