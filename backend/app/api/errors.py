"""Domain exception → the error envelope in `api-conventions.md`.

`CLAUDE.md` forbids raising `HTTPException` below the API layer. This is the
other half of that rule: without it the first route would have to break it.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, Final

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.constants.atas import PROCESSO_SEI_INVALIDO_CODE
from app.core.correlation import current
from app.services.errors import DomainError

# Domain checks that run in a schema, and the code each keeps when it fails alone.
_SCHEMA_CODES: Final = MappingProxyType({**PROCESSO_SEI_INVALIDO_CODE})


def register_handlers(app: FastAPI) -> None:
    """Map domain exceptions onto the envelope in `api-conventions.md`."""

    @app.exception_handler(DomainError)
    async def _handle(request: Request, exc: DomainError) -> JSONResponse:
        body: dict[str, object] = {
            "code": exc.code,
            "message": exc.message_text,
            "correlation_id": str(current()),
        }
        # `fields` drives inline per-field errors in the UI, which is the stated
        # mitigation for the transcription errors that motivated the project. It
        # is omitted rather than sent empty so the client can branch on presence.
        if exc.fields:
            body["fields"] = exc.fields
        body.update(exc.extra)
        headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else None
        return JSONResponse(status_code=exc.http, content={"error": body}, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        """FastAPI's own 422 body has a different shape from every other error.

        `api-conventions.md` says errors *always* use one envelope, and `fields`
        is the stated mitigation for the transcription errors that motivated the
        project — a client that has to parse two shapes ends up parsing neither.
        """
        errors = exc.errors()
        fields = {_field(error.get("loc", ())): _message(error) for error in errors}
        code, message = "INVALID_DATA", "Verifique os campos destacados."
        # A domain check that runs in the schema, so that it is reported with
        # the other fields, keeps its own code when it is the only failure.
        if len(errors) == 1 and errors[0].get("type") in _SCHEMA_CODES:
            code, message = _SCHEMA_CODES[errors[0]["type"]], _message(errors[0])
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "fields": fields,
                    "correlation_id": str(current()),
                }
            },
        )


def _message(error: Mapping[str, Any]) -> str:
    """Say what is wrong with a field in pt-BR, for the servidor (ADR-0013).

    Pydantic's own `msg` is English and addressed to a developer; passing it
    through put "value is not a valid email address" on the invite dialog.
    """
    kind = str(error.get("type", ""))
    context = error.get("ctx") or {}
    if kind == "missing":
        return "Campo obrigatório."
    if kind == "string_too_short":
        return "Campo obrigatório." if context.get("min_length") == 1 else "Texto curto demais."
    if kind == "string_too_long":
        return f"Use no máximo {context.get('max_length')} caracteres."
    if kind == "value_error" and "email" in str(error.get("msg", "")).lower():
        return "E-mail inválido."
    if kind == "string_pattern_mismatch":
        return "Valor não permitido."
    if kind == "greater_than":
        return "Informe um valor maior que zero."
    if kind == "decimal_max_places":
        return f"Use no máximo {context.get('decimal_places')} casas decimais."
    if kind == "decimal_max_digits":
        return f"Use no máximo {context.get('max_digits')} dígitos."
    if kind == "decimal_whole_digits":
        return f"Use no máximo {context.get('whole_digits')} dígitos antes da vírgula."
    if kind in _SCHEMA_CODES:
        return str(error.get("msg", ""))
    if kind.startswith("date"):
        return "Data inválida."
    return "Valor inválido."


def _field(loc: object) -> str:
    """Name the field the way the client named it.

    Drops the "body" or "query" prefix: the client knows where it sent the
    field, and the UI binds errors by the field's own name.
    """
    parts = [str(p) for p in loc] if isinstance(loc, list | tuple) else [str(loc)]
    if parts and parts[0] in ("body", "query", "path", "header", "cookie"):
        parts = parts[1:]
    return ".".join(parts) or "_"
