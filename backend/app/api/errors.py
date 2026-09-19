"""Domain exception → the error envelope in `api-conventions.md`.

`CLAUDE.md` forbids raising `HTTPException` below the API layer. This is the
other half of that rule: without it the first route would have to break it.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.correlation import current
from app.services.errors import DomainError


def register_handlers(app: FastAPI) -> None:
    """Map domain exceptions onto the envelope in `api-conventions.md`."""

    @app.exception_handler(DomainError)
    async def _handle(request: Request, exc: DomainError) -> JSONResponse:
        body: dict[str, object] = {
            "code": exc.code,
            "message": exc.mensagem,
            "correlation_id": str(current()),
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
        fields = {_field(error.get("loc", ())): str(error.get("msg", "")) for error in exc.errors()}
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "DADOS_INVALIDOS",
                    "message": "Verifique os fields destacados.",
                    "fields": fields,
                    "correlation_id": str(current()),
                }
            },
        )


def _field(loc: object) -> str:
    """Name the field the way the client named it.

    Drops the "body" or "query" prefix: the client knows where it sent the
    field, and the UI binds errors by the field's own name.
    """
    parts = [str(p) for p in loc] if isinstance(loc, list | tuple) else [str(loc)]
    if parts and parts[0] in ("body", "query", "path", "header", "cookie"):
        parts = parts[1:]
    return ".".join(parts) or "_"
