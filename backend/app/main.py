from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, convites, health, oidc, usuarios
from app.api.erros import registrar_tratadores
from app.core.autorizacao import verificar_cobertura
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
    app.include_router(usuarios.router)
    app.include_router(convites.router)
    app.include_router(oidc.router)

    # AC-0001-23, na montagem: uma rota de escrita sem decisão de acesso quebra
    # aqui — no build e nos testes — em vez de servir a requisição.
    verificar_cobertura(app)
    return app


app = create_app()
