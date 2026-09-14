"""Domain exception → the error envelope in `api-conventions.md`.

`CLAUDE.md` forbids raising `HTTPException` below the API layer. This is the
other half of that rule: without it the first route would have to break it.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.correlacao import atual
from app.services.erros import ErroDominio


def register_handlers(app: FastAPI) -> None:
    @app.exception_handler(ErroDominio)
    async def _tratar(request: Request, exc: ErroDominio) -> JSONResponse:
        body: dict[str, object] = {
            "code": exc.codigo,
            "message": exc.mensagem,
            "correlation_id": str(atual()),
        }
        # `fields` drives inline per-field errors in the UI, which is the stated
        # mitigation for the transcription errors that motivated the project. It
        # is omitted rather than sent empty so the client can branch on presence.
        if exc.campos:
            body["fields"] = exc.campos
        headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else None
        return JSONResponse(status_code=exc.http, content={"error": body}, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def _tratar_validacao(request: Request, exc: RequestValidationError) -> JSONResponse:
        """FastAPI's own 422 body has a different shape from every other error.

        `api-conventions.md` says errors *always* use one envelope, and `fields`
        is the stated mitigation for the transcription errors that motivated the
        project — a client that has to parse two shapes ends up parsing neither.
        """
        campos = {_campo(erro.get("loc", ())): str(erro.get("msg", "")) for erro in exc.errors()}
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "DADOS_INVALIDOS",
                    "message": "Verifique os campos destacados.",
                    "fields": campos,
                    "correlation_id": str(atual()),
                }
            },
        )


def _campo(loc: object) -> str:
    """Drop the "body"/"query" prefix: the client knows where it sent the field,
    and the UI binds errors by the field's own name."""
    partes = [str(p) for p in loc] if isinstance(loc, list | tuple) else [str(loc)]
    if partes and partes[0] in ("body", "query", "path", "header", "cookie"):
        partes = partes[1:]
    return ".".join(partes) or "_"
